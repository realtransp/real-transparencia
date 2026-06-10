"""Helpers de apresentação para os templates (formatação e mapeamentos do design)."""
from __future__ import annotations

import datetime

# Início da 57ª legislatura (mandato atual), usado p/ estimar salário acumulado.
INICIO_LEGISLATURA = datetime.date(2023, 2, 1)


def dias_uteis_ano(ano: int) -> int:
    """Dias úteis (seg–sex) decorridos no ano até hoje. Não desconta feriados."""
    hoje = datetime.date.today()
    inicio = datetime.date(ano, 1, 1)
    fim = min(hoje, datetime.date(ano, 12, 31))
    if fim < inicio:
        return 0
    dias, cur = 0, inicio
    while cur <= fim:
        if cur.weekday() < 5:
            dias += 1
        cur += datetime.timedelta(days=1)
    return dias


def meses_decorridos_ano(ano: int) -> int:
    hoje = datetime.date.today()
    return hoje.month if ano == hoje.year else 12


def meses_no_mandato() -> int:
    hoje = datetime.date.today()
    d = (hoje.year - INICIO_LEGISLATURA.year) * 12 + (hoje.month - INICIO_LEGISLATURA.month) + 1
    return max(d, 0)

# Cores base que o avatar/tag sabem tingir (ver app.js colorBg/colorFg)
_PARTY_COLORS = ["var(--green-600)", "var(--clay-600)", "var(--petro-500)", "var(--amber-500)"]


def brl(v, full: bool = False) -> str:
    """Formata em Real. full=True mostra centavos; senão abrevia milhares (R$ 198k)."""
    try:
        n = float(v)
    except (TypeError, ValueError):
        return "R$ 0"
    if full:
        s = f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return "R$ " + s
    if abs(n) >= 1_000_000:
        return "R$ " + f"{n/1_000_000:.1f}".replace(".", ",") + " mi"
    if abs(n) >= 1000:
        return "R$ " + f"{round(n/1000)}" + "k"
    return "R$ " + f"{n:,.0f}".replace(",", ".")


def brl_full(v) -> str:
    return brl(v, full=True)


def num(v) -> str:
    try:
        return f"{int(v):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def initials(nome: str | None) -> str:
    if not nome:
        return "?"
    parts = [p for p in nome.replace(".", " ").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def party_color(party: str | None) -> str:
    """Cor determinística por partido (estável entre páginas)."""
    if not party:
        return _PARTY_COLORS[3]
    return _PARTY_COLORS[sum(ord(c) for c in party) % len(_PARTY_COLORS)]


def avatar_bg(color: str) -> str:
    if "green" in color:
        return "var(--green-100)"
    if "clay" in color:
        return "var(--clay-100)"
    if "petro" in color:
        return "var(--petro-100)"
    return "var(--amber-100)"


def avatar_fg(color: str) -> str:
    if "green" in color:
        return "var(--green-700)"
    if "clay" in color:
        return "var(--clay-700)"
    if "petro" in color:
        return "var(--petro-700)"
    return "var(--amber-700)"


def vote_kind(voto: str | None) -> str:
    """Mapeia o texto do voto para a classe do VoteBadge (sim/nao/abs/aus)."""
    v = (voto or "").strip().lower()
    if v == "sim":
        return "sim"
    if v in ("não", "nao"):
        return "nao"
    if "absten" in v:
        return "abs"
    if "obstru" in v:
        return "abs"
    return "aus"


VOTE_LABEL = {"sim": "Votou Sim", "nao": "Votou Não", "abs": "Absteve-se", "aus": "Ausente"}
VOTE_ICON = {"sim": "check", "nao": "x", "abs": "minus", "aus": "user-x"}
