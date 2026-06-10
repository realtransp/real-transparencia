# UI Kit — Portal R$ Transparência

Recriação interativa do portal web. Telas clicáveis montadas com componentes modulares (React + Babel inline), usando os tokens de `colors_and_type.css` e os estilos de `portal.css`.

## Como abrir
Abra `index.html`. É um protótipo de fidelidade visual — navegação real, dados fictícios.

## Fluxo demonstrado
1. **Landing** (`screens-landing.jsx`) — hero, prévia do feed, features, "como cobrar", banda de CTA.
2. **Agora / Feed** (`screens-feed.jsx`) — o que tá rolando + sidebar de "mais vigiados" e CTA de cobrança.
3. **Perfil do deputado** (`screens-deputy.jsx`) — avatar, stats, abas (Votações / Gastos / Sobre).
4. **Votação** (`screens-votacao.jsx`) — resultado, placar, recorte por partido, voto por deputado.
5. **Gastos / CEAP** (`screens-gastos.jsx`) — total, por categoria, mês a mês, notas fiscais.
6. **Cobre seu deputado** (`screens-cobre.jsx`) — modal: modelo → mensagem editável → enviado por e-mail do gabinete.

Clique em **Cobrar** em qualquer tela para abrir o fluxo. A navegação superior alterna entre as seções.

## Arquivos
| Arquivo | Conteúdo |
|---|---|
| `index.html` | Monta React + Babel + Lucide e carrega os scripts |
| `colors_and_type.css` | Cópia dos tokens (fonte da verdade na raiz) |
| `portal.css` | Estilos de componentes e telas do kit |
| `data.jsx` | Dados fictícios (deputados, feed, votação, gastos) |
| `components.jsx` | Primitivos: `Icon`, `Avatar`, `PartyTag`, `VoteBadge`, `Header`, `Footer`, `brl()` |
| `screens-*.jsx` | Uma tela por arquivo |
| `app.jsx` | Shell: roteamento por estado + modal + toast |

## Componentes reutilizáveis
- **Header / Footer** — navegação pinheiro fixa e rodapé com fontes.
- **Avatar** — monograma tingido por partido (placeholder, sem foto real).
- **PartyTag / VoteBadge** — tags de partido/UF e badges de voto (Sim/Não/Abstenção/Ausente).
- **Cartões** — `.card` + `.card-pad`; stat cards, feed-item, cat-row, party-row.
- **CobreModal** — o fluxo de cobrança, reutilizável a partir de qualquer deputado.

## Observações
- **Ícones:** Lucide via CDN; reinstanciados após cada render (`useLucideRefresh`).
- **Sem backend:** "enviar" abre o estado de sucesso; em produção dispara `mailto:` para o e-mail do gabinete.
- **Avatares** são monogramas — troque por `<img>` se tiver fotos licenciadas.
- **Dados fictícios** — nomes, valores e placares são ilustrativos.
