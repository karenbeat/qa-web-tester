# Regras de validação — documentos e dados brasileiros

Consulte quando precisar da regra exata para decidir se o sistema testado acertou ou errou.

## CPF

11 dígitos. Os dois últimos são verificadores.

**Algoritmo:**
1. Remova pontuação. Se não sobrarem exatamente 11 dígitos, é inválido.
2. Se todos os dígitos forem iguais (`00000000000`, `11111111111`, …), é inválido —
   mesmo que os DVs "fechem" na conta.
3. **1º DV:** multiplique os 9 primeiros dígitos pelos pesos 10, 9, 8, 7, 6, 5, 4, 3, 2.
   Some. Calcule `resto = soma % 11`. Se `resto < 2`, DV = 0; senão DV = `11 - resto`.
4. **2º DV:** multiplique os 10 primeiros dígitos (incluindo o 1º DV) pelos pesos
   11, 10, 9, 8, 7, 6, 5, 4, 3, 2. Mesma regra do resto.

**Importante:** este algoritmo diz se o CPF é *matematicamente* válido, não se ele
*existe* na Receita Federal. Um CPF válido pelo cálculo pode não pertencer a ninguém. Se
o sistema afirma consultar a Receita, isso é uma integração à parte e precisa de teste
próprio (incluindo o comportamento quando a API está fora do ar).

**Máscara:** `000.000.000-00`

## CNPJ

14 dígitos. Dois últimos são verificadores.

1. Remova pontuação; exija 14 dígitos; rejeite todos iguais.
2. **1º DV:** pesos `5,4,3,2,9,8,7,6,5,4,3,2` sobre os 12 primeiros dígitos.
   `resto = soma % 11`; se `resto < 2` → 0, senão `11 - resto`.
3. **2º DV:** pesos `6,5,4,3,2,9,8,7,6,5,4,3,2` sobre os 13 primeiros.

**Máscara:** `00.000.000/0000-00`

Nota: existe um CNPJ alfanumérico previsto para entrar em vigor. Se o projeto precisar
suportá-lo, confirme a regra vigente com o desenvolvedor antes de testar — não assuma.

## Cartão de crédito — algoritmo de Luhn

1. Percorra os dígitos da direita para a esquerda.
2. Dobre cada segundo dígito. Se o resultado passar de 9, subtraia 9.
3. Some tudo. Se `soma % 10 == 0`, o número passa no Luhn.

Luhn detecta erro de digitação, não se o cartão existe ou tem saldo. Um número que passa
no Luhn ainda pode ser recusado pelo gateway — os dois casos precisam de teste separado.

**Bandeiras por prefixo (BIN) e comprimento:**

| Bandeira | Prefixo | Dígitos | CVV |
|----------|---------|---------|-----|
| Visa | 4 | 13 ou 16 | 3 |
| Mastercard | 51–55, 2221–2720 | 16 | 3 |
| Amex | 34, 37 | 15 | 4 |
| Elo | faixas específicas (consultar a operadora) | 16 | 3 |
| Hipercard | 606282 | 16 | 3 |

Use sempre os cartões de teste do sandbox do gateway usado no projeto (Stripe, Pagar.me,
Mercado Pago, Cielo etc.). Cada gateway publica números próprios que forçam aprovação,
recusa, timeout e fraude — teste todos esses estados, não só o de aprovação.

## CEP

8 dígitos, máscara `00000-000`. Um CEP com formato válido pode não existir; a validação
real depende da consulta a uma API (ViaCEP, BrasilAPI, Correios).

Pontos de teste que costumam passar batido:
- Comportamento quando a API demora ou cai — o formulário precisa permitir digitação manual.
- CEP geral de cidade (terminado em `-000`) — muitos retornam sem logradouro.
- Cache: mudar o CEP deve limpar os campos preenchidos pelo CEP anterior.

## Telefone

- Celular: 11 dígitos com DDD (`(61) 9XXXX-XXXX`), sempre iniciando com 9 após o DDD.
- Fixo: 10 dígitos (`(61) XXXX-XXXX`).
- DDDs válidos vão de 11 a 99, mas nem todos existem. DDD `00`, `01`, `10` são inválidos.

## E-mail

Não tente validar e-mail com regex perfeita — a especificação (RFC 5322) permite coisas
que nenhum formulário aceita na prática. O critério de teste é: tem exatamente um `@`,
tem algo antes, tem domínio com ponto e TLD depois, e não tem espaço. Casos ambíguos
(acento, `+alias`, subdomínio) devem ser decididos junto com o desenvolvedor e testados
de forma consistente com a decisão.
