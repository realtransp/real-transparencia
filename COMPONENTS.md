# Design System — R$ Transparência

Documentação dos componentes, tokens e padrões do portal. Baseado no UI kit
`claude.ai/design` ("R$ Transparência"), aplicado ao app real (FastAPI + Jinja2)
com dados verdadeiros da Câmara e do TSE.

**Veja ao vivo:** rota [`/componentes`](http://127.0.0.1:8010/componentes) — styleguide interativo.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `app/static/colors_and_type.css` | Tokens: cor, tipografia, espaçamento, raios, elevação (fonte da verdade) |
| `app/static/portal.css` | Estilos de componentes e telas (nav, botões, cards, feed, votação, gastos, modal) |
| `app/static/overrides.css` | Ajustes do app real (avatar com foto, grids de lista, tabelas, styleguide) |
| `app/static/app.js` | Interações: Lucide, abas do deputado, modal "Cobre" (mailto/wa.me), toast |
| `app/templates/_components.html` | Macros Jinja dos componentes reutilizáveis |
| `app/ui.py` | Helpers de apresentação (formatação BRL, cor por partido, iniciais, voto) |

## Tokens (design tokens)

- **Cores semânticas:** `--brand` (verde pinheiro), `--accent` (amber/cifrão), `--action` (clay/cobre),
  `--fg-1/2/3`, `--bg-page/surface/subtle/well`, status `--status-aprovado/rejeitado/tramitando/ausente`,
  ramp de dataviz `--viz-1..6`.
- **Tipografia:** `--font-serif` (IBM Plex Serif, títulos), `--font-sans` (UI/corpo), `--font-mono` (dados/números).
  Classes: `.t-display-1`, `.t-h1..h3`, `.t-body(-lg)`, `.t-small`, `.t-label`, `.t-data`.
- **Espaçamento:** `--space-1..9` (base 4px). **Raios:** `--radius-xs..lg`, `--radius-pill`. **Elevação:** `--shadow-sm/md/lg`.

## Componentes

### Primitivos (macros em `_components.html`)
- **`avatar(nome, foto, party, size)`** — foto real (`<img class="ava">`) quando disponível; senão monograma
  tingido pela cor do partido (`party_color`). 
- **`party_tag(party, uf, term=None)`** — tag mono com quadradinho de cor do partido. Ex.: `PT · SP · 3º mandato`.
- **`vote_badge(kind)`** — pílula de voto. `kind` ∈ `sim | nao | abs | aus` (use `vote_kind(voto)` para mapear o texto).
- **`cobre_button(dep, label, cls, icon)`** — botão que abre o modal "Cobrar", carregando os dados do deputado em `data-*`.
- **`cobre_modal()`** — instância única do modal (incluída na `base.html`), preenchida via `app.js`.

### CSS (classes)
- **Botões:** `.btn` + `.btn-primary | .btn-action | .btn-amber | .btn-secondary | .btn-ghost | .btn-wa`; tamanhos `.btn-sm | .btn-lg | .btn-block`.
- **Cards:** `.card` + `.card-pad`. Stat card = `.card-pad` com `.eyebrow` + `.data`.
- **Navegação:** `.nav` / `.nav-in` / `.nav-links a.on`. **Rodapé:** `.footer`.
- **Feed:** `.feed-item` + `.icn.icn-{aprovado|rejeitado|tramitando}`.
- **Votação:** `.result-banner.rb-{aprovado|rejeitado}`, `.tally-bar .seg`, `.party-row .party-bar .pf/.pa`.
- **Gastos:** `.cat-row` + `.cat-track .fill`, `.month-bars .mb(.hi)`, `.rec-table`.
- **Deputado:** `.dep-hero`, `.dep-stats .dep-stat`, `.tabs .tab.on` (abas via `data-tabs`/`data-panel`).
- **Cobre (modal):** `.overlay .modal`, `.channel(.on)`, `.chip(.on)`, `.msg-box`, `.sent`. **Toast:** `.toast`.

## Telas (rotas)
| Rota | Tela do kit | Dados reais |
|---|---|---|
| `/` | Landing | stats globais + prévia do feed |
| `/agora` | Feed "Agora" | votações recentes + mais vigiados (por gasto) |
| `/deputados` | (lista) | todos os deputados, com busca/filtros |
| `/deputados/{id}` | Perfil | presença, votos Sim/Não, cota, abas, eleição (TSE), resumo IA |
| `/deputados/{id}/gastos` | Gastos/CEAP | total, por categoria, mês a mês, notas fiscais |
| `/votacoes` · `/votacoes/{id}` | Votação | banner, placar, recorte por partido, voto por deputado, resumo IA |
| `/gastos` · `/fornecedores` | — | rankings globais |
| `/eleicoes` | — | eleitos por ano (TSE) |
| `/componentes` | — | este styleguide ao vivo |

## Notas
- **Ícones:** Lucide via CDN; `app.js` chama `lucide.createIcons()` no load e após o modal.
- **Cobrar:** em produção dispara `mailto:` (e-mail do gabinete, quando há) ou `https://wa.me/?text=`.
- **Avatares:** usam a foto oficial da Câmara (`url_foto`); monograma é fallback.
- **Resumos IA (Grok):** carregados sob demanda via HTMX; exigem `XAI_API_KEY`.
