# Relatório de QA — Loja Girassol

**Ambiente:** http://localhost:8000/checkout.html
**Cenários testados:** CPF · E-mail e nome · Pagamento · Cupom · CEP · Sanitização
**Casos executados:** 23

## Resumo

| Resultado | Qtd |
|-----------|-----|
| Passou | 10 |
| Falhou | 13 |
| Atenção | 0 |
| Erro de execução | 0 |

O checkout finaliza pedido com **cartão inválido, validade vencida e CVV de um dígito**.
Como o formulário não faz nenhuma dessas checagens no front, o pedido só será recusado
lá na frente pelo gateway — ou pior, será aceito e vira chargeback. Um cupom expirado
também é aplicado normalmente, e um cupom de valor fixo consegue deixar o total negativo.
Esses são os pontos que geram prejuízo direto.

---

## Bugs críticos

### BUG-01 · Cartão sem validação de Luhn é aceito

- **Severidade:** Crítica · **Casos:** 3.1, 3.2
- **Reproduzir:** preencher o checkout normalmente e usar o cartão `4539 5787 6362 1487`
  (um dígito alterado de um número válido). Também `1111 1111 1111 1111`.
- **Obtido:** pedido confirmado, com número gerado
- **Esperado:** rejeitar antes de enviar ao gateway, com "número de cartão inválido"
- **Impacto:** todo erro de digitação vira uma transação recusada no gateway. Alguns
  adquirentes penalizam taxa alta de recusa.

### BUG-02 · Validade vencida e mês inexistente são aceitos

- **Severidade:** Crítica · **Casos:** 3.3, 3.4
- **Reproduzir:** validade `01/20` (janeiro de 2020) ou `13/30` (mês 13)
- **Obtido:** pedido confirmado
- **Esperado:** rejeitar validade no passado e mês fora de 01–12
- **Observação:** o regex só confere o formato `MM/AA`, sem olhar os valores.

### BUG-03 · Cupom expirado é aplicado

- **Severidade:** Crítica · **Caso:** 4.1
- **Reproduzir:** aplicar o cupom `VERAO2024`, que expirou em 31/03/2024
- **Obtido:** "Cupom aplicado com sucesso", total caiu de R$ 235,30 para R$ 202,78
- **Esperado:** rejeitar com mensagem de cupom expirado
- **Impacto:** desconto indevido de R$ 32,52 por pedido. Se o código vazar, é prejuízo
  recorrente.

### BUG-04 · Cupom de valor fixo gera total negativo

- **Severidade:** Crítica · **Caso:** 4.3
- **Reproduzir:** aplicar `SUPER500` (R$ 500 de desconto) num pedido de R$ 235,30
- **Obtido:** total exibido como **R$ -264,70**
- **Esperado:** limitar o desconto ao valor do pedido, deixando o total em R$ 0,00
- **Impacto:** dependendo do gateway, um valor negativo pode virar estorno.

### BUG-05 · CPF com dígitos repetidos é aceito

- **Severidade:** Crítica · **Caso:** 1.4
- **Reproduzir:** informar `111.111.111-11`
- **Obtido:** pedido confirmado
- **Esperado:** rejeitar com "CPF inválido"
- **Observação:** o cálculo dos dígitos verificadores está correto (casos 1.3 e 1.6
  passaram), mas falta a checagem de sequência repetida — `111.111.111-11` satisfaz o
  algoritmo e por isso escapa. Corrigir com uma verificação de dígitos iguais antes do
  cálculo.

---

## Bugs de severidade alta

### BUG-06 · CVV aceita 1 dígito

- **Caso:** 3.5 · **Entrada:** `1` · **Obtido:** pedido confirmado
- **Esperado:** exigir 3 dígitos (4 para Amex)

### BUG-07 · Validação de e-mail exige apenas um arroba

- **Casos:** 2.1, 2.2 · **Entradas:** `cliente@` e `cliente@exemplo`
- **Obtido:** pedido confirmado nos dois casos
- **Esperado:** exigir domínio com ponto e TLD
- **Impacto:** confirmação de pedido nunca chega, e o cliente reclama de "não recebi nada".

### BUG-08 · Nome composto só de espaços passa como válido

- **Caso:** 2.3 · **Entrada:** `"   "` · **Obtido:** pedido confirmado
- **Esperado:** aplicar trim antes de checar se está vazio
- **Impacto:** pedido sem destinatário identificável na etiqueta de envio.

### BUG-09 · CEP inexistente é aceito sem aviso

- **Caso:** 5.2 · **Entrada:** `99999-999` · **Obtido:** pedido confirmado
- **Esperado:** avisar que o CEP não foi encontrado, e limpar os campos preenchidos pela
  consulta anterior
- **Impacto:** entrega com endereço inconsistente. Pior ainda quando o cliente troca o
  CEP e a rua antiga continua na tela.

---

## Bugs de severidade média

### BUG-10 · DDD inválido é aceito

- **Caso:** 2.4 · **Entrada:** `(00) 99999-8888` · **Obtido:** pedido confirmado
- **Esperado:** validar o DDD contra a faixa de 11 a 99 existente

### BUG-11 · Campo de cartão sem máscara

- Observado durante a execução: o campo aceita 16 dígitos corridos sem separação
- **Esperado:** formatar como `0000 0000 0000 0000` conforme o usuário digita
- **Impacto:** dificulta a conferência visual e aumenta erro de digitação — que, somado
  ao BUG-01, vira recusa no gateway

---

## Casos que passaram

| # | Caso | Resultado |
|---|------|-----------|
| 1.1 | CPF vazio | Bloqueou com "Informe o CPF" |
| 1.2 | CPF válido | Aceitou e concluiu |
| 1.3 | CPF com DV errado | Bloqueou com "CPF inválido" |
| 1.5 | Máscara do CPF | Formatou como `529.982.247-25` |
| 1.6 | CPF incompleto | Bloqueou com "CPF inválido" |
| 3.6 | Cartão válido | Aceitou e concluiu |
| 4.2 | Cupom inexistente | Rejeitou, total inalterado |
| 4.4 | Cupom válido GIRASSOL10 | Aplicou 10%, total foi para R$ 213,62 |
| 5.1 | CEP incompleto | Bloqueou com "CEP deve ter 8 dígitos" |
| 6.1 | Script no campo nome | Não executou, tratado como texto |

---

## Sugestões

O padrão que aparece nos bugs 01, 02, 05, 06 e 10 é o mesmo: a validação confere
**formato** e ignora **conteúdo**. Um regex de `MM/AA` aceita mês 13; contar dígitos do
CVV aceita `1`; checar comprimento do cartão aceita qualquer sequência. Vale revisar
todas as validações com essa lente antes de corrigir uma por uma.

As mensagens de erro estão boas — específicas por campo e associadas via
`aria-describedby`, o que ajudou o próprio runner a julgar corretamente. Manter esse
padrão nos campos que ainda não validam nada.

---

*Bateria executada pelo agente qa-web-tester. Evidências em `resultados/evidencias/`.*
