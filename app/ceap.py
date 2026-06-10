"""Limite mensal da Cota para Exercício da Atividade Parlamentar (CEAP) por UF.

Varia por estado conforme a distância até Brasília (custo de passagens).
A cota é MENSAL; o valor "anual" usado aqui é estimativa (mensal × 12).

Base: valores oficiais de 2025. A Câmara reajustou a CEAP em ~13,75% em fev/2026
(inflação acumulada fev/2023–dez/2025). Aplicamos esse fator para estimar 2026.
Fonte: Câmara dos Deputados / imprensa.
"""
from __future__ import annotations

# Valores oficiais 2025 (R$/mês)
_CEAP_2025: dict[str, float] = {
    "RR": 51406.33, "AC": 50426.26, "RO": 49466.29, "AM": 49363.92, "AP": 49168.58,
    "RN": 48525.79, "CE": 48245.57, "PA": 48021.25, "MA": 47945.49, "PB": 47826.36,
    "PE": 47470.60, "PI": 46765.57, "AL": 46737.90, "RS": 46669.70, "MS": 46336.64,
    "SE": 45933.06, "SC": 45671.58, "TO": 45297.41, "MT": 45221.83, "BA": 44804.65,
    "PR": 44665.66, "ES": 43217.71, "SP": 42837.33, "MG": 41886.51, "RJ": 41553.77,
    "GO": 41300.86, "DF": 36582.46,
}

REAJUSTE_2026 = 1.1375  # +13,75% (fev/2026)

# Valores de referência 2026 (estimados a partir de 2025 + reajuste)
CEAP_MENSAL: dict[str, float] = {uf: round(v * REAJUSTE_2026, 2) for uf, v in _CEAP_2025.items()}

ANO_REFERENCIA = 2026


def limite_mensal(uf: str | None) -> float | None:
    return CEAP_MENSAL.get((uf or "").upper())


def limite_anual(uf: str | None) -> float | None:
    """Estimativa do teto anual = limite mensal × 12 (a cota oficial é mensal)."""
    m = limite_mensal(uf)
    return round(m * 12, 2) if m else None
