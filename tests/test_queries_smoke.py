"""Smoke test das queries de leitura contra SQLite com dados semeados.

Não checa valores exatos (isso é responsabilidade dos testes de cálculo); o
objetivo é pegar regressões e quebras de portabilidade: toda função roda sem
estourar exceção e devolve o tipo esperado. `raiox_data` nos 3 escopos exercita
~40 sub-queries de uma vez, incluindo `extract`/datas (onde mora o risco
SQLite vs Postgres).
"""
from __future__ import annotations

from app import queries as Q

ANO = 2026


def test_home_e_listas(seed):
    assert isinstance(Q.home_stats(), dict)
    assert isinstance(Q.feed_grouped(6), list)
    assert isinstance(Q.feed_items(10, ano=ANO), list)
    assert isinstance(Q.filtros_disponiveis(), dict)
    assert isinstance(Q.partidos_list(), list)
    assert isinstance(Q.anos_despesa(), list)
    assert Q.ano_corrente() == ANO


def test_deputado(seed):
    dep = Q.get_deputado(1)
    assert dep and dep["nome"] == "Ana Teste"
    assert isinstance(Q.deputado_resumo_financeiro(1, ANO), dict)
    # presença pode ser None (heurística de plenário), só não pode quebrar:
    Q.deputado_presenca(1)
    assert isinstance(Q.deputado_stats(1, ANO), dict)
    assert isinstance(Q.deputado_votos_agrupado(1), list)
    assert isinstance(Q.deputado_serie_anual(1), list)
    Q.deputado_eleicao(1)


def test_busca(seed):
    assert isinstance(Q.buscar_deputados("Ana"), list)
    assert isinstance(Q.list_deputados(uf="SP"), list)
    assert isinstance(Q.list_deputados(partido="PT"), list)


def test_gastos(seed):
    assert isinstance(Q.gastos_overview(ANO), dict)
    assert isinstance(Q.top_fornecedores(ANO, 10), list)
    assert isinstance(Q.ranking_gastos_deputados(10), list)
    assert isinstance(Q.gasto_por_partido(ANO), list)
    assert isinstance(Q.valores_repetidos(ANO), list)
    assert isinstance(Q.relatorio_kpis(ANO), dict)
    assert isinstance(Q.fornecedor_detalhe("GRAFICA X", ANO), dict)


def test_partidos_e_producao(seed):
    anos = Q.anos_mandato(ANO)
    assert isinstance(anos, list) and anos
    assert isinstance(Q.producao_por_partido(anos), dict)
    assert isinstance(Q.ranking_partidos(ANO, min_dep=1), list)


def test_raiox_todos_os_escopos(seed):
    # O caso mais pesado: cada escopo dispara dezenas de sub-queries.
    assert isinstance(Q.raiox_data("geral", None, ANO), dict)
    assert isinstance(Q.raiox_data("deputado", "1", ANO), dict)
    assert isinstance(Q.raiox_data("partido", "PT", ANO), dict)


def test_sugestoes(seed):
    assert Q.salvar_sugestao("ideia anônima de teste", "/gastos") is True
    lista = Q.listar_sugestoes()
    assert isinstance(lista, list) and len(lista) == 1
    assert lista[0]["texto"] == "ideia anônima de teste"
