# Roteiro

O que vem pela frente, em ordem de prioridade. Contribuições são bem-vindas em
qualquer item (abra uma issue antes de começar algo grande).

## 1. Antes de divulgar (segurança e LGPD)

- [ ] Mascarar CPF de pessoa física na tela de fornecedores (mostrar só `***.456.789-**`; CNPJ segue visível)
- [ ] Rate-limit nos endpoints abertos (`/api/sugestao`, `/api/resumo/*`) contra spam e abuso de custo de IA
- [ ] Página de política de privacidade (LGPD + requisito do AdSense)
- [ ] Validar `alvo` de partido na rota `/relatorio` (hoje só o escopo deputado valida)

## 2. Cobrança 2.0: cobrar nas redes sociais

Hoje a cobrança é só por e-mail do gabinete. A ideia é a cobrança acontecer onde o
deputado sente: em público.

- [ ] Ingerir as redes sociais oficiais de cada deputado (campo `redeSocial` da API da
      Câmara: X/Twitter, Instagram, Facebook, YouTube). É autodeclarado, então nem todos têm.
- [ ] Botão **"Cobrar no X"**: post pré-pronto mencionando o @ do deputado, com um dado
      real (voto, gasto ou presença) e o link do perfil dele no site
- [ ] Botão **"Mandar no WhatsApp"**: compartilha a cobrança nos grupos do próprio usuário
      (`wa.me/?text=`). Os dados abertos não têm WhatsApp pessoal de deputado, só o
      telefone fixo do gabinete (já exibido no perfil), então o caminho é a cobrança viral.
- [ ] Links diretos para Instagram/Facebook oficiais do deputado (não há pré-preenchimento por API)
- [ ] **Card compartilhável por deputado**: imagem OG dinâmica com presença, gasto da cota e
      últimos votos, para a cobrança render bem quando colada em rede social
- [ ] Contador público de cobranças por deputado ("N pessoas cobraram este mês")

## 3. Municípios: prefeitos e vereadores (panorama completo)

Trazer o poder municipal para o site, começando pelo que tem dado uniforme nacional.

**Fase 1 — quem manda na sua cidade (TSE, uniforme para os 5.570 municípios):**
- [ ] Ingestão TSE das eleições municipais (2024 e anteriores): prefeitos e vereadores
      eleitos, votos recebidos, financiamento de campanha e doadores
- [ ] Páginas `/municipios` (busca por cidade) e `/municipio/{uf}/{cidade}`: prefeito,
      vice e bancada de vereadores, com o lado eleitoral de cada um
- [ ] Busca por cidade na home

**Fase 2 — dinheiro da prefeitura (SICONFI/Tesouro Nacional):**
- [ ] Receita e despesa anual de cada prefeitura (RREO/RGF), em linguagem simples
- [ ] Comparação com cidades vizinhas/do mesmo porte

**Fase 3 — atuação das câmaras municipais (heterogêneo, esforço contínuo):**
- [ ] Votações e pautas das câmaras que usam SAPL (Interlegis), onde a API existir
- [ ] Despesas detalhadas via portais/TCEs estaduais, estado a estado

> Realidade dos dados: diferente da Câmara federal, **não existe padrão nacional** para
> votos e gastos de vereador. Por isso a ordem: primeiro o que é uniforme (TSE), depois
> finanças agregadas (SICONFI), e o resto cidade a cidade, onde a comunidade puder ajudar.

## 4. Senado

- [ ] Senadores: votações, presença e cota (CEAPS) via dados abertos do Senado, num
      pipeline análogo ao da Câmara

## 5. Infra e qualidade

- [ ] Alertar quando o cron diário de ingestão falhar (hoje só registra log)
- [ ] Valores da CEAP parametrizados por ano (sem estimativa fixa no código)
- [ ] Atualizar as actions do CI para Node 24
- [ ] `CONTRIBUTING.md` e issues marcadas com `good first issue`
