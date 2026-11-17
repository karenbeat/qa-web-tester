#!/usr/bin/env python3
"""
Runner de testes de QA em navegador.

Este é o "braço" da skill: recebe um plano de teste em JSON e executa cada caso
no navegador com Playwright, capturando screenshot e o que apareceu na tela.

O plano é gerado pela skill a partir dos cenários que o desenvolvedor descreveu.
O runner não decide o que testar — só executa e reporta o que viu.

PRINCÍPIO DE ISOLAMENTO
-----------------------
Um formulário com vários campos obrigatórios dispara erro em todos eles quando
você envia com um campo só preenchido. Se o runner apenas perguntar "apareceu
algum erro?", ele vai achar que o campo sob teste foi validado quando na verdade
o erro veio de outro campo — e um bug real passa despercebido.

Por isso, cada caso precisa de:
  - "preenchimento_base": valores válidos para TODOS os campos, aplicados antes
    de cada caso, para que só o campo sob teste esteja em condição de erro;
  - "campo_alvo": o seletor do campo sendo testado, para que o julgamento olhe
    o estado DAQUELE campo e não da página inteira;
  - "indicador_sucesso": um seletor que só aparece quando o envio dá certo, que
    é uma evidência muito mais confiável do que a ausência de erro.

Instalação (uma vez):
    pip install playwright
    playwright install chromium

Uso:
    python runner.py plano.json --saida resultados/
    python runner.py plano.json --saida resultados/ --headless
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# O terminal do Windows usa cp1252 por padrão, e este script imprime acentos e
# travessões. Sem isto, a primeira linha de saída derruba a execução com
# UnicodeEncodeError. Em Linux e macOS a chamada não faz diferença.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass


SELETORES_ERRO = [
    "[role=alert]", ".error", ".invalid-feedback", ".text-danger",
    ".field-error", ".help-block", ".Mui-error", "small.error",
    ".ant-form-item-explain-error", ".form-error", ".errorMessage",
]

CLASSES_INVALIDO = ["is-invalid", "error", "invalid", "has-error", "Mui-error"]


def carregar_plano(caminho):
    with open(caminho, encoding="utf-8") as f:
        plano = json.load(f)
    if "url" not in plano:
        raise SystemExit("O plano precisa de uma chave 'url'.")
    if not plano.get("casos"):
        raise SystemExit("O plano não tem casos de teste.")
    return plano


# ---------------------------------------------------------------- Ações

def executar_acao(page, acao):
    """Executa uma ação. Devolve None em sucesso ou o erro como string."""
    tipo = acao.get("tipo")
    seletor = acao.get("seletor")
    valor = acao.get("valor", "")

    try:
        if tipo == "preencher":
            campo = page.locator(seletor).first
            campo.click()
            # Limpar antes é essencial: resíduo do caso anterior é a maior
            # fonte de falso positivo em teste de formulário.
            campo.fill("")
            if valor:
                # digitar caractere a caractere dispara a máscara do front
                campo.type(valor, delay=25)
            page.keyboard.press("Tab")  # tira o foco, dispara validação de blur

        elif tipo == "clicar":
            page.locator(seletor).first.click()
        elif tipo == "selecionar":
            page.locator(seletor).first.select_option(valor)
        elif tipo == "marcar":
            page.locator(seletor).first.check()
        elif tipo == "esperar":
            page.wait_for_timeout(int(valor or 1000))
        elif tipo == "navegar":
            page.goto(valor, wait_until="domcontentloaded")
        elif tipo == "recarregar":
            page.reload(wait_until="domcontentloaded")
        else:
            return f"tipo de ação desconhecido: {tipo}"

    except PWTimeout:
        return f"elemento não encontrado no tempo limite: {seletor}"
    except Exception as e:
        return f"{type(e).__name__}: {e}"
    return None


# ---------------------------------------------------------------- Coleta

def estado_do_campo(page, seletor):
    """
    Olha o estado APENAS do campo sob teste: ele está marcado como inválido?
    Existe uma mensagem de erro associada a ele? Qual é o texto?

    A associação é buscada em ordem de confiabilidade: aria-describedby,
    convenção de id (erro-<id>, <id>-error), e por fim o elemento irmão logo
    abaixo do campo.
    """
    if not seletor:
        return {"encontrado": False, "invalido": None, "mensagem": "", "valor": None}

    try:
        return page.evaluate(
            """([sel, classes, seletoresErro]) => {
                const el = document.querySelector(sel);
                if (!el) return {encontrado: false, invalido: null, mensagem: '', valor: null};

                const invalidoPorClasse = classes.some(c => el.classList.contains(c));
                const invalidoPorAria = el.getAttribute('aria-invalid') === 'true';
                const invalidoNativo = el.willValidate && !el.checkValidity();

                const visivel = n => n && n.offsetParent !== null
                                  && (n.innerText || '').trim().length > 0;

                let msg = '';

                // 1. aria-describedby — a forma correta e acessível
                const desc = el.getAttribute('aria-describedby');
                if (desc) {
                    for (const id of desc.split(/\\s+/)) {
                        const n = document.getElementById(id);
                        if (visivel(n)) { msg = n.innerText.trim(); break; }
                    }
                }

                // 2. convenção de id
                if (!msg && el.id) {
                    for (const padrao of ['erro-' + el.id, el.id + '-error',
                                          'error-' + el.id, el.id + '_error']) {
                        const n = document.getElementById(padrao);
                        if (visivel(n)) { msg = n.innerText.trim(); break; }
                    }
                }

                // 3. irmão seguinte que pareça mensagem de erro
                if (!msg) {
                    let irmao = el.nextElementSibling;
                    let saltos = 0;
                    while (irmao && saltos < 3) {
                        const combina = seletoresErro.some(s => {
                            try { return irmao.matches(s); } catch (e) { return false; }
                        });
                        if (combina && visivel(irmao)) { msg = irmao.innerText.trim(); break; }
                        irmao = irmao.nextElementSibling;
                        saltos++;
                    }
                }

                // 4. validação nativa do HTML5
                if (!msg && invalidoNativo) msg = el.validationMessage || '';

                return {
                    encontrado: true,
                    invalido: invalidoPorClasse || invalidoPorAria || invalidoNativo || msg.length > 0,
                    mensagem: msg,
                    valor: el.value
                };
            }""",
            [seletor, CLASSES_INVALIDO, SELETORES_ERRO],
        )
    except Exception as e:
        return {"encontrado": False, "invalido": None, "mensagem": "",
                "valor": None, "erro_leitura": str(e)}


def estado_da_pagina(page, indicador_sucesso):
    """Estado global: deu certo o envio? A página quebrou?"""
    page.wait_for_timeout(400)

    sucesso = False
    if indicador_sucesso:
        try:
            sucesso = page.locator(indicador_sucesso).first.is_visible()
        except Exception:
            sucesso = False

    todas_mensagens = []
    for sel in SELETORES_ERRO:
        try:
            for el in page.locator(sel).all():
                if el.is_visible():
                    t = (el.inner_text() or "").strip()
                    if t and t not in todas_mensagens:
                        todas_mensagens.append(t)
        except Exception:
            continue

    corpo = ""
    try:
        corpo = page.inner_text("body")[:3000]
    except Exception:
        pass

    return {
        "url_atual": page.url,
        "sucesso_visivel": sucesso,
        "todas_mensagens_da_pagina": todas_mensagens,
        "erro_servidor": bool(re.search(
            r"(Internal Server Error|Traceback|SQLSTATE|Exception:|500 -|Warning:)",
            corpo, re.IGNORECASE)),
    }


# ---------------------------------------------------------------- Julgamento

def julgar(caso, campo, pagina, url_inicial, erro_acao):
    """
    Compara observado com esperado, olhando o CAMPO sob teste — não a página
    inteira. Devolve (status, motivo).
    """
    if erro_acao:
        return "ERRO", erro_acao

    if pagina["erro_servidor"]:
        return "FALHOU", "a página exibiu erro de servidor ou stack trace"

    if caso.get("campo_alvo") and not campo["encontrado"]:
        return "ERRO", f"campo sob teste não encontrado: {caso['campo_alvo']}"

    esperado = caso.get("esperado", "bloqueia")
    avancou = pagina["sucesso_visivel"] or pagina["url_atual"] != url_inicial
    campo_marcado = bool(campo["invalido"])
    tem_mensagem = bool(campo["mensagem"].strip())

    if esperado == "bloqueia":
        if avancou:
            return "FALHOU", "ACEITOU um valor que deveria ter sido rejeitado — o envio foi concluído"
        if not campo_marcado:
            return "FALHOU", ("o envio não foi concluído, mas o campo sob teste não foi "
                              "marcado como inválido — a validação pode estar em outro campo")
        if not tem_mensagem:
            return "ATENCAO", "bloqueou corretamente, mas não exibiu nenhuma mensagem explicando o motivo"

        alvo = caso.get("mensagem_esperada")
        if alvo and alvo.lower() not in campo["mensagem"].lower():
            return "ATENCAO", (f"bloqueou e exibiu \"{campo['mensagem']}\", "
                               f"mas a mensagem não menciona '{alvo}'")
        return "PASSOU", f"bloqueou e exibiu \"{campo['mensagem']}\""

    if esperado == "aceita":
        if campo_marcado:
            return "FALHOU", f"REJEITOU um valor válido: \"{campo['mensagem']}\""
        if not avancou:
            return "FALHOU", ("o campo não foi marcado como inválido, mas o envio não foi "
                              "concluído — verifique se outro campo está bloqueando")
        return "PASSOU", "aceitou o valor válido e concluiu o envio"

    # esperado == "mascara": confere se o valor foi formatado
    if esperado == "mascara":
        alvo = caso.get("valor_formatado_esperado", "")
        obtido = campo["valor"] or ""
        if obtido == alvo:
            return "PASSOU", f"máscara aplicada corretamente: \"{obtido}\""
        return "FALHOU", f"máscara esperada \"{alvo}\", mas o campo ficou \"{obtido}\""

    # esperado == "verificacoes": para interações que não passam pelo submit
    # principal (aplicar cupom, calcular frete, recalcular total). Confere o
    # texto ou o valor de elementos específicos da página.
    if esperado == "verificacoes":
        falhas = []
        for v in caso.get("verificacoes", []):
            obtido = (v.get("_obtido") or "")
            if not v.get("_encontrado"):
                falhas.append(f"elemento {v['seletor']} não encontrado")
            elif "contem" in v and v["contem"].lower() not in obtido.lower():
                falhas.append(f"{v['seletor']} deveria conter \"{v['contem']}\", "
                              f"mas mostra \"{obtido[:80]}\"")
            elif "nao_contem" in v and v["nao_contem"].lower() in obtido.lower():
                falhas.append(f"{v['seletor']} não deveria conter \"{v['nao_contem']}\", "
                              f"mas mostra \"{obtido[:80]}\"")
            elif "igual" in v and v["igual"] != obtido.strip():
                falhas.append(f"{v['seletor']} deveria ser \"{v['igual']}\", "
                              f"mas é \"{obtido.strip()[:80]}\"")
        if falhas:
            return "FALHOU", "; ".join(falhas)
        return "PASSOU", "todas as verificações da página bateram com o esperado"

    return "ATENCAO", f"tipo de 'esperado' desconhecido: {esperado}"


def rodar_verificacoes(page, caso):
    """Lê os elementos citados nas verificações do caso, antes do julgamento."""
    for v in caso.get("verificacoes", []):
        try:
            el = page.locator(v["seletor"]).first
            v["_encontrado"] = el.count() > 0 if hasattr(el, "count") else True
            texto = (el.inner_text() or "").strip()
            if not texto:
                texto = el.input_value() if el.get_attribute("value") is not None else ""
            v["_obtido"] = texto
        except Exception:
            v["_encontrado"] = False
            v["_obtido"] = ""
    return caso


# ---------------------------------------------------------------- Execução

def rodar(plano, saida, headless, slow_mo, resumo=False):
    os.makedirs(os.path.join(saida, "evidencias"), exist_ok=True)
    resultados = []
    indicador = plano.get("indicador_sucesso")
    base = plano.get("preenchimento_base", [])

    if not base:
        print("AVISO: o plano não tem 'preenchimento_base'. Em formulários com vários\n"
              "campos obrigatórios isso gera falso negativo — erros de outros campos\n"
              "podem ser confundidos com validação do campo sob teste.\n")

    with sync_playwright() as pw:
        navegador = pw.chromium.launch(headless=headless, slow_mo=slow_mo)
        contexto = navegador.new_context(viewport={"width": 1280, "height": 900})
        page = contexto.new_page()

        erros_console = []
        page.on("console",
                lambda m: erros_console.append(m.text) if m.type == "error" else None)

        login = plano.get("login")
        if login:
            page.goto(login["url"], wait_until="domcontentloaded")
            page.fill(login["seletor_usuario"], login["usuario"])
            page.fill(login["seletor_senha"], login["senha"])
            page.click(login["seletor_botao"])
            page.wait_for_timeout(2000)

        for caso in plano["casos"]:
            cid = caso.get("id", "?")
            if not resumo:
                print(f"  [{cid}] {caso.get('descricao', '')[:70]}", flush=True)

            try:
                page.goto(plano["url"], wait_until="domcontentloaded")
            except Exception as e:
                resultados.append({"id": cid, "status": "ERRO",
                                   "motivo": f"não foi possível abrir a página: {e}"})
                print(f"  [{cid}] ERRO: página inacessível", flush=True)
                continue

            page.wait_for_timeout(250)

            # Limpar o armazenamento do navegador entre casos. Recarregar a
            # página zera os campos do formulário, mas não o localStorage — e
            # sem isto um item adicionado ao carrinho no caso anterior continua
            # lá no caso seguinte, contaminando o resultado.
            if plano.get("limpar_storage", True):
                try:
                    page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
                    page.reload(wait_until="domcontentloaded")
                    page.wait_for_timeout(200)
                except Exception:
                    pass

            url_inicial = page.url
            erros_console.clear()
            erro_acao = None

            # Preenche todos os campos com valores válidos, para isolar o campo sob teste.
            if not caso.get("pular_preenchimento_base"):
                for campo_base in base:
                    if campo_base["seletor"] == caso.get("campo_alvo"):
                        continue  # o caso vai definir esse
                    erro_acao = executar_acao(page, {"tipo": "preencher", **campo_base})
                    if erro_acao:
                        break

            if not erro_acao:
                for acao in caso.get("acoes", []):
                    erro_acao = executar_acao(page, acao)
                    if erro_acao:
                        break

            campo = estado_do_campo(page, caso.get("campo_alvo"))
            pagina = estado_da_pagina(page, indicador)
            if caso.get("esperado") == "verificacoes":
                rodar_verificacoes(page, caso)
            status, motivo = julgar(caso, campo, pagina, url_inicial, erro_acao)

            evidencia = os.path.join(saida, "evidencias", f"caso_{cid}.png")
            try:
                page.screenshot(path=evidencia)
            except Exception:
                evidencia = None

            resultados.append({
                "id": cid,
                "cenario": caso.get("cenario", ""),
                "descricao": caso.get("descricao", ""),
                "campo_alvo": caso.get("campo_alvo"),
                "entrada": [a.get("valor", "") for a in caso.get("acoes", [])
                            if a.get("tipo") == "preencher"],
                "esperado": caso.get("esperado"),
                "status": status,
                "motivo": motivo,
                "campo_marcado_invalido": campo["invalido"],
                "mensagem_do_campo": campo["mensagem"],
                "valor_final_do_campo": campo["valor"],
                "envio_concluido": pagina["sucesso_visivel"],
                "mensagens_da_pagina": pagina["todas_mensagens_da_pagina"],
                "erro_servidor": pagina["erro_servidor"],
                "erros_console": erros_console[:5],
                "evidencia": evidencia,
            })
            if resumo:
                # Só o que exige ação vai para a saída; o resto fica no JSON.
                if status != "PASSOU":
                    print(f"  [{cid}] {status}: {caso.get('descricao','')[:55]} "
                          f"-> {motivo[:90]}", flush=True)
            else:
                print(f"       -> {status}: {motivo}", flush=True)

        navegador.close()

    relatorio = {
        "url": plano["url"],
        "executado_em": datetime.now().isoformat(timespec="seconds"),
        "total": len(resultados),
        "passou": sum(1 for r in resultados if r["status"] == "PASSOU"),
        "falhou": sum(1 for r in resultados if r["status"] == "FALHOU"),
        "atencao": sum(1 for r in resultados if r["status"] == "ATENCAO"),
        "erro": sum(1 for r in resultados if r["status"] == "ERRO"),
        "resultados": resultados,
    }

    with open(os.path.join(saida, "resultados.json"), "w", encoding="utf-8") as f:
        json.dump(relatorio, f, ensure_ascii=False, indent=2)

    print(f"\n{relatorio['passou']} passou | {relatorio['falhou']} falhou | "
          f"{relatorio['atencao']} atenção | {relatorio['erro']} erro de execução")
    print(f"Resultados salvos em {os.path.join(saida, 'resultados.json')}")
    return relatorio


def gerar_relatorio_md(relatorio, caminho):
    """
    Escreve o relatório em markdown direto do runner.

    Existe por economia de contexto: sem isto, o agente precisa ler o
    resultados.json inteiro (dezenas de milhares de caracteres, com o estado de
    cada campo e trechos de página) só para redigir o relatório. Gerando aqui, o
    agente lê um arquivo pronto e curto, ou nem lê.
    """
    falhas = [r for r in relatorio["resultados"] if r["status"] == "FALHOU"]
    avisos = [r for r in relatorio["resultados"] if r["status"] == "ATENCAO"]
    erros = [r for r in relatorio["resultados"] if r["status"] == "ERRO"]
    ok = [r for r in relatorio["resultados"] if r["status"] == "PASSOU"]

    L = []
    L.append("# Relatório de QA\n")
    L.append(f"**Ambiente:** {relatorio['url']}  ")
    L.append(f"**Executado em:** {relatorio['executado_em']}\n")
    L.append("## Resumo\n")
    L.append("| Resultado | Qtd |")
    L.append("|-----------|-----|")
    L.append(f"| Passou | {relatorio['passou']} |")
    L.append(f"| Falhou | {relatorio['falhou']} |")
    L.append(f"| Atenção | {relatorio['atencao']} |")
    L.append(f"| Erro de execução | {relatorio['erro']} |\n")

    if falhas:
        L.append("## Falhas\n")
        for r in falhas:
            entrada = ", ".join(f"`{e}`" if e else "(vazio)" for e in r.get("entrada", [])) or "—"
            L.append(f"### {r['id']} — {r['descricao']}\n")
            L.append(f"- **Cenário:** {r.get('cenario','')}")
            L.append(f"- **Campo:** `{r.get('campo_alvo') or '—'}`")
            L.append(f"- **Entrada:** {entrada}")
            L.append(f"- **Esperado:** {r.get('esperado','')}")
            L.append(f"- **Obtido:** {r['motivo']}")
            if r.get("evidencia"):
                L.append(f"- **Evidência:** `{os.path.basename(r['evidencia'])}`")
            L.append("")

    if avisos:
        L.append("## Avisos\n")
        for r in avisos:
            L.append(f"- **{r['id']}** {r['descricao']} — {r['motivo']}")
        L.append("")

    if erros:
        L.append("## Não foi possível testar\n")
        for r in erros:
            L.append(f"- **{r['id']}** {r.get('descricao','')} — {r['motivo']}")
        L.append("")

    if ok:
        L.append("## Casos que passaram\n")
        L.append("| # | Caso | Resultado |")
        L.append("|---|------|-----------|")
        for r in ok:
            L.append(f"| {r['id']} | {r['descricao']} | {r['motivo']} |")
        L.append("")

    L.append("---\n")
    L.append("*Gerado automaticamente pelo runner. Revise a severidade de cada falha "
             "antes de enviar: o runner reporta o que observou, não o impacto no negócio.*")

    with open(caminho, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Executa um plano de testes no navegador")
    p.add_argument("plano", help="caminho do plano.json")
    p.add_argument("--saida", default="resultados", help="pasta de saída")
    p.add_argument("--headless", action="store_true",
                   help="roda sem abrir janela (padrão: janela visível)")
    p.add_argument("--slow-mo", type=int, default=0,
                   help="atraso em ms entre ações, para acompanhar visualmente")
    p.add_argument("--resumo", action="store_true",
                   help="imprime só as falhas e o placar, em vez de todos os casos")
    p.add_argument("--relatorio", action="store_true",
                   help="gera RELATORIO.md na pasta de saída")
    args = p.parse_args()

    rel = rodar(carregar_plano(args.plano), args.saida, args.headless,
                args.slow_mo, args.resumo)

    if args.relatorio:
        destino = os.path.join(args.saida, "RELATORIO.md")
        gerar_relatorio_md(rel, destino)
        print(f"Relatório em {destino}")
