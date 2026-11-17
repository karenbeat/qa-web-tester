# Bugs plantados na Loja Girassol

**Não leia antes de rodar o teste.** O objetivo é conferir se o agente acha os defeitos
sozinho. Ler antes contamina o exercício.

Resultado esperado:
- `plano-checkout.json` → **10 passou, 13 falhou**
- `plano-carrinho.json` → **2 passou, 3 falhou**

---

## Checkout (checkout.html)

| # | Onde | Defeito | Caso que pega |
|---|------|---------|---------------|
| 1 | Cupom | Não verifica a data de expiração — `VERAO2024` (expirado em 03/2024) é aplicado | 4.1 |
| 2 | Cupom | Não limita o desconto ao valor do pedido — `SUPER500` deixa o total em R$ -264,70 | 4.3 |
| 3 | Cartão | O campo não aplica máscara nenhuma | observado |
| 4 | CEP | Quando o CEP não existe, não avisa nada e não limpa a rua da consulta anterior | 5.2 |
| 5 | CPF | Valida os dígitos verificadores mas aceita sequências repetidas (`111.111.111-11`) | 1.4 |
| 6 | Nome | Verifica `length === 0` sem fazer trim, então três espaços passam | 2.3 |
| 7 | E-mail | Só exige um `@`, aceitando `cliente@` e `cliente@exemplo` | 2.1, 2.2 |
| 8 | Telefone | Confere só a quantidade de dígitos, não valida o DDD | 2.4 |
| 9 | Cartão | Aceita qualquer sequência de 13 a 19 dígitos, sem checar o algoritmo de Luhn | 3.1, 3.2 |
| 10 | Validade | Confere só o formato `MM/AA`, aceitando mês 13 e data no passado | 3.3, 3.4 |
| 11 | CVV | Aceita de 1 a 4 dígitos em vez de exigir 3 | 3.5 |

## Loja (index.html) — cobertos por `plano-carrinho.json`

| # | Onde | Defeito | Caso que pega |
|---|------|---------|---------------|
| 12 | Carrinho | Permite adicionar produto esgotado (Fita adesiva, estoque 0) | 8.1 |
| 13 | Carrinho | Aceita quantidade negativa, deixando o total em R$ -164,50 | 8.2 |
| 14 | Carrinho | Não limita a quantidade ao estoque disponível (aceita 99 de um item com 3) | 8.3 |

Os casos 8.4 e 8.5 são caminho feliz (adicionar e remover item) e devem passar.

## O padrão por trás dos bugs

Repare que 5, 8, 9, 10 e 11 são a mesma falha de raciocínio: a validação confere
**formato** e ignora **conteúdo**. Contar dígitos do CVV aceita `1`. Um regex de `MM/AA`
aceita mês 13. Checar o comprimento do cartão aceita `1111111111111111`.

Isso é comum em código real, e é o tipo de coisa que uma bateria de QA pega rápido —
desde que os casos de teste incluam valores que passam no formato mas não fazem sentido.
