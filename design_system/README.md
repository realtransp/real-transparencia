# Design — referência visual do Real Transparência

Esta pasta documenta a linguagem visual do app: cores, tipografia, espaçamento,
componentes e telas de exemplo. É **referência**, não o que roda no site.

> **Fonte da verdade do site é `app/static/`.** Para mudar a aparência do app,
> edite lá: `colors_and_type.css` (tokens), `portal.css` (componentes/telas) e
> `overrides.css` (ajustes específicos do app). Os arquivos desta pasta são um
> espelho de referência e podem ficar para trás. Em caso de divergência,
> **vale o que está em `app/static/`**.

## O que tem aqui

- `colors_and_type.css` — tokens de cor, tipografia, espaçamento, raios e sombras.
- `preview/` — cartões de especimens (cores, tipos, espaçamento, componentes).
- `ui_kits/portal/` — recriação clicável das telas (landing, feed, perfil, votação,
  gastos, cobrar) em React inline. Protótipo de fidelidade visual, com dados fictícios.

## Linguagem visual (resumo)

**Marca.** R$ Transparência. O cifrão lidera o nome (dinheiro público + prestação de
contas). Tom sério e institucional, de jornalismo de dados. Nunca a bandeira literal
nem o visual oficial do gov.br: é um observatório independente.

**Cor.** Verde-amarelo reinterpretado em tons terrosos: pinheiro `--green-800` (marca),
ouro `--amber-500` (destaque, o cifrão), terracota `--clay-600` (ação "cobrar" e
alerta/rejeitado), papel quente de fundo. Detalhes e tokens semânticos em `colors_and_type.css`.

**Tipografia.** Superfamília IBM Plex: Serif nos títulos, Sans no corpo e na interface,
Mono em todos os números (moeda `R$ 0.000,00`, placares, rótulos), com `tabular-nums`.

**Escrita.** PT-BR, factual e direta, trata o leitor por "você". Verbo no imperativo só
nos CTAs ("Cobrar"). Sem emoji; ícones de linha (Lucide). Neutralidade: mostra o dado e
deixa o cidadão julgar, sem tomar lado partidário.

**Contato com o deputado.** Só por e-mail oficial do gabinete (`mailto:`). Os dados
abertos da Câmara não trazem celular/WhatsApp, apenas o telefone fixo do gabinete.

---

*Marca, copy e identidade criadas para este projeto. Os dados nos protótipos são fictícios.*
