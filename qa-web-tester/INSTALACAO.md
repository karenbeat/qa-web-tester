# Instalação e uso — Agente QA Web Tester

Guia para colocar a skill + agente rodando no Claude Code.

---

## 1. Instalar a skill

Copie a pasta `qa-web-tester/` para o diretório de skills do projeto:

```bash
mkdir -p .claude/skills
cp -r qa-web-tester .claude/skills/
```

Estrutura final:

```
seu-projeto/
└── .claude/
    └── skills/
        └── qa-web-tester/
            ├── SKILL.md
            ├── references/
            │   ├── playbook-campos.md
            │   └── validacoes-br.md
            ├── scripts/
            │   ├── gerar_dados.py
            │   └── runner.py
            └── assets/
                └── template-relatorio.md
```

Para usar em qualquer projeto (e não só nesse), instale em `~/.claude/skills/`.

## 2. Instalar as dependências

```bash
pip install playwright
python -m playwright install chromium
```

O segundo comando baixa o navegador (~150 MB). Roda uma vez só.

Prefira `python -m playwright` ao `playwright` direto: em muitas instalações o
executável não fica no PATH, e o erro resultante (`'playwright' não é reconhecido`)
parece falha de instalação quando na verdade o pacote está lá.

Verifique:

```bash
python -c "from playwright.sync_api import sync_playwright; print('ok')"
```

## 3. Testar o agente no sandbox antes do site real

Na pasta `sandbox/` tem um formulário com **bugs plantados de propósito**. Use ele para
confirmar que o runner está funcionando — se o agente não achar os bugs conhecidos,
o problema é na ferramenta, não no seu site.

```bash
cd sandbox
python -m http.server 8000
```

Abra outro terminal e rode:

```bash
python .claude/skills/qa-web-tester/scripts/runner.py \
    exemplo-plano.json --saida resultados/ --slow-mo 300
```

Os bugs que ele deve encontrar estão listados em `sandbox/BUGS-PLANTADOS.md`.
Confira depois de rodar — não olhe antes, para o teste ser honesto.

## 4. Usar de verdade

No Claude Code, dentro do projeto:

```
Preciso testar o formulário de cadastro do meu e-commerce.
```

A skill ativa e pergunta o cenário. Você responde em tópicos:

```
Cenário 1: validar o campo CPF do cadastro — trava para vazio,
           CPF inexistente, só números, máscara
Cenário 2: validar e-mail e confirmação de e-mail
Cenário 3: CEP deve autopreencher o endereço

URL: http://localhost:3000/cadastro
Ambiente: staging
Sem login necessário
```

A partir daí o agente:

1. Expande cada cenário num plano de casos e **mostra para você aprovar**
2. Gera os dados sintéticos
3. Escreve o `plano.json`
4. Roda o `runner.py`
5. Lê o `resultados.json` e escreve o relatório

## 5. Formato do plano.json

Se quiser escrever um plano à mão (ou revisar o que o agente gerou):

```json
{
  "url": "http://localhost:3000/cadastro",
  "login": {
    "url": "http://localhost:3000/login",
    "usuario": "qa@teste.com",
    "senha": "senha-de-teste",
    "seletor_usuario": "#email",
    "seletor_senha": "#senha",
    "seletor_botao": "button[type=submit]"
  },
  "casos": [
    {
      "id": "1.1",
      "cenario": "Validar campo CPF",
      "descricao": "Campo vazio deve bloquear o envio",
      "acoes": [
        {"tipo": "preencher", "seletor": "#cpf", "valor": ""},
        {"tipo": "clicar", "seletor": "button[type=submit]"}
      ],
      "esperado": "bloqueia",
      "mensagem_esperada": "obrigat"
    }
  ]
}
```

**Tipos de ação:** `preencher`, `clicar`, `selecionar`, `marcar`, `esperar`,
`navegar`, `recarregar`.

**Valores de `esperado`:** `bloqueia` (o sistema deve rejeitar), `aceita` (deve
passar), `mensagem` (só verifica se apareceu alguma mensagem).

O campo `login` é opcional — remova se a página for pública.

## 6. Achar os seletores

O agente precisa saber onde clicar. Três formas, da melhor para a pior:

1. **`data-testid`** no HTML — o ideal. Peça ao time para adicionar
   `data-testid="campo-cpf"` nos campos críticos; o teste para de quebrar
   quando alguém mexe no CSS.
2. **`id` ou `name`** — `#cpf`, `[name=cpf]`. Funciona bem.
3. **Classe CSS** — `.form-control:nth-child(3)`. Frágil: quebra a cada
   refatoração de layout.

Para descobrir: abra o site, F12, clique com o botão direito no campo →
Copiar → Copiar seletor.

## 7. Rodando em CI (opcional, depois)

Quando a bateria estiver estável, dá para rodar a cada deploy:

```yaml
# .github/workflows/qa.yml
- run: pip install playwright && playwright install --with-deps chromium
- run: python scripts/runner.py plano.json --saida resultados/ --headless
```

Use `--headless` no CI (não existe janela para abrir) e guarde a pasta
`resultados/` como artefato do build para consultar os screenshots depois.

---

## Cuidados

- **Nunca aponte para produção sem cortar o escopo.** Testes que criam pedido,
  disparam e-mail ou tocam no gateway precisam de staging.
- **Nunca use CPF, cartão ou e-mail reais.** O `gerar_dados.py` existe para isso.
- **Só teste ambientes que você possui ou tem autorização para testar.**
