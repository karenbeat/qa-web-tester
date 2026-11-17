# Como rodar

Guia de execução manual, para quem não vai usar o Claude Code. Se você tem o Claude Code,
veja o README na raiz — lá o processo é conversacional e bem mais simples.

## 1. Instalar as dependências

```
pip install playwright
python -m playwright install chromium
```

O segundo comando baixa o navegador (~150 MB) e roda uma vez só.

**Use `python -m playwright`, não `playwright` direto.** O pip instala o executável numa
pasta que normalmente não está no PATH, e o erro resultante (`'playwright' não é
reconhecido`) parece falha de instalação quando na verdade o pacote está lá.

Se `python` não funcionar no Windows, tente `py`. Se abrir a Microsoft Store, você tem o
atalho falso do Windows: instale o Python de python.org marcando **"Add python.exe to
PATH"**.

## 2. Subir a loja

Abra um terminal **dentro da pasta `loja-girassol`** e rode:

```
python -m http.server 8000
```

Deixe essa janela aberta. Abra `http://localhost:8000` no navegador para conferir.

## 3. Rodar os testes

Abra um **segundo terminal**, também dentro de `loja-girassol`:

```
python ..\qa-web-tester\scripts\runner.py plano-checkout.json --saida resultados --slow-mo 200
```

No Linux e macOS, troque as barras invertidas por normais.

Confira o prompt antes de rodar: precisa terminar em `...\loja-girassol>`. O `..\` só
acha a pasta `qa-web-tester` a partir dali — se o terminal abriu em outro lugar, use
`cd` primeiro.

O `--slow-mo 200` coloca 200 ms entre cada ação, para você ver o navegador preenchendo os
campos. Troque por `--headless` para rodar sem janela, bem mais rápido.

**Resultado esperado: 10 passou, 13 falhou.**

Para testar também o carrinho:

```
python ..\qa-web-tester\scripts\runner.py plano-carrinho.json --saida resultados-carrinho --headless
```

**Resultado esperado: 2 passou, 3 falhou.**

## 4. Ver os resultados

- **No terminal** — caso a caso, com o motivo de cada falha
- **`resultados/resultados.json`** — detalhe completo de cada caso
- **`resultados/evidencias/`** — um screenshot por caso
- **`RELATORIO-QA.md`** — o relatório final, como modelo do que produzir

Compare com `BUGS-PLANTADOS.md`, que é o gabarito dos defeitos plantados. Só abra depois
de rodar — ler antes contamina o exercício.

## 5. Encerrar

`Ctrl+C` na janela do servidor. Se a porta 8000 ficar presa:

```
netstat -ano | findstr :8000
taskkill /PID <numero> /F
```

---

## Experimentar

**Corrija um bug e rode de novo.** No `checkout.html`, procure `DEFEITO 5` (validação de
CPF) e acrescente, logo depois de `if (n.length !== 11) return false;`:

```javascript
if (/^(\d)\1{10}$/.test(n)) return false;
```

Salve e rode a bateria. O caso 1.4 deve virar PASSOU. Esse é o loop de trabalho real:
testa, corrige, retesta.

**Quebre algo de propósito** e confira se o teste pega. Faça a validação de CEP aceitar
qualquer coisa e veja o caso 5.1 virar FALHOU. Um teste que não falha quando você
introduz um bug não está testando nada.

---

## Problemas comuns

**`ERR_CONNECTION_REFUSED`** — o servidor do passo 2 não está rodando.

**`can't open file '...runner.py'`** — o terminal não está em `loja-girassol`. Veja o
passo 3.

**"campo sob teste não encontrado"** — o seletor no plano não bate com o HTML. Abra a
página, F12, botão direito no campo → Copiar → Copiar seletor.

**Tudo passou, mas você sabe que tem bug** — falta `preenchimento_base` ou `campo_alvo`
no plano. Sem eles, os erros de outros campos mascaram o campo testado e o runner aprova
tudo.

**`UnicodeEncodeError`** — o runner já corrige o encoding do terminal sozinho. Se ainda
acontecer, rode `chcp 65001` antes.
