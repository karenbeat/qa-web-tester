# Passo a passo no Windows

Guia completo do zero até o relatório. Uns 10 minutos na primeira vez.

Se quiser pular direto para o resultado, o **`rodar-teste.bat`** faz os passos 3 e 4
sozinho — dois cliques e pronto. Mas vale ler o passo a passo pelo menos uma vez para
entender o que está acontecendo.

---

## Passo 1 — Ter o Python instalado

Abra o **PowerShell** (tecla Windows, digite `powershell`) e teste:

```powershell
python --version
```

Três coisas podem acontecer:

**Aparece `Python 3.x.x`** — está tudo certo, siga para o passo 2.

**Abre a Microsoft Store** — o Windows tem um atalho falso do Python que só leva para a
loja. Instale o Python de verdade em [python.org/downloads](https://python.org/downloads)
e **marque a caixa "Add python.exe to PATH"** na primeira tela do instalador. Essa caixa
é fácil de perder e é a causa de quase todo problema depois.

**"python não é reconhecido"** — o Python não está no PATH. Tente `py --version`. Se
funcionar, use `py` no lugar de `python` em todos os comandos deste guia. Se não
funcionar, reinstale marcando a caixa do PATH.

## Passo 2 — Instalar o Playwright

```powershell
pip install playwright
python -m playwright install chromium
```

O segundo comando baixa o navegador (uns 150 MB) e demora um pouco. Roda só uma vez.

**Use o `python -m playwright`, não o `playwright` direto.** O pip instala o
`playwright.exe` em `AppData\Roaming\Python\Python3xx\Scripts`, que normalmente não
está no PATH — ele avisa isso no fim da instalação, numa linha fácil de perder. Chamar
pelo módulo funciona independentemente do PATH.

Se mesmo assim aparecer `'playwright' não é reconhecido`, é esse o motivo: você usou o
executável em vez do módulo.

Confira se deu certo:

```powershell
python -c "from playwright.sync_api import sync_playwright; print('tudo certo')"
```

No Windows você **não** precisa do `playwright install-deps` — aquilo é só para Linux.

## Passo 3 — Subir a loja no localhost

Abra o PowerShell na pasta da loja. O jeito mais fácil: abra a pasta `loja-girassol` no
Explorador de Arquivos, clique na barra de endereço, digite `powershell` e dê Enter.

```powershell
python -m http.server 8000
```

Vai aparecer `Serving HTTP on :: port 8000`. **Deixe essa janela aberta** — se fechar, a
loja sai do ar.

Se o Windows Defender perguntar sobre liberar o acesso à rede, pode marcar só "redes
privadas" — o servidor é local.

Abra `http://localhost:8000` no navegador. Você deve ver a Loja Girassol com cinco
produtos. Clique em **Finalizar compra** para ver o checkout que vai ser testado.

Passeie um pouco pelo checkout antes de rodar o teste. Tente adivinhar onde estão os
defeitos — depois compare com o que o agente achou.

## Passo 4 — Rodar a bateria

Abra uma **segunda janela** do PowerShell (a primeira está ocupada com o servidor), na
mesma pasta `loja-girassol`:

```powershell
python ..\qa-web-tester\scripts\runner.py plano-checkout.json --saida resultados --slow-mo 200
```

Repare nas **barras invertidas** — no Windows o caminho é `..\qa-web-tester\...`, não
`../qa-web-tester/...`. O Python aceita os dois, mas o PowerShell completa com `\` no Tab.

O `--slow-mo 200` coloca 200 ms entre cada ação, para você ver o navegador preenchendo os
campos. Sem ele roda em segundos e você não vê nada.

Para rodar sem abrir janela (mais rápido, bom para repetir):

```powershell
python ..\qa-web-tester\scripts\runner.py plano-checkout.json --saida resultados --headless
```

**Resultado esperado: 10 passou, 13 falhou.**

## Passo 5 — Encerrar o servidor

Volte na primeira janela e pressione `Ctrl+C`. Se ela não responder, feche a janela.

Se por acaso o servidor ficou preso e a porta 8000 não libera:

```powershell
netstat -ano | findstr :8000
taskkill /PID <o-numero-que-apareceu> /F
```

## Passo 6 — Olhar os resultados

Três lugares:

1. **A janela do PowerShell** — caso a caso, com o motivo de cada falha.
2. **`resultados\resultados.json`** — o detalhe completo. Abra no VS Code ou no Bloco de
   Notas; se abrir no navegador fica mais legível.
3. **`resultados\evidencias\`** — um PNG por caso. É o que você anexa no ticket.

Só depois de olhar tudo isso, abra o `BUGS-PLANTADOS.md` e confira se o agente achou
todos os defeitos que eu plantei.

O `RELATORIO-QA.md` incluído é o relatório da execução que eu fiz — use como modelo do
que você deve produzir.

---

## Passo 7 — Experimentar

**Corrija um bug e rode de novo.** Abra o `checkout.html` no VS Code (ou no Bloco de
Notas), procure por `DEFEITO 5` e adicione a checagem de dígitos repetidos logo depois
da linha `if (n.length !== 11) return false;`:

```javascript
if (/^(\d)\1{10}$/.test(n)) return false;
```

Salve, dê F5 no navegador e rode a bateria de novo. O caso 1.4 deve virar PASSOU. Esse é
o loop de trabalho real: testa, corrige, retesta.

**Escreva um caso novo.** Abra o `plano-checkout.json` e adicione dentro de `"casos"`:

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

Cuidado com a vírgula: todo caso menos o último precisa de vírgula depois da chave.
Se der erro de JSON, é quase sempre isso.

**Quebre o formulário de propósito** e veja se o teste pega. Mude a validação de CEP para
aceitar qualquer coisa e confirme que o caso 5.1 vira FALHOU. Um teste que não falha
quando você introduz um bug não está testando nada.

---

## Passo 8 — Usar no Claude Code

Quando quiser fazer isso conversando em vez de editar JSON à mão, instale a skill no seu
projeto:

```powershell
mkdir .claude\skills
xcopy /E /I ..\qa-web-tester .claude\skills\qa-web-tester
```

Aí é só dizer no Claude Code: *"Quero testar o checkout do meu e-commerce."* A skill
ativa, pergunta o cenário, você descreve em tópicos, e ela gera o plano, executa e
escreve o relatório sozinha.

---

## Problemas comuns no Windows

**`UnicodeEncodeError` ou caracteres estranhos na saída** — o terminal está em cp1252. O
runner já corrige isso sozinho, mas se ainda acontecer, rode antes:

```powershell
chcp 65001
$env:PYTHONIOENCODING="utf-8"
```

**"python não é reconhecido"** — veja o passo 1. Use `py` no lugar de `python`.

**"pip não é reconhecido"** — chame pelo módulo: `python -m pip install playwright`.

**`ERR_CONNECTION_REFUSED`** — o servidor do passo 3 não está rodando, ou a janela foi
fechada. Suba de novo.

**"A execução de scripts foi desabilitada neste sistema"** — isso aparece com arquivos
`.ps1`. Os comandos deste guia são todos diretos, não precisam de script. Se quiser rodar
o `.bat`, dê dois cliques nele pelo Explorador em vez de chamar pelo PowerShell.

**"campo sob teste não encontrado"** — o seletor no plano não bate com o HTML. Abra a
página, F12, clique com o botão direito no campo → Copiar → Copiar seletor.

**Tudo passou (mas você sabe que tem bug)** — falta o `preenchimento_base` ou o
`campo_alvo` no plano. Sem eles, os erros de outros campos mascaram o campo testado e o
runner aprova tudo. Foi exatamente o que aconteceu na primeira versão deste runner.

**O antivírus reclama do Chromium** — o Playwright baixa um navegador próprio em
`%USERPROFILE%\AppData\Local\ms-playwright`. Se o antivírus bloquear, libere essa pasta.
