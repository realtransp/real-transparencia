"""Resumos em linguagem simples (Gemini/Grok) com cache no banco."""
from __future__ import annotations

from sqlalchemy import select

from ..db import engine, resumos_ia, votacoes
from . import llm
from . import llm as grok  # alias retrocompatível


def _cache_get(tipo: str, eid: str) -> str | None:
    with engine.connect() as conn:
        row = conn.execute(
            select(resumos_ia.c.texto)
            .where(resumos_ia.c.entidade_tipo == tipo, resumos_ia.c.entidade_id == eid)
            .order_by(resumos_ia.c.id.desc())
            .limit(1)
        ).first()
    return row[0] if row else None


def _cache_put(tipo: str, eid: str, texto: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            resumos_ia.insert().values(entidade_tipo=tipo, entidade_id=eid, modelo=llm.model_name(), texto=texto)
        )


def resumo_votacao(votacao: dict, placar: list[dict], orientacoes: list[dict], usar_cache: bool = True) -> str | None:
    eid = str(votacao["id"])
    if usar_cache and (cached := _cache_get("votacao", eid)):
        return cached
    if not grok.disponivel():
        return None
    placar_txt = ", ".join(f"{p['voto']}: {p['qtd']}" for p in placar) or "sem votos nominais"
    ori_txt = "; ".join(f"{o['sigla_partido']}={o['orientacao']}" for o in orientacoes[:15]) or "sem orientações"
    resultado = "APROVADA" if votacao.get("aprovacao") == 1 else ("REJEITADA" if votacao.get("aprovacao") == 0 else "EM TRAMITAÇÃO")
    prompt = (
        f"Explique esta votação da Câmara dos Deputados para uma pessoa leiga, em português claro.\n\n"
        f"Data: {votacao.get('data')}\n"
        f"Órgão: {votacao.get('sigla_orgao')}\n"
        f"Proposição: {votacao.get('objeto') or votacao.get('proposicao')}\n"
        f"ASSUNTO (ementa da proposição): {votacao.get('ementa') or '(não informado)'}\n"
        f"Texto procedimental: {votacao.get('descricao')}\n"
        f"Resultado: {resultado}\n"
        f"Placar: {placar_txt}\n"
        f"Orientação dos partidos: {ori_txt}\n\n"
        f"IMPORTANTE: a ementa pode ser o TEXTO ORIGINAL da proposição; emendas substitutivas "
        f"votadas podem ter mudado o conteúdo. Use a busca na web para confirmar o que foi "
        f"EFETIVAMENTE votado nesta proposição ({votacao.get('objeto') or ''}) e corrija detalhes "
        f"concretos (números, horas, escalas, valores) com base no texto realmente aprovado.\n\n"
        f"Responda EXATAMENTE neste formato, com estes rótulos (cada um em uma linha):\n"
        f"Título: <manchete curta e amigável, no máximo 9 palavras, linguagem do dia a dia, "
        f"SEM número de artigo/lei/inciso e SEM jargão — diga o tema na prática>\n"
        f"O que estava em jogo: <1-2 frases simples sobre o que essa proposta/decisão trata>\n"
        f"Se for aprovada: <1-2 frases sobre o que muda na prática para a população se for aprovada>\n"
        f"Se for rejeitada: <1-2 frases sobre o que acontece/continua igual se NÃO for aprovada>\n"
        f"O que foi decidido: <1 frase dizendo o resultado real desta votação e o efeito imediato>\n"
        f"Repercussão: <1-2 frases com as principais polêmicas, críticas ou pontos controversos do "
        f"que foi votado, segundo a cobertura/jornalismo — ex.: benefícios a grupos específicos, "
        f"'jabutis', quem ganha e quem perde. Se não houver controvérsia relevante, escreva 'Sem grande repercussão registrada.'>\n\n"
        f"Seja factual e neutro, sem opinião política — ao citar críticas, atribua a quem critica. "
        f"Foque no impacto concreto para o cidadão."
    )
    # Grounding (busca online) é best-effort: corrige fatos quando há cota.
    texto = None
    try:
        texto = llm.gerar_resumo(prompt, max_tokens=900, grounded=True)
    except Exception:  # noqa: BLE001 - inclui RateLimited do modelo de grounding
        texto = None
    if not texto:  # caminho garantido: modelo simples (pode propagar RateLimited)
        texto = llm.gerar_resumo(prompt, max_tokens=650)
    texto = _extrair_titulo(eid, texto)
    _cache_put("votacao", eid, texto)
    return texto


def _extrair_titulo(vid: str, texto: str) -> str:
    """Extrai a linha 'Título:' do resumo, grava em votacoes.titulo_ia e a remove do corpo."""
    linhas = texto.splitlines()
    corpo = []
    titulo = None
    for ln in linhas:
        s = ln.strip()
        low = s.lower()
        if low.startswith("título:") or low.startswith("titulo:"):
            titulo = s.split(":", 1)[1].strip().strip('"').strip("*").strip()
        else:
            corpo.append(ln)
    if titulo:
        with engine.begin() as conn:
            conn.execute(votacoes.update().where(votacoes.c.id == vid).values(titulo_ia=titulo[:180]))
    return "\n".join(l for l in corpo if l.strip())


def resumo_deputado(dep: dict, financeiro: dict, presenca: dict | None, eleicao: dict | None,
                    stats: dict | None = None, usar_cache: bool = True) -> str | None:
    eid = str(dep["id"])
    if usar_cache and (cached := _cache_get("deputado", eid)):
        return cached
    if not grok.disponivel():
        return None
    cats = ", ".join(f"{c['categoria']}: R$ {c['total']:,.0f}" for c in financeiro["por_categoria"][:5])
    pres = (
        f"presente em {presenca['presencas']} de {presenca['total_eventos']} sessões de plenário ({presenca['pct']}%)"
        if presenca
        else "presença sem dados"
    )
    elei = ""
    if eleicao and eleicao.get("candidaturas"):
        c = eleicao["candidaturas"][0]
        elei = f"Última candidatura {c.get('ano_eleicao')}: {c.get('situacao')}."
    votos_txt = ""
    if stats:
        votos_txt = (
            f"Em {stats['ano']} participou de {stats['participou']} de {stats['total_ano']} votações nominais: "
            f"votou Sim {stats['votes_for']}x, Não {stats['votes_against']}x, "
            f"absteve/obstruiu {stats['outros']}x."
        )
    prompt = (
        f"Faça uma análise factual e neutra do deputado {dep.get('nome')} "
        f"({dep.get('sigla_partido')}-{dep.get('sigla_uf')}), em português claro.\n\n"
        f"Gasto da cota parlamentar (ano): R$ {financeiro['total']:,.2f}.\n"
        f"Principais categorias de gasto: {cats}.\n"
        f"Presença: {pres}.\n"
        f"Atuação em votações: {votos_txt}\n"
        f"{elei}\n\n"
        f"Responda EXATAMENTE neste formato (cada rótulo em uma linha):\n"
        f"Atuação: <2 frases sobre presença e participação nas votações — é assíduo ou falta muito?>\n"
        f"Como vota: <1-2 frases sobre o padrão de voto (mais Sim ou Não) e o que isso sugere sobre alinhamento, sem opinião>\n"
        f"Gastos: <1-2 frases sobre o padrão de gastos da cota, destacando a maior categoria>\n"
        f"Em resumo: <1 frase fechando o perfil do mandato>\n\n"
        f"Seja neutro e factual, sem juízo político."
    )
    texto = grok.gerar_resumo(prompt, max_tokens=600)
    _cache_put("deputado", eid, texto)
    return texto
