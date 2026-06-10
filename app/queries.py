"""Consultas de leitura para as páginas (rankings, placares, presença, eleições)."""
from __future__ import annotations

from sqlalchemy import desc, func, insert, select

from .config import SUBSIDIO_MENSAL
from .db import (
    deputados,
    despesas,
    engine,
    orientacoes,
    presenca,
    proposicao_autores,
    proposicoes,
    sugestoes,
    tse_candidatos,
    tse_doacoes,
    votacoes,
    votos,
)


def salvar_sugestao(texto: str, pagina: str | None = None) -> bool:
    texto = (texto or "").strip()[:4000]
    if not texto:
        return False
    with engine.begin() as conn:
        conn.execute(insert(sugestoes).values(texto=texto, pagina=(pagina or "")[:300]))
    return True


def listar_sugestoes(limit: int = 1000) -> list[dict]:
    return _rows(select(sugestoes).order_by(desc(sugestoes.c.criado_em)).limit(limit))


def _rows(stmt) -> list[dict]:
    with engine.connect() as conn:
        return [dict(r._mapping) for r in conn.execute(stmt)]


def _scalar(stmt, default=0):
    with engine.connect() as conn:
        v = conn.execute(stmt).scalar()
    return v if v is not None else default


# ------------------------------------------------------------------- HOME
def home_stats() -> dict:
    total_gasto = _scalar(select(func.coalesce(func.sum(despesas.c.valor_liquido), 0)))
    n_dep = _scalar(select(func.count()).select_from(deputados))
    n_votacoes = _scalar(select(func.count()).select_from(votacoes))
    n_despesas = _scalar(select(func.count()).select_from(despesas))
    return dict(
        total_gasto=total_gasto,
        n_deputados=n_dep,
        n_votacoes=n_votacoes,
        n_despesas=n_despesas,
    )


# ------------------------------------------------------------------ GASTOS
def _desp_cond(ano=None, mes=None, cat=None):
    conds = []
    if ano:
        conds.append(despesas.c.ano == ano)
    if mes:
        conds.append(despesas.c.mes == mes)
    if cat:
        conds.append(despesas.c.tipo_despesa == cat)
    return conds


def ranking_gastos_deputados(limit: int = 50, uf: str | None = None, partido: str | None = None,
                             ano: int | None = None, mes: int | None = None) -> list[dict]:
    stmt = (
        select(
            deputados.c.id, deputados.c.nome, deputados.c.sigla_partido,
            deputados.c.sigla_uf, deputados.c.url_foto,
            func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("total"),
        )
        .select_from(deputados.join(despesas, despesas.c.deputado_id == deputados.c.id))
        .where(*_desp_cond(ano, mes))
        .group_by(deputados.c.id, deputados.c.nome, deputados.c.sigla_partido, deputados.c.sigla_uf, deputados.c.url_foto)
        .order_by(desc("total"))
        .limit(limit)
    )
    if uf:
        stmt = stmt.where(deputados.c.sigla_uf == uf)
    if partido:
        stmt = stmt.where(deputados.c.sigla_partido == partido)
    return _rows(stmt)


def gasto_por_partido(ano: int | None = None, mes: int | None = None, limit: int = 30) -> list[dict]:
    """Gasto agregado por partido: total, nº de deputados e média por deputado."""
    rows = _rows(
        select(
            deputados.c.sigla_partido.label("partido"),
            func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("total"),
            func.count(func.distinct(deputados.c.id)).label("deputados"),
            func.count().label("qtd"),
        )
        .select_from(deputados.join(despesas, despesas.c.deputado_id == deputados.c.id))
        .where(*_desp_cond(ano, mes), deputados.c.sigla_partido.isnot(None))
        .group_by(deputados.c.sigla_partido)
        .order_by(desc("total")).limit(limit)
    )
    for r in rows:
        r["media_dep"] = (r["total"] / r["deputados"]) if r["deputados"] else 0
    return rows


def partido_kpis(sigla: str, ano: int | None = None, mes: int | None = None) -> dict:
    base = deputados.join(despesas, despesas.c.deputado_id == deputados.c.id)
    cond = [deputados.c.sigla_partido == sigla, *_desp_cond(ano, mes)]
    total = _scalar(select(func.coalesce(func.sum(despesas.c.valor_liquido), 0)).select_from(base).where(*cond))
    ndep = _scalar(select(func.count(func.distinct(deputados.c.id))).select_from(base).where(*cond))
    qtd = _scalar(select(func.count()).select_from(base).where(*cond))
    return dict(sigla=sigla, total=total, deputados=ndep, qtd=qtd,
                media_dep=(total / ndep) if ndep else 0, ano=ano)


def partido_top_deputados(sigla: str, ano: int | None = None, mes: int | None = None, limit: int = 20) -> list[dict]:
    return ranking_gastos_deputados(limit=limit, partido=sigla, ano=ano, mes=mes)


def partido_categorias(sigla: str, ano: int | None = None, mes: int | None = None, limit: int = 12) -> list[dict]:
    return _rows(
        select(
            despesas.c.tipo_despesa.label("categoria"),
            func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("total"),
        )
        .select_from(deputados.join(despesas, despesas.c.deputado_id == deputados.c.id))
        .where(deputados.c.sigla_partido == sigla, *_desp_cond(ano, mes))
        .group_by(despesas.c.tipo_despesa).order_by(desc("total")).limit(limit)
    )


def partido_mensal(sigla: str, ano: int) -> list[float]:
    rows = _rows(
        select(despesas.c.mes, func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("t"))
        .select_from(deputados.join(despesas, despesas.c.deputado_id == deputados.c.id))
        .where(deputados.c.sigla_partido == sigla, despesas.c.ano == ano)
        .group_by(despesas.c.mes)
    )
    by = {int(r["mes"]): float(r["t"]) for r in rows if r["mes"]}
    return [round(by.get(m, 0.0)) for m in range(1, 13)]


def gasto_por_categoria(limit: int = 12) -> list[dict]:
    stmt = (
        select(
            despesas.c.tipo_despesa.label("categoria"),
            func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("total"),
        )
        .group_by(despesas.c.tipo_despesa)
        .order_by(desc("total"))
        .limit(limit)
    )
    return _rows(stmt)


def ranking_fornecedores(limit: int = 30) -> list[dict]:
    stmt = (
        select(
            despesas.c.fornecedor_nome.label("fornecedor"),
            despesas.c.fornecedor_cnpj_cpf.label("documento"),
            func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("total"),
            func.count().label("qtd"),
        )
        .where(despesas.c.fornecedor_nome.isnot(None))
        .group_by(despesas.c.fornecedor_nome, despesas.c.fornecedor_cnpj_cpf)
        .order_by(desc("total"))
        .limit(limit)
    )
    return _rows(stmt)


# ============================================================ ANÁLISE DE GASTOS
# Indicadores estatísticos sobre dados públicos. Linguagem sempre NEUTRA:
# concentração/repetição/exclusividade ajudam a fiscalização, não atestam nada.
def _gastos_base(ano):
    return despesas.join(deputados, deputados.c.id == despesas.c.deputado_id)


def gastos_overview(ano: int) -> dict:
    total = _scalar(select(func.coalesce(func.sum(despesas.c.valor_liquido), 0)).where(despesas.c.ano == ano))
    qtd = _scalar(select(func.count()).where(despesas.c.ano == ano))
    n_forn = _scalar(select(func.count(func.distinct(despesas.c.fornecedor_cnpj_cpf)))
                     .where(despesas.c.ano == ano, despesas.c.fornecedor_cnpj_cpf.isnot(None)))
    # pessoa física = documento com 11 dígitos (CPF)
    pf_total = _scalar(select(func.coalesce(func.sum(despesas.c.valor_liquido), 0))
                       .where(despesas.c.ano == ano, func.length(despesas.c.fornecedor_cnpj_cpf) == 11))
    # concentração: participação dos maiores fornecedores no total
    tops = _rows(select(func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("v"))
                 .where(despesas.c.ano == ano, despesas.c.fornecedor_cnpj_cpf.isnot(None))
                 .group_by(despesas.c.fornecedor_cnpj_cpf).order_by(desc("v")).limit(50))
    vals = [r["v"] for r in tops]
    top10 = sum(vals[:10]); top50 = sum(vals[:50])
    return dict(
        total=total, qtd=qtd, n_forn=n_forn, ticket=(total / qtd if qtd else 0),
        pf_total=pf_total, pf_pct=(round(100.0 * pf_total / total, 1) if total else 0),
        top10_pct=(round(100.0 * top10 / total, 1) if total else 0),
        top50_pct=(round(100.0 * top50 / total, 1) if total else 0))


def top_fornecedores(ano: int, limit: int = 25) -> list[dict]:
    """Maiores fornecedores: total, nº de deputados/partidos atendidos, partido
    predominante e o deputado que mais pagou. Base do panorama de fornecedores."""
    base = _gastos_base(ano)
    tops = _rows(
        select(despesas.c.fornecedor_nome.label("nome"), despesas.c.fornecedor_cnpj_cpf.label("doc"),
               func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("total"),
               func.count().label("qtd"),
               func.count(func.distinct(despesas.c.deputado_id)).label("n_dep"),
               func.count(func.distinct(deputados.c.sigla_partido)).label("n_part"))
        .select_from(base).where(despesas.c.ano == ano, despesas.c.fornecedor_nome.isnot(None))
        .group_by(despesas.c.fornecedor_nome, despesas.c.fornecedor_cnpj_cpf)
        .order_by(desc("total")).limit(limit))
    nomes = [t["nome"] for t in tops if t["nome"]]
    if not nomes:
        for t in tops:
            t["partido_top"] = None; t["dep_top"] = None; t["ticket"] = (t["total"] / t["qtd"] if t["qtd"] else 0)
        return tops
    # casa por NOME (cobre fornecedores sem CNPJ, como companhias aéreas)
    part_rows = _rows(
        select(despesas.c.fornecedor_nome.label("nome"), deputados.c.sigla_partido.label("p"),
               func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("v"))
        .select_from(base).where(despesas.c.ano == ano, despesas.c.fornecedor_nome.in_(nomes))
        .group_by(despesas.c.fornecedor_nome, deputados.c.sigla_partido))
    dep_rows = _rows(
        select(despesas.c.fornecedor_nome.label("nome"), deputados.c.id.label("did"),
               deputados.c.nome.label("dn"), deputados.c.sigla_partido.label("dp"), deputados.c.sigla_uf.label("du"),
               func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("v"))
        .select_from(base).where(despesas.c.ano == ano, despesas.c.fornecedor_nome.in_(nomes))
        .group_by(despesas.c.fornecedor_nome, deputados.c.id, deputados.c.nome,
                  deputados.c.sigla_partido, deputados.c.sigla_uf))
    part_by, dep_by = {}, {}
    for r in part_rows:
        part_by.setdefault(r["nome"], []).append((r["p"], r["v"]))
    for r in dep_rows:
        dep_by.setdefault(r["nome"], []).append(r)
    for t in tops:
        ps = part_by.get(t["nome"], [])
        t["partido_top"] = max(ps, key=lambda x: x[1])[0] if ps else None
        t["partido_top_pct"] = round(100.0 * max(ps, key=lambda x: x[1])[1] / t["total"], 0) if (ps and t["total"]) else None
        ds = dep_by.get(t["nome"], [])
        t["dep_top"] = max(ds, key=lambda x: x["v"]) if ds else None
        t["ticket"] = t["total"] / t["qtd"] if t["qtd"] else 0
    return tops


def fornecedores_exclusivos(ano: int, limit: int = 15, min_total: float = 60000) -> list[dict]:
    """Fornecedores cujo faturamento no ano veio de UM único deputado (ponto de
    atenção: vale checar a relação). Linguagem neutra, não imputa irregularidade."""
    base = _gastos_base(ano)
    rows = _rows(
        select(despesas.c.fornecedor_nome.label("nome"), despesas.c.fornecedor_cnpj_cpf.label("doc"),
               func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("total"), func.count().label("qtd"),
               func.max(deputados.c.nome).label("dep"), func.max(deputados.c.id).label("dep_id"),
               func.max(deputados.c.sigla_partido).label("part"), func.max(deputados.c.sigla_uf).label("uf"))
        .select_from(base).where(despesas.c.ano == ano, despesas.c.fornecedor_nome.isnot(None))
        .group_by(despesas.c.fornecedor_nome, despesas.c.fornecedor_cnpj_cpf)
        .having(func.count(func.distinct(despesas.c.deputado_id)) == 1)
        .order_by(desc("total")).limit(limit * 4))
    return [r for r in rows if r["total"] >= min_total][:limit]


def valores_repetidos(ano: int, limit: int = 15, min_rep: int = 13, min_valor: float = 300) -> list[dict]:
    """Um MESMO deputado pagando a um MESMO fornecedor o MESMO valor exato muitas
    vezes no ano (acima do mensal). Ponto de atenção neutro, pode ser rotina, vale ver."""
    base = _gastos_base(ano)
    rows = _rows(
        select(despesas.c.fornecedor_nome.label("nome"), despesas.c.valor_liquido.label("valor"),
               deputados.c.id.label("dep_id"), deputados.c.nome.label("dep"),
               deputados.c.sigla_partido.label("part"), deputados.c.sigla_uf.label("uf"),
               func.count().label("vezes"))
        .select_from(base)
        .where(despesas.c.ano == ano, despesas.c.fornecedor_nome.isnot(None),
               despesas.c.valor_liquido >= min_valor)
        .group_by(despesas.c.fornecedor_nome, despesas.c.valor_liquido, deputados.c.id,
                  deputados.c.nome, deputados.c.sigla_partido, deputados.c.sigla_uf)
        .having(func.count() >= min_rep).order_by(desc("vezes")).limit(limit))
    for r in rows:
        r["total"] = (r["valor"] or 0) * r["vezes"]
    return rows


def pessoa_fisica_top(ano: int, limit: int = 10) -> list[dict]:
    """Maiores recebimentos por pessoa física (CPF): ponto de atenção neutro."""
    base = _gastos_base(ano)
    return _rows(
        select(despesas.c.fornecedor_nome.label("nome"), despesas.c.fornecedor_cnpj_cpf.label("doc"),
               func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("total"), func.count().label("qtd"),
               func.count(func.distinct(despesas.c.deputado_id)).label("n_dep"))
        .select_from(base).where(despesas.c.ano == ano, func.length(despesas.c.fornecedor_cnpj_cpf) == 11,
                                 despesas.c.fornecedor_nome.isnot(None))
        .group_by(despesas.c.fornecedor_nome, despesas.c.fornecedor_cnpj_cpf)
        .order_by(desc("total")).limit(limit))


def fornecedor_detalhe(nome: str, ano: int | None = None, dep: int | None = None) -> dict:
    """Tudo sobre um fornecedor: quem pagou (deputados), em quê (categorias) e as notas.

    `dep` filtra as notas para um deputado específico (clique em 'Quem pagou')."""
    base = despesas.join(deputados, deputados.c.id == despesas.c.deputado_id)
    conds = [despesas.c.fornecedor_nome == nome]
    if ano:
        conds.append(despesas.c.ano == ano)
    total = _scalar(select(func.coalesce(func.sum(despesas.c.valor_liquido), 0)).select_from(base).where(*conds))
    qtd = _scalar(select(func.count()).select_from(base).where(*conds))
    doc = _scalar(select(despesas.c.fornecedor_cnpj_cpf).where(*conds).limit(1), default=None)
    anos = [r["ano"] for r in _rows(select(despesas.c.ano).where(despesas.c.fornecedor_nome == nome)
                                    .group_by(despesas.c.ano).order_by(desc(despesas.c.ano)))]
    por_dep = _rows(
        select(deputados.c.id, deputados.c.nome, deputados.c.sigla_partido, deputados.c.sigla_uf,
               func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("total"), func.count().label("qtd"))
        .select_from(base).where(*conds)
        .group_by(deputados.c.id, deputados.c.nome, deputados.c.sigla_partido, deputados.c.sigla_uf)
        .order_by(desc("total")))
    por_cat = _rows(
        select(despesas.c.tipo_despesa.label("categoria"),
               func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("total"), func.count().label("qtd"))
        .where(*conds).group_by(despesas.c.tipo_despesa).order_by(desc("total")))
    nconds = list(conds)
    dep_sel = None
    if dep:
        nconds.append(despesas.c.deputado_id == int(dep))
        dep_sel = next((r for r in por_dep if r["id"] == int(dep)), None)
    notas = _rows(
        select(despesas.c.data_documento, despesas.c.tipo_despesa, despesas.c.valor_liquido,
               despesas.c.url_documento, despesas.c.ano, deputados.c.nome.label("deputado"),
               deputados.c.id.label("deputado_id"), deputados.c.sigla_partido, deputados.c.sigla_uf)
        .select_from(base).where(*nconds)
        .order_by(desc(despesas.c.valor_liquido)).limit(300 if dep else 80))
    return dict(nome=nome, doc=doc, total=total, qtd=qtd, n_dep=len(por_dep),
                por_dep=por_dep, por_cat=por_cat, notas=notas, ano=ano, anos=anos,
                dep=dep, dep_sel=dep_sel)


def filtros_disponiveis() -> dict:
    ufs = _rows(select(deputados.c.sigla_uf).distinct().where(deputados.c.sigla_uf.isnot(None)).order_by(deputados.c.sigla_uf))
    partidos = _rows(
        select(deputados.c.sigla_partido).distinct().where(deputados.c.sigla_partido.isnot(None)).order_by(deputados.c.sigla_partido)
    )
    return dict(ufs=[r["sigla_uf"] for r in ufs], partidos=[r["sigla_partido"] for r in partidos])


# --------------------------------------------------------------- DEPUTADOS
def buscar_deputados(q: str, limit: int = 8) -> list[dict]:
    """Busca leve por deputado (autocomplete da home): nome começando com `q`,
    palavra do nome começando com `q`, ou UF exata. Prefixo vem primeiro."""
    from sqlalchemy import case
    ql = (q or "").strip().lower()
    if not ql:
        return []
    nome = func.lower(deputados.c.nome)
    pre = nome.like(f"{ql}%")
    cond = pre | nome.like(f"% {ql}%") | (func.lower(deputados.c.sigla_uf) == ql)
    # prefixo do nome inteiro vem primeiro (Paulo antes de "Alice Portugal")
    prioridade = case((pre, 0), else_=1)
    rows = _rows(
        select(deputados.c.id, deputados.c.nome, deputados.c.sigla_partido,
               deputados.c.sigla_uf, deputados.c.url_foto)
        .where(cond).order_by(prioridade, deputados.c.nome).limit(limit))
    return rows


def list_deputados(uf: str | None = None, partido: str | None = None, busca: str | None = None) -> list[dict]:
    ano = _scalar(select(func.max(despesas.c.ano)), default=2024) or 2024
    cota_sub = (
        select(despesas.c.deputado_id, func.sum(despesas.c.valor_liquido).label("cota_total"))
        .where(despesas.c.ano == ano)
        .group_by(despesas.c.deputado_id)
        .subquery()
    )
    # presença = % das sessões de plenário (eventos com >=100 deputados) a que compareceu
    plen = (
        select(presenca.c.evento_id).group_by(presenca.c.evento_id)
        .having(func.count(func.distinct(presenca.c.deputado_id)) >= 100).subquery()
    )
    total_plen = _scalar(select(func.count()).select_from(plen)) or 1
    pres_sub = (
        select(presenca.c.deputado_id, func.count(func.distinct(presenca.c.evento_id)).label("pres_n"))
        .where(presenca.c.evento_id.in_(select(plen.c.evento_id)))
        .group_by(presenca.c.deputado_id).subquery()
    )
    stmt = (
        select(
            deputados,
            func.coalesce(cota_sub.c.cota_total, 0).label("cota_total"),
            func.coalesce(pres_sub.c.pres_n, 0).label("pres_n"),
        )
        .outerjoin(cota_sub, cota_sub.c.deputado_id == deputados.c.id)
        .outerjoin(pres_sub, pres_sub.c.deputado_id == deputados.c.id)
        .order_by(deputados.c.nome)
    )
    if uf:
        stmt = stmt.where(deputados.c.sigla_uf == uf)
    if partido:
        stmt = stmt.where(deputados.c.sigla_partido == partido)
    if busca:
        from sqlalchemy import or_
        termo = f"%{busca.strip()}%"
        stmt = stmt.where(or_(
            deputados.c.nome.ilike(termo),
            deputados.c.nome_eleitoral.ilike(termo),
            deputados.c.sigla_partido.ilike(termo),
            deputados.c.sigla_uf.ilike(termo),
        ))
    rows = _rows(stmt)
    for r in rows:
        r["pct_presenca"] = round(100 * (r.get("pres_n") or 0) / total_plen, 1) if total_plen else None
    return rows


def get_deputado(dep_id: int) -> dict | None:
    rows = _rows(select(deputados).where(deputados.c.id == dep_id))
    return rows[0] if rows else None


def ano_corrente() -> int:
    """Ano mais recente com dados de despesa."""
    return _scalar(select(func.max(despesas.c.ano)), default=2024) or 2024


def deputado_resumo_financeiro(dep_id: int, ano: int | None = None) -> dict:
    base = [despesas.c.deputado_id == dep_id]
    if ano:
        base.append(despesas.c.ano == ano)
    total = _scalar(select(func.coalesce(func.sum(despesas.c.valor_liquido), 0)).where(*base))
    qtd = _scalar(select(func.count()).where(*base))
    por_categoria = _rows(
        select(despesas.c.tipo_despesa.label("categoria"), func.sum(despesas.c.valor_liquido).label("total"))
        .where(*base).group_by(despesas.c.tipo_despesa).order_by(desc("total"))
    )
    fornecedores = _rows(
        select(despesas.c.fornecedor_nome.label("fornecedor"), func.sum(despesas.c.valor_liquido).label("total"))
        .where(*base, despesas.c.fornecedor_nome.isnot(None))
        .group_by(despesas.c.fornecedor_nome).order_by(desc("total")).limit(10)
    )
    return dict(total=total, qtd=qtd, por_categoria=por_categoria, fornecedores=fornecedores,
                subsidio_mensal=SUBSIDIO_MENSAL, ano=ano)


def deputado_presenca(dep_id: int) -> dict | None:
    """Presença nas sessões do plenário.

    O arquivo oficial lista presenças por evento (sem tipo). Como denominador justo
    usamos as sessões de plenário, identificadas como os eventos com presença em massa
    (>= 100 deputados), em que se espera o comparecimento de todos. Assim a taxa não é
    distorcida por eventos de comissões das quais o deputado nem participa.
    """
    from sqlalchemy import text

    sql = text(
        """
        WITH plenarias AS (
            SELECT evento_id FROM presenca
            GROUP BY evento_id HAVING COUNT(DISTINCT deputado_id) >= 100
        )
        SELECT
            (SELECT COUNT(*) FROM plenarias) AS total,
            (SELECT COUNT(DISTINCT p.evento_id) FROM presenca p
             WHERE p.deputado_id = :dep AND p.evento_id IN (SELECT evento_id FROM plenarias)) AS presentes
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"dep": dep_id}).first()
    if not row or not row.total:
        return None
    total, presentes = row.total, row.presentes or 0
    pct = round(100 * presentes / total, 1)
    return dict(presencas=presentes, total_eventos=total, ausencias=total - presentes, pct=pct)


def deputado_dias_presenca(dep_id: int, ano: int) -> int:
    """Dias distintos com presença registrada (em qualquer evento) no ano."""
    return _scalar(
        select(func.count(func.distinct(presenca.c.data)))
        .where(presenca.c.deputado_id == dep_id, presenca.c.ano == ano),
        default=0,
    )


def deputado_votos(dep_id: int, limit: int = 20) -> list[dict]:
    stmt = (
        select(
            votacoes.c.id,
            votacoes.c.data,
            votacoes.c.descricao,
            votacoes.c.objeto,
            votacoes.c.ementa,
            votos.c.voto,
        )
        .select_from(votos.join(votacoes, votos.c.votacao_id == votacoes.c.id))
        .where(votos.c.deputado_id == dep_id)
        .order_by(desc(votacoes.c.data))
        .limit(limit)
    )
    return _rows(stmt)


def deputado_votos_agrupado(dep_id: int, limit: int = 15, raw: int = 140) -> list[dict]:
    """Votos do deputado agrupados por proposição (objeto), como no feed 'Agora'.

    Uma mesma PEC/PL tem vários turnos/destaques; aqui aparece uma vez, com o
    resumo de como o deputado votou no conjunto (ex.: 5 Não, 2 Sim).
    """
    rows = deputado_votos(dep_id, raw)  # já ordenado por data desc
    groups, index = [], {}
    for r in rows:
        key = r["objeto"] or ("__" + str(r["id"]))
        g = index.get(key)
        if g is None:
            g = dict(objeto=r["objeto"], titulo=(r["ementa"] or r["descricao"] or r["id"]),
                     data=r["data"], id=r["id"], n=0, sim=0, nao=0, outros=0)
            index[key] = g
            groups.append(g)
        g["n"] += 1
        v = r["voto"] or ""
        if v in _SIM:
            g["sim"] += 1
        elif v in _NAO:
            g["nao"] += 1
        else:
            g["outros"] += 1
    return groups[:limit]


def deputado_eleicao(dep_id: int) -> dict | None:
    dep = get_deputado(dep_id)
    if not dep or not dep.get("cpf"):
        return None
    cpf = dep["cpf"]
    candidaturas = _rows(
        select(tse_candidatos).where(tse_candidatos.c.cpf == cpf).order_by(desc(tse_candidatos.c.ano_eleicao))
    )
    doacoes = _rows(
        select(
            tse_doacoes.c.doador,
            func.sum(tse_doacoes.c.valor).label("total"),
        )
        .where(tse_doacoes.c.cpf_candidato == cpf)
        .group_by(tse_doacoes.c.doador)
        .order_by(desc("total"))
        .limit(10)
    )
    if not candidaturas and not doacoes:
        return None
    return dict(candidaturas=candidaturas, doacoes=doacoes)


# --------------------------------------------------------------- VOTAÇÕES
def votacoes_recentes(limit: int = 30) -> list[dict]:
    return _rows(select(votacoes).order_by(desc(votacoes.c.data)).limit(limit))


def get_votacao(vid: str) -> dict | None:
    rows = _rows(select(votacoes).where(votacoes.c.id == vid))
    return rows[0] if rows else None


def votacao_placar(vid: str) -> list[dict]:
    return _rows(
        select(votos.c.voto, func.count().label("qtd"))
        .where(votos.c.votacao_id == vid)
        .group_by(votos.c.voto)
        .order_by(desc("qtd"))
    )


def votacao_orientacoes(vid: str) -> list[dict]:
    return _rows(
        select(orientacoes.c.sigla_partido, orientacoes.c.orientacao)
        .where(orientacoes.c.votacao_id == vid)
        .order_by(orientacoes.c.sigla_partido)
    )


def votacao_votos(vid: str) -> list[dict]:
    stmt = (
        select(
            deputados.c.nome,
            deputados.c.sigla_partido,
            deputados.c.sigla_uf,
            votos.c.voto,
            votos.c.deputado_id,
        )
        .select_from(votos.join(deputados, votos.c.deputado_id == deputados.c.id))
        .where(votos.c.votacao_id == vid)
        .order_by(deputados.c.nome)
    )
    return _rows(stmt)


# --------------------------------------------------------------- ELEIÇÕES
def eleicao_eleitos(ano: int, limit: int = 600) -> list[dict]:
    """Quem se elegeu deputado federal no ano, ordenado por UF e nome."""
    return _rows(
        select(tse_candidatos)
        .where(tse_candidatos.c.ano_eleicao == ano, tse_candidatos.c.situacao.ilike("ELEITO%"))
        .order_by(tse_candidatos.c.sigla_uf, tse_candidatos.c.nome)
        .limit(limit)
    )


def anos_eleicao() -> list[int]:
    rows = _rows(select(tse_candidatos.c.ano_eleicao).distinct().order_by(desc(tse_candidatos.c.ano_eleicao)))
    return [r["ano_eleicao"] for r in rows]


# ===================================================================
#  Design system R$ Transparência: consultas das telas novas
# ===================================================================
from sqlalchemy import case  # noqa: E402

ANO_REF = 2024  # ano de referência dos dados ingeridos (ajustar conforme backfill)
_SIM = ["Sim"]
_NAO = ["Não", "Nao"]


def kind_votacao(aprovacao) -> str:
    if aprovacao == 1:
        return "aprovado"
    if aprovacao == 0:
        return "rejeitado"
    return "tramitando"


def kind_resultado(aprovacao, sim=0, nao=0) -> str:
    """Resultado considerando o placar: se houve votação nominal, não é 'tramitando'."""
    if aprovacao == 1:
        return "aprovado"
    if aprovacao == 0:
        return "rejeitado"
    if (sim or 0) + (nao or 0) > 0:  # votou: decide pelo placar
        return "aprovado" if (sim or 0) >= (nao or 0) else "rejeitado"
    return "tramitando"


def _sim_nao_cols():
    return (
        func.coalesce(func.sum(case((votos.c.voto.in_(_SIM), 1), else_=0)), 0).label("sim"),
        func.coalesce(func.sum(case((votos.c.voto.in_(_NAO), 1), else_=0)), 0).label("nao"),
    )


def feed_items(limit: int = 12, ano: int | None = None, mes: int | None = None) -> list[dict]:
    """Votações recentes com placar real (do arquivo) e o ASSUNTO (ementa)."""
    from sqlalchemy import extract

    stmt = (
        select(
            votacoes.c.id, votacoes.c.data, votacoes.c.sigla_orgao, votacoes.c.descricao,
            votacoes.c.objeto, votacoes.c.ementa, votacoes.c.titulo_ia, votacoes.c.aprovacao,
            votacoes.c.votos_sim.label("sim"), votacoes.c.votos_nao.label("nao"),
        )
        # só votações nominais (com placar): as que de fato importam e têm assunto
        .where((func.coalesce(votacoes.c.votos_sim, 0) + func.coalesce(votacoes.c.votos_nao, 0)) > 0)
    )
    if ano:
        stmt = stmt.where(extract("year", votacoes.c.data) == ano)
    if mes:
        stmt = stmt.where(extract("month", votacoes.c.data) == mes)
    out = _rows(stmt.order_by(desc(votacoes.c.data)).limit(limit))
    for r in out:
        r["kind"] = kind_resultado(r["aprovacao"], r["sim"], r["nao"])
        r["titulo"] = r["titulo_ia"] or r["ementa"] or r["descricao"] or ("Votação " + r["id"])
        r["subtitulo"] = r["ementa"] if r["titulo_ia"] else None
    return out


def feed_grouped(limit: int = 12, raw: int = 140) -> list[dict]:
    """Agrupa votações por proposição (objeto): uma mesma PEC/PL tem vários turnos/destaques."""
    items = feed_items(raw)
    groups, index = [], {}
    for it in items:
        key = it["objeto"] or ("__" + it["id"])
        if key not in index:
            index[key] = dict(
                objeto=it["objeto"], titulo=it["titulo"], ementa=it["ementa"],
                data=it["data"], sigla_orgao=it["sigla_orgao"], kind=it["kind"], votacoes=[],
            )
            groups.append(index[key])
        index[key]["votacoes"].append(it)
    return groups[:limit]


def mais_vigiados(limit: int = 5) -> list[dict]:
    """Top deputados por gasto + % de presença (para a sidebar do feed)."""
    deps = ranking_gastos_deputados(limit)
    for d in deps:
        p = deputado_presenca(d["id"])
        d["presence"] = p["pct"] if p else None
    return deps


def ausentes_recentes(n: int = 100, limit: int = 6) -> list[dict]:
    """Quem mais faltou nas últimas n votações nominais."""
    with engine.connect() as conn:
        ids = [r[0] for r in conn.execute(
            select(votacoes.c.id)
            .where((func.coalesce(votacoes.c.votos_sim, 0) + func.coalesce(votacoes.c.votos_nao, 0)) > 0)
            .order_by(desc(votacoes.c.data)).limit(n)
        )]
        if not ids:
            return []
        total = len(ids)
        pres = dict(conn.execute(
            select(votos.c.deputado_id, func.count(func.distinct(votos.c.votacao_id)))
            .where(votos.c.votacao_id.in_(ids)).group_by(votos.c.deputado_id)
        ).all())
    deps = _rows(select(deputados.c.id, deputados.c.nome, deputados.c.sigla_partido,
                        deputados.c.sigla_uf, deputados.c.url_foto))
    for d in deps:
        p = pres.get(d["id"], 0)
        d["ausencias"] = total - p
        d["total"] = total
        d["pct"] = round(100 * (total - p) / total, 1) if total else 0
    deps.sort(key=lambda x: -x["ausencias"])
    return deps[:limit]


def gastoes_recentes(meses: int = 3, limit: int = 6) -> list[dict]:
    """Maiores gastadores nos últimos `meses` meses com dados."""
    periodos = _rows(
        select(despesas.c.ano, despesas.c.mes).distinct()
        .where(despesas.c.ano.isnot(None), despesas.c.mes.isnot(None))
        .order_by(desc(despesas.c.ano), desc(despesas.c.mes)).limit(meses)
    )
    if not periodos:
        return []
    cond = None
    for p in periodos:
        c = (despesas.c.ano == p["ano"]) & (despesas.c.mes == p["mes"])
        cond = c if cond is None else (cond | c)
    rows = _rows(
        select(
            deputados.c.id, deputados.c.nome, deputados.c.sigla_partido,
            deputados.c.sigla_uf, deputados.c.url_foto,
            func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("total"),
        )
        .select_from(deputados.join(despesas, despesas.c.deputado_id == deputados.c.id))
        .where(cond)
        .group_by(deputados.c.id, deputados.c.nome, deputados.c.sigla_partido, deputados.c.sigla_uf, deputados.c.url_foto)
        .order_by(desc("total")).limit(limit)
    )
    return rows


def deputado_stats(dep_id: int, ano: int | None = None) -> dict:
    """Atuação do deputado no ano: votos Sim/Não/outros, votações que participou,
    total de votações nominais do ano (denominador) e cota gasta."""
    from sqlalchemy import extract

    ano = ano or ano_corrente()
    base = votos.join(votacoes, votos.c.votacao_id == votacoes.c.id)
    ano_cond = extract("year", votacoes.c.data) == ano

    def _count(extra):
        return _scalar(select(func.count()).select_from(base).where(votos.c.deputado_id == dep_id, ano_cond, extra))

    sim = _count(votos.c.voto.in_(_SIM))
    nao = _count(votos.c.voto.in_(_NAO))
    participou = _scalar(
        select(func.count(func.distinct(votos.c.votacao_id))).select_from(base)
        .where(votos.c.deputado_id == dep_id, ano_cond)
    )
    outros = max(participou - sim - nao, 0)
    total_ano = _scalar(
        select(func.count()).select_from(votacoes).where(
            ano_cond, (func.coalesce(votacoes.c.votos_sim, 0) + func.coalesce(votacoes.c.votos_nao, 0)) > 0
        )
    )
    cota_ano = _scalar(
        select(func.coalesce(func.sum(despesas.c.valor_liquido), 0)).where(
            despesas.c.deputado_id == dep_id, despesas.c.ano == ano
        )
    )
    faltou = max(total_ano - participou, 0)
    pct_part = round(100 * participou / total_ano, 1) if total_ano else 0
    return dict(votes_for=sim, votes_against=nao, outros=outros, participou=participou,
                total_ano=total_ano, faltou=faltou, pct_part=pct_part, cota_ano=cota_ano, ano=ano)


def deputado_gasto_mensal(dep_id: int, ano: int = ANO_REF) -> list[float]:
    rows = _rows(
        select(despesas.c.mes, func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("total"))
        .where(despesas.c.deputado_id == dep_id, despesas.c.ano == ano)
        .group_by(despesas.c.mes)
    )
    by_mes = {int(r["mes"]): float(r["total"]) for r in rows if r["mes"]}
    return [round(by_mes.get(m, 0.0)) for m in range(1, 13)]


def deputado_recibos(dep_id: int, limit: int = 12, categoria: str | None = None,
                     ano: int | None = None, mes: int | None = None) -> list[dict]:
    stmt = select(
        despesas.c.data_documento, despesas.c.fornecedor_nome, despesas.c.fornecedor_cnpj_cpf,
        despesas.c.tipo_despesa, despesas.c.valor_liquido, despesas.c.url_documento,
    ).where(despesas.c.deputado_id == dep_id)
    if categoria:
        stmt = stmt.where(despesas.c.tipo_despesa == categoria)
    if ano:
        stmt = stmt.where(despesas.c.ano == ano)
    if mes:
        stmt = stmt.where(despesas.c.mes == mes)
    return _rows(stmt.order_by(desc(despesas.c.valor_liquido)).limit(limit))


# ===================================================================
#  RELATÓRIO GERAL (panorama de gastos agregados + drill-down)
# ===================================================================
def anos_despesa() -> list[int]:
    rows = _rows(select(despesas.c.ano).distinct().where(despesas.c.ano.isnot(None)).order_by(desc(despesas.c.ano)))
    return [r["ano"] for r in rows if r["ano"]]


def _media(total, qtd):
    return (total / qtd) if qtd else 0


# ===================================================================
#  RAIO-X: dashboard configurável (Geral / Partido / Deputado)
# ===================================================================
def partidos_list() -> list[str]:
    return [r["sigla_partido"] for r in _rows(
        select(deputados.c.sigla_partido).distinct()
        .where(deputados.c.sigla_partido.isnot(None)).order_by(deputados.c.sigla_partido))]


def deputados_min() -> list[dict]:
    return _rows(select(deputados.c.id, deputados.c.nome, deputados.c.sigla_partido, deputados.c.sigla_uf)
                 .order_by(deputados.c.nome))


def _scope_despesas(escopo, alvo, ano, ate_mes=None):
    """Tabela + condições de despesa para o escopo. `ate_mes` limita ao período
    (mes <= ate_mes), usado na comparação justa de mesmo período entre anos."""
    extra = [despesas.c.mes <= ate_mes] if ate_mes else []
    if escopo == "deputado":
        return despesas, [despesas.c.deputado_id == int(alvo), despesas.c.ano == ano, *extra]
    if escopo == "partido":
        return (deputados.join(despesas, despesas.c.deputado_id == deputados.c.id),
                [deputados.c.sigla_partido == alvo, despesas.c.ano == ano, *extra])
    return despesas, [despesas.c.ano == ano, *extra]


def _scope_votos(escopo, alvo, ano):
    from sqlalchemy import extract
    j = votos.join(votacoes, votos.c.votacao_id == votacoes.c.id)
    conds = [extract("year", votacoes.c.data) == ano]
    if escopo == "deputado":
        conds.append(votos.c.deputado_id == int(alvo))
    elif escopo == "partido":
        j = j.join(deputados, deputados.c.id == votos.c.deputado_id)
        conds.append(deputados.c.sigla_partido == alvo)
    return j, conds


MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
# Siglas das orientações de bloco na tabela `orientacoes` (variam de grafia ao longo do tempo).
_ORI_GOV = ["Governo", "GOV."]
_ORI_MAI = ["Maioria"]


def _scope_dep_ids(escopo, alvo):
    """IDs dos deputados do escopo (None = todos / geral)."""
    if escopo == "deputado":
        return [int(alvo)]
    if escopo == "partido":
        return [r["id"] for r in _rows(
            select(deputados.c.id).where(deputados.c.sigla_partido == alvo))]
    return None


# ------------------------------------------------------- PRESENÇA (escopo)
def _plenarias_por_ano(ano, ate_mes=None):
    """IDs das sessões de plenário (eventos com >=100 deputados) do ano/período."""
    from sqlalchemy import extract
    conds = [presenca.c.ano == ano]
    if ate_mes:
        conds.append(extract("month", presenca.c.data) <= ate_mes)
    return [r["evento_id"] for r in _rows(
        select(presenca.c.evento_id).where(*conds)
        .group_by(presenca.c.evento_id)
        .having(func.count(func.distinct(presenca.c.deputado_id)) >= 100))]


def presenca_escopo(escopo, alvo, ano, ate_mes=None):
    """Taxa de presença no plenário do escopo no ano/período.

    - deputado: a presença dele;
    - partido: média da bancada (presenças/sessões somadas);
    - geral: média da Câmara (média das taxas individuais dos deputados que votam).
    Compara com a média geral da Câmara no mesmo período.
    """
    plen = _plenarias_por_ano(ano, ate_mes)
    total = len(plen)
    if not total:
        return None
    ids = _scope_dep_ids(escopo, alvo)

    # presenças por deputado dentro do conjunto de plenárias
    base = select(presenca.c.deputado_id, func.count(func.distinct(presenca.c.evento_id)).label("n")) \
        .where(presenca.c.evento_id.in_(plen)).group_by(presenca.c.deputado_id)
    pres_by = {r["deputado_id"]: r["n"] for r in _rows(base)}

    # universo de deputados "ativos" (que registraram alguma presença no período)
    ativos = set(pres_by.keys())

    def _media_taxa(dep_ids):
        if not dep_ids:
            return None
        taxas = [100.0 * pres_by.get(d, 0) / total for d in dep_ids]
        return round(sum(taxas) / len(taxas), 1) if taxas else None

    media_geral = _media_taxa(list(ativos))

    if escopo == "deputado":
        presentes = pres_by.get(int(alvo), 0)
        pct = round(100.0 * presentes / total, 1)
        faltas = total - presentes
    elif escopo == "partido":
        dep_ativos = [d for d in (ids or []) if d in ativos]
        pct = _media_taxa(dep_ativos)
        # faltas agregadas da bancada
        faltas = sum(max(total - pres_by.get(d, 0), 0) for d in dep_ativos)
        presentes = sum(pres_by.get(d, 0) for d in dep_ativos)
    else:  # geral
        pct = media_geral
        presentes = sum(pres_by.values())
        faltas = len(ativos) * total - presentes

    if pct is None:
        return None
    delta = round(pct - media_geral, 1) if media_geral is not None else None
    return dict(pct=pct, faltas=faltas, presentes=presentes, total=total,
                media_geral=media_geral, delta=delta,
                acima=(delta is not None and delta > 0))


def dias_trabalhados_escopo(escopo, alvo, ano, ate_mes=None):
    """Datas distintas com presença registrada (em qualquer evento) no período."""
    from sqlalchemy import extract
    conds = [presenca.c.ano == ano]
    if ate_mes:
        conds.append(extract("month", presenca.c.data) <= ate_mes)
    ids = _scope_dep_ids(escopo, alvo)
    if ids is not None:
        conds.append(presenca.c.deputado_id.in_(ids))
    return _scalar(select(func.count(func.distinct(presenca.c.data))).where(*conds), default=0)


# ------------------------------------------ ALINHAMENTO COM GOVERNO/MAIORIA
def alinhamento_escopo(escopo, alvo, ano):
    """% das vezes que o escopo votou conforme a orientação do Governo e da Maioria.

    Considera só votações em que houve orientação Sim/Não e voto efetivo Sim/Não.
    Para deputado: voto dele vs orientação. Para partido/geral: agrega votos de todos.
    """
    from sqlalchemy import extract, text

    ids = _scope_dep_ids(escopo, alvo)
    id_filter = ""
    params = {"ano_ini": f"{ano}-01-01", "ano_fim": f"{ano + 1}-01-01"}
    if ids is not None:
        # lista pequena (1 dep) ou bancada: usa IN com bind dinâmico
        place = ",".join(str(int(i)) for i in ids) or "-1"
        id_filter = f"AND vo.deputado_id IN ({place})"

    def _pct(siglas):
        sig_list = ",".join(f"'{s}'" for s in siglas)
        sql = text(f"""
            SELECT
              SUM(CASE WHEN vo.voto = o.orientacao THEN 1 ELSE 0 END) AS conf,
              COUNT(*) AS tot
            FROM votos vo
            JOIN votacoes va ON va.id = vo.votacao_id
            JOIN orientacoes o ON o.votacao_id = vo.votacao_id
            WHERE va.data >= :ano_ini AND va.data < :ano_fim
              AND o.sigla_partido IN ({sig_list})
              AND o.orientacao IN ('Sim','Não')
              AND vo.voto IN ('Sim','Não')
              {id_filter}
        """)
        with engine.connect() as conn:
            row = conn.execute(sql, params).first()
        if not row or not row.tot:
            return None
        return dict(pct=round(100.0 * row.conf / row.tot, 1), conforme=row.conf, total=row.tot)

    return dict(governo=_pct(_ORI_GOV), maioria=_pct(_ORI_MAI))


def coesao_partido(sigla, ano):
    """Coesão da bancada: em média, qual a fração de votos do partido que vai com
    o voto majoritário do próprio partido em cada votação nominal do ano."""
    from sqlalchemy import text
    sql = text("""
        WITH pv AS (
            SELECT vo.votacao_id,
                   SUM(CASE WHEN vo.voto='Sim' THEN 1 ELSE 0 END) AS sim,
                   SUM(CASE WHEN vo.voto='Não' THEN 1 ELSE 0 END) AS nao
            FROM votos vo
            JOIN votacoes va ON va.id = vo.votacao_id
            JOIN deputados d ON d.id = vo.deputado_id
            WHERE d.sigla_partido = :sig
              AND va.data >= :ano_ini AND va.data < :ano_fim
              AND vo.voto IN ('Sim','Não')
            GROUP BY vo.votacao_id
        )
        SELECT AVG(CAST(CASE WHEN sim > nao THEN sim ELSE nao END AS FLOAT) / (sim+nao)) AS coesao, COUNT(*) AS n
        FROM pv WHERE (sim+nao) > 0
    """)
    with engine.connect() as conn:
        row = conn.execute(sql, {"sig": sigla, "ano_ini": f"{ano}-01-01", "ano_fim": f"{ano + 1}-01-01"}).first()
    if not row or not row.n:
        return None
    return dict(pct=round(100.0 * row.coesao, 1), votacoes=row.n)


# ---------------------------------- RETRATO INDIVIDUAL (só deputado)
def fidelidade_partidaria(dep_id: int, ano: int) -> dict | None:
    """Quantas vezes o deputado votou conforme a orientação do PRÓPRIO partido.

    É a métrica-assinatura do retrato individual: mede independência. O complemento
    (total - conforme) são as vezes em que ele "bateu de frente" com o líder.
    """
    from sqlalchemy import text

    d = get_deputado(dep_id)
    if not d or not d.get("sigla_partido"):
        return None
    sql = text("""
        SELECT
          SUM(CASE WHEN vo.voto = o.orientacao THEN 1 ELSE 0 END) AS conf,
          COUNT(*) AS tot
        FROM votos vo
        JOIN votacoes va ON va.id = vo.votacao_id
        JOIN orientacoes o ON o.votacao_id = vo.votacao_id AND o.sigla_partido = :sig
        WHERE vo.deputado_id = :did
          AND va.data >= :ano_ini AND va.data < :ano_fim
          AND o.orientacao IN ('Sim','Não') AND vo.voto IN ('Sim','Não')
    """)
    with engine.connect() as conn:
        row = conn.execute(sql, {
            "sig": d["sigla_partido"], "did": dep_id,
            "ano_ini": f"{ano}-01-01", "ano_fim": f"{ano + 1}-01-01",
        }).first()
    if not row or not row.tot:
        return None
    conf, tot = row.conf or 0, row.tot
    return dict(pct=round(100.0 * conf / tot, 1), conforme=conf, total=tot,
                rebelde=tot - conf, partido=d["sigla_partido"])


def gasto_percentil(dep_id: int, ano: int) -> dict | None:
    """Posição do deputado no ranking de gasto do ano: gasta mais que X% dos demais."""
    tot_dep = func.coalesce(func.sum(despesas.c.valor_liquido), 0)
    rows = _rows(
        select(despesas.c.deputado_id.label("did"), tot_dep.label("t"))
        .where(despesas.c.ano == ano).group_by(despesas.c.deputado_id))
    if not rows:
        return None
    vals = sorted((r["t"] for r in rows), reverse=True)
    n = len(vals)
    meu = next((r["t"] for r in rows if r["did"] == dep_id), 0.0)
    # rank 1 = quem mais gasta
    rank = sum(1 for v in vals if v > meu) + 1
    abaixo = sum(1 for v in vals if v < meu)
    return dict(gasto=meu, rank=rank, total=n,
                acima_de=round(100.0 * abaixo / n) if n else 0)


# ---------------------------------- DISPERSÃO INTERNA (só partido)
def partido_ranking_interno(sigla: str, ano: int, limit: int = 5) -> dict:
    """Quem se destaca dentro da bancada: maiores gastadores e mais faltosos.

    Métrica-assinatura do retrato de partido: só faz sentido no coletivo.
    """
    j = deputados.join(despesas, despesas.c.deputado_id == deputados.c.id)
    top_gasto = _rows(
        select(deputados.c.id, deputados.c.nome, deputados.c.sigla_uf,
               func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("total"))
        .select_from(j)
        .where(deputados.c.sigla_partido == sigla, despesas.c.ano == ano)
        .group_by(deputados.c.id, deputados.c.nome, deputados.c.sigla_uf)
        .order_by(desc("total")).limit(limit))

    # presença por deputado da bancada nas plenárias do ano
    plen = _plenarias_por_ano(ano)
    faltosos: list[dict] = []
    if plen:
        total_sessoes = len(plen)
        ids = _scope_dep_ids("partido", sigla) or []
        pres_by = {r["deputado_id"]: r["n"] for r in _rows(
            select(presenca.c.deputado_id, func.count(func.distinct(presenca.c.evento_id)).label("n"))
            .where(presenca.c.evento_id.in_(plen), presenca.c.deputado_id.in_(ids))
            .group_by(presenca.c.deputado_id))}
        nomes = {r["id"]: r for r in _rows(
            select(deputados.c.id, deputados.c.nome, deputados.c.sigla_uf)
            .where(deputados.c.id.in_(ids)))} if ids else {}
        for did in pres_by:  # só quem tem presença registrada (ativo no período)
            pres = pres_by.get(did, 0)
            info = nomes.get(did, {})
            faltosos.append(dict(id=did, nome=info.get("nome", "—"),
                                 sigla_uf=info.get("sigla_uf", ""),
                                 faltas=total_sessoes - pres,
                                 pct=round(100.0 * pres / total_sessoes, 1)))
        faltosos.sort(key=lambda x: x["faltas"], reverse=True)
        faltosos = faltosos[:limit]
    return dict(top_gasto=top_gasto, faltosos=faltosos)


# --------------------------------------------------- FINANCIAMENTO (TSE)
def partido_deputados(sigla, ano, limit=120):
    """Todos os deputados da bancada com o gasto do ano (clicáveis p/ o raio-x)."""
    j = deputados.outerjoin(despesas, (despesas.c.deputado_id == deputados.c.id) & (despesas.c.ano == ano))
    return _rows(
        select(deputados.c.id, deputados.c.nome, deputados.c.sigla_uf, deputados.c.url_foto,
               func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("gasto"))
        .select_from(j).where(deputados.c.sigla_partido == sigla)
        .group_by(deputados.c.id, deputados.c.nome, deputados.c.sigla_uf, deputados.c.url_foto)
        .order_by(desc("gasto")).limit(limit))


def _cpfs_escopo(escopo, alvo):
    if escopo == "deputado":
        d = get_deputado(int(alvo))
        return [d["cpf"]] if d and d.get("cpf") else []
    if escopo == "partido":
        return [r["cpf"] for r in _rows(
            select(deputados.c.cpf).where(deputados.c.sigla_partido == alvo, deputados.c.cpf.isnot(None)))]
    return None  # geral: todos


def financiamento_escopo(escopo, alvo):
    """Arrecadação de campanha (tse_doacoes) e força eleitoral (tse_candidatos.votos)."""
    cpfs = _cpfs_escopo(escopo, alvo)
    dconds, vconds = [], [tse_candidatos.c.situacao.ilike("ELEITO%")]
    if cpfs is not None:
        if not cpfs:
            return None
        dconds.append(tse_doacoes.c.cpf_candidato.in_(cpfs))
        vconds.append(tse_candidatos.c.cpf.in_(cpfs))

    total = _scalar(select(func.coalesce(func.sum(tse_doacoes.c.valor), 0)).where(*dconds))
    doadores = _rows(
        select(tse_doacoes.c.doador.label("doador"),
               func.coalesce(func.sum(tse_doacoes.c.valor), 0).label("total"),
               func.count().label("qtd"))
        .where(*dconds, tse_doacoes.c.doador.isnot(None))
        .group_by(tse_doacoes.c.doador).order_by(desc("total")).limit(8))
    votos_recebidos = _scalar(
        select(func.coalesce(func.sum(tse_candidatos.c.votos), 0)).where(*vconds))
    n_eleitos = _scalar(select(func.count()).select_from(tse_candidatos).where(*vconds))
    if not total and not votos_recebidos:
        return None
    custo_por_voto = round(total / votos_recebidos, 2) if (total and votos_recebidos) else None
    dependencia = None
    if total and doadores:
        top = doadores[0]
        dependencia = dict(doador=top["doador"], valor=top["total"],
                           pct=round(100.0 * top["total"] / total, 1))
    return dict(total=total, doadores=doadores, votos_recebidos=votos_recebidos,
                n_eleitos=n_eleitos, custo_por_voto=custo_por_voto, dependencia=dependencia)


# ----------------------------------------- PRODUÇÃO LEGISLATIVA (proposições)
def producao_legislativa(escopo, alvo, ano):
    """Projetos apresentados (de autoria) pelo escopo no ano, por tipo.

    Usa proponente=1 (autor principal). Para partido/geral soma a bancada/Casa.
    """
    ids = _scope_dep_ids(escopo, alvo)
    conds = [proposicao_autores.c.ano == ano, proposicao_autores.c.proponente == 1]
    if ids is not None:
        if not ids:
            return None
        conds.append(proposicao_autores.c.deputado_id.in_(ids))
    # proposições distintas de autoria
    total = _scalar(select(func.count(func.distinct(proposicao_autores.c.proposicao_id))).where(*conds))
    if not total:
        return dict(total=0, projetos=0, por_tipo=[])
    j = proposicao_autores.join(proposicoes, proposicoes.c.id == proposicao_autores.c.proposicao_id)
    por_tipo = _rows(
        select(proposicoes.c.sigla_tipo.label("tipo"),
               func.count(func.distinct(proposicao_autores.c.proposicao_id)).label("n"))
        .select_from(j).where(*conds)
        .group_by(proposicoes.c.sigla_tipo).order_by(desc("n")))
    # projetos de lei "de verdade" (vs. peças procedimentais como REQ/PRL/RDF)
    projetos = sum(t["n"] for t in por_tipo if t["tipo"] in _TIPOS_PROJETO)
    # desfecho dos projetos de lei: em tramitação / virou lei / arquivado-retirado
    sit_rows = _rows(
        select(proposicoes.c.situacao, func.count(func.distinct(proposicao_autores.c.proposicao_id)).label("n"))
        .select_from(j).where(*conds, proposicoes.c.sigla_tipo.in_(_TIPOS_PROJETO))
        .group_by(proposicoes.c.situacao))
    desfecho = {"tramitando": 0, "lei": 0, "arquivado": 0}
    for r in sit_rows:
        desfecho[_desfecho_situacao(r["situacao"])] += r["n"]
    return dict(total=total, projetos=projetos, por_tipo=por_tipo[:8],
                por_tipo_projeto=[t for t in por_tipo if t["tipo"] in _TIPOS_PROJETO][:6],
                desfecho=desfecho)


def _desfecho_situacao(situacao) -> str:
    """Classifica a situação de tramitação em: 'lei' | 'arquivado' | 'tramitando'."""
    s = (situacao or "").lower()
    if "norma jurídica" in s or "transformado em lei" in s or "promulg" in s or "sancion" in s:
        return "lei"
    if s.startswith("arquivad") or "retirad" in s or "devolvid" in s or "rejeitad" in s or "prejudicad" in s:
        return "arquivado"
    return "tramitando"


# Tipos de proposição que são "projetos de lei" no sentido cidadão (vs. peças internas).
_TIPOS_PROJETO = {"PL", "PEC", "PLP", "PDL", "PDC", "PLV", "PLC", "PLN"}
_TIPO_NOME = {"PL": "projeto de lei", "PEC": "PEC", "PLP": "lei complementar",
              "PDL": "decreto legislativo", "PDC": "decreto legislativo",
              "PLV": "lei de conversão", "PLC": "projeto de lei", "PLN": "plano"}


def producao_percentil(dep_id, ano):
    """Posição do deputado no ranking de projetos de lei apresentados no ano."""
    j = proposicao_autores.join(proposicoes, proposicoes.c.id == proposicao_autores.c.proposicao_id)
    rows = _rows(
        select(proposicao_autores.c.deputado_id.label("did"),
               func.count(func.distinct(proposicao_autores.c.proposicao_id)).label("n"))
        .select_from(j)
        .where(proposicao_autores.c.ano == ano, proposicao_autores.c.proponente == 1,
               proposicoes.c.sigla_tipo.in_(_TIPOS_PROJETO))
        .group_by(proposicao_autores.c.deputado_id))
    if not rows:
        return None
    meu = next((r["n"] for r in rows if r["did"] == dep_id), 0)
    n = len(rows)
    abaixo = sum(1 for r in rows if r["n"] < meu)
    media = round(sum(r["n"] for r in rows) / n, 1) if n else 0
    return dict(projetos=meu, acima_de=round(100.0 * abaixo / n) if n else 0, media=media, total=n)


def proposicoes_recentes(escopo, alvo, ano, limit=6):
    """Projetos de lei mais recentes apresentados pelo escopo no ano.

    Filtra para tipos substantivos (PL/PEC/PLP…), não peças procedimentais (REQ/PRL/RDF).
    """
    ids = _scope_dep_ids(escopo, alvo)
    conds = [proposicao_autores.c.ano == ano, proposicao_autores.c.proponente == 1,
             proposicoes.c.sigla_tipo.in_(_TIPOS_PROJETO)]
    if ids is not None:
        if not ids:
            return []
        conds.append(proposicao_autores.c.deputado_id.in_(ids))
    j = proposicao_autores.join(proposicoes, proposicoes.c.id == proposicao_autores.c.proposicao_id)
    rows = _rows(
        select(proposicoes.c.id, proposicoes.c.sigla_tipo, proposicoes.c.numero,
               proposicoes.c.ano, proposicoes.c.ementa, proposicoes.c.data_apresentacao,
               proposicoes.c.url_inteiro_teor, proposicoes.c.ultimo_status)
        .select_from(j).where(*conds)
        .group_by(proposicoes.c.id, proposicoes.c.sigla_tipo, proposicoes.c.numero,
                  proposicoes.c.ano, proposicoes.c.ementa, proposicoes.c.data_apresentacao,
                  proposicoes.c.url_inteiro_teor, proposicoes.c.ultimo_status)
        .order_by(desc(proposicoes.c.data_apresentacao)).limit(limit))
    for r in rows:
        r["rotulo"] = f"{r['sigla_tipo']} {r['numero']}/{r['ano']}"
    return rows


# ---------------------------------------------- TETO DA CEAP (uso vs limite)
def teto_ceap_escopo(escopo, alvo, ano, gasto, parcial, ate_mes):
    """Uso da cota vs. o teto legal (CEAP), pró-rateado no ano em curso.

    O teto é mensal e varia por UF. Para o ano parcial, comparamos o gasto com o
    teto disponível ATÉ AGORA (mensal × meses decorridos): leitura justa de ritmo.
    """
    from .ceap import CEAP_MENSAL

    if escopo == "deputado":
        d = get_deputado(int(alvo)) if alvo else None
        ufs = [d["sigla_uf"]] if d else []
    elif escopo == "partido":
        ufs = [r["sigla_uf"] for r in _rows(
            select(deputados.c.sigla_uf).where(deputados.c.sigla_partido == alvo))]
    else:
        ufs = [r["sigla_uf"] for r in _rows(select(deputados.c.sigla_uf))]

    mensal = sum(CEAP_MENSAL.get((u or "").upper(), 0) for u in ufs)
    if not mensal:
        return None
    meses = ate_mes if parcial else 12
    limite_ano = mensal * 12
    limite_periodo = mensal * meses
    pct_periodo = round(100.0 * gasto / limite_periodo, 1) if limite_periodo else None
    pct_ano = round(100.0 * gasto / limite_ano, 1) if limite_ano else None
    return dict(limite_ano=limite_ano, limite_periodo=limite_periodo,
                pct_periodo=pct_periodo, pct_ano=pct_ano, meses=meses,
                usado=gasto, sobra=max(limite_periodo - gasto, 0))


# ---------------------------------------- PARTICIPAÇÃO EM VOTAÇÕES NOMINAIS
def participacao_votacoes(escopo, alvo, ano):
    """Em quantas das votações nominais do ano o escopo efetivamente votou.

    Diferente da presença em sessão: mede se o parlamentar registra voto quando há
    votação nominal. Para partido/geral: média da participação da bancada.
    """
    from sqlalchemy import text

    nominais = [r["id"] for r in _rows(
        select(votacoes.c.id).where(
            votacoes.c.data >= __import__("datetime").date(ano, 1, 1),
            votacoes.c.data < __import__("datetime").date(ano + 1, 1, 1),
            (votacoes.c.votos_sim + votacoes.c.votos_nao) > 0))]
    total = len(nominais)
    if not total:
        return None

    if escopo == "deputado":
        votou = _scalar(select(func.count(func.distinct(votos.c.votacao_id)))
                        .where(votos.c.deputado_id == int(alvo), votos.c.votacao_id.in_(nominais)))
        return dict(votou=votou, total=total, pct=round(100.0 * votou / total, 1))

    ids = _scope_dep_ids(escopo, alvo)
    cond = [votos.c.votacao_id.in_(nominais)]
    if ids is not None:
        cond.append(votos.c.deputado_id.in_(ids))
    by = {r["deputado_id"]: r["n"] for r in _rows(
        select(votos.c.deputado_id, func.count(func.distinct(votos.c.votacao_id)).label("n"))
        .where(*cond).group_by(votos.c.deputado_id))}
    if not by:
        return None
    taxas = [100.0 * n / total for n in by.values()]
    media = round(sum(taxas) / len(taxas), 1)
    return dict(votou=round(sum(by.values()) / len(by)), total=total, pct=media, bancada=True)


# ----------------------------------------- CONCENTRAÇÃO DE FORNECEDOR
def concentracao_fornecedor(escopo, alvo, ano):
    """Quanto do gasto vai para o MAIOR fornecedor (red flag de concentração)."""
    frm, conds = _scope_despesas(escopo, alvo, ano)
    rows = _rows(
        select(despesas.c.fornecedor_nome.label("nome"),
               despesas.c.fornecedor_cnpj_cpf.label("doc"),
               func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("v"))
        .select_from(frm).where(*conds, despesas.c.fornecedor_cnpj_cpf.isnot(None))
        .group_by(despesas.c.fornecedor_nome, despesas.c.fornecedor_cnpj_cpf)
        .order_by(desc("v")))
    if not rows:
        return None
    total = sum(r["v"] for r in rows)
    if total <= 0:
        return None
    top = rows[0]
    return dict(top_nome=top["nome"], top_valor=top["v"],
                pct=round(100.0 * top["v"] / total, 1), n_fornecedores=len(rows))


# ----------------------------------------- BENCHMARK (vs média partido/UF)
def benchmark_deputado(dep_id, ano, gasto):
    """Gasto do deputado vs. a média por deputado do seu partido e da sua UF."""
    d = get_deputado(dep_id)
    if not d:
        return None

    def _media(col, val):
        sub = (select(despesas.c.deputado_id, func.sum(despesas.c.valor_liquido).label("g"))
               .select_from(deputados.join(despesas, despesas.c.deputado_id == deputados.c.id))
               .where(col == val, despesas.c.ano == ano)
               .group_by(despesas.c.deputado_id)).subquery()
        return _scalar(select(func.avg(sub.c.g)), default=0)

    media_part = _media(deputados.c.sigla_partido, d["sigla_partido"])
    media_uf = _media(deputados.c.sigla_uf, d["sigla_uf"])
    return dict(
        partido=d["sigla_partido"], uf=d["sigla_uf"],
        media_partido=media_part, media_uf=media_uf,
        vs_partido=round((gasto - media_part) / media_part * 100, 1) if media_part else None,
        vs_uf=round((gasto - media_uf) / media_uf * 100, 1) if media_uf else None)


# ----------------------------------------- SÉRIE HISTÓRICA (desde 2022)
def serie_historica(escopo, alvo, ano_fim, desde=2022):
    """Gasto e presença ano a ano (mini-tendência). Anos de `desde` até `ano_fim`."""
    anos = list(range(desde, ano_fim + 1))
    out = []
    for a in anos:
        frm, conds = _scope_despesas(escopo, alvo, a)
        g = _scalar(select(func.coalesce(func.sum(despesas.c.valor_liquido), 0)).select_from(frm).where(*conds))
        pres = presenca_escopo(escopo, alvo, a)
        out.append(dict(ano=a, gasto=g, presenca=(pres["pct"] if pres else None)))
    return out


def proposicao_link(objeto: str) -> dict | None:
    """Resolve o link do texto original a partir do objeto da votação (ex.: 'PEC 5/2023').

    Tenta achar a proposição no banco (url do inteiro teor + página da Câmara);
    se não achar, devolve um link de busca na Câmara como fallback.
    """
    import re
    if not objeto:
        return None
    m = re.match(r"\s*([A-Za-zÇç]+)\s*(\d+)\s*/\s*(\d{4})", objeto)
    if not m:
        return None
    sigla, num, ano = m.group(1).upper(), int(m.group(2)), int(m.group(3))
    rows = _rows(
        select(proposicoes.c.id, proposicoes.c.url_inteiro_teor)
        .where(func.upper(proposicoes.c.sigla_tipo) == sigla,
               proposicoes.c.numero == num, proposicoes.c.ano == ano).limit(1))
    if rows:
        r = rows[0]
        return dict(inteiro_teor=r["url_inteiro_teor"],
                    camara=f"https://www.camara.leg.br/propostas-legislativas/{r['id']}",
                    rotulo=f"{sigla} {num}/{ano}")
    return dict(inteiro_teor=None,
                camara=f"https://www.camara.leg.br/busca-portal?q={sigla}%20{num}%2F{ano}",
                rotulo=f"{sigla} {num}/{ano}")


def _desfecho_cond(desfecho):
    """Condição SQL para o desfecho da proposição (espelha _desfecho_situacao)."""
    s = func.lower(proposicoes.c.situacao)
    if desfecho == "lei":
        return s.like("%norma jurídica%") | s.like("%transform%lei%") | s.like("%promulg%") | s.like("%sancion%")
    if desfecho == "arquivado":
        return (s.like("arquivad%") | s.like("%retirad%") | s.like("%devolvid%")
                | s.like("%rejeitad%") | s.like("%prejudicad%"))
    return None


def partido_projetos(sigla: str, anos, desfecho: str = "lei", limit: int = 300) -> list[dict]:
    """Projetos de lei de autoria da bancada no mandato, por desfecho, com o autor."""
    if isinstance(anos, int):
        anos = [anos]
    j = (proposicao_autores
         .join(proposicoes, proposicoes.c.id == proposicao_autores.c.proposicao_id)
         .join(deputados, deputados.c.id == proposicao_autores.c.deputado_id))
    conds = [deputados.c.sigla_partido == sigla, proposicao_autores.c.proponente == 1,
             proposicao_autores.c.ano.in_(anos), proposicoes.c.sigla_tipo.in_(list(_TIPOS_PROJETO))]
    dc = _desfecho_cond(desfecho)
    if dc is not None:
        conds.append(dc)
    rows = _rows(
        select(proposicoes.c.id, proposicoes.c.sigla_tipo, proposicoes.c.numero, proposicoes.c.ano,
               proposicoes.c.ementa, proposicoes.c.situacao, proposicoes.c.data_apresentacao,
               proposicoes.c.url_inteiro_teor,
               func.max(deputados.c.nome).label("autor"), func.max(deputados.c.id).label("autor_id"),
               func.count(func.distinct(proposicao_autores.c.deputado_id)).label("n_aut"))
        .select_from(j).where(*conds)
        .group_by(proposicoes.c.id, proposicoes.c.sigla_tipo, proposicoes.c.numero, proposicoes.c.ano,
                  proposicoes.c.ementa, proposicoes.c.situacao, proposicoes.c.data_apresentacao,
                  proposicoes.c.url_inteiro_teor)
        .order_by(desc(proposicoes.c.data_apresentacao)).limit(limit))
    for r in rows:
        r["rotulo"] = f"{r['sigla_tipo']} {r['numero']}/{r['ano']}"
    return rows


def producao_por_partido(anos):
    """Projetos de lei por partido nos anos do mandato: apresentados / viraram lei / arquivados.

    Conta sobre TODOS os anos informados (o mandato), porque há defasagem entre
    apresentar e o desfecho: olhar só o ano corrente daria ~0 leis/arquivados.
    `anos` pode ser um int (um ano) ou uma lista de anos.
    """
    if isinstance(anos, int):
        anos = [anos]
    j = (proposicao_autores
         .join(proposicoes, proposicoes.c.id == proposicao_autores.c.proposicao_id)
         .join(deputados, deputados.c.id == proposicao_autores.c.deputado_id))
    rows = _rows(
        select(deputados.c.sigla_partido.label("sig"), proposicoes.c.situacao,
               func.count(func.distinct(proposicao_autores.c.proposicao_id)).label("n"))
        .select_from(j)
        .where(proposicao_autores.c.ano.in_(anos), proposicao_autores.c.proponente == 1,
               proposicoes.c.sigla_tipo.in_(list(_TIPOS_PROJETO)))
        .group_by(deputados.c.sigla_partido, proposicoes.c.situacao))
    out: dict = {}
    for r in rows:
        d = out.setdefault(r["sig"], {"apresentados": 0, "lei": 0, "arquivado": 0})
        d["apresentados"] += r["n"]
        desf = _desfecho_situacao(r["situacao"])
        if desf == "lei":
            d["lei"] += r["n"]
        elif desf == "arquivado":
            d["arquivado"] += r["n"]
    return out


# ----------------------------------------- RANKING ENTRE PARTIDOS (geral)
def ranking_partidos(ano, min_dep=5, limit=18):
    """Para o escopo geral: por partido, gasto médio/dep, governismo e coesão."""
    # gasto médio por deputado, por partido
    sub = (select(despesas.c.deputado_id, deputados.c.sigla_partido.label("sig"),
                  func.sum(despesas.c.valor_liquido).label("g"))
           .select_from(deputados.join(despesas, despesas.c.deputado_id == deputados.c.id))
           .where(despesas.c.ano == ano)
           .group_by(despesas.c.deputado_id, deputados.c.sigla_partido)).subquery()
    gasto_rows = {r["sig"]: r for r in _rows(
        select(sub.c.sig, func.avg(sub.c.g).label("media"), func.count().label("nd"))
        .group_by(sub.c.sig))}
    prod = producao_por_partido(anos_mandato(ano))  # mandato inteiro (defasagem apresentar→desfecho)
    out = []
    for sig, gr in gasto_rows.items():
        if not sig or gr["nd"] < min_dep:
            continue
        al = alinhamento_escopo("partido", sig, ano)
        co = coesao_partido(sig, ano)
        pr = prod.get(sig, {})
        out.append(dict(partido=sig, n_dep=gr["nd"], media_gasto=gr["media"],
                        governo=(al["governo"]["pct"] if al and al.get("governo") else None),
                        coesao=(co["pct"] if co else None),
                        apresentados=pr.get("apresentados", 0),
                        lei=pr.get("lei", 0), arquivado=pr.get("arquivado", 0)))
    out.sort(key=lambda x: (x["coesao"] or 0), reverse=True)
    return out[:limit]


# ----------------------------------------- SELO DE TRANSPARÊNCIA (composto)
def selo_transparencia(presenca_d, participacao, teto=None, fidelidade=None):
    """Índice de assiduidade 0–100 (método aberto): média da presença em sessões e
    da participação em votações nominais: os dois deveres mais objetivos do cargo.

    NÃO é juízo de mérito político nem inclui gasto (a cota é verba de trabalho).
    """
    comps = []
    if presenca_d:
        comps.append(("Presença em sessões", round(presenca_d["pct"])))
    if participacao:
        comps.append(("Participação em votações", round(participacao["pct"])))
    if not comps:
        return None
    nota = round(sum(v for _, v in comps) / len(comps))
    grau = "A" if nota >= 85 else "B" if nota >= 70 else "C" if nota >= 55 else "D"
    return dict(nota=nota, grau=grau, componentes=comps)


# ------------------------------------------------------------- INSIGHTS
def _fmt_pct(x):
    return f"{abs(x):.0f}%".replace(".0", "")


def gerar_insights(d) -> list[dict]:
    """Frases automáticas (sem IA) a partir dos números já calculados."""
    out = []
    quem = {"geral": "A Câmara", "partido": f"O {d['alvo_nome']}", "deputado": (d['alvo_nome'] or '').split(' ')[0] or "Ele"}[d["escopo"]]

    # 1. gasto vs mesmo período
    dg = d.get("delta_periodo")
    if dg is not None and d.get("gasto_prev_periodo"):
        rotulo = f"até {MESES_PT[d['ate_mes']-1]}" if d.get("parcial") else d["prev"]
        if dg > 1:
            out.append(dict(tipo="gasto", bom=False, icon="trending-up",
                            txt=f"Gastou {_fmt_pct(dg)} a mais que no mesmo período de {d['prev']} ({rotulo})."))
        elif dg < -1:
            out.append(dict(tipo="gasto", bom=True, icon="trending-down",
                            txt=f"Gastou {_fmt_pct(dg)} a menos que no mesmo período de {d['prev']} ({rotulo})."))
        else:
            out.append(dict(tipo="gasto", bom=None, icon="minus",
                            txt=f"Gasto praticamente estável em relação ao mesmo período de {d['prev']}."))

    # 2. presença
    p = d.get("presenca")
    if p:
        if d["escopo"] == "geral":
            out.append(dict(tipo="presenca", bom=None, icon="user-check",
                            txt=f"Presença média da Câmara no plenário: {p['pct']}%."))
        else:
            comp = "acima" if p["acima"] else "abaixo"
            out.append(dict(tipo="presenca", bom=p["acima"], icon="user-check",
                            txt=f"Presença de {p['pct']}% no plenário, {comp} da média da Câmara ({p['media_geral']}%)."))
        if d["escopo"] == "deputado" and p["faltas"]:
            out.append(dict(tipo="presenca", bom=False, icon="user-x",
                            txt=f"Faltou em {p['faltas']} de {p['total']} sessões do plenário no período."))

    # 3. projeção
    proj = d.get("projecao")
    if proj and d.get("parcial"):
        out.append(dict(tipo="gasto", bom=None, icon="target",
                        txt=f"No ritmo atual, o ano deve fechar em ~{ui_brl(proj)}."))

    # 4. alinhamento
    al = d.get("alinhamento") or {}
    g = al.get("governo")
    if g:
        out.append(dict(tipo="voto", bom=None, icon="landmark",
                        txt=f"Votou com o Governo em {g['pct']}% das vezes ({g['conforme']} de {g['total']})."))
    m = al.get("maioria")
    if m:
        out.append(dict(tipo="voto", bom=None, icon="users",
                        txt=f"Acompanhou a Maioria em {m['pct']}% das votações."))

    # 5a. fidelidade ao próprio partido (só deputado): independência
    fi = d.get("fidelidade")
    if fi:
        if fi["pct"] >= 90:
            out.append(dict(tipo="voto", bom=None, icon="git-commit-horizontal",
                            txt=f"Vota fechado com o partido: seguiu a orientação da legenda em {fi['pct']}% das votações."))
        elif fi["pct"] >= 70:
            out.append(dict(tipo="voto", bom=None, icon="git-branch",
                            txt=f"Segue o partido em {fi['pct']}% das vezes, mas bateu de frente em {fi['rebelde']} votações."))
        else:
            out.append(dict(tipo="voto", bom=None, icon="git-branch",
                            txt=f"Voto independente: divergiu da orientação do próprio partido em {fi['rebelde']} de {fi['total']} votações ({100 - fi['pct']:.0f}%)."))

    # 5b. percentil de gasto (só deputado)
    pc = d.get("percentil")
    if pc and pc["total"] > 1:
        out.append(dict(tipo="gasto", bom=None, icon="bar-chart-3",
                        txt=f"Gasta mais que {pc['acima_de']}% dos deputados, {pc['rank']}º maior gasto da Câmara em {d['ano']}."))

    # 5c. peso do bloco (só partido)
    if d.get("pct_camara"):
        out.append(dict(tipo="voto", bom=None, icon="users",
                        txt=f"Ocupa {d['n_deputados']} das 513 cadeiras ({d['pct_camara']}% da Câmara)."))

    # 5. coesão (partido)
    co = d.get("coesao")
    if co:
        out.append(dict(tipo="voto", bom=None, icon="git-merge",
                        txt=f"Disciplina da bancada: {co['pct']}%, vota unida em {co['votacoes']} votações nominais."))

    # 6. teto da CEAP
    te = d.get("teto")
    if te and te.get("pct_periodo") is not None:
        rotulo = "até agora" if d.get("parcial") else f"em {d['ano']}"
        if te["pct_periodo"] >= 90:
            out.append(dict(tipo="gasto", bom=False, icon="gauge",
                            txt=f"Raspou o teto da cota: usou {te['pct_periodo']}% do limite disponível {rotulo}."))
        elif te["pct_periodo"] <= 40:
            out.append(dict(tipo="gasto", bom=True, icon="piggy-bank",
                            txt=f"Usou só {te['pct_periodo']}% do teto da cota disponível {rotulo}."))
        else:
            out.append(dict(tipo="gasto", bom=None, icon="gauge",
                            txt=f"Usou {te['pct_periodo']}% do teto da cota disponível {rotulo}."))

    # 7. participação em votações nominais
    pa = d.get("participacao")
    if pa:
        if d["escopo"] == "deputado":
            out.append(dict(tipo="voto", bom=(pa["pct"] >= 80), icon="list-checks",
                            txt=f"Votou em {pa['votou']} de {pa['total']} votações nominais ({pa['pct']}%)."))
        else:
            out.append(dict(tipo="voto", bom=None, icon="list-checks",
                            txt=f"Participação média em votações nominais: {pa['pct']}%."))

    # 8. concentração de fornecedor
    cf = d.get("concentracao")
    if cf and cf["pct"] >= 50:
        out.append(dict(tipo="gasto", bom=False, icon="alert-triangle",
                        txt=f"Concentra {cf['pct']}% da cota num só fornecedor ({cf['top_nome']})."))

    # 9. produção legislativa
    pr = d.get("producao")
    if pr and pr.get("projetos"):
        tipos = ", ".join(f"{t['n']} {t['tipo']}" for t in pr.get("por_tipo_projeto", [])[:3])
        outras = pr["total"] - pr["projetos"]
        extra = f" e {outras} outras peças" if outras > 0 else ""
        out.append(dict(tipo="producao", bom=None, icon="file-text",
                        txt=f"Apresentou {pr['projetos']} projetos de lei em {d['ano']}" + (f" ({tipos})" if tipos else "") + f"{extra}."))

    # 10. dependência de doador
    fin = d.get("financiamento")
    if fin and fin.get("dependencia") and fin["dependencia"]["pct"] >= 40:
        dep = fin["dependencia"]
        out.append(dict(tipo="eleicao", bom=None, icon="hand-coins",
                        txt=f"Dependeu de um só doador: {dep['doador']} bancou {dep['pct']}% da campanha."))

    # 11. financiamento / força eleitoral
    if fin and fin.get("votos_recebidos"):
        votos_fmt = f"{fin['votos_recebidos']:,}".replace(",", ".")
        cpv = ""
        if fin.get("custo_por_voto"):
            cpv = " · R$ " + f"{fin['custo_por_voto']:.2f}".replace(".", ",") + "/voto"
        out.append(dict(tipo="eleicao", bom=None, icon="vote",
                        txt=f"Força eleitoral: {votos_fmt} votos recebidos em 2022{cpv}."))
    return out


def ui_brl(v):
    from .ui import brl as _brl
    return _brl(v)


def _b(s):
    """Negrito para a narrativa (renderizada com |safe no template)."""
    return f"<strong>{s}</strong>"


def narrativa(d) -> dict:
    """Story telling: abertura ('como está situado') + fechamento, conectando as seções.

    Texto fluido em PT-BR para o eleitor, montado dos números reais (sem inventar).
    Retorna dict(lede=html, fecho=(texto, tom) | None).
    """
    esc = d["escopo"]
    if esc == "deputado":
        return _narr_deputado(d)
    if esc == "partido":
        return _narr_partido(d)
    return _narr_geral(d)


def _narr_deputado(d) -> dict:
    dd = get_deputado(int(d["alvo"])) if d.get("alvo") else None
    nome = (d.get("alvo_nome") or "").split(" ")[0] or "O deputado"
    sigla = (dd or {}).get("sigla_partido", "")
    uf = (dd or {}).get("sigla_uf", "")
    ident = f"{_b(d.get('alvo_nome') or nome)}" + (f" ({sigla}-{uf})" if sigla else "")

    s1 = []
    pres, part = d.get("presenca"), d.get("participacao")
    if pres:
        if pres["pct"] >= 90:
            adj = "é um deputado assíduo"
        elif pres["pct"] >= 75:
            adj = "tem presença regular"
        else:
            adj = "falta com frequência"
        frase = f"{ident} {adj}: esteve em {_b(str(pres['pct']) + '%')} das sessões do plenário"
        if pres.get("delta") is not None:
            frase += f" ({abs(pres['delta'])} pts {'acima' if pres['acima'] else 'abaixo'} da média)"
        s1.append(frase)
        if part and (pres["pct"] - part["pct"]) >= 10:
            s1.append(f"mas registra mais presença do que decisão: votou em só {_b(str(part['pct']) + '%')} das votações nominais")
    elif part:
        s1.append(f"{ident} participou de {_b(str(part['pct']) + '%')} das votações nominais")
    else:
        s1.append(f"{ident}")

    # produção
    s2 = None
    prod, pp = d.get("producao"), d.get("prod_percentil")
    if prod and prod.get("projetos"):
        txt = f"Propôs {_b(str(prod['projetos']) + ' projetos de lei')} em {d['ano']}"
        if pp and pp["total"] > 1:
            if pp["acima_de"] >= 50:
                txt += f", mais que {_b(str(pp['acima_de']) + '%')} dos colegas"
            else:
                txt += f", abaixo da maioria (média da Casa: {pp['media']})"
        s2 = txt

    # gasto (complicação)
    s3 = []
    pc, te = d.get("percentil"), d.get("teto")
    if pc and pc["total"] > 1:
        if pc["acima_de"] >= 80:
            s3.append(f"Nos gastos chama atenção: está entre os {_b(str(100 - pc['acima_de']) + '%')} que mais gastam ({pc['rank']}º da Câmara)")
        elif pc["acima_de"] <= 30:
            s3.append(f"Nos gastos é econômico: gasta menos que {_b(str(100 - pc['acima_de']) + '%')} dos colegas")
        else:
            s3.append(f"Gasta perto da média da Câmara")
    if te and te.get("pct_periodo") is not None:
        s3.append(f"usou {_b(str(te['pct_periodo']) + '%')} da cota disponível")

    # política + financiamento
    s4 = []
    fi, al = d.get("fidelidade"), (d.get("alinhamento") or {})
    if fi:
        if fi["pct"] >= 90:
            s4.append(f"Vota fiel ao {sigla or fi['partido']} ({fi['pct']}%)")
        elif fi["pct"] < 70:
            s4.append(f"Mostra independência: divergiu do {sigla or fi['partido']} {fi['rebelde']}x")
        else:
            s4.append(f"Segue o {sigla or fi['partido']} na maioria das vezes ({fi['pct']}%)")
    g = al.get("governo")
    if g:
        lado = "alinhado à base do governo" if g["pct"] >= 60 else ("perfil de oposição" if g["pct"] <= 40 else "posição intermediária")
        s4.append(f"{lado} ({g['pct']}% com o governo)")

    fin = d.get("financiamento")
    alerta = None
    if fin and fin.get("dependencia") and fin["dependencia"]["pct"] >= 50:
        alerta = (f"Atenção ao financiamento: {_b(str(fin['dependencia']['pct']) + '%')} da campanha de 2022 veio de um único doador ({fin['dependencia']['doador']}).", "flag")

    sentencas = []
    if s1:
        sentencas.append(", ".join(s1) + ".")
    if s2:
        sentencas.append(s2 + ".")
    if s3:
        sentencas.append(", e ".join(s3) + ".")
    if s4:
        sentencas.append("; ".join(s4) + ".")
    lede = " ".join(sentencas)

    return dict(lede=lede, fecho=alerta)


def _narr_partido(d) -> dict:
    nome = d.get("alvo_nome") or d.get("alvo")
    n = d.get("n_deputados")
    parts = []
    abertura = f"A bancada do {_b(nome)} tem {_b(str(n) + ' deputados')}"
    if d.get("pct_camara"):
        abertura += f" ({d['pct_camara']}% da Câmara)"
    parts.append(abertura + ".")

    co, al = d.get("coesao"), (d.get("alinhamento") or {})
    g = al.get("governo")
    s = ""
    if co:
        if co["pct"] >= 90:
            s = f"É das mais disciplinadas: vota unida {_b(str(co['pct']) + '%')} das vezes"
        elif co["pct"] <= 70:
            s = f"É uma bancada dividida ({co['pct']}% de coesão)"
        else:
            s = f"Tem disciplina mediana ({co['pct']}% de coesão)"
    if g:
        lado = "é base do governo" if g["pct"] >= 60 else ("faz oposição" if g["pct"] <= 40 else "fica no centro")
        s += (f" e {lado} ({g['pct']}% com o governo)" if s else f"{lado.capitalize()} ({g['pct']}% com o governo)")
    if s:
        parts.append(s + ".")

    prod = d.get("producao")
    if prod and prod.get("projetos"):
        parts.append(f"Apresentou {_b(str(prod['projetos']) + ' projetos de lei')} em {d['ano']}.")

    te = d.get("teto")
    g_txt = f"Em gastos, usou {_b(str(te['pct_periodo']) + '%')} da cota da bancada" if (te and te.get("pct_periodo") is not None) else ""
    if d.get("media_por_dep"):
        g_txt += (f", média de {ui_brl(d['media_por_dep'])} por deputado" if g_txt else f"Média de {ui_brl(d['media_por_dep'])} por deputado")
    if g_txt:
        parts.append(g_txt + ".")

    fin = d.get("financiamento")
    fecho = None
    if fin and fin.get("dependencia") and fin["dependencia"]["pct"] >= 50:
        fecho = (f"O financiamento é concentrado: {_b(str(fin['dependencia']['pct']) + '%')} do dinheiro de campanha veio de um só doador.", "flag")

    return dict(lede=" ".join(parts), fecho=fecho)


def _narr_geral(d) -> dict:
    parts = [f"Em {d['ano']}, a Câmara gastou {_b(ui_brl(d['gasto']))} de cota"]
    dg = d.get("delta_periodo") if d.get("parcial") else d.get("delta_gasto")
    if dg is not None:
        parts[0] += f" ({'+' if dg > 0 else ''}{dg}% vs {d['prev']})"
    extra = []
    if d.get("presenca"):
        extra.append(f"os deputados estiveram em {_b(str(d['presenca']['pct']) + '%')} das sessões")
    if d.get("participacao"):
        extra.append(f"votaram em {d['participacao']['pct']}% das decisões")
    lede = parts[0] + ". " + ("; ".join(extra).capitalize() + "." if extra else "")
    if d.get("producao") and d["producao"].get("projetos"):
        lede += f" Foram {_b(str(d['producao']['projetos']) + ' projetos de lei')} apresentados. "
    lede += "Escolha um partido ou um deputado para ver o retrato completo."
    return dict(lede=lede, fecho=None)


def leituras(d) -> dict:
    """Frases analíticas curtas, uma por widget: acopladas ao dado, não num bloco solto.

    Cada chave devolve (texto, tom) onde tom ∈ {'good','bad','flag',None}.
    O foco é interpretação comparativa ("so what"), não repetir o número cru.
    """
    L: dict = {}
    esc = d["escopo"]
    ano = d["ano"]
    parcial = d.get("parcial")
    sujeito = {"geral": "A Câmara", "partido": "A bancada",
               "deputado": (d.get("alvo_nome") or "").split(" ")[0] or "O deputado"}[esc]

    # gasto vs mesmo período
    dg = d.get("delta_periodo") if parcial else d.get("delta_gasto")
    if dg is not None:
        ref = f"{d['prev']} (mesmo período)" if parcial else str(d["prev"])
        if dg <= -5:
            L["gasto"] = (f"Gastando menos: {_fmt_pct(dg)} abaixo de {ref}.", "good")
        elif dg >= 5:
            L["gasto"] = (f"Gasto em alta: {_fmt_pct(dg)} acima de {ref}.", "bad")
        else:
            L["gasto"] = (f"Ritmo de gasto estável frente a {ref} ({'+' if dg > 0 else ''}{dg}%).", None)

    # teto da cota
    te = d.get("teto")
    if te and te.get("pct_periodo") is not None:
        p = te["pct_periodo"]
        if p >= 90:
            L["teto"] = (f"Está raspando o teto: usou {p}% do limite proporcional ao período. No ritmo atual, fecha o ano perto do máximo permitido.", "bad")
        elif p <= 45:
            L["teto"] = (f"Folgado no limite: usou só {p}% do teto proporcional. Sobra {ui_brl(te['sobra'])} disponível.", "good")
        else:
            L["teto"] = (f"Usou {p}% do teto proporcional, dentro do esperado para {te['meses']} meses.", None)

    # presença
    pr = d.get("presenca")
    if pr:
        if esc == "geral":
            L["presenca"] = (f"Em média, os deputados estiveram em {pr['pct']}% das sessões de plenário.", None)
        elif pr.get("delta") is not None:
            comp = "acima" if pr["acima"] else "abaixo"
            L["presenca"] = (f"Comparece a {pr['pct']}% das sessões, {abs(pr['delta'])} pts {comp} da média da Câmara.", "good" if pr["acima"] else "bad")

    # presença x participação (contraste: só faz sentido individual/bancada)
    pa = d.get("participacao")
    if pa and pr and esc != "geral":
        gap = round(pr["pct"] - pa["pct"], 1)
        if gap >= 10:
            L["participacao"] = (f"Registra presença ({pr['pct']}%) bem mais do que participa das decisões: votou em só {pa['pct']}% das votações nominais.", "bad")
        elif pa["pct"] >= 85:
            L["participacao"] = (f"Vota na maioria das decisões: participou de {pa['pct']}% das votações nominais.", "good")
        else:
            L["participacao"] = (f"Participou de {pa['pct']}% das votações nominais.", None)
    elif pa and esc == "geral":
        L["participacao"] = (f"Na média, os deputados votam em {pa['pct']}% das votações nominais, bem menos do que comparecem.", None)

    # fidelidade / independência
    fi = d.get("fidelidade")
    if fi:
        if fi["pct"] >= 90:
            L["fidelidade"] = (f"Voto fiel à legenda: seguiu o {fi['partido']} em {fi['pct']}% das orientações, divergindo só {fi['rebelde']}x.", None)
        elif fi["pct"] >= 70:
            L["fidelidade"] = (f"Segue o {fi['partido']} na maioria das vezes ({fi['pct']}%), mas tem voz própria: divergiu {fi['rebelde']}x.", None)
        else:
            L["fidelidade"] = (f"Independente: divergiu da orientação do {fi['partido']} em {fi['rebelde']} de {fi['total']} votações ({100 - fi['pct']:.0f}%).", None)

    # alinhamento (bancada/geral): posição no eixo governo/oposição
    al = d.get("alinhamento") or {}
    g = al.get("governo")
    if g and esc != "deputado":
        if g["pct"] >= 70:
            L["alinhamento"] = (f"Base do governo: acompanhou a orientação governista em {g['pct']}% das votações.", None)
        elif g["pct"] <= 40:
            L["alinhamento"] = (f"Perfil de oposição: votou com o governo em só {g['pct']}% das vezes.", None)
        else:
            L["alinhamento"] = (f"Posição intermediária: votou com o governo em {g['pct']}% das votações.", None)

    # coesão (bancada)
    co = d.get("coesao")
    if co:
        if co["pct"] >= 90:
            L["coesao"] = (f"Bancada muito disciplinada: vota unida {co['pct']}% das vezes, o líder controla os votos.", None)
        elif co["pct"] <= 70:
            L["coesao"] = (f"Bancada dividida: a unidade média é de só {co['pct']}%, vota rachada com frequência.", None)
        else:
            L["coesao"] = (f"Disciplina mediana: {co['pct']}% de unidade nas votações.", None)

    # produção legislativa
    prod = d.get("producao")
    pp = d.get("prod_percentil")
    if prod and prod.get("projetos"):
        if pp and esc == "deputado" and pp["total"] > 1:
            comp = "mais" if pp["acima_de"] >= 50 else "menos"
            L["producao"] = (f"Apresentou {prod['projetos']} projetos de lei, {comp} que {pp['acima_de'] if pp['acima_de']>=50 else 100-pp['acima_de']}% dos deputados (média da Casa: {pp['media']}).", None)
        else:
            L["producao"] = (f"{prod['projetos']} projetos de lei propostos; as outras {prod['total'] - prod['projetos']} peças são requerimentos, pareceres e emendas (rotina parlamentar).", None)

    # concentração de fornecedor
    cf = d.get("concentracao")
    if cf and esc == "deputado":
        if cf["pct"] >= 50:
            L["concentracao"] = (f"Concentração alta: {cf['pct']}% da cota foi para um único fornecedor ({cf['top_nome'][:40]}). Vale investigar.", "flag")
        elif cf["pct"] >= 30:
            L["concentracao"] = (f"O maior fornecedor responde por {cf['pct']}% da cota, entre {cf['n_fornecedores']} fornecedores.", None)
        else:
            L["concentracao"] = (f"Gasto pulverizado: o maior fornecedor é só {cf['pct']}% do total ({cf['n_fornecedores']} fornecedores).", "good")

    # financiamento
    fin = d.get("financiamento")
    if fin:
        partes = []
        if fin.get("custo_por_voto"):
            partes.append(f"cada voto custou R$ {('%.2f' % fin['custo_por_voto']).replace('.', ',')}")
        dep = fin.get("dependencia")
        if dep and dep["pct"] >= 50:
            partes.append(f"e {dep['pct']}% do dinheiro veio de um só doador ({dep['doador']})")
        if partes:
            tom = "flag" if (dep and dep["pct"] >= 60) else None
            L["financiamento"] = ("Na campanha de 2022, " + ", ".join(partes) + ".", tom)

    # tendência (série): direção do gasto
    serie = d.get("serie") or []
    gastos = [(s["ano"], s["gasto"]) for s in serie if s.get("gasto")]
    if len(gastos) >= 3:
        prim, ult = gastos[0], gastos[-1]
        pico = max(gastos, key=lambda x: x[1])
        if pico[0] not in (prim[0], ult[0]):
            L["serie"] = (f"O gasto cresceu até {pico[0]} ({ui_brl(pico[1])}) e depois recuou.", None)
        elif ult[1] > prim[1] * 1.15:
            L["serie"] = (f"Tendência de alta: o gasto subiu de {ui_brl(prim[1])} em {prim[0]} para o patamar atual.", None)
        elif ult[1] < prim[1] * 0.85:
            L["serie"] = (f"Tendência de queda no gasto desde {prim[0]}.", None)

    # ranking entre partidos (geral)
    rk = d.get("ranking_partidos")
    if rk:
        com_co = [p for p in rk if p.get("coesao") is not None]
        gov = [p for p in rk if p.get("governo") is not None and p["governo"] >= 50]
        if com_co:
            mais = max(com_co, key=lambda x: x["coesao"])
            menos = min(com_co, key=lambda x: x["coesao"])
            L["ranking"] = (
                f"{mais['partido']} é a bancada mais disciplinada ({mais['coesao']}% de coesão) e "
                f"{menos['partido']} a mais dividida ({menos['coesao']}%). "
                f"{len(gov)} das {len(rk)} bancadas votam majoritariamente com o governo.", None)

    return L


def raiox_data(escopo: str = "geral", alvo: str | None = None, ano: int | None = None) -> dict:
    import datetime as _dt
    from .ui import meses_decorridos_ano, dias_uteis_ano

    ano = ano or ano_corrente()
    prev = ano - 1
    hoje = _dt.date.today()
    parcial = (ano == hoje.year)
    ate_mes = hoje.month if parcial else 12

    def _gasto(a, ate=None):
        frm, conds = _scope_despesas(escopo, alvo, a, ate_mes=ate)
        return _scalar(select(func.coalesce(func.sum(despesas.c.valor_liquido), 0)).select_from(frm).where(*conds))

    gasto, gasto_prev = _gasto(ano), _gasto(prev)
    delta_gasto = round((gasto - gasto_prev) / gasto_prev * 100, 1) if gasto_prev else None

    # comparação JUSTA: mesmo período (até o mês atual) ano vs ano anterior
    gasto_periodo = _gasto(ano, ate=ate_mes if parcial else None)
    gasto_prev_periodo = _gasto(prev, ate=ate_mes if parcial else None)
    delta_periodo = round((gasto_periodo - gasto_prev_periodo) / gasto_prev_periodo * 100, 1) if gasto_prev_periodo else None

    # projeção do ano no ritmo atual
    meses = meses_decorridos_ano(ano)
    projecao = round(gasto / meses * 12) if (parcial and meses) else None

    frm, conds = _scope_despesas(escopo, alvo, ano)
    qtd = _scalar(select(func.count()).select_from(frm).where(*conds))
    categorias = _rows(
        select(despesas.c.tipo_despesa.label("categoria"), func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("total"))
        .select_from(frm).where(*conds).group_by(despesas.c.tipo_despesa).order_by(desc("total")).limit(8))
    fornecedores = _rows(
        select(despesas.c.fornecedor_nome.label("fornecedor"), func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("total"),
               func.count().label("qtd"))
        .select_from(frm).where(*conds, despesas.c.fornecedor_nome.isnot(None))
        .group_by(despesas.c.fornecedor_nome).order_by(desc("total")).limit(8))

    # votos no escopo
    def _votos(a):
        j, vc = _scope_votos(escopo, alvo, a)
        sim = _scalar(select(func.count()).select_from(j).where(*vc, votos.c.voto.in_(_SIM)))
        nao = _scalar(select(func.count()).select_from(j).where(*vc, votos.c.voto.in_(_NAO)))
        tot = _scalar(select(func.count()).select_from(j).where(*vc))
        return dict(sim=sim, nao=nao, outros=max(tot - sim - nao, 0), total=tot)

    votos_ano = _votos(ano)

    # contexto: nº de deputados
    n_dep = None
    if escopo == "partido":
        n_dep = _scalar(select(func.count()).where(deputados.c.sigla_partido == alvo))
    elif escopo == "geral":
        n_dep = _scalar(select(func.count()).select_from(deputados))

    # custo médio por deputado e por dia útil
    media_por_dep = (gasto / n_dep) if (n_dep and escopo != "deputado") else None
    du = dias_uteis_ano(ano)
    custo_dia_util = round(gasto / du) if du else None

    alvo_nome = alvo
    if escopo == "deputado":
        dd = get_deputado(int(alvo)) if alvo else None
        alvo_nome = dd["nome"] if dd else alvo

    # módulos novos
    presenca_d = presenca_escopo(escopo, alvo, ano, ate_mes=ate_mes if parcial else None)
    dias_trab = dias_trabalhados_escopo(escopo, alvo, ano, ate_mes=ate_mes if parcial else None)
    alinhamento = alinhamento_escopo(escopo, alvo, ano)
    coesao = coesao_partido(alvo, ano) if escopo == "partido" else None
    financiamento = financiamento_escopo(escopo, alvo)

    # módulos exclusivos de cada narrativa
    fidelidade = fidelidade_partidaria(int(alvo), ano) if escopo == "deputado" and alvo else None
    percentil = gasto_percentil(int(alvo), ano) if escopo == "deputado" and alvo else None
    ranking_interno = partido_ranking_interno(alvo, ano) if escopo == "partido" else None
    bancada = partido_deputados(alvo, ano) if escopo == "partido" else None
    pct_camara = round(100.0 * n_dep / 513, 1) if (escopo == "partido" and n_dep) else None

    # análises adicionais (todas escopo-aware)
    teto = teto_ceap_escopo(escopo, alvo, ano, gasto, parcial, ate_mes)
    participacao = participacao_votacoes(escopo, alvo, ano)
    concentracao = concentracao_fornecedor(escopo, alvo, ano)
    benchmark = benchmark_deputado(int(alvo), ano, gasto) if escopo == "deputado" and alvo else None
    serie = serie_historica(escopo, alvo, ano)
    rk_partidos = ranking_partidos(ano) if escopo == "geral" else None
    producao = producao_legislativa(escopo, alvo, ano)
    prod_percentil = producao_percentil(int(alvo), ano) if escopo == "deputado" and alvo else None
    props_recentes = proposicoes_recentes(escopo, alvo, ano)
    selo = selo_transparencia(presenca_d, participacao, teto, fidelidade) if escopo != "geral" else None

    # comparação plurianual (anos do mandato, mesmo período p/ ser justa)
    cut = ate_mes if parcial else 12
    anos_mand = anos_mandato(ano)
    gasto_multiano = gasto_mensal_multiano(escopo, alvo, anos_mand, cut)
    categorias_cmp = categorias_multiano(escopo, alvo, anos_mand, cut)
    fornecedores_cmp = fornecedores_multiano(escopo, alvo, anos_mand, cut)
    ranking_multi = ranking_gastos_multiano(anos_mand, cut) if escopo == "geral" else None

    d = dict(
        escopo=escopo, alvo=alvo, alvo_nome=alvo_nome, ano=ano, prev=prev,
        parcial=parcial, ate_mes=ate_mes,
        gasto=gasto, gasto_prev=gasto_prev, delta_gasto=delta_gasto, qtd=qtd,
        gasto_periodo=gasto_periodo, gasto_prev_periodo=gasto_prev_periodo, delta_periodo=delta_periodo,
        projecao=projecao, media_por_dep=media_por_dep, custo_dia_util=custo_dia_util, dias_uteis=du,
        categorias=categorias, fornecedores=fornecedores, votos=votos_ano,
        n_deputados=n_dep, mensal=_scope_mensal(escopo, alvo, ano),
        presenca=presenca_d, dias_trabalhados=dias_trab,
        alinhamento=alinhamento, coesao=coesao, financiamento=financiamento,
        fidelidade=fidelidade, percentil=percentil,
        ranking_interno=ranking_interno, bancada=bancada, pct_camara=pct_camara,
        teto=teto, participacao=participacao, concentracao=concentracao,
        benchmark=benchmark, serie=serie, ranking_partidos=rk_partidos,
        producao=producao, prod_percentil=prod_percentil,
        props_recentes=props_recentes, selo=selo,
        anos_mandato=anos_mand, cut=cut, gasto_multiano=gasto_multiano,
        categorias_cmp=categorias_cmp, fornecedores_cmp=fornecedores_cmp,
        ranking_multi=ranking_multi,
        ultimas=feed_items(6),
    )
    d["insights"] = gerar_insights(d)
    d["leitura"] = leituras(d)
    d["narrativa"] = narrativa(d)
    return d


def _scope_mensal(escopo, alvo, ano):
    frm, conds = _scope_despesas(escopo, alvo, ano)
    rows = _rows(select(despesas.c.mes, func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("t"))
                 .select_from(frm).where(*conds).group_by(despesas.c.mes))
    by = {int(r["mes"]): float(r["t"]) for r in rows if r["mes"]}
    return [round(by.get(m, 0.0)) for m in range(1, 13)]


# ---------------------------------------- COMPARAÇÃO PLURIANUAL (mandato)
def anos_mandato(ano):
    """Anos da legislatura (mandato) que contém `ano`, até o ano selecionado.

    Legislaturas começam em 2003, 2007, 2011, 2015, 2019, 2023…
    """
    start = 2003 + 4 * ((ano - 2003) // 4)
    return list(range(start, ano + 1))


def gasto_mensal_multiano(escopo, alvo, anos, cut):
    """Gasto por mês (1..cut) para cada ano do mandato: base do gráfico de barras."""
    out = {}
    for a in anos:
        frm, conds = _scope_despesas(escopo, alvo, a, ate_mes=cut)
        rows = _rows(select(despesas.c.mes, func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("t"))
                     .select_from(frm).where(*conds).group_by(despesas.c.mes))
        by = {int(r["mes"]): float(r["t"]) for r in rows if r["mes"]}
        out[a] = [round(by.get(m, 0.0)) for m in range(1, cut + 1)]
    return out


def categorias_multiano(escopo, alvo, anos, cut, limit=8):
    """Top categorias do ano atual com o valor em cada ano do mandato (mesmo período)."""
    ano_atual = anos[-1]
    frm, conds = _scope_despesas(escopo, alvo, ano_atual, ate_mes=cut)
    top = _rows(select(despesas.c.tipo_despesa.label("c"), func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("t"))
                .select_from(frm).where(*conds).group_by(despesas.c.tipo_despesa).order_by(desc("t")).limit(limit))
    cats = [r["c"] for r in top]
    if not cats:
        return []
    vals = {c: {} for c in cats}
    for a in anos:
        frm, conds = _scope_despesas(escopo, alvo, a, ate_mes=cut)
        rows = _rows(select(despesas.c.tipo_despesa.label("c"), func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("t"))
                     .select_from(frm).where(*conds, despesas.c.tipo_despesa.in_(cats)).group_by(despesas.c.tipo_despesa))
        for r in rows:
            vals[r["c"]][a] = float(r["t"] or 0)
    return [dict(categoria=c, por_ano={a: vals[c].get(a, 0.0) for a in anos}, atual=vals[c].get(ano_atual, 0.0)) for c in cats]


def fornecedores_multiano(escopo, alvo, anos, cut, limit=8):
    """Maiores fornecedores do ano atual com o total em cada ano do mandato."""
    ano_atual = anos[-1]
    frm, conds = _scope_despesas(escopo, alvo, ano_atual, ate_mes=cut)
    top = _rows(select(despesas.c.fornecedor_nome.label("f"), func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("t"),
                       func.count().label("qtd"))
                .select_from(frm).where(*conds, despesas.c.fornecedor_nome.isnot(None))
                .group_by(despesas.c.fornecedor_nome).order_by(desc("t")).limit(limit))
    fns = [r["f"] for r in top]
    if not fns:
        return []
    vals = {f: {} for f in fns}
    for a in anos:
        frm, conds = _scope_despesas(escopo, alvo, a, ate_mes=cut)
        rows = _rows(select(despesas.c.fornecedor_nome.label("f"), func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("t"))
                     .select_from(frm).where(*conds, despesas.c.fornecedor_nome.in_(fns)).group_by(despesas.c.fornecedor_nome))
        for r in rows:
            vals[r["f"]][a] = float(r["t"] or 0)
    by_qtd = {r["f"]: r["qtd"] for r in top}
    return [dict(fornecedor=f, qtd=by_qtd.get(f, 0), por_ano={a: vals[f].get(a, 0.0) for a in anos},
                 atual=vals[f].get(ano_atual, 0.0)) for f in fns]


def ranking_gastos_multiano(anos, cut, limit=15):
    """Top deputados por gasto do ano atual, com o gasto em cada ano do mandato."""
    ano_atual = anos[-1]
    top = _rows(select(despesas.c.deputado_id, func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("t"))
                .where(despesas.c.ano == ano_atual, despesas.c.mes <= cut)
                .group_by(despesas.c.deputado_id).order_by(desc("t")).limit(limit))
    ids = [r["deputado_id"] for r in top]
    if not ids:
        return []
    info = {r["id"]: r for r in _rows(select(deputados.c.id, deputados.c.nome, deputados.c.sigla_partido, deputados.c.sigla_uf)
                                      .where(deputados.c.id.in_(ids)))}
    vals = {i: {} for i in ids}
    for a in anos:
        rows = _rows(select(despesas.c.deputado_id, func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("t"))
                     .where(despesas.c.deputado_id.in_(ids), despesas.c.ano == a, despesas.c.mes <= cut)
                     .group_by(despesas.c.deputado_id))
        for r in rows:
            vals[r["deputado_id"]][a] = float(r["t"] or 0)
    out = []
    for r in top:
        i = r["deputado_id"]
        nf = info.get(i, {})
        out.append(dict(id=i, nome=nf.get("nome", "—"), sigla_partido=nf.get("sigla_partido", ""),
                        sigla_uf=nf.get("sigla_uf", ""), atual=float(r["t"] or 0),
                        por_ano={a: vals[i].get(a, 0.0) for a in anos}))
    return out


def relatorio_kpis(ano: int, mes: int | None = None) -> dict:
    cond = _desp_cond(ano, mes)
    total = _scalar(select(func.coalesce(func.sum(despesas.c.valor_liquido), 0)).where(*cond))
    qtd = _scalar(select(func.count()).where(*cond))
    n_dep = _scalar(select(func.count(func.distinct(despesas.c.deputado_id))).where(*cond))
    return dict(total=total, qtd=qtd, media=_media(total, qtd), n_deputados=n_dep, ano=ano)


def gasto_mensal_global(ano: int) -> list[float]:
    rows = _rows(
        select(despesas.c.mes, func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("t"))
        .where(despesas.c.ano == ano).group_by(despesas.c.mes)
    )
    by = {int(r["mes"]): float(r["t"]) for r in rows if r["mes"]}
    return [round(by.get(m, 0.0)) for m in range(1, 13)]


def categorias_agg(ano: int, mes: int | None = None, limit: int = 30) -> list[dict]:
    rows = _rows(
        select(
            despesas.c.tipo_despesa.label("categoria"),
            func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("total"),
            func.count().label("qtd"),
        )
        .where(*_desp_cond(ano, mes))
        .group_by(despesas.c.tipo_despesa)
        .order_by(desc("total"))
        .limit(limit)
    )
    for r in rows:
        r["media"] = _media(r["total"], r["qtd"])
    return rows


def categoria_kpis(cat: str, ano: int) -> dict:
    total = _scalar(select(func.coalesce(func.sum(despesas.c.valor_liquido), 0)).where(
        despesas.c.ano == ano, despesas.c.tipo_despesa == cat))
    qtd = _scalar(select(func.count()).where(despesas.c.ano == ano, despesas.c.tipo_despesa == cat))
    n_dep = _scalar(select(func.count(func.distinct(despesas.c.deputado_id))).where(
        despesas.c.ano == ano, despesas.c.tipo_despesa == cat))
    return dict(total=total, qtd=qtd, media=_media(total, qtd), n_deputados=n_dep, categoria=cat, ano=ano)


def categoria_mensal(cat: str, ano: int) -> list[float]:
    rows = _rows(
        select(despesas.c.mes, func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("t"))
        .where(despesas.c.ano == ano, despesas.c.tipo_despesa == cat).group_by(despesas.c.mes)
    )
    by = {int(r["mes"]): float(r["t"]) for r in rows if r["mes"]}
    return [round(by.get(m, 0.0)) for m in range(1, 13)]


def categoria_fornecedores(cat: str, ano: int, limit: int = 15) -> list[dict]:
    rows = _rows(
        select(
            despesas.c.fornecedor_nome.label("fornecedor"),
            despesas.c.fornecedor_cnpj_cpf.label("documento"),
            func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("total"),
            func.count().label("qtd"),
        )
        .where(despesas.c.ano == ano, despesas.c.tipo_despesa == cat, despesas.c.fornecedor_nome.isnot(None))
        .group_by(despesas.c.fornecedor_nome, despesas.c.fornecedor_cnpj_cpf)
        .order_by(desc("total")).limit(limit)
    )
    for r in rows:
        r["media"] = _media(r["total"], r["qtd"])
    return rows


def categoria_notas(cat: str, ano: int, limit: int = 40) -> list[dict]:
    return _rows(
        select(
            despesas.c.data_documento, despesas.c.fornecedor_nome, despesas.c.valor_liquido,
            despesas.c.url_documento, deputados.c.nome.label("deputado"), despesas.c.deputado_id,
        )
        .select_from(despesas.outerjoin(deputados, deputados.c.id == despesas.c.deputado_id))
        .where(despesas.c.ano == ano, despesas.c.tipo_despesa == cat)
        .order_by(desc(despesas.c.valor_liquido)).limit(limit)
    )


def maiores_notas(ano: int, limit: int = 10, cat: str | None = None, mes: int | None = None) -> list[dict]:
    """Maiores notas (custos) individuais do período."""
    stmt = (
        select(
            despesas.c.data_documento, despesas.c.fornecedor_nome, despesas.c.tipo_despesa,
            despesas.c.valor_liquido, despesas.c.url_documento,
            deputados.c.nome.label("deputado"), despesas.c.deputado_id,
        )
        .select_from(despesas.outerjoin(deputados, deputados.c.id == despesas.c.deputado_id))
        .where(*_desp_cond(ano, mes, cat))
    )
    return _rows(stmt.order_by(desc(despesas.c.valor_liquido)).limit(limit))


def ultimos_meses(ano: int, n: int = 3) -> list[dict]:
    """Totais dos últimos n meses com gasto no ano (para o padrão 'últimos 3 meses')."""
    meses = gasto_mensal_global(ano)
    nomes = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    com_dado = [(i, v) for i, v in enumerate(meses) if v > 0]
    return [{"mes": nomes[i], "total": v} for i, v in com_dado[-n:]]


def variacao_preco_categoria(cat: str, ano: int, limit: int = 12) -> list[dict]:
    """Mesmo fornecedor na mesma categoria com preços (médias) diferentes: revela disparidade.

    Mostra fornecedores com várias notas e a diferença entre a maior e a menor.
    """
    rows = _rows(
        select(
            despesas.c.fornecedor_nome.label("fornecedor"),
            func.count().label("qtd"),
            func.min(despesas.c.valor_liquido).label("min"),
            func.max(despesas.c.valor_liquido).label("max"),
            func.coalesce(func.sum(despesas.c.valor_liquido), 0).label("total"),
        )
        .where(despesas.c.ano == ano, despesas.c.tipo_despesa == cat, despesas.c.fornecedor_nome.isnot(None))
        .group_by(despesas.c.fornecedor_nome)
        .having(func.count() >= 3)
        .order_by(desc(func.max(despesas.c.valor_liquido) - func.min(despesas.c.valor_liquido)))
        .limit(limit)
    )
    for r in rows:
        r["amplitude"] = (r["max"] or 0) - (r["min"] or 0)
    return rows


def votacao_partidos(vid: str, limit: int = 12) -> list[dict]:
    """Recorte por partido: quantos votaram Sim e Não."""
    sim, nao = _sim_nao_cols()
    return _rows(
        select(deputados.c.sigla_partido.label("party"), sim, nao)
        .select_from(votos.join(deputados, votos.c.deputado_id == deputados.c.id))
        .where(votos.c.votacao_id == vid)
        .group_by(deputados.c.sigla_partido)
        .order_by(desc(sim + nao))
        .limit(limit)
    )


# ===================================================================
#  Série multi-ano do deputado (comparação 2022→atual)
# ===================================================================
def deputado_serie_anual(dep_id: int) -> list[dict]:
    """Atuação e gasto do deputado ano a ano, para comparar a evolução do mandato."""
    from sqlalchemy import extract

    anos = sorted(anos_despesa())
    base = votos.join(votacoes, votos.c.votacao_id == votacoes.c.id)
    out = []
    for a in anos:
        gasto = _scalar(select(func.coalesce(func.sum(despesas.c.valor_liquido), 0)).where(
            despesas.c.deputado_id == dep_id, despesas.c.ano == a))
        ycond = extract("year", votacoes.c.data) == a
        sim = _scalar(select(func.count()).select_from(base).where(votos.c.deputado_id == dep_id, ycond, votos.c.voto.in_(_SIM)))
        nao = _scalar(select(func.count()).select_from(base).where(votos.c.deputado_id == dep_id, ycond, votos.c.voto.in_(_NAO)))
        part = _scalar(select(func.count(func.distinct(votos.c.votacao_id))).select_from(base).where(
            votos.c.deputado_id == dep_id, ycond))
        out.append(dict(ano=a, gasto=gasto, participou=part, sim=sim, nao=nao))
    return out


# ===================================================================
#  Frequência oficial em plenário, com motivo de falta (presenca_dia)
# ===================================================================
def faltas_deputado(dep_id: int, ano: int | None = None) -> dict | None:
    """Dias de sessão do deputado: presenças, faltas justificadas (com % de cada
    motivo declarado) e faltas sem justificativa. Fonte: registro oficial diário."""
    from .db import presenca_dia as pd

    cond = [pd.c.deputado_id == dep_id]
    if ano:
        cond.append(pd.c.ano == ano)
    rows = _rows(select(pd.c.frequencia, pd.c.justificativa).where(*cond))
    if not rows:
        return None
    total = len(rows)
    pres = sum(1 for r in rows if r["frequencia"] == "presenca")
    just = sum(1 for r in rows if r["frequencia"] == "ausencia_justificada")
    nao_just = total - pres - just
    motivos: dict[str, int] = {}
    for r in rows:
        if r["frequencia"] == "ausencia_justificada":
            m = r["justificativa"] or "Justificativa não detalhada"
            motivos[m] = motivos.get(m, 0) + 1
    if nao_just:
        motivos["Sem justificativa registrada"] = nao_just
    aus_total = just + nao_just
    lista = sorted(motivos.items(), key=lambda kv: -kv[1])
    return dict(
        ano=ano, dias=total, presencas=pres,
        justificadas=just, nao_justificadas=nao_just,
        pct_presenca=round(100 * pres / total, 1),
        motivos=[dict(motivo=m, dias=q, pct=round(100 * q / aus_total, 1)) for m, q in lista] if aus_total else [],
    )


def rank_faltas_sem_justificativa(ano: int, limit: int = 15) -> list[dict]:
    """Deputados com mais faltas SEM justificativa registrada no ano (registro oficial),
    com o total de dias, as justificadas e o motivo mais comum das justificadas."""
    from .db import presenca_dia as pd

    nj = func.sum(case((pd.c.frequencia == "ausencia", 1), else_=0)).label("nao_just")
    jt = func.sum(case((pd.c.frequencia == "ausencia_justificada", 1), else_=0)).label("just")
    tot = func.count().label("dias")
    q = (
        select(pd.c.deputado_id, nj, jt, tot,
               deputados.c.nome_eleitoral, deputados.c.sigla_partido, deputados.c.sigla_uf, deputados.c.url_foto)
        .join(deputados, deputados.c.id == pd.c.deputado_id)
        .where(pd.c.ano == ano)
        .group_by(pd.c.deputado_id, deputados.c.nome_eleitoral, deputados.c.sigla_partido,
                  deputados.c.sigla_uf, deputados.c.url_foto)
        .having(nj > 0)
        .order_by(desc("nao_just"), desc("just"))
        .limit(limit)
    )
    out = []
    for r in _rows(q):
        # motivo mais comum das justificadas desse deputado (contexto, não acusação)
        top = _rows(
            select(pd.c.justificativa, func.count().label("q"))
            .where(pd.c.deputado_id == r["deputado_id"], pd.c.ano == ano,
                   pd.c.frequencia == "ausencia_justificada", pd.c.justificativa.isnot(None))
            .group_by(pd.c.justificativa).order_by(desc("q")).limit(1)
        )
        out.append(dict(
            deputado_id=r["deputado_id"], nome=r["nome_eleitoral"],
            partido=r["sigla_partido"], uf=r["sigla_uf"], foto=r["url_foto"],
            dias=r["dias"], nao_justificadas=r["nao_just"], justificadas=r["just"],
            pct_falta_nj=round(100 * r["nao_just"] / r["dias"], 1) if r["dias"] else 0,
            motivo_top=top[0]["justificativa"] if top else None,
        ))
    return out


def motivos_faltas_globais(ano: int) -> dict | None:
    """Panorama da Câmara no ano: % de presença e a distribuição dos motivos de
    todas as ausências (incluindo as sem justificativa registrada)."""
    from .db import presenca_dia as pd

    total = _scalar(select(func.count()).where(pd.c.ano == ano))
    if not total:
        return None
    pres = _scalar(select(func.count()).where(pd.c.ano == ano, pd.c.frequencia == "presenca"))
    nao_just = _scalar(select(func.count()).where(pd.c.ano == ano, pd.c.frequencia == "ausencia"))
    rows = _rows(
        select(pd.c.justificativa, func.count().label("q"))
        .where(pd.c.ano == ano, pd.c.frequencia == "ausencia_justificada")
        .group_by(pd.c.justificativa).order_by(desc("q"))
    )
    motivos = [dict(motivo=r["justificativa"] or "Justificativa não detalhada", dias=r["q"]) for r in rows]
    if nao_just:
        motivos.append(dict(motivo="Sem justificativa registrada", dias=nao_just))
    motivos.sort(key=lambda m: -m["dias"])
    aus_total = total - pres
    for m in motivos:
        m["pct"] = round(100 * m["dias"] / aus_total, 1) if aus_total else 0
    return dict(ano=ano, registros=total, pct_presenca=round(100 * pres / total, 1),
                ausencias=aus_total, motivos=motivos)
