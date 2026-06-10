"""Testes da frequência oficial em plenário (motivos de falta).

Cobrem o parse do XML do web service, o casamento por nome+UF com deputados.id,
a idempotência por dia e as queries de breakdown/ranking.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select

from app import queries as Q
from app.db import bulk_insert, engine, presenca_dia
from app.ingest import camara
from app.ingest import sources as S

XML_DIA = """<?xml version="1.0" encoding="utf-8"?>
<dia>
  <data>03/06/2026</data>
  <parlamentares>
    <parlamentar>
      <nomeParlamentar>Ana Teste-PT/SP</nomeParlamentar>
      <siglaUF>SP</siglaUF>
      <descricaoFrequenciaDia>Presença</descricaoFrequenciaDia>
      <justificativa>
      </justificativa>
    </parlamentar>
    <parlamentar>
      <nomeParlamentar>Bruno Teste-PL/RJ</nomeParlamentar>
      <siglaUF>RJ</siglaUF>
      <descricaoFrequenciaDia>Ausência justificada</descricaoFrequenciaDia>
      <justificativa>Missão Autorizada</justificativa>
    </parlamentar>
    <parlamentar>
      <nomeParlamentar>Fulano Desconhecido-XX/ZZ</nomeParlamentar>
      <siglaUF>ZZ</siglaUF>
      <descricaoFrequenciaDia>Ausência</descricaoFrequenciaDia>
      <justificativa></justificativa>
    </parlamentar>
  </parlamentares>
</dia>"""

XML_VAZIO = '<?xml version="1.0" encoding="utf-8"?>\n<dia />'


def test_norm_nome():
    assert camara._norm_nome("Acácio  Favacho") == "acacio favacho"
    assert camara._norm_nome(None) == ""


def _count_rows():
    with engine.connect() as c:
        return len(c.execute(select(presenca_dia)).fetchall())


def test_load_dia_casa_nomes_e_ignora_desconhecidos(seed, monkeypatch):
    monkeypatch.setattr(S, "http_get_text", lambda *a, **k: XML_DIA)
    n = camara.load_presenca_plenario(dt.date(2026, 6, 3), dt.date(2026, 6, 3))
    assert n == 2  # Ana e Bruno casaram; o desconhecido foi ignorado
    with engine.connect() as c:
        rows = {r.deputado_id: r for r in c.execute(select(presenca_dia))}
    assert rows[1].frequencia == "presenca"
    assert rows[1].justificativa is None  # justificativa em branco vira NULL
    assert rows[2].frequencia == "ausencia_justificada"
    assert rows[2].justificativa == "Missão Autorizada"


def test_load_dia_idempotente(seed, monkeypatch):
    monkeypatch.setattr(S, "http_get_text", lambda *a, **k: XML_DIA)
    camara.load_presenca_plenario(dt.date(2026, 6, 3), dt.date(2026, 6, 3))
    camara.load_presenca_plenario(dt.date(2026, 6, 3), dt.date(2026, 6, 3))
    assert _count_rows() == 2  # regravar o dia não duplica


def test_dia_sem_sessao_nao_grava(seed, monkeypatch):
    monkeypatch.setattr(S, "http_get_text", lambda *a, **k: XML_VAZIO)
    n = camara.load_presenca_plenario(dt.date(2026, 6, 7), dt.date(2026, 6, 7))
    assert n == 0
    assert _count_rows() == 0


def _seed_presenca():
    """3 dias: Ana presente sempre; Bruno 1 presença, 1 justificada, 1 sem justificativa."""
    bulk_insert(presenca_dia, [
        dict(deputado_id=1, data=dt.date(2026, 6, 2), ano=2026, frequencia="presenca", justificativa=None),
        dict(deputado_id=1, data=dt.date(2026, 6, 3), ano=2026, frequencia="presenca", justificativa=None),
        dict(deputado_id=1, data=dt.date(2026, 6, 4), ano=2026, frequencia="presenca", justificativa=None),
        dict(deputado_id=2, data=dt.date(2026, 6, 2), ano=2026, frequencia="presenca", justificativa=None),
        dict(deputado_id=2, data=dt.date(2026, 6, 3), ano=2026, frequencia="ausencia_justificada", justificativa="Missão Autorizada"),
        dict(deputado_id=2, data=dt.date(2026, 6, 4), ano=2026, frequencia="ausencia", justificativa=None),
    ])


def test_faltas_deputado(seed):
    _seed_presenca()
    f = Q.faltas_deputado(2, 2026)
    assert f["dias"] == 3 and f["presencas"] == 1
    assert f["justificadas"] == 1 and f["nao_justificadas"] == 1
    motivos = {m["motivo"]: m for m in f["motivos"]}
    assert motivos["Missão Autorizada"]["pct"] == 50.0
    assert motivos["Sem justificativa registrada"]["pct"] == 50.0
    # deputado 100% presente: sem lista de motivos
    assert Q.faltas_deputado(1, 2026)["motivos"] == []
    # sem dados: None
    assert Q.faltas_deputado(999, 2026) is None


def test_rank_faltas_sem_justificativa(seed):
    _seed_presenca()
    rank = Q.rank_faltas_sem_justificativa(2026)
    assert len(rank) == 1  # só Bruno tem falta sem justificativa
    assert rank[0]["deputado_id"] == 2
    assert rank[0]["nao_justificadas"] == 1
    assert rank[0]["motivo_top"] == "Missão Autorizada"


def test_motivos_faltas_globais(seed):
    _seed_presenca()
    g = Q.motivos_faltas_globais(2026)
    assert g["registros"] == 6 and g["ausencias"] == 2
    motivos = {m["motivo"]: m["pct"] for m in g["motivos"]}
    assert motivos == {"Missão Autorizada": 50.0, "Sem justificativa registrada": 50.0}
    assert Q.motivos_faltas_globais(1999) is None
