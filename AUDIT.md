# Auditoria — R$ Transparência

Auditoria de **correção** (não mostrar nada errado), **usabilidade** e correção do
**filtro de deputado** na página `/relatorio`.

Ambiente: branch `audit`, banco real `resumo_real.db` (2022–2026), data de referência 2026-05.
Status de cada item: **[CORRIGIDO]** aplicado neste worktree / **[RECOMENDA]** sugerido, não aplicado.

---

## 1. Bugs must-fix

### 1.1 [CORRIGIDO] 500 em `/relatorio?escopo=deputado&alvo=<não-numérico>`
- **Rota/evidência:** `GET /relatorio?escopo=deputado&alvo=notanumber` → **500 Internal Server Error**.
  Traceback em `queries.py:579` `_scope_despesas` faz `int(alvo)` e estoura `ValueError` para qualquer `alvo` não numérico.
- **Causa:** a validação em `main.py` só checava `escopo in (...)` e `alvo` truthy, mas não que `alvo` fosse um id numérico.
- **Correção:** `app/main.py` (rota `relatorio`) — se `escopo=='deputado'` e `alvo` não é dígito, volta ao escopo geral.
  Verificado: agora retorna **200**.

### 1.2 [CORRIGIDO] Filtro de deputado horrível (`<select>` com 513 nomes)
- **Rota:** `/relatorio` (template `relatorio.html`), terceiro controle do `.rx-filter`.
- **Problema:** `<select>` com 513 `<option>` para rolar — inviável de usar.
- **Correção:** trocado por **busca com autocomplete nativo** (`<input type="search" list>` + `<datalist>`).
  Ao escolher um nome navega para `/relatorio?escopo=deputado&alvo=ID&ano=ANO` (handler `rxPickDeputado` no próprio template;
  estilo `.rx-search` em `overrides.css`). Mantém o valor preenchido com o nome quando já há um deputado selecionado.
  É o **único** seletor gigante de deputado do app (os demais `<select>` são ano/mês/UF/partido, pequenos).

### 1.3 [CORRIGIDO] Busca de deputado só casava o nome, mas o placeholder promete "nome, partido ou estado"
- **Rota:** `/` (hero) e `/deputados` (campo `busca`). Placeholder: "Busque por nome, partido ou estado…".
- **Problema:** `list_deputados` filtrava apenas `nome ILIKE`. Buscar "PT" ou "SP" não filtrava por partido/UF (retornava nomes que contêm essas letras).
- **Correção:** `queries.list_deputados` agora casa `nome`, `nome_eleitoral`, `sigla_partido` e `sigla_uf`.
  Verificado: `?busca=PT` retorna a bancada do PT.

---

## 2. Dados / consistência (verificado — em geral OK)

Conferências feitas direto no banco vs. telas:

- **Home / Raio-X geral 2026:** 513 deputados, 45.608 votações, 27.103 "Sim" / 15.269 "Não" — batem com o banco. OK.
- **Perfil × /gastos × Raio-X (deputado 221329, Ricardo Abrão, 2026):** gasto R$ 99.378,70 (mostrado "R$ 99k") idêntico nas três telas;
  limite anual RJ R$ 567k e 17,5% coerentes; votos 55 Sim / 24 Não consistentes. OK.
- **Votação `2351506-122`:** placar do cabeçalho (368 a 96) = soma dos votos individuais = `votos_sim/votos_nao` armazenados. Recorte por partido coerente. OK.
- **Soma de categorias ≈ total, fornecedores:** coerentes nas amostras (`/relatorio/categoria/TELEFONIA`).
- **Vote mapping:** `_SIM=["Sim"]`, `_NAO=["Não","Nao"]` cobre os valores reais do banco ("Sim"/"Não"). OK.

### 2.1 [RECOMENDA] "Presença em plenário" mistura anos; o resto do perfil é só do ano corrente
- **Rota/evidência:** `/deputados/{id}`. Hero mostra "**36,9%** Presença em plenário" ao lado de "**79** Votações em **2026**", "Cota gasta · 2026".
- **Causa:** `deputado_presenca()` (queries.py) **não filtra por ano** — soma plenárias de 2023+2025+2026 (ex.: dep 221329 = 142+296+128 eventos).
  Os demais KPIs do hero são de 2026. Além disso o modal "Cobrar" (`app.js`, template de presença) diz
  "presença de 36,9% nas sessões do plenário" sugerindo que é atual.
- **Risco:** número correto em si (mandato inteiro), mas **enganoso ao lado dos números de 2026** — usuário lê como "presença em 2026".
- **Recomendação:** ou (a) filtrar a presença pelo mesmo ano dos outros KPIs, ou (b) rotular claramente "Presença no mandato (desde 2023)".
  Não alterei a semântica por ser decisão de produto.

### 2.2 [RECOMENDA] "Votações em {ano}" usa 2 denominadores diferentes (presença vs. nominais)
- O hero/aba "Participou: 79 de 121" usa votações **nominais** do ano (denominador 121), enquanto a "Presença em plenário" usa **eventos de plenário** (heurística ≥100 deputados). São métricas distintas com nomes parecidos ("presença"/"participou"); vale uma nota explicativa para não parecer contradição (65% vs 36,9%).

### 2.3 [RECOMENDA] Limite anual da CEAP é estimativa (mensal × 12) e o reajuste 2026 é estimado
- `ceap.py` documenta isso, e o template já diz "~limite ... (12× o limite mensal)". Mantido. Apenas garantir que o texto "estimativa" continue visível onde o % de cota aparece (já está em `/deputados/{id}/gastos`).

---

## 3. UX — priorizado

### [CORRIGIDO]
1. **Filtro de deputado** virou autocomplete (item 1.2) — maior ganho de usabilidade da auditoria.
2. **Busca por partido/UF** passou a funcionar conforme o placaholder promete (item 1.3).

### [RECOMENDA] (não aplicado — exige decisão de design/produto)
3. **Overflow horizontal em 375px** no `/relatorio`: o `.metric-strip` e o `<h1>` vazam à direita no celular
   (faixa de métricas não quebra; título cortado). Recomendo `.metric-strip` rolar/empilhar e `overflow-x:hidden` no container em telas estreitas.
4. **Rótulo "Presença em plenário"** no perfil deveria deixar claro o período (ver 2.1) para não conflitar visualmente com os KPIs de 2026.
5. **Nomenclatura de navegação:** "Raio-X" é jargão; para o público leigo, considerar "Gastos" ou "Panorama" como rótulo (o dono achou tudo confuso).
   O link de rodapé "Gastos da cota" aponta para `/gastos` que **redireciona** para `/relatorio` — ok, mas dois nomes para o mesmo lugar confunde.

---

## Resumo do que foi corrigido neste worktree
- `app/main.py` — guarda contra `alvo` não numérico em `escopo=deputado` (corrige 500).
- `app/templates/relatorio.html` — `<select>` de 513 nomes → busca/autocomplete (`<datalist>`) + handler `rxPickDeputado`.
- `app/static/overrides.css` — estilo `.rx-search` / `.rx-search-input`.
- `app/queries.py` — `list_deputados` busca também por `nome_eleitoral`, partido e UF.
