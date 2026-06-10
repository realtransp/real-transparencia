"""CLI de ingestão.

Exemplos:
  uv run python -m app.ingest sample            # preview rápido (via API)
  uv run python -m app.ingest backfill --de 2008 --ate 2026
  uv run python -m app.ingest daily             # atualização incremental (cron)
"""
from __future__ import annotations

import argparse
import datetime as _dt
import logging

from . import camara, tse
from ..db import deputados, engine, init_db
from sqlalchemy import select

# Ano corrente, derivado da data (não chumbado): evita que o cron pare de
# ingerir o ano novo na virada e que o backfill tenha um teto desatualizado.
ANO_ATUAL = _dt.date.today().year

log = logging.getLogger("ingest")


def _deputado_ids(limit: int | None = None) -> list[int]:
    with engine.connect() as conn:
        q = select(deputados.c.id).order_by(deputados.c.id)
        if limit:
            q = q.limit(limit)
        return [r[0] for r in conn.execute(q)]


def cmd_sample(args: argparse.Namespace) -> None:
    init_db()
    print("→ deputados (API)...")
    n = camara.load_deputados()
    print(f"  {n} deputados")

    ids = _deputado_ids(limit=args.deputados)
    anos = [ANO_ATUAL, ANO_ATUAL - 1]
    print(f"→ despesas (API) de {len(ids)} deputados em {anos}...")
    nd = camara.load_despesas_api(ids, anos)
    print(f"  {nd} despesas")

    print(f"→ votações recentes (API, {args.paginas} página(s)) + votos...")
    nv = camara.load_votacoes_api(limite_paginas=args.paginas)
    print(f"  {nv} votações")
    print("✔ amostra pronta. Rode: uv run uvicorn app.main:app --reload")


def cmd_backfill(args: argparse.Namespace) -> None:
    init_db()
    print("→ deputados (API, com CPF p/ casar com TSE)...")
    camara.load_deputados(enrich_cpf=True)

    for ano in range(args.de, args.ate + 1):
        print(f"=== {ano} ===")
        for nome, fn in (
            ("despesas", camara.load_despesas_bulk),
            ("votações", camara.load_votacoes_bulk),
            ("votos", camara.load_votos_bulk),
            ("orientações", camara.load_orientacoes_bulk),
            ("presença", camara.load_presenca_bulk),
        ):
            try:
                print(f"  {nome}: {fn(ano)} linhas")
            except Exception as exc:  # noqa: BLE001
                print(f"  {nome}: pulado ({exc})")
        # proposições (produção legislativa) — só a legislatura atual (2023+)
        if ano >= 2023:
            try:
                np_, na_ = camara.load_proposicoes_bulk(ano)
                print(f"  proposições: {np_} props, {na_} vínculos autor")
            except Exception as exc:  # noqa: BLE001
                print(f"  proposições: pulado ({exc})")

    print("→ enriquecendo votações com o assunto (ementa) via API...")
    try:
        print(f"  ementas: {camara.enrich_votacoes(limite=args.enrich)}")
    except Exception as exc:  # noqa: BLE001
        print(f"  ementas: pulado ({exc})")

    if not args.sem_tse:
        for ano in range(args.de, args.ate + 1):
            if ano % 2 == 0 and ano >= 2002:  # anos de eleição
                try:
                    print(f"  TSE {ano}: {tse.load_candidatos(ano)} candidatos, {tse.load_doacoes(ano)} doações")
                except Exception as exc:  # noqa: BLE001
                    print(f"  TSE {ano}: pulado ({exc})")
                try:
                    print(f"  TSE {ano} votos recebidos: {tse.load_votos_recebidos(ano)} candidatos")
                except Exception as exc:  # noqa: BLE001
                    print(f"  TSE {ano} votos recebidos: pulado ({exc})")
    print("✔ backfill concluído.")


def _step(nome: str, fn) -> int:
    """Roda um passo da ingestão. Retorna 0 se ok/indisponível, 1 se falhou.

    Um 404 (arquivo do ano ainda não publicado) é tratado como indisponível, não
    como falha — não polui o exit code do cron.
    """
    try:
        res = fn()
        log.info("  %s: %s", nome, res)
        return 0
    except Exception as exc:  # noqa: BLE001
        resp = getattr(exc, "response", None)
        if resp is not None and getattr(resp, "status_code", None) == 404:
            log.warning("  %s: arquivo ainda indisponível (404), pulado", nome)
            return 0
        log.warning("  %s: FALHOU (%s)", nome, exc)
        return 1


def cmd_daily(args: argparse.Namespace) -> None:
    """Atualização incremental (cron diário). Não-destrutiva e atômica.

    Diferente do backfill, não regrava tabelas inteiras: faz upsert do roster
    (preserva CPF/telefone), atualiza só as votações recentes por id (preserva o
    histórico) e regrava despesas/proposições do ano numa única transação cada.
    """
    init_db()
    ano = args.ano or ANO_ATUAL
    log.info("atualização diária (%s)", ano)
    falhas = 0
    falhas += _step("deputados", lambda: camara.upsert_deputados())
    falhas += _step("despesas", lambda: camara.load_despesas_bulk(ano))
    falhas += _step("votações", lambda: camara.load_votacoes_recentes(limite_paginas=2))
    falhas += _step("proposições", lambda: camara.load_proposicoes_bulk(ano))
    falhas += _step("ementas", lambda: camara.enrich_votacoes(limite=60))
    if falhas:
        log.error("diário concluído com %d passo(s) com falha", falhas)
        raise SystemExit(1)
    log.info("diário concluído.")


def cmd_resumos(args: argparse.Namespace) -> None:
    """Pré-gera e cacheia resumos das votações recentes do feed (throttled)."""
    import time
    import app.queries as Q
    from app.analysis import summaries, llm

    init_db()
    if not llm.disponivel():
        print("nenhum provedor de IA configurado")
        return
    feed = Q.feed_items(args.limite)
    ok = falhou = 0
    for it in feed:
        v = Q.get_votacao(it["id"])
        try:
            summaries.resumo_votacao(v, Q.votacao_placar(v["id"]), Q.votacao_orientacoes(v["id"]))
            ok += 1
            print(f"  ✓ {it['id']}")
        except llm.RateLimited:
            falhou += 1
            print(f"  ⏳ rate limit em {it['id']} — pausando mais")
            time.sleep(args.sleep * 4)
        except Exception as exc:  # noqa: BLE001
            falhou += 1
            print(f"  ✗ {it['id']}: {str(exc)[:80]}")
        time.sleep(args.sleep)
    print(f"resumos: {ok} gerados, {falhou} falharam")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(prog="app.ingest", description="Ingestão Resumo Real")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("sample", help="preview rápido via API")
    s.add_argument("--deputados", type=int, default=60, help="quantos deputados p/ despesas")
    s.add_argument("--paginas", type=int, default=2, help="páginas de votações (100/pág)")
    s.set_defaults(func=cmd_sample)

    b = sub.add_parser("backfill", help="histórico completo via arquivos em massa")
    b.add_argument("--de", type=int, default=2008)
    b.add_argument("--ate", type=int, default=ANO_ATUAL)
    b.add_argument("--sem-tse", action="store_true")
    b.add_argument("--enrich", type=int, default=300, help="quantas votações enriquecer com ementa")
    b.set_defaults(func=cmd_backfill)

    def _cmd_enrich(a):
        init_db()
        print(f"ementas: {camara.enrich_votacoes(limite=a.limite)}")

    e = sub.add_parser("enrich", help="busca o assunto (ementa) das votações via API")
    e.add_argument("--limite", type=int, default=300)
    e.set_defaults(func=_cmd_enrich)

    r = sub.add_parser("resumos", help="pré-gera resumos de IA (com pausa p/ respeitar rate limit)")
    r.add_argument("--limite", type=int, default=20)
    r.add_argument("--sleep", type=float, default=3.0)
    r.set_defaults(func=cmd_resumos)

    d = sub.add_parser("daily", help="atualização incremental (cron)")
    d.add_argument("--ano", type=int, default=None)
    d.set_defaults(func=cmd_daily)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
