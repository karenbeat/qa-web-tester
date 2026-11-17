---
name: qa-web-tester
description: Testador de QA para aplicações web, com foco em e-commerce brasileiro. Faz dois tipos de trabalho: (1) validação de formulário — recebe cenários em linguagem natural, expande em casos concretos (campo vazio, formato inválido, máscara, limites) e executa no navegador; (2) auditoria de site — verifica links quebrados, tempo de carregamento e responsividade em desktop, tablet e mobile. Use esta skill sempre que o usuário mencionar testar um site, validar um formulário, QA, homologação, testar checkout ou cadastro, validar CPF/CNPJ/CEP/cartão, verificar links quebrados, medir performance de página, testar responsividade ou layout mobile — mesmo que não use a palavra "QA".
---

# QA Web Tester

Esta skill transforma cenários escritos em linguagem natural em uma bateria de testes
executada de verdade no navegador, e devolve um relatório de bugs com evidências.

O princípio central: **quem manda é o cenário do desenvolvedor.** A skill não tem uma
lista fixa de coisas para testar. Ela pega o que foi descrito no prompt e expande cada
item em casos de teste concretos, usando os playbooks de campo como munição.

## Autorização

Só execute testes contra ambientes que o usuário possui ou tem autorização explícita
para testar (localhost, staging, homologação, ou produção do próprio projeto). Se a URL
apontar para um site de terceiros, pergunte antes de rodar qualquer coisa.

Nunca preencha formulários com CPF, cartão ou dados pessoais reais. Use apenas os dados
sintéticos gerados por `scripts/gerar_dados.py`.

---

## Fluxo de trabalho

### Passo 1 — Perguntar o cenário

Quando a skill é ativada, a primeira coisa a fazer é perguntar ao desenvolvedor quais
são os cenários de teste. Use exatamente esta pergunta (adapte só se o usuário já tiver
descrito o cenário na mensagem que ativou a skill):

> **Qual é o cenário de testes?**
>
> Descreva em tópicos o que você quer que eu teste. Exemplo:
> - Cenário 1: validar o campo CPF do formulário de cadastro
> - Cenário 2: finalizar uma compra com cartão de crédito
> - Cenário 3: aplicar um cupom expirado no carrinho
>
> Me passe também:
> - **URL** do ambiente (localhost, staging ou produção)
> - **Credenciais de teste**, se precisar de login
> - Alguma **regra de negócio** específica que eu deva conhecer

Não invente cenários. Se o desenvolvedor não passar URL, pergunte antes de prosseguir —
sem URL não há como executar nada.

### Passo 1b — Perguntar o tipo de teste e o modo de execução

Depois de receber os cenários, confirme duas coisas antes de montar qualquer plano.

**Qual tipo de teste.** A skill faz dois trabalhos diferentes, e o cenário do
desenvolvedor pode pedir um, outro ou os dois:

- **Validação de formulário** (`scripts/runner.py`) — campos, máscaras, regras de
  negócio, fluxo de compra. É o que os Passos 2 a 5 descrevem.
- **Auditoria de site** (`scripts/auditor.py`) — links quebrados, tempo de carregamento
  e responsividade em desktop, tablet e mobile. Ver a seção "Auditoria de site" abaixo.

Se o cenário fala de "validar CPF" ou "testar checkout", é validação. Se fala de "links
funcionando", "tempo de carregamento", "abre bem no celular" ou "responsividade", é
auditoria. Se pedir os dois, rode a auditoria primeiro: se a página nem carrega ou quebra
no mobile, testar campo a campo é perda de tempo.

**Como executar.** Pergunte ao desenvolvedor, porque a escolha muda a experiência:

> Como você prefere acompanhar o teste?
> - **Navegador visível** — você vê cada campo sendo preenchido. Bom para entender o que
>   está sendo testado ou demonstrar para alguém. Mais lento.
> - **Em segundo plano** — sem janela, bem mais rápido. Bom para rodar a bateria inteira
>   ou repetir depois de uma correção.

O padrão do `runner.py` é visível; `--headless` roda em segundo plano. No `auditor.py` é
o contrário: o padrão é em segundo plano e `--visivel` abre a janela. Para acompanhar
visualmente com calma, acrescente `--slow-mo 200` ao runner.

Não decida sozinho: alguém que pediu para "ver o teste rodando" fica frustrado com uma
execução headless, e alguém repetindo a bateria pela quinta vez não quer esperar a
animação.

### Passo 2 — Expandir os cenários em um plano de teste

Cada cenário descrito vira vários casos de teste concretos. Essa expansão é o coração da
skill: o desenvolvedor escreve uma linha, você devolve oito casos.

Para expandir, identifique de que **tipo** é cada campo ou ação mencionada e aplique o
playbook correspondente de `references/playbook-campos.md`. Para as regras de validação
brasileiras (CPF, CNPJ, CEP, cartão, telefone), consulte `references/validacoes-br.md`.

**Exemplo de expansão:**

Cenário do dev:
```
Cenário 1: validar o campo CPF do formulário de cadastro
```

Plano gerado:
| # | Caso | Entrada | Resultado esperado |
|---|------|---------|--------------------|
| 1.1 | Campo vazio | `` | Bloqueia envio, exibe mensagem de obrigatório |
| 1.2 | CPF válido com máscara | `529.982.247-25` | Aceita |
| 1.3 | CPF válido sem máscara | `52998224725` | Aceita (ou aplica máscara automaticamente) |
| 1.4 | Dígito verificador errado | `529.982.247-26` | Rejeita com mensagem de CPF inválido |
| 1.5 | Todos os dígitos iguais | `111.111.111-11` | Rejeita |
| 1.6 | Menos de 11 dígitos | `529.982.247` | Rejeita / não permite envio |
| 1.7 | Letras no campo | `abc.def.ghi-jk` | Campo não aceita letras |
| 1.8 | Máscara automática | digitar `52998224725` | Formata para `529.982.247-25` enquanto digita |
| 1.9 | CPF duplicado | CPF já cadastrado | Rejeita com mensagem de já cadastrado |

**Sempre mostre o plano ao desenvolvedor e peça confirmação antes de executar.** Ele pode
querer remover casos que não se aplicam ou acrescentar regras de negócio que você não
tinha como saber. Pergunte também se ele quer que casos destrutivos (criar pedido real,
enviar e-mail, cobrar cartão) sejam executados ou apenas simulados.

### Passo 3 — Gerar os dados de teste

Rode `scripts/gerar_dados.py` para produzir CPFs, CNPJs, cartões e CEPs válidos e
inválidos. Nunca escreva esses números "de cabeça" — CPF inventado quase sempre tem
dígito verificador errado, o que faz um teste de "CPF válido" falhar por culpa do teste,
não do sistema.

```bash
python scripts/gerar_dados.py --formato json > dados_teste.json
```

### Passo 4 — Executar no navegador

Use `scripts/runner.py` como base. Ele abre o navegador com Playwright, executa cada caso
do plano e captura evidência.

Regras de execução que evitam falsos positivos:

- **Um caso por vez, com estado limpo.** Limpe o campo (ou recarregue a página) entre
  casos. Resíduo de um teste anterior é a causa número um de resultado errado.
- **Espere a validação acontecer.** Muitos formulários validam no `blur` ou no submit.
  Clique fora do campo ou tente enviar antes de concluir que "não validou".
- **Procure a mensagem de erro, não só o bloqueio.** Um campo que bloqueia sem explicar
  o motivo é um bug de usabilidade — registre como severidade baixa.
- **Capture screenshot de cada falha.** Sem evidência, o dev não consegue reproduzir.
- **Se o seletor não for encontrado, isso é um resultado**, não um crash. Registre como
  "não foi possível localizar o campo" e siga para o próximo caso.

### Passo 5 — Relatar

Use o template de `assets/template-relatorio.md`. O relatório precisa ser acionável: cada
falha deve dizer o que foi digitado, o que aconteceu e o que deveria ter acontecido.

Classifique a severidade assim:

- **Crítica** — aceita dado inválido e persiste no banco, ou permite fechar pedido sem
  pagamento válido. Gera prejuízo ou dado sujo.
- **Alta** — validação ausente ou incorreta que bloqueia um usuário legítimo, ou expõe
  erro de sistema (stack trace, erro 500) na tela.
- **Média** — máscara quebrada, mensagem de erro confusa, validação só no backend
  causando ida e volta desnecessária.
- **Baixa** — texto de mensagem, alinhamento, foco do campo, ordem de tabulação.

No fim do relatório, some quantos casos passaram e quantos falharam, e liste os bugs em
ordem de severidade. Não amenize resultado: se um campo de CPF aceita `111.111.111-11`,
isso é crítico mesmo que o resto do formulário esteja perfeito.

---

## Arquivos de apoio

| Arquivo | Quando ler |
|---------|-----------|
| `references/playbook-campos.md` | Ao expandir cenários — tem a lista de casos por tipo de campo (CPF, e-mail, senha, cartão, CEP, upload, etc.) |
| `references/validacoes-br.md` | Quando precisar da regra exata de CPF, CNPJ, CEP, cartão (Luhn), telefone |
| `scripts/gerar_dados.py` | Passo 3, sempre |
| `scripts/runner.py` | Passo 4, como base da automação |
| `assets/template-relatorio.md` | Passo 5 |

## Quando o cenário não é sobre campos

Nem todo cenário é formulário. Se o dev pedir "Cenário 2: finalizar uma compra", trate
como um **fluxo**: liste os passos (adicionar ao carrinho → login → endereço → frete →
pagamento → confirmação), e em cada passo verifique tanto o caminho feliz quanto o que
acontece ao interromper (voltar, recarregar, abrir em outra aba, estoque acabando no meio).
O playbook tem uma seção para fluxos.

---

## Isolamento do campo — o erro que faz o teste mentir

Este é o ponto onde automação de QA falha silenciosamente, então vale entender antes de
escrever qualquer plano.

Um formulário com cinco campos obrigatórios dispara erro em **todos** eles quando você
envia com um campo só preenchido. Se o runner apenas perguntar "apareceu alguma mensagem
de erro na página?", ele vai concluir que o campo sob teste foi validado — quando o erro
na verdade veio de outro campo. O resultado é uma bateria que passa 100% num formulário
cheio de bugs.

Para evitar isso, todo plano precisa de três coisas:

1. **`preenchimento_base`** — valores válidos para todos os campos, aplicados antes de
   cada caso. Assim só o campo sob teste fica em condição de erro.
2. **`campo_alvo`** — o seletor do campo testado, para o julgamento olhar o estado
   daquele campo (classe `is-invalid`, `aria-invalid`, mensagem associada) em vez da
   página inteira.
3. **`indicador_sucesso`** — um seletor que só aparece quando o envio dá certo. É
   evidência muito mais confiável do que a ausência de erro.

Uma quarta coisa importa quando o estado vive no navegador: **`limpar_storage`**.
Recarregar a página zera os campos do formulário, mas não o `localStorage`. Em carrinhos
e fluxos com estado salvo, sem limpar, o item adicionado num caso continua lá no caso
seguinte. O runner limpa por padrão; passe `"limpar_storage": false` no plano se precisar
preservar sessão entre casos.

---

## Economia de contexto

Uma bateria de QA gera muito texto, e quase todo ele é descartável. Siga estas regras
para a sessão não encher de saída que não agrega.

**Reaproveite o plano antes de gerar um.** Procure por `plano*.json` na pasta do projeto.
Se já existir um plano para os cenários pedidos, use direto e pule a expansão — é a fase
mais cara do processo. Só gere um novo quando o cenário for realmente novo, ou acrescente
casos ao existente em vez de recomeçar.

**Leia só a seção relevante do playbook.** `references/playbook-campos.md` tem um índice no
topo. Se o cenário fala de CPF e cartão, leia essas duas seções, não o arquivo inteiro.
O mesmo vale para `validacoes-br.md`.

**Apresente o plano de forma compacta.** Uma linha por caso, em lista simples:

```
1.1 #cpf  vazio                  -> bloqueia
1.2 #cpf  529.982.247-25         -> aceita
1.3 #cpf  111.111.111-11         -> bloqueia
```

Não desenhe tabelas com bordas para dezenas de casos — elas custam muitos tokens e não
ajudam a decidir. Agrupe por cenário e mostre o total ao fim.

**Rode com `--resumo --relatorio --headless`.** O `--resumo` imprime só as falhas e o
placar; o `--relatorio` faz o próprio runner escrever o `RELATORIO.md`, e o `--headless`
evita esperar a animação do navegador.

```bash
python scripts/runner.py plano.json --saida resultados --headless --resumo --relatorio
```

**Não leia o `resultados.json` inteiro.** Ele traz o estado de cada campo e trechos da
página — muito volume para pouca informação nova. A saída do `--resumo` já diz o que
falhou e por quê. Leia o JSON apenas quando precisar investigar um caso específico.

**Confira o plano antes de rodar.** O erro mais comum e mais caro é esquecer o clique no
botão de submit em formulários que só validam no envio: a bateria inteira roda, tudo dá
resultado errado, e você precisa refazer. Antes de executar, verifique se cada caso de
campo termina com uma ação `clicar` no botão de submit — exceto os de tipo `mascara` e
`verificacoes`, que não passam pelo envio.

---

## Auditoria de site

Trabalho diferente da validação de formulário. Use `scripts/auditor.py` quando o cenário
pedir links quebrados, tempo de carregamento ou responsividade.

```bash
python scripts/auditor.py https://site.com.br --saida auditoria --so-internos
python scripts/auditor.py --lote sites.txt --saida auditoria        # vários sites
python scripts/auditor.py https://site.com.br --visivel             # navegador na tela
python scripts/auditor.py https://site.com.br --pular-links         # só perf e layout
```

O script gera `RELATORIO-AUDITORIA.md` e screenshots em `auditoria/responsivo/`, um por
viewport e por site. Não é preciso ler o `auditoria.json` para redigir — o relatório já
sai pronto.

### O que ele mede

**Carregamento** — TTFB, First Contentful Paint, DOM carregado, carregamento completo,
peso total e os recursos mais pesados. Os limites (bom até 2,5 s, aceitável até 4 s) são
referência de contexto, não regra de aprovação.

**Links** — coleta todos os `<a href>`, normaliza, remove duplicatas e confere o status
HTTP de cada um usando a sessão do navegador (não `requests`, porque muitos e-commerces
devolvem 403 para cliente HTTP sem cookies, o que geraria falsos positivos aos montes).
Separa quebrados de redirecionamentos: redirecionar não é erro, mas em link interno
costuma indicar URL desatualizada.

**Responsividade** — renderiza em 1920, 768 e 390 px e procura o que dá para verificar com
confiança: overflow horizontal (a página mais larga que a tela), ausência de
`<meta name=viewport>`, fonte abaixo de 12 px e alvos de toque menores que 44×44 px.

### O que ele não mede

Seja explícito com o desenvolvedor sobre isto, senão o relatório passa uma sensação falsa
de cobertura completa:

- **Estética e hierarquia visual** — alinhamento, espaçamento, contraste, se o layout
  "ficou bonito". Os screenshots existem para revisão humana; use-os.
- **Conteúdo carregado por rolagem** — carrosséis, lazy loading e seções que só aparecem
  depois de scroll não são exercitados.
- **Links atrás de login ou interação** — só os presentes no HTML inicial são coletados.
- **Performance percebida** — a medição é de uma execução, numa rede, num momento. Para
  número confiável, rode três vezes e compare, ou use uma ferramenta dedicada.

### Cuidado com o volume

Verificar links gera uma requisição por link. Num e-commerce grande isso é tráfego real
no servidor de produção de alguém. Use `--max-links` para limitar, `--so-internos` para
focar no que é responsabilidade do time, e mantenha o `--intervalo` padrão. Se o site for
de produção e alguém monitorar tráfego, avise antes.

### Armadilhas de site real

A auditoria lida automaticamente com três coisas que não existem em página de teste mas
aparecem em todo e-commerce:

**Banner de LGPD.** É fechado antes de medir. Sem isso ele cobre a tela, arruína o
screenshot e frequentemente usa `position:fixed` mais largo que a viewport, gerando falso
overflow. Se o site usar uma plataforma de consentimento não coberta, o banner aparece nos
screenshots — nesse caso, avise o desenvolvedor em vez de tratar como bug de layout.

**Lazy loading.** A página é rolada até o fim e de volta ao topo antes de coletar links e
medir layout. Em e-commerce, metade do conteúdo e boa parte dos links só existem depois do
scroll. Use `--sem-rolagem` para pular isso quando quiser velocidade.

**Timeout no evento `load`.** Site pesado com muito script de terceiro às vezes nunca
dispara `load`. Em vez de abortar, a auditoria segue com o que já renderizou e registra a
observação no relatório.

Uma medição de overflow depende da largura configurada da viewport, não de
`window.innerWidth`: em emulação mobile o Chromium expande a viewport quando o conteúdo
estoura, e perguntar ao navegador devolve a largura do conteúdo em vez da tela — o que faz
o overflow nunca ser detectado justamente quando ele existe.
