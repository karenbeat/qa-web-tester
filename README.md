# Agente de QA para E-commerce

Skill para o Claude Code que testa aplicações web automaticamente, com foco em validação
de dados brasileiros (CPF, CNPJ, CEP, cartão) em fluxos de e-commerce.

Você descreve em linguagem natural o que quer testar. A skill expande cada cenário em
casos de teste concretos, executa no navegador e devolve um relatório de bugs com
evidências em imagem.

Esta versão foi otimizada para consumo de contexto: o runner comprime a saída e gera o
relatório sozinho, e a skill instrui o agente a reaproveitar planos existentes em vez de
regerá-los. Detalhes na seção [Economia de contexto](#economia-de-contexto).

---

## Instalação

**Requisitos:** Claude Code instalado, com conta Pro, Max, Team, Enterprise ou Console.
O plano gratuito do Claude.ai não dá acesso ao Claude Code.

Se ainda não tem, no PowerShell:

```powershell
irm https://claude.ai/install.ps1 | iex
```

No macOS e Linux:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Se depois disso o comando `claude` não for reconhecido, falta adicionar `~/.local/bin` ao
PATH — o instalador avisa isso no fim, numa linha fácil de perder.

**Instalar a skill.** Copie a pasta `qa-web-tester` para o diretório de skills:

```powershell
# Windows — disponível em todos os seus projetos
xcopy /E /I qa-web-tester %USERPROFILE%\.claude\skills\qa-web-tester
```

```bash
# macOS e Linux
cp -r qa-web-tester ~/.claude/skills/
```

Para instalar só num projeto específico, use `.claude/skills/` dentro da pasta dele.

**Dependências da execução.** O Claude Code orquestra, mas quem abre o navegador é o
Playwright:

```
pip install playwright
python -m playwright install chromium
```

Use `python -m playwright`, não `playwright` direto — o executável costuma ficar fora do
PATH. O próprio Claude Code instala isso se você pedir, já que tem acesso ao terminal.

---

## Como usar

Abra o Claude Code na pasta do projeto e diga o que quer:

```
Quero testar o checkout do meu e-commerce.
```

A skill ativa e pergunta o cenário. Você responde em tópicos:

```
URL: http://localhost:3000/checkout

Cenário 1: validar o campo CPF — vazio, inválido, máscara, duplicado
Cenário 2: pagamento — cartão, validade, CVV
Cenário 3: cupom de desconto, incluindo expirado
```

A partir daí ela expande os cenários em casos concretos, mostra o plano para você
aprovar, executa no navegador e escreve o relatório.

Antes de rodar, a skill pergunta **como você quer acompanhar**: navegador visível (você vê
cada campo sendo preenchido, bom para entender ou demonstrar) ou em segundo plano (sem
janela, bem mais rápido).

### Auditoria de site

Além da validação de formulário, a skill audita páginas inteiras:

```
Preciso verificar se os links do site estão funcionando, o tempo de
carregamento e se abre bem em celular e tablet.

URL: https://meusite.com.br
```

Ou direto pela linha de comando, inclusive em lote:

```bash
python qa-web-tester/scripts/auditor.py https://site.com.br --saida auditoria --so-internos
python qa-web-tester/scripts/auditor.py --lote sites.txt --saida auditoria
```

Mede TTFB, First Contentful Paint e carregamento completo; confere o status HTTP de cada
link; e renderiza em 1920, 768 e 390 px procurando overflow horizontal, falta de meta
viewport, fonte abaixo de 12 px e alvos de toque menores que 44×44 px. Gera screenshot de
cada viewport para a parte que exige olho humano — alinhamento, espaçamento e hierarquia
visual não são automatizáveis com confiança.

---

## O que tem no pacote

### `qa-web-tester/` — a skill

| Arquivo | O que faz |
|---------|-----------|
| `SKILL.md` | O fluxo de trabalho: perguntar os cenários, expandir em casos, confirmar, executar, relatar — mais as regras de economia de contexto |
| `references/playbook-campos.md` | Converte "testar o campo CPF" em 12 casos concretos. Tem playbook para e-mail, senha, cartão, CEP, cupom, upload e fluxos de compra |
| `references/validacoes-br.md` | Algoritmos de CPF, CNPJ e Luhn, mais regras de CEP, telefone e bandeiras de cartão |
| `scripts/gerar_dados.py` | Gera CPFs, CNPJs e cartões sintéticos com dígito verificador correto |
| `scripts/runner.py` | Validação de formulário: Playwright, execução com estado limpo, detecção de erros, screenshots, relatório |
| `scripts/auditor.py` | Auditoria de site: links quebrados, tempo de carregamento e responsividade em desktop, tablet e mobile |
| `assets/template-relatorio.md` | Formato do relatório com classificação de severidade |
| `INSTALACAO.md` | Formato do arquivo de plano e detalhes de configuração |

### `loja-girassol/` — demonstração

Loja fictícia com 14 defeitos plantados de propósito, para validar a ferramenta antes de
apontá-la para um sistema real.

| Arquivo | O que é |
|---------|---------|
| `index.html`, `checkout.html` | A loja e o checkout testados |
| `plano-checkout.json` | Os 23 casos do checkout |
| `plano-carrinho.json` | Os 5 casos do carrinho |
| `resultados/`, `resultados-carrinho/` | Saída das execuções, com screenshot de cada caso |
| `RELATORIO-QA.md` | O relatório final, agrupado por severidade |
| `BUGS-PLANTADOS.md` | Gabarito. Não leia antes de rodar. |
| `COMO-RODAR.md` | Execução manual, para quem não vai usar o Claude Code |

---

## Resultados da demonstração

| Bateria | Casos | Passou | Falhou |
|---------|-------|--------|--------|
| Checkout | 23 | 10 | 13 |
| Carrinho | 5 | 2 | 3 |

Os 14 defeitos plantados foram encontrados. Os de maior impacto:

- Checkout finaliza pedido com **cartão que falha no algoritmo de Luhn**
- Aceita **validade vencida** (01/20), **mês 13** e **CVV de um dígito**
- **Cupom expirado** desde março de 2024 é aplicado normalmente
- Cupom de valor fixo deixa o **total negativo** (R$ -264,70)
- **CPF `111.111.111-11` é aceito** — o cálculo dos dígitos verificadores está certo, mas
  falta rejeitar sequências repetidas
- Carrinho aceita **produto esgotado** e **quantidade negativa**

Sete desses seguem o mesmo padrão: a validação confere **formato** e ignora **conteúdo**.
Contar dígitos do CVV aceita `1`; um regex de `MM/AA` aceita mês 13; checar o comprimento
do cartão aceita `1111111111111111`.

Numa execução conduzida pelo Claude Code, com os mesmos cenários descritos em linguagem
natural, a skill gerou 37 casos e identificou 9 defeitos únicos — incluindo variações que
o plano manual não cobria (`000.000.000-00`, mês `00`, espaço no meio do e-mail) e a falta
de máscara no campo de cartão.

---

## Economia de contexto

Baterias de QA geram muito texto, e quase todo ele é descartável. Encher o contexto faz o
agente perder precisão e esbarrar no limite de uso mais rápido. Esta versão traz três
mecanismos para evitar isso.

**Saída comprimida (`--resumo`).** Imprime só as falhas e o placar, em vez de uma linha
para cada caso. Numa bateria de 23 casos, corta mais da metade do que volta ao contexto.

**Relatório gerado pelo runner (`--relatorio`).** O próprio script escreve o
`RELATORIO.md`. Sem isso, o agente precisa ler o `resultados.json` inteiro — 15 KB com o
estado de cada campo e trechos de página — só para redigir. Com isso, ele recebe 5 KB
prontos, ou nem lê.

**Regras na skill.** O `SKILL.md` instrui o agente a reaproveitar planos existentes em vez
de regerá-los (a fase mais cara), ler apenas a seção relevante do playbook, e apresentar o
plano em lista simples em vez de tabelas desenhadas.

Comando recomendado:

```bash
python scripts/runner.py plano.json --saida resultados --headless --resumo --relatorio
```

E o atalho mais efetivo: quando o plano já existe e está validado, peça para rodá-lo
direto em vez de deixar a skill remontar tudo.

---

## Decisões de projeto

Dois detalhes que fazem a diferença entre um runner que funciona e um que aprova tudo:

**Isolamento do campo.** Um formulário com vários campos obrigatórios dispara erro em
todos eles quando você envia com um campo só preenchido. Um runner que só pergunta
"apareceu erro?" conclui que o campo testado foi validado — quando o erro veio de outro
campo. Por isso cada plano preenche todos os campos com dados válidos
(`preenchimento_base`) e estraga só o campo sob teste (`campo_alvo`), julgando pelo estado
daquele campo específico.

Isso não é teórico: a primeira versão deste runner aprovou 11 de 11 casos num formulário
com 6 bugs, justamente por não fazer isso.

**Limpeza de estado.** Recarregar a página zera os campos, mas não o `localStorage`. Sem
limpar, um item adicionado ao carrinho num caso continua lá no caso seguinte.

---

## Cuidados de uso

- Só executar contra ambientes próprios ou com autorização explícita
- Preferir staging a produção: a bateria cria pedidos, dispara e-mails e toca o gateway
- Nunca usar CPF, cartão ou e-mail reais — o `gerar_dados.py` existe para isso

---

## Próximos passos

1. Rodar contra um ambiente de staging real, começando por um formulário só
2. Pedir ao time que adicione `data-testid` nos campos críticos, para os testes não
   quebrarem a cada mudança de CSS
3. Integrar ao CI para rodar a cada deploy (exemplo em `qa-web-tester/INSTALACAO.md`)
