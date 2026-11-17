# Playbook de casos por tipo de campo

Use este arquivo no Passo 2 (expansão dos cenários). Identifique o tipo do campo citado
pelo desenvolvedor e aplique os casos correspondentes. Não é obrigatório rodar todos —
corte os que claramente não se aplicam ao contexto e diga ao dev o que cortou.

## Índice

- [Universais](#universais-valem-para-qualquer-campo)
- [CPF](#cpf) · [CNPJ](#cnpj) · [E-mail](#e-mail) · [Senha](#senha)
- [Telefone](#telefone) · [CEP e endereço](#cep-e-endereço) · [Data de nascimento](#data-de-nascimento)
- [Cartão de crédito](#cartão-de-crédito) · [Quantidade e valores](#quantidade-e-valores)
- [Cupom de desconto](#cupom-de-desconto) · [Busca](#busca) · [Upload](#upload)
- [Fluxos](#fluxos-multi-etapa) · [Sanitização de entrada](#sanitização-de-entrada)

---

## Universais (valem para qualquer campo)

| Caso | Esperado |
|------|----------|
| Campo vazio + submit | Bloqueia, mensagem de campo obrigatório visível e associada ao campo |
| Só espaços em branco | Tratado como vazio, não como preenchido |
| Espaços antes/depois do valor válido | Faz trim e aceita |
| Colar (Ctrl+V) em vez de digitar | Máscara e validação funcionam igual |
| Autocompletar do navegador | Valor preenchido dispara a validação |
| Valor acima do limite de caracteres | Trunca ou avisa, nunca envia e quebra no backend |
| Submit duplo (clique rápido 2x) | Não cria registro/pedido duplicado |
| Navegação por Tab | Ordem lógica, campo recebe foco visível |

## CPF

| Caso | Entrada de exemplo | Esperado |
|------|--------------------|----------|
| Vazio | | Obrigatório |
| Válido com máscara | `529.982.247-25` | Aceita |
| Válido sem máscara | `52998224725` | Aceita ou formata |
| Dígito verificador errado | `529.982.247-26` | Rejeita: "CPF inválido" |
| Todos os dígitos iguais | `111.111.111-11` | Rejeita — armadilha clássica, o DV bate mas o CPF não existe |
| Incompleto | `529.982.247` | Rejeita / impede submit |
| Com letras | `abc.def.ghi-jk` | Campo não aceita ou rejeita |
| Caracteres especiais | `529@982#247$25` | Rejeita |
| Máscara em tempo real | digitar `52998224725` | Vira `529.982.247-25` |
| Apagar do meio | remover dígitos com Backspace | Máscara se reajusta sem travar o cursor |
| Duplicado | CPF já cadastrado | Rejeita: "já cadastrado" — e não vaza dados do titular existente |
| Excesso de dígitos | `529982247251` | Não aceita o 12º dígito |

## CNPJ

Mesma estrutura do CPF, trocando: válido `11.222.333/0001-81`, DV errado
`11.222.333/0001-82`, todos iguais `11.111.111/1111-11`, incompleto, com letras, máscara
em tempo real, duplicado. Se o formulário alterna PF/PJ, teste também a **troca de tipo**:
preencher CPF, mudar para PJ, e conferir se o campo limpa e revalida.

## E-mail

| Caso | Entrada | Esperado |
|------|---------|----------|
| Válido | `teste@exemplo.com.br` | Aceita |
| Sem @ | `testeexemplo.com` | Rejeita |
| Sem domínio | `teste@` | Rejeita |
| Sem TLD | `teste@exemplo` | Rejeita |
| Espaço no meio | `tes te@exemplo.com` | Rejeita |
| Maiúsculas | `TESTE@EXEMPLO.COM` | Aceita, normaliza para minúsculo |
| Acento | `usuário@exemplo.com` | Definir a regra com o dev e testar consistente |
| Duplicado | e-mail já cadastrado | Rejeita sem revelar dados da conta existente |
| Confirmação de e-mail | campos divergentes | Rejeita |

## Senha

| Caso | Esperado |
|------|----------|
| Abaixo do mínimo | Rejeita, informa a regra **antes** do submit |
| Sem maiúscula / número / símbolo (se exigido) | Rejeita, indica qual regra falta |
| Só espaços | Rejeita |
| Muito longa (200+ chars) | Aceita ou trunca com aviso — nunca erro 500 |
| Confirmação divergente | Rejeita |
| Botão "mostrar senha" | Alterna corretamente |
| Senha visível no HTML/DOM | Não deve estar em texto puro em atributo |

## Telefone

Válido `(61) 99999-9999`; DDD inexistente `(00) 99999-9999` deve rejeitar; celular com 8
dígitos vs 9 dígitos conforme a regra do projeto; fixo vs celular; máscara ajustando ao
digitar o 9º dígito; letras rejeitadas; com `+55` na frente.

## CEP e endereço

| Caso | Esperado |
|------|----------|
| CEP válido | Preenche rua/bairro/cidade/UF automaticamente |
| CEP inexistente (`99999-999`) | Mensagem clara, não trava a tela |
| CEP incompleto | Não dispara a busca |
| API de CEP fora do ar | Permite preenchimento manual (teste com a rede offline) |
| Editar campo autopreenchido | Permite ou bloqueia — conforme a regra, mas de forma consistente |
| Número vazio | Obrigatório, ou aceita "S/N" |
| Complemento vazio | Opcional |
| Entrega ≠ cobrança | Ambos os endereços persistem corretamente |

## Data de nascimento

Data válida; data futura (rejeita); 31/02 (rejeita); menor de 18 anos (conforme a regra do
produto); idade absurda (150 anos); formato `dd/mm/aaaa` vs `aaaa-mm-dd`; máscara.

## Cartão de crédito

Use **apenas números de teste de sandbox**, nunca cartão real.

| Caso | Esperado |
|------|----------|
| Número válido (passa no Luhn) | Aceita |
| Número que falha no Luhn | Rejeita antes de enviar ao gateway |
| Bandeira detectada | Ícone/bandeira muda conforme o BIN digitado |
| Validade no passado | Rejeita |
| Validade inválida (mês 13) | Rejeita |
| CVV com 3 vs 4 dígitos | Amex usa 4, demais 3 |
| Nome do titular vazio | Obrigatório |
| Nome com número | Rejeita |
| Parcelamento | Valor da parcela × nº de parcelas bate com o total |
| Cartão recusado (sandbox) | Mensagem clara, pedido **não** é criado como pago |
| Número visível em log/console | Não deve aparecer — verifique o console do navegador |

## Quantidade e valores

Zero; negativo; decimal onde só cabe inteiro; acima do estoque; acima do limite por
pedido; alterar quantidade e conferir se o subtotal recalcula; remover último item
(carrinho volta ao estado vazio corretamente).

## Cupom de desconto

Cupom válido; expirado; inexistente; já usado (uso único); cupom válido mas abaixo do
valor mínimo; aplicar dois cupons; aplicar e depois esvaziar o carrinho (desconto some);
desconto maior que o total (não pode gerar total negativo).

## Busca

Termo existente; inexistente (mensagem de vazio, não tela em branco); com acento; sem
acento; com erro de digitação; termo muito longo; caracteres especiais; busca vazia.

## Upload

Formato permitido; formato proibido (`.exe`); acima do tamanho máximo; arquivo de 0 byte;
nome com acentos e espaços; cancelar no meio do upload.

## Fluxos multi-etapa

Quando o cenário for um fluxo (compra, cadastro em etapas, recuperação de senha), teste:

1. **Caminho feliz** completo, do início ao fim.
2. **Voltar** uma etapa — os dados preenchidos continuam lá?
3. **Recarregar** a página no meio — perde tudo ou recupera?
4. **Abrir em outra aba** e continuar — o estado conflita?
5. **Pular etapa pela URL** — dá para acessar o pagamento sem endereço?
6. **Sessão expirada** no meio do fluxo.
7. **Condição de corrida**: estoque acaba entre adicionar ao carrinho e finalizar.
8. **Confirmação**: pedido aparece no histórico, e-mail dispara, status correto.

## Sanitização de entrada

Verificação padrão de QA para confirmar que a aplicação **escapa** o que recebe. Rode
apenas em ambiente próprio ou autorizado.

| Entrada | Esperado |
|---------|----------|
| `<script>alert(1)</script>` no nome | Salvo e exibido como texto literal, sem executar |
| `' OR '1'='1` no login | Login falha normalmente, sem erro de banco na tela |
| Emoji e acentuação (`José 🎉`) | Salvo e exibido corretamente, sem virar `Jos?` |
| String de 5000 caracteres | Truncada ou rejeitada com mensagem — nunca erro 500 |

Se qualquer um desses devolver stack trace, mensagem do banco de dados ou erro 500 na
tela, registre como **severidade alta**: além do bug em si, a mensagem entrega detalhes
da infraestrutura.
