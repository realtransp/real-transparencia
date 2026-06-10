"""Migra os dados do SQLite local para um Postgres (ex.: Railway).

Uso:
  SOURCE_URL="sqlite:///resumo_real.db" \
  DEST_URL="postgresql+psycopg://user:pass@host:port/db" \
  uv run python migrate_to_postgres.py

Cria o schema no destino e copia todas as tabelas em lotes.
"""
from __future__ import annotations

import os
import time

from sqlalchemy import String, Text, create_engine, insert, select

from app.db import metadata

# Postgres valida o tamanho de VARCHAR (SQLite não). Para a migração não quebrar
# com textos longos, usamos TEXT em todas as colunas de string no destino.
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


def main() -> None:
    src = create_engine(SOURCE_URL, future=True)
    dst = create_engine(DEST_URL, future=True)

    print("→ recriando schema no destino (TEXT em strings)…")
    metadata.drop_all(dst)
    metadata.create_all(dst)

    for table in metadata.sorted_tables:
        with src.connect() as sc:
            total = sc.execute(select(table)).rowcount  # pode ser -1 em sqlite
        # limpa destino e copia
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

    print("✔ migração concluída.")


if __name__ == "__main__":
    main()
