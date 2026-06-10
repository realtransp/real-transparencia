"""Testes da ingestão diária com a rede mockada.

Provam que o conserto do `daily` funciona: rodar a atualização incremental
- NÃO duplica despesas;
- NÃO apaga o histórico de votações/votos (o bug original do replace_table);
- NÃO zera CPF/telefone do roster (o que quebrava o cruzamento com o TSE).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select

from app.db import bulk_insert, deputados, engine, despesas, votacoes, votos
from app.ingest import camara
from app.ingest import sources as S


def _scalar(q):
    with engine.connect() as conn:
        return conn.execute(q).scalar()


def _count(table):
    with engine.connect() as conn:
        return len(conn.execute(select(table)).fetchall())


# --------------------------------------------------------------------- despesas
def test_despesas_bulk_idempotente(monkeypatch):
    csv_rows = [
        {"ideCadastro": "1", "numAno": "2026", "numMes": "1", "txtDescricao": "X",
         "txtFornecedor": "F", "txtCNPJCPF": "1", "vlrLiquido": "1.000,00",
         "datEmissao": "10/01/2026", "urlDocumento": ""},
        {"ideCadastro": "1", "numAno": "2026", "numMes": "2", "txtDescricao": "Y",
         "txtFornecedor": "G", "txtCNPJCPF": "2", "vlrLiquido": "500,00",
         "datEmissao": "05/02/2026", "urlDocumento": ""},
    ]
    monkeypatch.setattr(S, "download_csv_rows", lambda *a, **k: iter(csv_rows))

    camara.load_despesas_bulk(2026)
    camara.load_despesas_bulk(2026)  # rodar de novo (cron) não pode duplicar

    assert _count(despesas) == 2
    total = _scalar(select(despesas.c.valor_liquido).where(despesas.c.mes == 1))
    assert total == 1000.0  # vírgula decimal parseada certo


def test_despesas_mes_malformado_nao_quebra(monkeypatch):
    csv_rows = [
        {"ideCadastro": "1", "numAno": "2026", "numMes": "lixo", "txtDescricao": "X",
         "txtFornecedor": "F", "txtCNPJCPF": "1", "vlrLiquido": "10,00",
         "datEmissao": "10/01/2026", "urlDocumento": ""},
    ]
    monkeypatch.setattr(S, "download_csv_rows", lambda *a, **k: iter(csv_rows))
    camara.load_despesas_bulk(2026)  # não deve estourar ValueError
    assert _count(despesas) == 1
    assert _scalar(select(despesas.c.mes)) == 0  # mês inválido vira 0


# ------------------------------------------------------------ votações (daily)
def _fake_recent_votacao(vid):
    return {"id": vid, "data": "2026-04-01", "siglaOrgao": "PLEN",
            "descricao": "nova", "proposicaoObjeto": "PL 9/2026", "aprovacao": 1}


def test_daily_votacoes_preserva_historico(monkeypatch):
    # Histórico: uma votação antiga com votos e ementa enriquecida.
    bulk_insert(votacoes, [dict(id="HIST-1", data=dt.date(2026, 1, 1), sigla_orgao="PLEN",
                                descricao="antiga", proposicao="PL 1/2025", aprovacao=1,
                                votos_sim=300, votos_nao=100, votos_outros=0,
                                objeto="PL 1/2025", ementa="ASSUNTO HISTORICO",
                                titulo_ia="Manchete antiga")])
    bulk_insert(votos, [dict(votacao_id="HIST-1", deputado_id=1, voto="Sim"),
                        dict(votacao_id="HIST-1", deputado_id=2, voto="Não")])

    # A API só devolve a votação NOVA.
    monkeypatch.setattr(S, "api_paginate", lambda *a, **k: iter([_fake_recent_votacao("NEW-1")]))
    monkeypatch.setattr(camara, "_votos_api", lambda vid: [
        dict(votacao_id=vid, deputado_id=1, voto="Sim"),
        dict(votacao_id=vid, deputado_id=2, voto="Sim"),
    ])
    monkeypatch.setattr(camara, "_orientacoes_api", lambda vid: [])

    camara.load_votacoes_recentes(limite_paginas=1)

    # O histórico continua intacto (o bug original apagava tudo).
    assert _count(votacoes) == 2
    hist = _scalar(select(votacoes.c.ementa).where(votacoes.c.id == "HIST-1"))
    assert hist == "ASSUNTO HISTORICO"
    votos_hist = [r for r in _all_votos() if r == "HIST-1"]
    assert len(votos_hist) == 2  # votos do histórico preservados
    # A nova entrou com placar calculado (2 Sim).
    new_sim = _scalar(select(votacoes.c.votos_sim).where(votacoes.c.id == "NEW-1"))
    assert new_sim == 2


def _all_votos():
    with engine.connect() as conn:
        return [r[0] for r in conn.execute(select(votos.c.votacao_id))]


def test_daily_votacoes_idempotente(monkeypatch):
    monkeypatch.setattr(S, "api_paginate", lambda *a, **k: iter([_fake_recent_votacao("NEW-1")]))
    monkeypatch.setattr(camara, "_votos_api", lambda vid: [dict(votacao_id=vid, deputado_id=1, voto="Sim")])
    monkeypatch.setattr(camara, "_orientacoes_api", lambda vid: [])

    camara.load_votacoes_recentes(limite_paginas=1)
    camara.load_votacoes_recentes(limite_paginas=1)  # 2x não duplica

    assert _count(votacoes) == 1
    assert len(_all_votos()) == 1


# ----------------------------------------------------------------- roster (daily)
def test_upsert_deputados_preserva_cpf_e_telefone(monkeypatch):
    # Roster já enriquecido pelo backfill.
    bulk_insert(deputados, [dict(id=1, cpf="11111111111", nome="Ana", nome_eleitoral="Ana T.",
                                 sigla_partido="PT", sigla_uf="SP", url_foto=None,
                                 situacao="Em exercício", email="x@y", telefone="3215-1111")])

    # A API de lista NÃO traz cpf/telefone e a deputada trocou de partido.
    api_rows = [{"id": 1, "nome": "Ana", "siglaPartido": "PSOL", "siglaUf": "SP",
                 "urlFoto": None, "email": "novo@camara"}]
    monkeypatch.setattr(S, "api_paginate", lambda *a, **k: iter(api_rows))

    camara.upsert_deputados()

    with engine.connect() as conn:
        row = conn.execute(select(deputados).where(deputados.c.id == 1)).mappings().first()
    assert row["sigla_partido"] == "PSOL"      # atualizou o partido
    assert row["email"] == "novo@camara"       # atualizou o e-mail
    assert row["cpf"] == "11111111111"         # PRESERVOU o CPF (cruzamento TSE)
    assert row["telefone"] == "3215-1111"      # PRESERVOU o telefone do gabinete


def test_upsert_deputados_insere_novo(monkeypatch):
    api_rows = [{"id": 99, "nome": "Novato", "siglaPartido": "MDB", "siglaUf": "BA",
                 "urlFoto": None, "email": "n@camara"}]
    monkeypatch.setattr(S, "api_paginate", lambda *a, **k: iter(api_rows))
    camara.upsert_deputados()
    assert _count(deputados) == 1
    assert _scalar(select(deputados.c.nome).where(deputados.c.id == 99)) == "Novato"
