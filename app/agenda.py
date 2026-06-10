"""Próximas votações (pauta): dados AO VIVO da API da Câmara, com cache em memória.

A pauta muda diariamente e não vem nos arquivos em massa; buscamos sob demanda e
guardamos por alguns minutos para não bater na API a cada acesso. Falha de rede é
silenciosa (devolve lista vazia), o bloco simplesmente não aparece.
"""
from __future__ import annotations

import datetime as dt
import time

import httpx

_API = "https://dadosabertos.camara.leg.br/api/v2"
_H = {"Accept": "application/json", "User-Agent": "resumo-real/0.1"}
_TTL = 1800  # 30 min
_cache: dict = {"t": 0.0, "data": None}


def _get(url: str, params: dict | None = None) -> list:
    r = httpx.get(url, params=params, headers=_H, timeout=12)
    r.raise_for_status()
    return r.json().get("dados", [])


def proximas_votacoes(dias: int = 12, max_eventos: int = 6) -> list[dict]:
    now = time.time()
    if _cache["data"] is not None and now - _cache["t"] < _TTL:
        return _cache["data"]
    out: list[dict] = []
    try:
        hoje = dt.date.today()
        fim = hoje + dt.timedelta(days=dias)
        evs = _get(f"{_API}/eventos", {
            "dataInicio": hoje.isoformat(), "dataFim": fim.isoformat(),
            "ordem": "ASC", "ordenarPor": "dataHoraInicio", "itens": 80})
        delib = [e for e in evs if "eliberativ" in (e.get("descricaoTipo") or "")]
        for e in delib:
            if len(out) >= max_eventos:
                break
            try:
                pauta = _get(f"{_API}/eventos/{e['id']}/pauta")
            except Exception:
                pauta = []
            itens, seen = [], set()
            for it in pauta:
                pr = it.get("proposicao_") or {}
                if not pr.get("siglaTipo"):
                    continue
                rot = f"{pr.get('siglaTipo')} {pr.get('numero')}/{pr.get('ano')}"
                if rot in seen:
                    continue
                seen.add(rot)
                itens.append(dict(rotulo=rot, id=pr.get("id"),
                                  ementa=(pr.get("ementa") or "")[:160]))
                if len(itens) >= 6:
                    break
            if not itens:
                continue
            orgs = ", ".join(o.get("sigla", "") for o in e.get("orgaos", []) if o.get("sigla"))
            dh = e.get("dataHoraInicio", "") or ""
            out.append(dict(
                data=dh[:10], hora=dh[11:16], orgao=orgs, tipo=e.get("descricaoTipo"),
                plenario=("PLEN" in orgs), n_itens=len(pauta), itens=itens))
        out.sort(key=lambda x: (not x["plenario"], x["data"]))
    except Exception:
        pass
    _cache["t"] = now
    _cache["data"] = out
    return out
