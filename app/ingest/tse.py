"""Ingestão de dados do TSE (eleições): candidatos e financiamento de campanha.

Arquivos do repositório de dados eleitorais (CDN do TSE), por ano de eleição.
São grandes e nacionais; filtramos para DEPUTADO FEDERAL e ligamos por CPF.
"""
from __future__ import annotations

from . import sources as S
from ..db import bulk_insert, delete_where, engine, tse_candidatos, tse_doacoes

CDN = "https://cdn.tse.jus.br/estatistica/sead/odsele"
CARGO_ALVO = "DEPUTADO FEDERAL"


def _pick(row: dict, *keys, default=None):
    for k in keys:
        if k in row and row[k] not in (None, "", "#NULO#", "#NE#"):
            return row[k]
    return default


def load_candidatos(ano: int) -> int:
    """consulta_cand_{ano}.zip — um CSV por UF, latin-1, separador ';'."""
    url = f"{CDN}/consulta_cand/consulta_cand_{ano}.zip"
    delete_where(tse_candidatos, ano_eleicao=ano)
    rows, total = [], 0
    for r in S.download_csv_rows(url, skip_contains=["_BRASIL", "_BR."]):
        if (_pick(r, "DS_CARGO") or "").upper() != CARGO_ALVO:
            continue
        rows.append(
            dict(
                ano_eleicao=ano,
                cpf=S.only_digits(_pick(r, "NR_CPF_CANDIDATO")),
                nome=_pick(r, "NM_CANDIDATO"),
                sigla_partido=_pick(r, "SG_PARTIDO"),
                sigla_uf=_pick(r, "SG_UF"),
                cargo=_pick(r, "DS_CARGO"),
                situacao=_pick(r, "DS_SIT_TOT_TURNO", "DS_SITUACAO_CANDIDATO_TOT"),
                votos=None,
            )
        )
        if len(rows) >= 5000:
            total += bulk_insert(tse_candidatos, rows)
            rows = []
    total += bulk_insert(tse_candidatos, rows)
    return total


def load_doacoes(ano: int) -> int:
    """Receitas de campanha (doadores) por candidato a deputado federal.

    O ZIP de prestação de contas do TSE mistura despesas, receitas e o detalhe
    de doador originário (que duplicaria os valores). Lemos APENAS os arquivos
    `receitas_candidatos_{ano}_<UF>.csv` (um por UF), ignorando os consolidados
    nacionais ("_BRASIL") e o recorte de doador originário.
    """
    url = f"{CDN}/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_{ano}.zip"
    delete_where(tse_doacoes, ano_eleicao=ano)
    rows, total = [], 0
    try:
        iterator = S.download_csv_rows(
            url,
            skip_contains=["_BRASIL", "DOADOR_ORIGINARIO"],
            include_only=["RECEITAS_CANDIDATOS_"],
        )
    except Exception:
        return 0
    for r in iterator:
        if (_pick(r, "DS_CARGO") or "").upper() != CARGO_ALVO:
            continue
        rows.append(
            dict(
                ano_eleicao=ano,
                cpf_candidato=S.only_digits(_pick(r, "NR_CPF_CANDIDATO")),
                doador=_pick(r, "NM_DOADOR", "NM_DOADOR_ORIGINARIO"),
                doador_documento=S.only_digits(_pick(r, "NR_CPF_CNPJ_DOADOR")),
                valor=S.parse_float(_pick(r, "VR_RECEITA")),
            )
        )
        if len(rows) >= 5000:
            total += bulk_insert(tse_doacoes, rows)
            rows = []
    total += bulk_insert(tse_doacoes, rows)
    return total


def load_votos_recebidos(ano: int) -> int:
    """Soma os votos nominais por candidato a deputado federal e grava em
    `tse_candidatos.votos`.

    A votação vem de `votacao_candidato_munzona_{ano}.zip` (um registro por
    município/zona/turno), que traz SQ_CANDIDATO mas não o CPF. Usamos
    `consulta_cand_{ano}.zip` para mapear SQ_CANDIDATO -> CPF e então agregamos
    os votos por CPF (chave usada em tse_candidatos). Retorna o nº de
    candidatos atualizados.
    """
    # 1) SQ_CANDIDATO -> CPF (deputado federal), via consulta_cand
    cc_url = f"{CDN}/consulta_cand/consulta_cand_{ano}.zip"
    sq_to_cpf: dict[str, str] = {}
    for r in S.download_csv_rows(cc_url, skip_contains=["_BRASIL", "_BR."]):
        if (_pick(r, "DS_CARGO") or "").upper() != CARGO_ALVO:
            continue
        sq = _pick(r, "SQ_CANDIDATO")
        cpf = S.only_digits(_pick(r, "NR_CPF_CANDIDATO"))
        if sq and cpf:
            sq_to_cpf[str(sq)] = cpf

    # 2) soma QT_VOTOS_NOMINAIS por SQ_CANDIDATO (deputado federal)
    vcm_url = f"{CDN}/votacao_candidato_munzona/votacao_candidato_munzona_{ano}.zip"
    votos_por_sq: dict[str, int] = {}
    for r in S.download_csv_rows(vcm_url, skip_contains=["_BRASIL", "_BR."]):
        if (_pick(r, "DS_CARGO") or "").upper() != CARGO_ALVO:
            continue
        sq = _pick(r, "SQ_CANDIDATO")
        if not sq:
            continue
        try:
            qt = int(float(_pick(r, "QT_VOTOS_NOMINAIS", default=0) or 0))
        except (TypeError, ValueError):
            qt = 0
        votos_por_sq[str(sq)] = votos_por_sq.get(str(sq), 0) + qt

    # 3) agrega por CPF e atualiza tse_candidatos
    votos_por_cpf: dict[str, int] = {}
    for sq, qt in votos_por_sq.items():
        cpf = sq_to_cpf.get(sq)
        if cpf:
            votos_por_cpf[cpf] = votos_por_cpf.get(cpf, 0) + qt

    atualizados = 0
    with engine.begin() as conn:
        for cpf, qt in votos_por_cpf.items():
            res = conn.execute(
                tse_candidatos.update()
                .where(tse_candidatos.c.ano_eleicao == ano)
                .where(tse_candidatos.c.cpf == cpf)
                .values(votos=qt)
            )
            atualizados += res.rowcount or 0
    return atualizados
