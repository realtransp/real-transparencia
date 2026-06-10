"""Ingestão dos dados da Câmara dos Deputados.

Dois caminhos:
- API REST (rápido, p/ preview e atualização incremental)
- Arquivos em massa CSV/ZIP (p/ backfill histórico 2008+)
"""
from __future__ import annotations

from . import sources as S
from ..db import (
    bulk_insert,
    deputados,
    despesas,
    merge_by_pk,
    orientacoes,
    presenca,
    presenca_dia,
    proposicao_autores,
    proposicoes,
    replace_table,
    replace_where_atomic,
    votacoes,
    votos,
)


def _pick(row: dict, *keys, default=None):
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
    return default


# ----------------------------------------------------------------- DEPUTADOS
def load_deputados(legislatura: int | None = None, enrich_cpf: bool = False) -> int:
    """Carrega a lista de deputados via API v2 (legislatura atual por padrão)."""
    params = {"ordem": "ASC", "ordenarPor": "nome"}
    if legislatura:
        params["idLegislatura"] = legislatura
    rows = []
    for d in S.api_paginate("/deputados", params):
        rows.append(
            dict(
                id=d["id"],
                cpf=None,
                nome=d.get("nome"),
                nome_eleitoral=d.get("nome"),
                sigla_partido=d.get("siglaPartido"),
                sigla_uf=d.get("siglaUf"),
                url_foto=d.get("urlFoto"),
                situacao="Em exercício",
                email=d.get("email"),
            )
        )
    n = replace_table(deputados, rows)
    if enrich_cpf:
        _enrich_cpf([r["id"] for r in rows])
    return n


def upsert_deputados(legislatura: int | None = None) -> int:
    """Atualiza o roster (uso diário) SEM destruir os dados enriquecidos.

    Diferente de `load_deputados`, não regrava a tabela: faz upsert por id e só
    toca em nome/partido/UF/foto/situação/e-mail. Preserva `cpf`, `telefone` e
    `nome_eleitoral` (obtidos por `_enrich_cpf` no backfill) — sem eles o
    cruzamento com o TSE quebraria a cada rodada do cron.
    """
    params = {"ordem": "ASC", "ordenarPor": "nome"}
    if legislatura:
        params["idLegislatura"] = legislatura
    rows = []
    for d in S.api_paginate("/deputados", params):
        rows.append(
            dict(
                id=d["id"],
                nome=d.get("nome"),
                nome_eleitoral=d.get("nome"),  # só usado se o deputado for NOVO (insert)
                sigla_partido=d.get("siglaPartido"),
                sigla_uf=d.get("siglaUf"),
                url_foto=d.get("urlFoto"),
                situacao="Em exercício",
                email=d.get("email"),
            )
        )
    # update_cols exclui cpf/telefone/nome_eleitoral: atualizados não são tocados.
    return merge_by_pk(
        deputados, rows,
        update_cols={"nome", "sigla_partido", "sigla_uf", "url_foto", "situacao", "email"},
    )


def _enrich_cpf(ids: list[int]) -> None:
    """Busca CPF, nome eleitoral, e-mail e telefone do gabinete no detalhe de cada deputado."""
    from ..db import engine

    for dep_id in ids:
        try:
            det = S.api_get(f"/deputados/{dep_id}").get("dados", {})
        except Exception:
            continue
        cpf = S.only_digits(det.get("cpf"))
        us = det.get("ultimoStatus") or {}
        gab = us.get("gabinete") or {}
        nome_el = us.get("nomeEleitoral")
        email = gab.get("email") or us.get("email")
        telefone = gab.get("telefone")  # ex.: "3215-5704" (Brasília, DDD 61)
        with engine.begin() as conn:
            conn.execute(
                deputados.update()
                .where(deputados.c.id == dep_id)
                .values(
                    cpf=cpf or None,
                    nome_eleitoral=nome_el or det.get("nomeCivil"),
                    email=email,
                    telefone=telefone,
                )
            )


# ------------------------------------------------------------------ DESPESAS
def load_despesas_api(deputado_ids: list[int], anos: list[int]) -> int:
    """Despesas via API — usado no preview (subconjunto de deputados)."""
    total = 0
    for dep_id in deputado_ids:
        rows = []
        for ano in anos:
            for e in S.api_paginate(f"/deputados/{dep_id}/despesas", {"ano": ano, "ordem": "DESC", "ordenarPor": "dataDocumento"}):
                rows.append(_despesa_row_api(dep_id, e))
        total += bulk_insert(despesas, rows)
    return total


def _despesa_row_api(dep_id: int, e: dict) -> dict:
    return dict(
        deputado_id=dep_id,
        ano=int(e.get("ano") or 0),
        mes=int(e.get("mes") or 0),
        tipo_despesa=e.get("tipoDespesa"),
        fornecedor_nome=e.get("nomeFornecedor"),
        fornecedor_cnpj_cpf=S.only_digits(e.get("cnpjCpfFornecedor")),
        valor_liquido=S.parse_float(e.get("valorLiquido")),
        data_documento=S.parse_date(e.get("dataDocumento")),
        url_documento=e.get("urlDocumento"),
    )


def _despesas_rows(ano: int):
    """Itera as linhas de despesa do arquivo do ano como dicts (streaming)."""
    url = f"{S.CEAP_BASE}/Ano-{ano}.csv.zip"
    for r in S.download_csv_rows(url):
        dep_id = _to_int(_pick(r, "ideCadastro", "nuDeputadoId", "idDeputado"))
        yield dict(
            deputado_id=dep_id,
            ano=_to_int(_pick(r, "numAno", "ano")) or ano,
            mes=_to_int(_pick(r, "numMes", "mes")) or 0,
            tipo_despesa=_pick(r, "txtDescricao", "descricao"),
            fornecedor_nome=_pick(r, "txtFornecedor", "fornecedor"),
            fornecedor_cnpj_cpf=S.only_digits(_pick(r, "txtCNPJCPF", "cnpjCpf")),
            valor_liquido=S.parse_float(_pick(r, "vlrLiquido", "valorLiquido")),
            data_documento=S.parse_date(_pick(r, "datEmissao", "dataDocumento")),
            url_documento=_pick(r, "urlDocumento"),
        )


def load_despesas_bulk(ano: int) -> int:
    """Despesas (CEAP) do ano inteiro a partir do arquivo oficial.

    Atômico: o delete do ano e os inserts acontecem numa única transação, então
    um 404 (arquivo do ano ainda não publicado) ou um download truncado não
    deixa o ano sem dados — os antigos permanecem.
    """
    return replace_where_atomic(despesas, {"ano": ano}, _despesas_rows(ano), chunk=5000)


# ------------------------------------------------------------------ VOTAÇÕES
def load_votacoes_api(limite_paginas: int = 1, com_votos: bool = True) -> int:
    """Votações recentes via API + votos e orientações (preview)."""
    vrows, voto_rows, ori_rows = [], [], []
    for v in S.api_paginate("/votacoes", {"ordem": "DESC", "ordenarPor": "dataHoraRegistro"}, max_pages=limite_paginas):
        vid = v["id"]
        vrows.append(
            dict(
                id=vid,
                data=S.parse_date(v.get("data")),
                sigla_orgao=v.get("siglaOrgao"),
                descricao=v.get("descricao"),
                proposicao=v.get("proposicaoObjeto"),
                aprovacao=v.get("aprovacao"),
            )
        )
        if com_votos:
            voto_rows += _votos_api(vid)
            ori_rows += _orientacoes_api(vid)
    replace_table(votacoes, vrows)
    replace_table(votos, voto_rows)
    replace_table(orientacoes, ori_rows)
    return len(vrows)


def load_votacoes_recentes(limite_paginas: int = 2) -> int:
    """Atualização diária das votações: incremental e não-destrutiva.

    Diferente de `load_votacoes_api` (que usa replace_table e zeraria todo o
    histórico), faz UPSERT só das votações recentes por id e regrava votos/
    orientações APENAS dessas votações. Preserva o backfill e os campos
    enriquecidos (objeto/ementa/titulo_ia) das votações que já existiam.
    """
    vrows, voto_rows, ori_rows = [], [], []
    for v in S.api_paginate("/votacoes", {"ordem": "DESC", "ordenarPor": "dataHoraRegistro"}, max_pages=limite_paginas):
        vid = v["id"]
        vs = _votos_api(vid)
        ori = _orientacoes_api(vid)
        sim = sum(1 for x in vs if x["voto"] == "Sim")
        nao = sum(1 for x in vs if (x["voto"] or "") in ("Não", "Nao"))
        outros = len(vs) - sim - nao
        vrows.append(
            dict(
                id=vid,
                data=S.parse_date(v.get("data")),
                sigla_orgao=v.get("siglaOrgao"),
                descricao=v.get("descricao"),
                proposicao=v.get("proposicaoObjeto"),
                aprovacao=v.get("aprovacao"),
                votos_sim=sim,
                votos_nao=nao,
                votos_outros=outros,
            )
        )
        voto_rows += vs
        ori_rows += ori
    n = merge_by_pk(
        votacoes, vrows,
        update_cols={"data", "sigla_orgao", "descricao", "proposicao", "aprovacao",
                     "votos_sim", "votos_nao", "votos_outros"},
    )
    _delete_by_votacao(votos, voto_rows)
    bulk_insert(votos, voto_rows)
    _delete_by_votacao(orientacoes, ori_rows)
    bulk_insert(orientacoes, ori_rows)
    return n


def _votos_api(vid: str) -> list[dict]:
    out = []
    try:
        data = S.api_get(f"/votacoes/{vid}/votos").get("dados", [])
    except Exception:
        return out
    for item in data:
        dep = item.get("deputado_") or {}
        out.append(dict(votacao_id=vid, deputado_id=dep.get("id"), voto=item.get("tipoVoto")))
    return out


def _orientacoes_api(vid: str) -> list[dict]:
    out = []
    try:
        data = S.api_get(f"/votacoes/{vid}/orientacoes").get("dados", [])
    except Exception:
        return out
    for item in data:
        out.append(
            dict(
                votacao_id=vid,
                sigla_partido=_pick(item, "siglaPartidoBloco", "siglaBancada", "nomeBancada"),
                orientacao=item.get("orientacaoVoto"),
            )
        )
    return out


def load_votacoes_bulk(ano: int) -> int:
    url = f"{S.ARQUIVOS}/votacoes/csv/votacoes-{ano}.csv"
    rows = [
        dict(
            id=_pick(r, "id", "idVotacao"),
            data=S.parse_date(_pick(r, "data", "dataHoraRegistro")),
            sigla_orgao=_pick(r, "siglaOrgao"),
            descricao=_pick(r, "descricao"),
            proposicao=_pick(r, "proposicaoObjeto", "ultimaApresentacaoProposicao_descricao"),
            aprovacao=_to_int(_pick(r, "aprovacao")),
            votos_sim=_to_int(_pick(r, "votosSim")) or 0,
            votos_nao=_to_int(_pick(r, "votosNao")) or 0,
            votos_outros=_to_int(_pick(r, "votosOutros")) or 0,
        )
        for r in S.download_csv_rows(url)
    ]
    return _upsert_votacoes(rows)


def load_proposicoes_bulk(ano: int) -> tuple[int, int]:
    """Proposições apresentadas no ano + seus autores deputados (produção legislativa).

    Cruza `proposicoesAutores` (idDeputadoAutor) com os deputados. Idempotente por ano.
    Retorna (n_proposicoes, n_vinculos_autor_deputado).
    """
    # Baixa e materializa ANTES de tocar no banco: um 404/erro estoura aqui,
    # sem ter apagado nada. O delete+insert seguinte é atômico (uma transação).
    url = f"{S.ARQUIVOS}/proposicoes/csv/proposicoes-{ano}.csv"
    prows = [
        dict(
            id=_to_int(_pick(r, "id")),
            sigla_tipo=_pick(r, "siglaTipo"),
            numero=_to_int(_pick(r, "numero")),
            ano=_to_int(_pick(r, "ano")) or ano,
            descricao_tipo=(_pick(r, "descricaoTipo") or "")[:120],
            ementa=_pick(r, "ementa"),
            data_apresentacao=S.parse_date(_pick(r, "dataApresentacao")),
            url_inteiro_teor=(_pick(r, "urlInteiroTeor") or "")[:600] or None,
            ultimo_status=_pick(r, "ultimoStatus_descricaoTramitacao"),
            situacao=(_pick(r, "ultimoStatus_descricaoSituacao") or "")[:120] or None,
        )
        for r in S.download_csv_rows(url)
    ]
    prows = [p for p in prows if p["id"]]
    n_prop = replace_where_atomic(proposicoes, {"ano": ano}, prows)

    # autores: só vínculos de deputados (idDeputadoAutor preenchido)
    url2 = f"{S.ARQUIVOS}/proposicoesAutores/csv/proposicoesAutores-{ano}.csv"
    arows = []
    for r in S.download_csv_rows(url2):
        did = _to_int(_pick(r, "idDeputadoAutor"))
        pid = _to_int(_pick(r, "idProposicao"))
        if not did or not pid:
            continue
        arows.append(dict(
            proposicao_id=pid, deputado_id=did, ano=ano,
            ordem=_to_int(_pick(r, "ordemAssinatura")),
            proponente=_to_int(_pick(r, "proponente")) or 0,
        ))
    n_aut = replace_where_atomic(proposicao_autores, {"ano": ano}, arows)
    return n_prop, n_aut


def enrich_votacoes(limite: int = 200, somente_com_votos: bool = True) -> int:
    """Busca o ASSUNTO real (ementa + objeto) das votações via API e grava.

    Por padrão enriquece as votações mais recentes que têm votos nominais
    (as que aparecem no feed/listas), evitando milhares de chamadas.
    """
    from ..db import engine
    from sqlalchemy import select, desc as _desc, func as _func

    q = select(votacoes.c.id)
    if somente_com_votos:
        sub = select(votos.c.votacao_id).group_by(votos.c.votacao_id)
        q = q.where(votacoes.c.id.in_(sub))
    q = q.where(votacoes.c.ementa.is_(None)).order_by(_desc(votacoes.c.data)).limit(limite)
    with engine.connect() as conn:
        ids = [r[0] for r in conn.execute(q)]

    n = 0
    for vid in ids:
        try:
            d = S.api_get(f"/votacoes/{vid}").get("dados", {})
        except Exception:
            continue
        objeto, ementa = _objeto_ementa(d)
        if not ementa:
            continue
        with engine.begin() as conn:
            conn.execute(votacoes.update().where(votacoes.c.id == vid).values(objeto=objeto, ementa=ementa))
        n += 1
    return n


def _objeto_ementa(d: dict) -> tuple[str | None, str | None]:
    """Extrai (objeto, ementa) do detalhe da votação."""
    cand = (d.get("proposicoesAfetadas") or []) + (d.get("objetosPossiveis") or [])
    for p in cand:
        ementa = (p.get("ementa") or "").strip()
        if ementa:
            sigla = p.get("siglaTipo") or ""
            num = p.get("numero") or ""
            ano = p.get("ano") or ""
            objeto = f"{sigla} {num}/{ano}".strip() if num else (sigla or None)
            return objeto, ementa
    return None, None


def load_votos_bulk(ano: int) -> int:
    url = f"{S.ARQUIVOS}/votacoesVotos/csv/votacoesVotos-{ano}.csv"
    rows = [
        dict(
            votacao_id=_pick(r, "idVotacao", "votacao_id", "votacaoId"),
            deputado_id=_to_int(_pick(r, "deputado_id", "deputado_id_", "idDeputado")),
            voto=_pick(r, "voto", "tipoVoto"),
        )
        for r in S.download_csv_rows(url)
    ]
    _delete_by_votacao(votos, rows)
    return bulk_insert(votos, rows)


def load_orientacoes_bulk(ano: int) -> int:
    url = f"{S.ARQUIVOS}/votacoesOrientacoes/csv/votacoesOrientacoes-{ano}.csv"
    rows = [
        dict(
            votacao_id=_pick(r, "idVotacao", "votacao_id"),
            sigla_partido=_pick(r, "siglaBancada", "siglaPartidoBloco", "siglaOrgao"),
            orientacao=_pick(r, "orientacao", "orientacaoVoto"),
        )
        for r in S.download_csv_rows(url)
    ]
    _delete_by_votacao(orientacoes, rows)
    return bulk_insert(orientacoes, rows)


# ------------------------------------------------------------------ PRESENÇA
def _presenca_rows(ano: int):
    """Itera as presenças registradas do ano (cada linha = compareceu ao evento)."""
    url = f"{S.ARQUIVOS}/eventosPresencaDeputados/csv/eventosPresencaDeputados-{ano}.csv"
    for r in S.download_csv_rows(url):
        d = S.parse_date(_pick(r, "dataHoraInicio", "data"))
        yield dict(
            deputado_id=_to_int(_pick(r, "idDeputado", "deputado_id")),
            evento_id=_to_int(_pick(r, "idEvento", "evento_id")),
            data=d,
            ano=d.year if d else ano,
            descricao_evento=None,
            presente=True,
        )


def load_presenca_bulk(ano: int) -> int:
    """Presença em eventos/sessões do ano (atômico: delete+insert numa transação)."""
    return replace_where_atomic(presenca, {"ano": ano}, _presenca_rows(ano), chunk=5000)


# ----------------------------------------- PRESENÇA OFICIAL EM PLENÁRIO (com motivo)
# Fonte: web service XML da Câmara (SitCamaraWS). É o registro oficial diário,
# o mesmo do relatório "presença em plenário" do portal: Presença, Ausência
# justificada (com o motivo declarado) ou Ausência (sem justificativa).
PRESENCA_WS = "https://www.camara.leg.br/SitCamaraWS/SessoesReunioes.asmx/ListarPresencasDia"

_FREQ_MAP = {
    "presença": "presenca",
    "ausência justificada": "ausencia_justificada",
    "ausência": "ausencia",
}


def _norm_nome(s: str | None) -> str:
    """Normaliza nome p/ casar o web service (sem id) com deputados.id: sem acento, minúsculo."""
    import unicodedata

    s = unicodedata.normalize("NFKD", (s or "")).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def _mapa_deputados() -> dict[tuple[str, str], int | None]:
    """(nome normalizado, UF) -> id. Nome eleitoral e nome civil; ambíguo vira None."""
    from sqlalchemy import select
    from ..db import engine

    mapa: dict[tuple[str, str], int | None] = {}
    with engine.connect() as conn:
        rows = conn.execute(select(deputados.c.id, deputados.c.nome,
                                   deputados.c.nome_eleitoral, deputados.c.sigla_uf))
        for did, nome, nome_el, uf in rows:
            for n in {_norm_nome(nome), _norm_nome(nome_el)}:
                if not n:
                    continue
                key = (n, (uf or "").upper())
                mapa[key] = None if (key in mapa and mapa[key] != did) else did
    return mapa


def _presencas_dia(d, mapa) -> list[dict]:
    """Busca e interpreta o XML de um dia. Lista vazia se não houve sessão."""
    import xml.etree.ElementTree as ET

    data_br = d.strftime("%d/%m/%Y")
    resp = S.http_get_text(PRESENCA_WS, params={
        "data": data_br, "numLegislatura": "", "numMatriculaParlamentar": "",
        "siglaPartido": "", "siglaUF": "",
    })
    root = ET.fromstring(resp)
    rows = []
    for p in root.iter("parlamentar"):
        nome_raw = (p.findtext("nomeParlamentar") or "").rsplit("-", 1)[0]
        uf = (p.findtext("siglaUF") or "").strip().upper()
        freq = _FREQ_MAP.get((p.findtext("descricaoFrequenciaDia") or "").strip().lower())
        if not freq:
            continue
        dep_id = mapa.get((_norm_nome(nome_raw), uf))
        if dep_id is None:
            continue  # não casou (homônimo ou fora do roster): ignora e segue
        just = " ".join((p.findtext("justificativa") or "").split()) or None
        rows.append(dict(deputado_id=dep_id, data=d, ano=d.year,
                         frequencia=freq, justificativa=just))
    return rows


def load_presenca_plenario(de, ate) -> int:
    """Frequência oficial em plenário no intervalo [de, ate], com motivo de ausência.

    Uma chamada por dia (dias sem sessão respondem vazio e são pulados).
    Idempotente e atômico por dia: regravar um dia não duplica nem deixa vazio.
    """
    import datetime as dt
    import time

    mapa = _mapa_deputados()
    total = 0
    d = de
    while d <= ate:
        try:
            rows = _presencas_dia(d, mapa)
        except Exception:
            rows = []  # dia com erro de rede/parse: mantém o que já existe
        if rows:
            total += replace_where_atomic(presenca_dia, {"data": d}, rows)
        d += dt.timedelta(days=1)
        time.sleep(0.2)  # educado com o serviço
    return total


def load_presenca_plenario_ano(ano: int) -> int:
    """Frequência oficial em plenário do ano inteiro (até hoje, se ano corrente)."""
    import datetime as dt

    hoje = dt.date.today()
    de = dt.date(ano, 1, 1)
    ate = min(dt.date(ano, 12, 31), hoje)
    if de > ate:
        return 0
    return load_presenca_plenario(de, ate)


# ------------------------------------------------------------------ helpers
def _to_int(v):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def _delete_by_votacao(table, rows: list[dict]) -> None:
    """Apaga linhas das votações presentes no lote (idempotência ao reprocessar)."""
    from ..db import engine

    ids = sorted({r["votacao_id"] for r in rows if r.get("votacao_id")})
    if not ids:
        return
    with engine.begin() as conn:
        for i in range(0, len(ids), 500):
            conn.execute(table.delete().where(table.c.votacao_id.in_(ids[i : i + 500])))


def _upsert_votacoes(rows: list[dict]) -> int:
    """Regrava votações por id (apaga as que vão ser reinseridas)."""
    from ..db import engine

    ids = [r["id"] for r in rows if r.get("id")]
    if ids:
        with engine.begin() as conn:
            conn.execute(votacoes.delete().where(votacoes.c.id.in_(ids)))
    return bulk_insert(votacoes, [r for r in rows if r.get("id")])
