"""Configuração dos testes.

IMPORTANTE: definimos DATABASE_URL para um SQLite temporário ANTES de importar
qualquer módulo do app, porque `app.config` cria a engine na importação. Assim os
testes nunca tocam o banco real (nem o prod). `load_dotenv()` no config não
sobrescreve variáveis já presentes no ambiente (override=False), então este valor
vence o eventual DATABASE_URL do .env.
"""
from __future__ import annotations

import os
import pathlib
import tempfile

_TMP_DB = pathlib.Path(tempfile.gettempdir()) / "resumo_real_pytest.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"
# Sem chaves de IA nos testes: garante que nada chame a rede.
os.environ["GEMINI_API_KEY"] = ""
os.environ["XAI_API_KEY"] = ""

import datetime as dt  # noqa: E402

import pytest  # noqa: E402

from app.db import (  # noqa: E402
    deputados,
    despesas,
    engine,
    init_db,
    metadata,
    orientacoes,
    proposicao_autores,
    proposicoes,
    presenca,
    votacoes,
    votos,
)
from app.db import bulk_insert  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    """Recria o schema do zero a cada teste (isolamento total)."""
    metadata.drop_all(engine)
    init_db()
    yield
    metadata.drop_all(engine)


# Ano usado nos fixtures e nas asserções (coerente com os dados semeados).
ANO = 2026


@pytest.fixture
def seed():
    """Semeia um conjunto pequeno mas coerente de dados para os testes de query."""
    bulk_insert(deputados, [
        dict(id=1, cpf="11111111111", nome="Ana Teste", nome_eleitoral="Ana Teste",
             sigla_partido="PT", sigla_uf="SP", url_foto=None, situacao="Em exercício",
             email="dep.ana@camara.leg.br", telefone="3215-1111"),
        dict(id=2, cpf="22222222222", nome="Bruno Teste", nome_eleitoral="Bruno Teste",
             sigla_partido="PL", sigla_uf="RJ", url_foto=None, situacao="Em exercício",
             email="dep.bruno@camara.leg.br", telefone="3215-2222"),
    ])
    bulk_insert(despesas, [
        dict(deputado_id=1, ano=ANO, mes=1, tipo_despesa="DIVULGAÇÃO",
             fornecedor_nome="GRAFICA X", fornecedor_cnpj_cpf="00000000000100",
             valor_liquido=1000.0, data_documento=dt.date(ANO, 1, 10), url_documento=None),
        dict(deputado_id=1, ano=ANO, mes=2, tipo_despesa="COMBUSTÍVEIS",
             fornecedor_nome="POSTO Y", fornecedor_cnpj_cpf="00000000000200",
             valor_liquido=500.0, data_documento=dt.date(ANO, 2, 5), url_documento=None),
        dict(deputado_id=2, ano=ANO, mes=1, tipo_despesa="DIVULGAÇÃO",
             fornecedor_nome="GRAFICA X", fornecedor_cnpj_cpf="00000000000100",
             valor_liquido=2000.0, data_documento=dt.date(ANO, 1, 12), url_documento=None),
    ])
    bulk_insert(votacoes, [
        dict(id="A-1", data=dt.date(ANO, 3, 1), sigla_orgao="PLEN",
             descricao="Votação A", proposicao="PL 1/2025", aprovacao=1,
             votos_sim=1, votos_nao=1, votos_outros=0, objeto="PL 1/2025",
             ementa="Cria a política X.", titulo_ia="Política X aprovada"),
        dict(id="B-2", data=dt.date(ANO, 3, 2), sigla_orgao="PLEN",
             descricao="Votação B", proposicao="PEC 2/2025", aprovacao=0,
             votos_sim=0, votos_nao=2, votos_outros=0, objeto="PEC 2/2025",
             ementa="Altera a Constituição.", titulo_ia="PEC rejeitada"),
    ])
    bulk_insert(votos, [
        dict(votacao_id="A-1", deputado_id=1, voto="Sim"),
        dict(votacao_id="A-1", deputado_id=2, voto="Não"),
        dict(votacao_id="B-2", deputado_id=1, voto="Não"),
        dict(votacao_id="B-2", deputado_id=2, voto="Não"),
    ])
    bulk_insert(orientacoes, [
        dict(votacao_id="A-1", sigla_partido="PT", orientacao="Sim"),
        dict(votacao_id="A-1", sigla_partido="PL", orientacao="Não"),
    ])
    bulk_insert(presenca, [
        dict(deputado_id=1, evento_id=900, data=dt.date(ANO, 3, 1), ano=ANO,
             descricao_evento=None, presente=True),
    ])
    bulk_insert(proposicoes, [
        dict(id=10001, sigla_tipo="PL", numero=1, ano=2023,
             descricao_tipo="Projeto de Lei", ementa="Projeto da Ana.",
             data_apresentacao=dt.date(2023, 5, 1), url_inteiro_teor=None,
             ultimo_status="Tramitando", situacao="Transformado em Norma Jurídica"),
    ])
    bulk_insert(proposicao_autores, [
        dict(proposicao_id=10001, deputado_id=1, ano=2023, ordem=1, proponente=1),
    ])
    return {"ano": ANO}
