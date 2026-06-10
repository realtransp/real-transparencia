"""Testes dos helpers de escrita atômica/idempotente do banco.

Cobrem exatamente o que estava quebrado na ingestão diária:
- replace_where_atomic: o delete NÃO pode persistir se o insert falhar no meio.
- merge_by_pk: atualizar não pode destruir colunas enriquecidas nem duplicar.
"""
from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import select

from app.db import (
    bulk_insert,
    despesas,
    engine,
    merge_by_pk,
    replace_where_atomic,
    votacoes,
)


def _count(table, **eq):
    q = select(table)
    for k, v in eq.items():
        q = q.where(table.c[k] == v)
    with engine.connect() as conn:
        return len(conn.execute(q).fetchall())


def _despesa(mes, valor):
    return dict(deputado_id=1, ano=2026, mes=mes, tipo_despesa="X",
                fornecedor_nome="F", fornecedor_cnpj_cpf="1",
                valor_liquido=valor, data_documento=dt.date(2026, mes, 1),
                url_documento=None)


class TestReplaceWhereAtomic:
    def test_idempotente_nao_duplica(self):
        rows = [_despesa(1, 100), _despesa(2, 200)]
        replace_where_atomic(despesas, {"ano": 2026}, list(rows))
        replace_where_atomic(despesas, {"ano": 2026}, list(rows))
        assert _count(despesas, ano=2026) == 2  # rodar 2x não dobra

    def test_so_afeta_o_escopo(self):
        bulk_insert(despesas, [dict(_despesa(1, 1), ano=2025)])
        replace_where_atomic(despesas, {"ano": 2026}, [_despesa(1, 100)])
        assert _count(despesas, ano=2025) == 1  # ano fora do escopo preservado
        assert _count(despesas, ano=2026) == 1

    def test_rollback_se_a_geracao_falhar(self):
        # Estado inicial: 1 linha em 2026.
        replace_where_atomic(despesas, {"ano": 2026}, [_despesa(1, 100)])
        assert _count(despesas, ano=2026) == 1

        def gerador_que_explode():
            yield _despesa(2, 200)
            raise RuntimeError("download truncado")

        # A falha no meio NÃO pode deixar a tabela vazia: o delete é desfeito.
        with pytest.raises(RuntimeError):
            replace_where_atomic(despesas, {"ano": 2026}, gerador_que_explode())
        assert _count(despesas, ano=2026) == 1  # dado antigo continua lá


class TestMergeByPk:
    def _votacao(self, vid, **extra):
        base = dict(id=vid, data=dt.date(2026, 1, 1), sigla_orgao="PLEN",
                    descricao="d", proposicao="p", aprovacao=1,
                    votos_sim=0, votos_nao=0, votos_outros=0,
                    objeto=None, ementa=None, titulo_ia=None)
        base.update(extra)
        return base

    def test_preserva_colunas_fora_de_update_cols(self):
        # Votação já enriquecida (ementa/titulo_ia) e com placar.
        bulk_insert(votacoes, [self._votacao("A-1", ementa="ASSUNTO REAL",
                                             titulo_ia="Manchete", votos_sim=10)])
        # Daily reprocessa a mesma votação sem trazer ementa/titulo_ia.
        merge_by_pk(votacoes, [self._votacao("A-1", votos_sim=42)],
                    update_cols={"votos_sim", "votos_nao", "votos_outros", "aprovacao"})
        with engine.connect() as conn:
            row = conn.execute(select(votacoes).where(votacoes.c.id == "A-1")).mappings().first()
        assert row["votos_sim"] == 42            # atualizou o que devia
        assert row["ementa"] == "ASSUNTO REAL"   # PRESERVOU o enriquecimento
        assert row["titulo_ia"] == "Manchete"

    def test_insere_novos_e_nao_duplica(self):
        bulk_insert(votacoes, [self._votacao("OLD-1", ementa="historico")])
        merge_by_pk(votacoes, [self._votacao("OLD-1"), self._votacao("NEW-1")],
                    update_cols={"aprovacao"})
        assert _count(votacoes) == 2                       # OLD preservado + NEW inserido
        assert _count(votacoes, id="OLD-1") == 1           # não duplicou
        with engine.connect() as conn:
            old = conn.execute(select(votacoes.c.ementa).where(votacoes.c.id == "OLD-1")).scalar()
        assert old == "historico"                          # histórico intacto
