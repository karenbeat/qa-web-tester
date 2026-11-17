#!/usr/bin/env python3
"""
Auditoria de site: links, tempo de carregamento e responsividade.

Complementa o runner.py. Enquanto o runner testa validação de formulário
(preenche campo, clica, julga), este script audita a página como um todo:

  1. LINKS         — coleta todos os <a href> e confere o status HTTP de cada um
  2. PERFORMANCE   — mede TTFB, DOMContentLoaded, load e First Contentful Paint
  3. RESPONSIVIDADE— renderiza em desktop, tablet e mobile, detecta overflow
                     horizontal, texto pequeno demais e alvos de toque pequenos

Instalação:
    pip install playwright
    python -m playwright install chromium

Uso:
    python auditor.py https://exemplo.com.br
    python auditor.py https://exemplo.com.br --saida audit --visivel
    python auditor.py https://exemplo.com.br --max-links 50 --so-internos
    python auditor.py --lote sites.txt --saida audit-lote

USO RESPONSÁVEL
---------------
Verificar links gera uma requisição por link. Num e-commerce com centenas de
links isso é tráfego real no servidor de alguém. Só rode contra sites que você
possui ou tem autorização para testar, use --max-links para limitar o volume, e
mantenha o --intervalo se o site for de produção.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass


VIEWPORTS = [
    {"nome": "desktop", "largura": 1920, "altura": 1080, "mobile": False},
    {"nome": "tablet",  "largura": 768,  "altura": 1024, "mobile": True},
    {"nome": "mobile",  "largura": 390,  "altura": 844,  "mobile": True},
]

# Referências de performance. Não são regras absolutas — servem para dar
# contexto ao número, não para reprovar um site automaticamente.
LIMITES_MS = {"bom": 2500, "aceitavel": 4000}


# ------------------------------------------------------------- Performance

def medir_performance(page, url):
    """Mede os tempos de carregamento usando a Navigation Timing API do navegador."""
    inicio = time.time()
    erro = None
    try:
        page.goto(url, wait_until="load", timeout=60000)
    except PWTimeout:
        erro = "timeout de 60s ao carregar a página"
    except Exception as e:
        erro = f"{type(e).__name__}: {e}"

    total_medido = round((time.time() - inicio) * 1000)

    metricas = {}
    try:
        metricas = page.evaluate("""() => {
            const n = performance.getEntriesByType('navigation')[0];
            const paint = performance.getEntriesByType('paint');
            const fcp = paint.find(p => p.name === 'first-contentful-paint');
            if (!n) return {};
            return {
                ttfb: Math.round(n.responseStart - n.requestStart),
                dom_interativo: Math.round(n.domInteractive),
                dom_carregado: Math.round(n.domContentLoadedEventEnd),
                carregamento_total: Math.round(n.loadEventEnd),
                fcp: fcp ? Math.round(fcp.startTime) : null,
                transferido_kb: n.transferSize ? Math.round(n.transferSize / 1024) : null
            };
        }""")
    except Exception:
        pass

    recursos = {}
    try:
        recursos = page.evaluate("""() => {
            const r = performance.getEntriesByType('resource');
            const porTipo = {};
            let totalBytes = 0;
            for (const x of r) {
                const t = x.initiatorType || 'outro';
                porTipo[t] = (porTipo[t] || 0) + 1;
                totalBytes += x.transferSize || 0;
            }
            const pesados = r
                .filter(x => x.transferSize > 200000)
                .sort((a, b) => b.transferSize - a.transferSize)
                .slice(0, 5)
                .map(x => ({url: x.name.split('?')[0].slice(-90),
                            kb: Math.round(x.transferSize / 1024)}));
            return {quantidade: r.length, por_tipo: porTipo,
                    total_kb: Math.round(totalBytes / 1024), pesados};
        }""")
    except Exception:
        pass

    tempo = metricas.get("carregamento_total") or total_medido
    if tempo <= LIMITES_MS["bom"]:
        veredito = "bom"
    elif tempo <= LIMITES_MS["aceitavel"]:
        veredito = "aceitável"
    else:
        veredito = "lento"

    return {
        "erro": erro,
        "tempo_total_medido_ms": total_medido,
        "metricas": metricas,
        "recursos": recursos,
        "veredito": veredito,
    }


# ------------------------------------------------------------- Links

def coletar_links(page, base_url):
    """Coleta os links da página, normalizados e sem duplicatas."""
    try:
        brutos = page.evaluate("""() => Array.from(document.querySelectorAll('a[href]'))
            .map(a => ({href: a.getAttribute('href'),
                        texto: (a.innerText || a.getAttribute('aria-label') || '').trim().slice(0, 60),
                        visivel: a.offsetParent !== null}))""")
    except Exception:
        return []

    dominio_base = urlparse(base_url).netloc
    vistos, links = set(), []

    for l in brutos:
        href = (l.get("href") or "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:", "data:", "whatsapp:")):
            continue
        absoluto = urljoin(base_url, href).split("#")[0]
        if absoluto in vistos:
            continue
        vistos.add(absoluto)
        links.append({
            "url": absoluto,
            "texto": l.get("texto") or "(sem texto)",
            "visivel": l.get("visivel", True),
            "interno": urlparse(absoluto).netloc == dominio_base,
        })
    return links


def verificar_links(contexto, links, intervalo, mostrar_progresso=True):
    """
    Confere o status HTTP de cada link.

    Usa o contexto do navegador em vez de requests para herdar cookies e
    cabeçalhos — muitos e-commerces bloqueiam cliente HTTP sem sessão, o que
    geraria uma enxurrada de falsos 403.
    """
    resultados = []
    total = len(links)

    for i, link in enumerate(links, 1):
        if mostrar_progresso and (i % 10 == 0 or i == total):
            print(f"    link {i}/{total}", flush=True)

        status, erro, redirecionou = None, None, False
        try:
            r = contexto.request.get(link["url"], timeout=20000, max_redirects=5)
            status = r.status
            redirecionou = r.url.split("#")[0] != link["url"]
            destino_final = r.url
        except Exception as e:
            erro = f"{type(e).__name__}: {str(e)[:120]}"
            destino_final = None

        if erro:
            situacao = "ERRO"
        elif status >= 500:
            situacao = "QUEBRADO"
        elif status >= 400:
            situacao = "QUEBRADO"
        elif status >= 300:
            situacao = "REDIRECIONA"
        else:
            situacao = "OK"

        resultados.append({**link, "status": status, "situacao": situacao,
                           "erro": erro, "redirecionou": redirecionou,
                           "destino_final": destino_final})
        if intervalo:
            time.sleep(intervalo)

    return resultados


# ------------------------------------------------------------- Responsividade

def fechar_banners(page):
    """
    Fecha banner de cookies/LGPD antes de medir layout.

    Em site brasileiro isso é quase obrigatório: o banner cobre a tela, arruína o
    screenshot de responsividade e frequentemente usa position:fixed com largura
    maior que a viewport, gerando falso positivo de overflow horizontal.

    Tenta seletores comuns das plataformas de consentimento mais usadas, depois
    cai para busca por texto de botão. Silencioso se não achar nada.
    """
    seletores = [
        "#onetrust-accept-btn-handler",
        ".onetrust-close-btn-handler",
        "#cookie-accept", "#aceitar-cookies", "#btn-aceitar-cookies",
        "[id*='lgpd'] button", "[class*='lgpd'] button",
        "[class*='cookie'] button[class*='accept']",
        "[class*='cookie'] button[class*='aceit']",
        "[id*='cookie'] button",
        ".cc-allow", ".cc-dismiss", "#cookiescript_accept",
        "button[aria-label*='ceitar']", "button[aria-label*='echar']",
    ]
    for sel in seletores:
        try:
            el = page.locator(sel).first
            if el.count() and el.is_visible():
                el.click(timeout=2500)
                page.wait_for_timeout(600)
                return sel
        except Exception:
            continue

    # Fallback por texto do botão
    for texto in ["Aceitar todos", "Aceitar tudo", "Aceitar", "Concordo",
                  "Entendi", "OK, entendi", "Prosseguir"]:
        try:
            el = page.get_by_role("button", name=texto, exact=False).first
            if el.count() and el.is_visible():
                el.click(timeout=2500)
                page.wait_for_timeout(600)
                return f"texto:{texto}"
        except Exception:
            continue
    return None


def rolar_pagina(page):
    """
    Rola até o fim e volta ao topo, para disparar lazy loading.

    Sem isto, imagens e seções abaixo da dobra nunca carregam, e o relatório
    mede uma página pela metade — em e-commerce, que é quase todo lazy loaded,
    a diferença é grande.
    """
    try:
        page.evaluate("""async () => {
            const passo = window.innerHeight * 0.8;
            const altura = document.body.scrollHeight;
            for (let y = 0; y < altura; y += passo) {
                window.scrollTo(0, y);
                await new Promise(r => setTimeout(r, 180));
            }
            window.scrollTo(0, 0);
            await new Promise(r => setTimeout(r, 400));
        }""")
    except Exception:
        pass


def testar_responsividade(navegador, url, saida, nome_site, visivel, rolar=True):
    """
    Renderiza em três larguras e procura problemas objetivos de layout.

    Os checados aqui são os que dá para automatizar com confiança: overflow
    horizontal, texto pequeno demais e alvos de toque pequenos. Alinhamento,
    hierarquia visual e estética continuam precisando de olho humano — por isso
    os screenshots.
    """
    achados = []

    for vp in VIEWPORTS:
        contexto = navegador.new_context(
            viewport={"width": vp["largura"], "height": vp["altura"]},
            is_mobile=vp["mobile"],
            has_touch=vp["mobile"],
            device_scale_factor=2 if vp["mobile"] else 1,
            user_agent=("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
            if vp["nome"] == "mobile" else None,
        )
        page = contexto.new_page()
        resultado = {"viewport": vp["nome"], "largura": vp["largura"], "problemas": []}

        try:
            try:
                page.goto(url, wait_until="load", timeout=45000)
            except PWTimeout:
                # Site pesado que nunca dispara 'load' ainda pode ser avaliado:
                # segue com o que já renderizou e registra a observação.
                resultado["observacao"] = "a página não concluiu o evento load em 45s"
            page.wait_for_timeout(1200)

            banner = fechar_banners(page)
            if banner:
                resultado["banner_fechado"] = banner

            if rolar:
                rolar_pagina(page)

            # Overflow horizontal: o sintoma mais comum e mais visível de layout
            # que não se adapta. O usuário precisa arrastar a página de lado.
            #
            # A largura de referência vem do Python, não de window.innerWidth: em
            # emulação mobile o Chromium expande a viewport quando o conteúdo
            # estoura, e innerWidth passa a refletir o conteúdo em vez da tela —
            # o que faz o overflow nunca ser detectado, justamente no caso que
            # mais importa.
            overflow = page.evaluate("""(larguraReal) => {
                const larguraDoc = Math.max(
                    document.documentElement.scrollWidth, document.body.scrollWidth);
                const estourando = [];
                if (larguraDoc > larguraReal + 2) {
                    for (const el of document.querySelectorAll('body *')) {
                        const r = el.getBoundingClientRect();
                        if (r.width > 0 && r.right > larguraReal + 2) {
                            estourando.push({
                                tag: el.tagName.toLowerCase(),
                                classe: (el.className || '').toString().slice(0, 60),
                                largura_px: Math.round(r.width),
                                excesso_px: Math.round(r.right - larguraReal)
                            });
                            if (estourando.length >= 8) break;
                        }
                    }
                }
                return {largura_janela: larguraReal, largura_documento: larguraDoc,
                        excesso_px: Math.round(larguraDoc - larguraReal),
                        elementos: estourando};
            }""", vp["largura"])

            if overflow["excesso_px"] > 2:
                resultado["problemas"].append({
                    "tipo": "overflow_horizontal",
                    "severidade": "alta",
                    "descricao": (f"a página é {overflow['excesso_px']}px mais larga que a tela "
                                  f"({overflow['largura_documento']}px de conteúdo para "
                                  f"{overflow['largura_janela']}px de viewport) — o usuário "
                                  f"precisa arrastar de lado"),
                    "elementos": overflow["elementos"],
                })
            resultado["overflow"] = overflow

            # Meta viewport: sem ela o navegador mobile renderiza como desktop
            # e encolhe tudo. Só faz sentido checar uma vez.
            if vp["nome"] == "mobile":
                meta = page.evaluate(
                    """() => {const m = document.querySelector('meta[name=viewport]');
                              return m ? m.getAttribute('content') : null;}""")
                resultado["meta_viewport"] = meta
                if not meta:
                    resultado["problemas"].append({
                        "tipo": "sem_meta_viewport", "severidade": "crítica",
                        "descricao": "a página não declara <meta name=viewport> — o navegador "
                                     "mobile vai renderizar em largura de desktop e encolher tudo",
                    })

                texto_pequeno = page.evaluate("""() => {
                    let contagem = 0; const amostras = [];
                    for (const el of document.querySelectorAll('p,span,a,li,td,label,div')) {
                        if (!el.offsetParent) continue;
                        const txt = (el.childNodes.length === 1 &&
                                     el.childNodes[0].nodeType === 3)
                                    ? el.innerText.trim() : '';
                        if (!txt || txt.length < 4) continue;
                        const tam = parseFloat(getComputedStyle(el).fontSize);
                        if (tam && tam < 12) {
                            contagem++;
                            if (amostras.length < 5)
                                amostras.push({texto: txt.slice(0, 40), px: Math.round(tam*10)/10});
                        }
                    }
                    return {contagem, amostras};
                }""")
                if texto_pequeno["contagem"] > 0:
                    resultado["problemas"].append({
                        "tipo": "texto_pequeno", "severidade": "média",
                        "descricao": (f"{texto_pequeno['contagem']} trechos com fonte abaixo de "
                                      f"12px no mobile, difíceis de ler"),
                        "amostras": texto_pequeno["amostras"],
                    })

                alvos = page.evaluate("""() => {
                    let contagem = 0; const amostras = [];
                    for (const el of document.querySelectorAll('a,button,input[type=submit],[role=button]')) {
                        if (!el.offsetParent) continue;
                        const r = el.getBoundingClientRect();
                        if (r.width === 0 || r.height === 0) continue;
                        if (r.width < 44 || r.height < 44) {
                            contagem++;
                            if (amostras.length < 5)
                                amostras.push({
                                    texto: (el.innerText || el.getAttribute('aria-label') || el.tagName).trim().slice(0,30),
                                    largura: Math.round(r.width), altura: Math.round(r.height)});
                        }
                    }
                    return {contagem, amostras};
                }""")
                if alvos["contagem"] > 0:
                    resultado["problemas"].append({
                        "tipo": "alvo_toque_pequeno", "severidade": "média",
                        "descricao": (f"{alvos['contagem']} elementos clicáveis menores que "
                                      f"44x44px, o mínimo recomendado para toque"),
                        "amostras": alvos["amostras"],
                    })

            caminho = os.path.join(saida, "responsivo", f"{nome_site}_{vp['nome']}.png")
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            page.screenshot(path=caminho, full_page=False)
            resultado["screenshot"] = caminho

        except PWTimeout:
            resultado["erro"] = "timeout ao carregar"
        except Exception as e:
            resultado["erro"] = f"{type(e).__name__}: {e}"
        finally:
            contexto.close()

        achados.append(resultado)

    return achados


# ------------------------------------------------------------- Orquestração

def auditar(url, saida, visivel, max_links, so_internos, intervalo,
            pular_links, rolar=True):
    os.makedirs(saida, exist_ok=True)
    nome_site = urlparse(url).netloc.replace(".", "_") or "site"

    print(f"\n=== {url} ===", flush=True)

    with sync_playwright() as pw:
        navegador = pw.chromium.launch(headless=not visivel)
        contexto = navegador.new_context(viewport={"width": 1920, "height": 1080})
        page = contexto.new_page()

        erros_console = []
        page.on("console", lambda m: erros_console.append(m.text[:200])
                if m.type == "error" else None)

        print("  [1/3] medindo carregamento...", flush=True)
        perf = medir_performance(page, url)
        banner = fechar_banners(page)
        if banner:
            print(f"        banner de cookies fechado ({banner})", flush=True)
            perf["banner_fechado"] = banner
        t = perf["metricas"].get("carregamento_total") or perf["tempo_total_medido_ms"]
        print(f"        {t} ms ({perf['veredito']})", flush=True)

        links_result = []
        if not pular_links:
            print("  [2/3] verificando links...", flush=True)
            rolar_pagina(page)
            links = coletar_links(page, url)
            if so_internos:
                links = [l for l in links if l["interno"]]
            total_encontrados = len(links)
            links = links[:max_links]
            print(f"        {total_encontrados} links encontrados, "
                  f"verificando {len(links)}", flush=True)
            links_result = verificar_links(contexto, links, intervalo)
            quebrados = sum(1 for l in links_result if l["situacao"] in ("QUEBRADO", "ERRO"))
            print(f"        {quebrados} com problema", flush=True)
        else:
            print("  [2/3] verificação de links pulada", flush=True)
            total_encontrados = 0

        contexto.close()

        print("  [3/3] testando responsividade...", flush=True)
        resp = testar_responsividade(navegador, url, saida, nome_site, visivel, rolar)
        n_problemas = sum(len(r.get("problemas", [])) for r in resp)
        print(f"        {n_problemas} problemas de layout", flush=True)

        navegador.close()

    return {
        "url": url,
        "auditado_em": datetime.now().isoformat(timespec="seconds"),
        "performance": perf,
        "links": {
            "total_encontrados": total_encontrados,
            "verificados": len(links_result),
            "quebrados": [l for l in links_result if l["situacao"] in ("QUEBRADO", "ERRO")],
            "redirecionam": [l for l in links_result if l["situacao"] == "REDIRECIONA"],
            "ok": sum(1 for l in links_result if l["situacao"] == "OK"),
        },
        "responsividade": resp,
        "erros_console": erros_console[:10],
    }


def escrever_relatorio(auditorias, caminho):
    L = ["# Relatório de auditoria de sites\n"]
    L.append(f"**Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")

    L.append("## Visão geral\n")
    L.append("| Site | Carregamento | Links quebrados | Problemas de layout |")
    L.append("|------|--------------|-----------------|---------------------|")
    for a in auditorias:
        t = a["performance"]["metricas"].get("carregamento_total") or \
            a["performance"]["tempo_total_medido_ms"]
        nq = len(a["links"]["quebrados"])
        np_ = sum(len(r.get("problemas", [])) for r in a["responsividade"])
        L.append(f"| {urlparse(a['url']).netloc} | {t} ms ({a['performance']['veredito']}) "
                 f"| {nq} | {np_} |")
    L.append("")

    for a in auditorias:
        L.append(f"\n---\n\n## {a['url']}\n")

        p = a["performance"]
        m = p["metricas"]
        L.append("### Carregamento\n")
        if p["erro"]:
            L.append(f"**Erro:** {p['erro']}\n")
        L.append("| Métrica | Valor |")
        L.append("|---------|-------|")
        if m.get("ttfb") is not None:
            L.append(f"| TTFB (resposta do servidor) | {m['ttfb']} ms |")
        if m.get("fcp") is not None:
            L.append(f"| First Contentful Paint | {m['fcp']} ms |")
        if m.get("dom_carregado") is not None:
            L.append(f"| DOM carregado | {m['dom_carregado']} ms |")
        if m.get("carregamento_total") is not None:
            L.append(f"| Carregamento completo | {m['carregamento_total']} ms |")
        r = p.get("recursos", {})
        if r.get("quantidade"):
            L.append(f"| Recursos carregados | {r['quantidade']} |")
        if r.get("total_kb"):
            L.append(f"| Peso total | {r['total_kb']} KB |")
        L.append(f"\n**Veredito:** {p['veredito']} "
                 f"(bom até {LIMITES_MS['bom']} ms, aceitável até {LIMITES_MS['aceitavel']} ms)\n")

        if r.get("pesados"):
            L.append("Recursos mais pesados:\n")
            for x in r["pesados"]:
                L.append(f"- `{x['url']}` — {x['kb']} KB")
            L.append("")

        lk = a["links"]
        L.append("### Links\n")
        L.append(f"{lk['total_encontrados']} encontrados, {lk['verificados']} verificados, "
                 f"{lk['ok']} respondendo normalmente.\n")
        if lk["quebrados"]:
            L.append("**Com problema:**\n")
            L.append("| Status | Texto do link | URL |")
            L.append("|--------|---------------|-----|")
            for l in lk["quebrados"]:
                st = l["status"] or l["erro"] or "?"
                L.append(f"| {st} | {l['texto'][:40]} | {l['url'][:80]} |")
            L.append("")
        else:
            L.append("Nenhum link quebrado entre os verificados.\n")
        if lk["redirecionam"]:
            L.append(f"{len(lk['redirecionam'])} links redirecionam. "
                     "Não é erro, mas redirecionamento em link interno costuma ser "
                     "URL desatualizada e custa um salto extra ao usuário.\n")

        L.append("### Responsividade\n")
        for v in a["responsividade"]:
            L.append(f"#### {v['viewport'].title()} ({v['largura']}px)\n")
            if v.get("erro"):
                L.append(f"Erro: {v['erro']}\n")
                continue
            if not v.get("problemas"):
                L.append("Nenhum problema automático detectado.\n")
            for pr in v["problemas"]:
                L.append(f"- **{pr['tipo']}** ({pr['severidade']}): {pr['descricao']}")
                for chave in ("elementos", "amostras"):
                    for item in pr.get(chave, [])[:4]:
                        L.append(f"  - `{item}`")
            if v.get("screenshot"):
                L.append(f"\nScreenshot: `{os.path.basename(v['screenshot'])}`\n")

        if a["erros_console"]:
            L.append("### Erros de console\n")
            for e in a["erros_console"][:5]:
                L.append(f"- `{e[:150]}`")
            L.append("")

    L.append("\n---\n")
    L.append("*As verificações automáticas cobrem overflow horizontal, tamanho de fonte, "
             "alvos de toque e meta viewport. Alinhamento, hierarquia visual e estética "
             "precisam de revisão humana — use os screenshots em `responsivo/`.*")

    with open(caminho, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Audita links, performance e responsividade")
    p.add_argument("url", nargs="?", help="URL do site a auditar")
    p.add_argument("--lote", help="arquivo texto com uma URL por linha")
    p.add_argument("--saida", default="auditoria", help="pasta de saída")
    p.add_argument("--visivel", action="store_true",
                   help="abre o navegador na tela (padrão: invisível, mais rápido)")
    p.add_argument("--max-links", type=int, default=100,
                   help="quantos links verificar por página (padrão 100)")
    p.add_argument("--so-internos", action="store_true",
                   help="verifica apenas links do mesmo domínio")
    p.add_argument("--intervalo", type=float, default=0.15,
                   help="pausa em segundos entre requisições, para não sobrecarregar o site")
    p.add_argument("--pular-links", action="store_true",
                   help="só performance e responsividade")
    p.add_argument("--sem-rolagem", action="store_true",
                   help="não rola a página (mais rápido, mas perde conteúdo lazy loaded)")
    args = p.parse_args()

    urls = []
    if args.lote:
        with open(args.lote, encoding="utf-8") as f:
            urls = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    elif args.url:
        urls = [args.url]
    else:
        p.error("informe uma URL ou --lote com um arquivo de URLs")

    os.makedirs(args.saida, exist_ok=True)
    auditorias = []
    for u in urls:
        try:
            auditorias.append(auditar(u, args.saida, args.visivel, args.max_links,
                                      args.so_internos, args.intervalo, args.pular_links,
                                      not args.sem_rolagem))
        except Exception as e:
            print(f"  FALHA ao auditar {u}: {e}", flush=True)
            auditorias.append({"url": u, "erro_fatal": str(e),
                               "performance": {"metricas": {}, "tempo_total_medido_ms": 0,
                                               "veredito": "não medido", "erro": str(e)},
                               "links": {"total_encontrados": 0, "verificados": 0,
                                         "quebrados": [], "redirecionam": [], "ok": 0},
                               "responsividade": [], "erros_console": []})

    with open(os.path.join(args.saida, "auditoria.json"), "w", encoding="utf-8") as f:
        json.dump(auditorias, f, ensure_ascii=False, indent=2)

    destino = os.path.join(args.saida, "RELATORIO-AUDITORIA.md")
    escrever_relatorio(auditorias, destino)

    print(f"\nRelatório em {destino}")
    print(f"Screenshots em {os.path.join(args.saida, 'responsivo')}")
