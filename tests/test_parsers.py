"""Testes dos parsers de CSV/valores e dos limites de CEAP.

Estes são os pontos onde uma mudança de formato a montante (vírgula decimal,
encoding, data) corromperia dados silenciosamente, então valem teste unitário.
"""
from __future__ import annotations

import datetime as dt

from app.ingest import sources as S
from app.ingest.camara import _pick, _to_int
from app import ceap


class TestParseFloat:
    def test_formato_brasileiro(self):
        assert S.parse_float("1.234,56") == 1234.56

    def test_formato_americano(self):
        assert S.parse_float("1234.56") == 1234.56

    def test_so_virgula_decimal(self):
        assert S.parse_float("0,50") == 0.5

    def test_com_simbolo_e_espacos(self):
        assert S.parse_float(" R$ 2.000,00 ") == 2000.0

    def test_vazio_e_none_viram_zero(self):
        assert S.parse_float("") == 0.0
        assert S.parse_float(None) == 0.0

    def test_lixo_nao_quebra(self):
        assert S.parse_float("abc") == 0.0


class TestParseDate:
    def test_iso(self):
        assert S.parse_date("2026-03-01") == dt.date(2026, 3, 1)

    def test_br(self):
        assert S.parse_date("01/03/2026") == dt.date(2026, 3, 1)

    def test_iso_com_hora(self):
        assert S.parse_date("2026-03-01T14:30:00") == dt.date(2026, 3, 1)

    def test_vazio_e_invalido(self):
        assert S.parse_date("") is None
        assert S.parse_date(None) is None
        assert S.parse_date("31/31/2026") is None


class TestOnlyDigits:
    def test_extrai_digitos(self):
        assert S.only_digits("12.345.678/0001-90") == "12345678000190"

    def test_none(self):
        assert S.only_digits(None) == ""


class TestToInt:
    def test_ok(self):
        assert _to_int("42") == 42
        assert _to_int(" 7 ") == 7

    def test_lixo_vira_none(self):
        assert _to_int("x") is None
        assert _to_int(None) is None
        assert _to_int("") is None


class TestPick:
    def test_primeira_chave_com_valor(self):
        row = {"a": "", "b": "X", "c": "Y"}
        assert _pick(row, "a", "b", "c") == "X"

    def test_default_quando_nenhuma(self):
        assert _pick({}, "a", "b", default="z") == "z"


class TestCeap:
    def test_limite_mensal_conhecido(self):
        assert ceap.limite_mensal("SP") is not None
        assert ceap.limite_mensal("sp") == ceap.limite_mensal("SP")  # case-insensitive

    def test_limite_anual_eh_12x(self):
        m = ceap.limite_mensal("SP")
        assert ceap.limite_anual("SP") == round(m * 12, 2)

    def test_uf_desconhecida(self):
        assert ceap.limite_mensal("ZZ") is None
        assert ceap.limite_anual(None) is None
