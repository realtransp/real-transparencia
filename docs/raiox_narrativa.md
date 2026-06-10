# Raio-X — Plano de narrativa (deputado vs. partido)

> Aplicação das skills: `analysis-planning` → `dashboard-specification` →
> `data-narrative-builder` → `insight-synthesis`. Objetivo: o Raio-X deixa de ser
> "o mesmo painel com números trocados" e passa a contar **duas histórias diferentes**,
> porque deputado e partido respondem a perguntas diferentes.

## 1. dashboard-specification — uma frase por escopo

| Escopo | Pergunta central | Para quem | Decisão que habilita |
|---|---|---|---|
| **Deputado** | "Esse parlamentar que EU pago faz o trabalho — e a serviço de quem vota?" | cidadão/eleitor | confiar / cobrar / votar de novo |
| **Partido** | "Quão grande é esse bloco, quão disciplinado, e de que lado ele usa o poder?" | cidadão/jornalista | entender quem manda na pauta |
| **Geral** | "Como anda a Câmara como um todo este ano?" | panorama | navegar para o detalhe |

A consequência de design: **não são mais filtros do mesmo dashboard, são layouts diferentes.**

## 2. Hierarquia de métricas (KPI-herói distinto)

- **Deputado** — herói: *custo aos cofres no ano* + *presença*. Métrica-assinatura
  exclusiva: **independência / fidelidade partidária** (quantas vezes seguiu vs. bateu
  de frente com o líder do próprio partido) e **percentil de gasto** (gasta mais que X%
  dos 513). Encerra com **de onde veio o dinheiro de campanha** (a serviço de quem).
- **Partido** — herói: *tamanho do bloco* (cadeiras, % da Câmara → poder) + *coesão*
  (o líder controla a bancada?). Métrica-assinatura exclusiva: **dispersão interna /
  ranking de membros** (maiores gastadores, mais faltosos) — só existe no coletivo.

## 3. data-narrative-builder — arco (Situação → Complicação → Resolução)

**Deputado** (rolagem):
1. Hook/herói — nome, "custou R$X aos cofres em {ano}", crachá de presença.
2. Situação — quem é e quanto custa (subsídio fixo + cota; percentil).
3. Complicação — *a serviço de quem vota?* independência do próprio partido + Governo/Maioria.
4. Trabalho — aparece pra votar? presença + dias.
5. Rastro do dinheiro — doadores de campanha → conflito de interesse.

**Partido** (rolagem):
1. Hook/herói — sigla, "{n} cadeiras = {x}% da Câmara", crachá de coesão.
2. Situação — o peso do bloco (poder de barganha) + custo coletivo e médio por deputado.
3. Complicação — *anda em fila?* coesão + alinhamento Governo/Oposição.
4. Dispersão — quem se destaca dentro da bancada (ranking interno: gasto e faltas).
5. Rastro do dinheiro — arrecadação agregada e maiores doadores.

## 4. insight-synthesis — frases "So what" por escopo

Os insights automáticos passam a ser escritos no enquadramento de cada história:
deputado → responsabilização individual ("seguiu o líder em X%", "gasta mais que X%");
partido → poder coletivo ("disciplina de X%", "a bancada custa R$Y, média R$Z/deputado").
