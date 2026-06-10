"""Migra SÓ as tabelas de proposições (produção legislativa) para o Postgres do Railway.

Não toca nas demais tabelas — cria as que faltam (proposicoes, proposicao_autores)
e copia as linhas. Idempotente: limpa o destino dessas duas tabelas antes de copiar.

Uso:
  DEST_URL="postgresql://user:pass@host:port/railway" \
  uv run python migrate_proposicoes.py
"""
from __future__ import annotations

import os
import time

from sqlalchemy import String, Text, create_engine, insert, select

from app.db import metadata, proposicao_autores, proposicoes

# Postgres valida VARCHAR; usa TEXT nas strings p/ não quebrar com textos longos.
for _t in metadata.tables.values():
    for _c in _t.columns:
        if isinstance(_c.type, String):
            _c.type = Text()

SOURCE_URL = os.environ.get("SOURCE_URL", "sqlite:///resumo_real.db")
DEST_URL = os.environ["DEST_URL"]
if DEST_URL.startswith("postgres://"):
    DEST_URL = DEST_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DEST_URL.startswith("postgresql://"):
    DEST_URL = DEST_URL.replace("postgresql://", "postgresql+psycopg://", 1)

CHUNK = 5000
TABELAS = [proposicoes, proposicao_autores]


def main() -> None:
    src = create_engine(SOURCE_URL, future=True)
    dst = create_engine(DEST_URL, future=True)

    print("→ criando tabelas que faltam no destino (não mexe nas existentes)…")
    metadata.create_all(dst, tables=TABELAS)

    for table in TABELAS:
        with dst.begin() as dc:
            dc.execute(table.delete())
        t0 = time.time()
        n = 0
        with src.connect() as sc:
            result = sc.execution_options(stream_results=True).execute(select(table))
            while True:
                rows = result.fetchmany(CHUNK)
                if not rows:
                    break
                payload = [dict(r._mapping) for r in rows]
                with dst.begin() as dc:
                    dc.execute(insert(table), payload)
                n += len(payload)
                print(f"   {table.name}: {n} linhas…", end="\r")
        print(f"✔ {table.name}: {n} linhas em {time.time()-t0:.1f}s" + " " * 20)

    print("✔ migração de proposições concluída.")


if __name__ == "__main__":
    main()
