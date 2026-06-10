"""Acesso às fontes de dados: API REST da Câmara e arquivos em massa (CSV/ZIP)."""
from __future__ import annotations

import csv
import io
import time
import zipfile
from datetime import date
from typing import Iterator

import httpx

API_BASE = "https://dadosabertos.camara.leg.br/api/v2"
ARQUIVOS = "https://dadosabertos.camara.leg.br/arquivos"
CEAP_BASE = "https://www.camara.leg.br/cotas"

_HEADERS = {"Accept": "application/json", "User-Agent": "resumo-real/0.1"}


# --------------------------------------------------------------------------- API
def api_get(path: str, params: dict | None = None, retries: int = 3) -> dict:
    url = f"{API_BASE}{path}"
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            r = httpx.get(url, params=params, headers=_HEADERS, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as exc:  # noqa: BLE001 - retry simples
            last_exc = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Falha ao buscar {url}: {last_exc}")


def api_paginate(path: str, params: dict | None = None, max_pages: int | None = None) -> Iterator[dict]:
    """Itera sobre todos os itens de um endpoint paginado da API v2."""
    params = dict(params or {})
    params.setdefault("itens", 100)
    params.setdefault("pagina", 1)
    page = 0
    while True:
        payload = api_get(path, params)
        for item in payload.get("dados", []):
            yield item
        # segue o link 'next' se existir
        nxt = next((l for l in payload.get("links", []) if l.get("rel") == "next"), None)
        page += 1
        if not nxt or (max_pages and page >= max_pages):
            break
        params["pagina"] += 1


# --------------------------------------------------------------------- arquivos
def _decode(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def download_csv_rows(
    url: str,
    sep: str = ";",
    skip_contains: list[str] | None = None,
    include_only: list[str] | None = None,
) -> Iterator[dict]:
    """Baixa um CSV (ou ZIP) e itera linhas como dicts.

    Um ZIP pode conter vários CSVs (ex.: TSE entrega um por UF) — todos são lidos.
    `skip_contains`: ignora membros do ZIP cujo nome contenha qualquer um dos termos
    (ex.: arquivos consolidados "_BRASIL"/"_BR" do TSE, que duplicariam os por UF).
    `include_only`: se informado, lê SÓ os membros cujo nome contenha algum dos termos
    (útil em ZIPs grandes que misturam receitas/despesas, como prestação de contas TSE).
    """
    skip = [s.upper() for s in (skip_contains or [])]
    keep = [s.upper() for s in (include_only or [])]
    with httpx.stream("GET", url, headers={"User-Agent": "resumo-real/0.1"}, timeout=600, follow_redirects=True) as r:
        r.raise_for_status()
        raw = r.read()
    if url.endswith(".zip") or raw[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            csvs = [n for n in zf.namelist() if n.lower().endswith(".csv")] or zf.namelist()
            for name in csvs:
                up = name.upper()
                if any(s in up for s in skip):
                    continue
                if keep and not any(s in up for s in keep):
                    continue
                yield from _iter_csv(zf.read(name), sep)
    else:
        yield from _iter_csv(raw, sep)


def _iter_csv(raw: bytes, sep: str) -> Iterator[dict]:
    reader = csv.DictReader(io.StringIO(_decode(raw)), delimiter=sep)
    for row in reader:
        yield row


# ------------------------------------------------------------------- utilidades
def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    value = value.strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return date(*time.strptime(value, fmt)[:3])
        except ValueError:
            continue
    return None


def parse_float(value: str | None) -> float:
    if value is None:
        return 0.0
    value = str(value).strip().replace("R$", "").replace(" ", "")
    if not value:
        return 0.0
    # lida com formato BR "1.234,56" e US "1234.56"
    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return 0.0


def only_digits(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())
