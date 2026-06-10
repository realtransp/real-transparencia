# Como contribuir

Obrigado pelo interesse! Este projeto é mantido pela comunidade e toda ajuda conta:
código, dados, design, texto, revisão ou só uma boa ideia.

## O fluxo, em 5 passos

1. **Escolha uma issue** em [Issues](../../issues). As marcadas com
   [`good first issue`](../../labels/good%20first%20issue) são as melhores portas de entrada;
   as com [`help wanted`](../../labels/help%20wanted) são onde mais precisamos de gente.
2. **Comente na issue dizendo que vai pegar** ("vou trabalhar nessa"). Isso evita duas
   pessoas fazendo a mesma coisa. Se uma issue está sem movimento há mais de 2 semanas,
   pode assumir.
3. **Faça o fork e crie um branch** com nome descritivo (`cobranca-no-x`, `mascara-cpf`).
4. **Abra o PR cedo**, mesmo incompleto (marque como draft). O CI roda os testes
   automaticamente. Descreva o que mudou e linke a issue (`Closes #12`).
5. Um mantenedor revisa, conversa se precisar e faz o merge. O deploy em produção é
   manual e acontece depois do merge.

Tem uma ideia que não está nas issues? Abra uma issue nova antes de codar, pra gente
alinhar (e ninguém perder trabalho).

## Rodando o projeto

```bash
uv sync                                   # dependências (use uv, não pip)
uv run python -m app.ingest sample        # popula um SQLite local via API (1-2 min)
uv run uvicorn app.main:app --reload      # http://127.0.0.1:8000
```

Testes (rode antes de abrir o PR):

```bash
uv sync --extra dev
uv run pytest
```

## Padrões do projeto

- **Linguagem da interface: português claro.** Nada de jargão jurídico sem explicação.
  O público é qualquer cidadão, não especialista.
- **Neutralidade.** O site mostra o dado e deixa a pessoa julgar. Nada partidário, nada
  acusatório: em especial, nunca usar palavras como "fraude" ou acusações de crime.
  Mostramos fatos com fonte oficial; o leitor tira as conclusões.
- **Fontes oficiais, sem raspagem de HTML.** Dados entram por API ou arquivos abertos
  (Câmara, TSE, Senado, SICONFI). Sempre linkar a fonte primária.
- **SQL portável.** Tudo roda em SQLite (local) e Postgres (produção). Evite funções
  específicas de um banco; o smoke de testes pega a maioria dos casos.
- **Sem travessão (—) em texto.** Use vírgula, dois-pontos ou parênteses.
- **Ingestão idempotente.** Rodar duas vezes não pode duplicar nem apagar histórico
  (os testes de `tests/test_ingest_idempotency.py` mostram o padrão).
- Python 3.11+, sem build de front-end: FastAPI + Jinja2 + HTMX, CSS próprio em
  `app/static/` (referência visual em `design_system/`).

## Dados pessoais

Cuidado redobrado com LGPD: não exibir CPF completo de pessoa física, não coletar
dados pessoais de visitantes (as sugestões são anônimas de propósito) e não adicionar
rastreadores além do estritamente necessário.
