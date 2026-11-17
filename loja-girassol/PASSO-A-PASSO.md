# Passo a passo — rodar o QA na loja fictícia

> **Está no Windows?** Use o `PASSO-A-PASSO-WINDOWS.md`, que tem os comandos adaptados.
> Ou dê dois cliques no `rodar-teste.bat`, que faz tudo sozinho.

Guia completo, do zero até o relatório. Leva uns 10 minutos na primeira vez.

---

## Passo 1 — Organizar as pastas

Descompacte tudo numa pasta só. A estrutura deve ficar assim:

```
qa-teste/
├── qa-web-tester/          ← a skill e os scripts
│   ├── SKILL.md
│   ├── references/
│   ├── scripts/
│   │   ├── gerar_dados.py
│   │   └── runner.py
│   └── assets/
└── loja-girassol/          ← a loja fictícia para testar
    ├── index.html
    ├── checkout.html
    ├── plano-checkout.json
    └── BUGS-PLANTADOS.md
```

## Passo 2 — Instalar as dependências

```bash
pip install playwright
playwright install chromium
```

O segundo comando baixa o navegador (~150 MB). Só precisa rodar uma vez.

Confira se deu certo:

```bash
python -c "from playwright.sync_api import sync_playwright; print('tudo certo')"
```

Se o `pip` reclamar de "externally managed environment" (comum no Linux), use:

```bash
pip install playwright --break-system-packages
```

## Passo 3 — Subir a loja no localhost

Num terminal, entre na pasta da loja e suba um servidor:

```bash
cd loja-girassol
python -m http.server 8000
```

Deixe esse terminal aberto — se fechar, a loja sai do ar.

Abra `http://localhost:8000` no navegador. Você deve ver a Loja Girassol com cinco
produtos. Clique em `Finalizar compra` para ver o checkout que vai ser testado.

Passeie um pouco pelo checkout antes de rodar o teste. Tente adivinhar onde estão os
defeitos — depois compare com o que o agente achou. É um exercício bom.

## Passo 4 — Rodar a bateria

Abra um **segundo terminal** (o primeiro está ocupado com o servidor):

```bash
cd loja-girassol
python ../qa-web-tester/scripts/runner.py plano-checkout.json --saida resultados/ --slow-mo 200
```

O `--slow-mo 200` coloca 200ms entre cada ação, para você conseguir acompanhar o
navegador preenchendo os campos. Sem ele, roda em poucos segundos e você não vê nada.

Para rodar sem abrir janela (mais rápido, bom para repetir):

```bash
python ../qa-web-tester/scripts/runner.py plano-checkout.json --saida resultados/ --headless
```

**Resultado esperado: 10 passou, 13 falhou.**

## Passo 5 — Olhar os resultados

Três lugares para ver:

1. **O terminal** — mostra caso a caso, com o motivo de cada falha.
2. **`resultados/resultados.json`** — o detalhe completo: o que foi digitado, o que o
   campo mostrou, se o envio concluiu, erros de console.
3. **`resultados/evidencias/`** — um screenshot por caso. É o que você anexa quando for
   abrir o ticket.

Só depois de olhar tudo isso, abra o `BUGS-PLANTADOS.md` e confira se o agente achou
todos os defeitos que eu plantei.

## Passo 6 — Escrever ou gerar o relatório

O `RELATORIO-QA.md` incluído é o relatório da execução que eu fiz aqui — use como
modelo do que você deve produzir. No Claude Code, o agente faz esse passo sozinho: ele lê
o `resultados.json`, agrupa por severidade e escreve o markdown.

Manualmente, use `qa-web-tester/assets/template-relatorio.md` como base.

---

## Passo 7 — Experimentar

Agora que o ciclo funciona, brinque com ele:

**Corrija um bug e rode de novo.** Abra o `checkout.html`, ache o comentário
`DEFEITO 5` (a validação de CPF), adicione a checagem de dígitos repetidos:

```javascript
if (/^(\d)\1{10}$/.test(n)) return false;
```

Rode a bateria de novo. O caso 1.4 deve virar PASSOU. Esse é o loop de trabalho real:
testa, corrige, retesta.

**Escreva um caso novo.** Abra o `plano-checkout.json` e adicione:

```json
{
  "id": "7.1",
  "cenario": "Cenário 7 — Meu teste",
  "campo_alvo": "#titular",
  "descricao": "Nome do titular com números deve ser rejeitado",
  "acoes": [
    {"tipo": "preencher", "seletor": "#titular", "valor": "MARIA 12345"},
    {"tipo": "clicar", "seletor": "#finalizar"}
  ],
  "esperado": "bloqueia"
}
```

**Quebre o formulário de propósito** e veja se o teste pega. Mude a validação de CEP para
aceitar qualquer coisa e confirme que o caso 5.1 passa de PASSOU para FALHOU. Um teste que
não falha quando você introduz um bug não está testando nada.

---

## Passo 8 — Usar no Claude Code

Quando quiser fazer isso conversando em vez de escrever JSON à mão:

```bash
mkdir -p .claude/skills
cp -r qa-web-tester .claude/skills/
```

Aí é só dizer no Claude Code:

```
Quero testar o checkout do meu e-commerce.
```

A skill ativa, pergunta o cenário, você descreve em tópicos, e ela gera o plano,
executa e escreve o relatório sozinha.

---

## Problemas comuns

**"ERR_CONNECTION_REFUSED"** — o servidor do Passo 3 não está rodando, ou você fechou o
terminal. Suba de novo.

**"campo sob teste não encontrado"** — o seletor no plano não bate com o HTML. Abra a
página, F12, confira o `id` do campo.

**Tudo passou (mas você sabe que tem bug)** — falta o `preenchimento_base` ou o
`campo_alvo` no plano. Sem eles, os erros de outros campos mascaram o campo testado e
o runner aprova tudo. Foi exatamente o que aconteceu na primeira versão deste runner.

**Playwright não instala o chromium** — em Linux talvez falte dependência de sistema:
`playwright install-deps chromium` (precisa de sudo).
