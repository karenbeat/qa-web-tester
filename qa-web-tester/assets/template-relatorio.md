# Relatório de QA — [Nome do projeto]

**Ambiente:** [URL testada]
**Data:** [data e hora]
**Cenários testados:** [lista dos cenários que o dev pediu]

## Resumo

| Resultado | Qtd |
|-----------|-----|
| Passou | |
| Falhou | |
| Atenção | |
| Erro de execução | |

[Uma ou duas frases dizendo o que mais preocupa. Seja direto: se um campo crítico
aceita dado inválido, isso vai aqui, mesmo que o resto esteja bom.]

## Bugs encontrados

Ordene por severidade: crítica → alta → média → baixa.

### BUG-01 · [Título curto do problema]

- **Severidade:** Crítica
- **Cenário:** Cenário 1 — validação de CPF
- **Caso:** 1.5
- **Passos para reproduzir:**
  1. Acessar [URL]
  2. Preencher o campo CPF com `111.111.111-11`
  3. Clicar em Cadastrar
- **Resultado obtido:** o cadastro foi concluído com sucesso
- **Resultado esperado:** rejeitar com mensagem "CPF inválido"
- **Evidência:** `evidencias/caso_1.5.png`
- **Observação:** [console, erro de rede, comportamento correlato]

### BUG-02 · [...]

## Casos que passaram

| # | Caso | Entrada | Resultado |
|---|------|---------|-----------|
| 1.1 | Campo vazio | (vazio) | Bloqueou com mensagem de obrigatório |

## Não foi possível testar

[Casos que deram erro de execução — seletor não encontrado, página fora do ar,
login falhou. Diga o que travou e o que você precisa do dev para destravar.]

## Sugestões

[Melhorias que não são bugs: mensagem confusa, validação só no submit quando
poderia ser no blur, falta de indicação de campo obrigatório.]
