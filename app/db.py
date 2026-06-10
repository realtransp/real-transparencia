"""Banco de dados: engine + esquema (SQLAlchemy Core, portável SQLite/Postgres)."""
from __future__ import annotations

from typing import Iterable, Sequence

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    func,
    insert,
    select,
    text,
)

from .config import DATABASE_URL, IS_SQLITE

engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=not IS_SQLITE)
metadata = MetaData()

if IS_SQLITE:
    # WAL: leituras (servidor web) não travam durante escritas (backfill/ingestão).
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=8000")
        cur.close()

deputados = Table(
    "deputados", metadata,
    Column("id", Integer, primary_key=True, autoincrement=False),
    Column("cpf", String(11), index=True),
    Column("nome", String(255)),
    Column("nome_eleitoral", String(255)),
    Column("sigla_partido", String(20), index=True),
    Column("sigla_uf", String(2), index=True),
    Column("url_foto", String(500)),
    Column("situacao", String(50)),
    Column("email", String(255)),
    Column("telefone", String(40)),  # telefone do gabinete (DDD 61)
)

despesas = Table(
    "despesas", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("deputado_id", Integer, index=True),
    Column("ano", Integer, index=True),
    Column("mes", Integer),
    Column("tipo_despesa", String(255), index=True),
    Column("fornecedor_nome", Text),
    Column("fornecedor_cnpj_cpf", String(20), index=True),
    Column("valor_liquido", Float),
    Column("data_documento", Date),
    Column("url_documento", String(500)),
)

votacoes = Table(
    "votacoes", metadata,
    Column("id", String(40), primary_key=True),
    Column("data", Date, index=True),
    Column("sigla_orgao", String(20)),
    Column("descricao", Text),       # texto procedimental da Câmara
    Column("proposicao", Text),
    Column("aprovacao", Integer),    # 1 aprovada, 0 rejeitada
    Column("votos_sim", Integer),
    Column("votos_nao", Integer),
    Column("votos_outros", Integer),
    Column("objeto", String(60)),    # ex.: "PEC 31/2007"
    Column("ementa", Text),          # assunto real da proposição (formal)
    Column("titulo_ia", String(180)),  # manchete curta e amigável (gerada por IA)
)

votos = Table(
    "votos", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("votacao_id", String(40), index=True),
    Column("deputado_id", Integer, index=True),
    Column("voto", String(40)),
)

orientacoes = Table(
    "orientacoes", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("votacao_id", String(40), index=True),
    Column("sigla_partido", String(40)),
    Column("orientacao", String(40)),
)

presenca = Table(
    "presenca", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("deputado_id", Integer, index=True),
    Column("evento_id", BigInteger),
    Column("data", Date),
    Column("ano", Integer, index=True),
    Column("descricao_evento", String(255)),
    Column("presente", Boolean),
)

# Frequência OFICIAL em plenário, por dia, com justificativa de ausência.
# Fonte: web service SitCamaraWS ListarPresencasDia (XML oficial da Câmara).
# frequencia: 'presenca' | 'ausencia_justificada' | 'ausencia' (sem justificativa)
presenca_dia = Table(
    "presenca_dia", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("deputado_id", Integer, index=True),
    Column("data", Date, index=True),
    Column("ano", Integer, index=True),
    Column("frequencia", String(30), index=True),
    Column("justificativa", String(255)),  # motivo oficial declarado; NULL se não houver
)

# Proposições (projetos apresentados pelos deputados): produção legislativa.
proposicoes = Table(
    "proposicoes", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=False),
    Column("sigla_tipo", String(20), index=True),   # PL, PEC, PLP, PDL...
    Column("numero", Integer),
    Column("ano", Integer, index=True),
    Column("descricao_tipo", String(120)),
    Column("ementa", Text),
    Column("data_apresentacao", Date, index=True),
    Column("url_inteiro_teor", String(600)),
    Column("ultimo_status", Text),
    Column("situacao", String(120), index=True),  # descricaoSituacao (limpo): Tramitando/Norma/Arquivada
)

proposicao_autores = Table(
    "proposicao_autores", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("proposicao_id", BigInteger, index=True),
    Column("deputado_id", Integer, index=True),
    Column("ano", Integer, index=True),       # ano de apresentação (p/ idempotência)
    Column("ordem", Integer),                  # ordem de assinatura
    Column("proponente", Integer),             # 1 = autor principal
)

# Eleições (TSE), ligadas ao deputado por CPF.
tse_candidatos = Table(
    "tse_candidatos", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ano_eleicao", Integer, index=True),
    Column("cpf", String(11), index=True),
    Column("nome", String(255)),
    Column("sigla_partido", String(40)),
    Column("sigla_uf", String(2)),
    Column("cargo", String(60)),
    Column("situacao", String(120)),
    Column("votos", Integer),
)

tse_doacoes = Table(
    "tse_doacoes", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ano_eleicao", Integer, index=True),
    Column("cpf_candidato", String(11), index=True),
    Column("doador", Text),
    Column("doador_documento", String(20)),
    Column("valor", Float),
)

# Sugestões anônimas dos visitantes (sem nome nem dado pessoal).
sugestoes = Table(
    "sugestoes", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("texto", Text),
    Column("pagina", String(300)),
    Column("criado_em", DateTime, server_default=func.now()),
)

# Cache de resumos gerados pelo Grok.
resumos_ia = Table(
    "resumos_ia", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("entidade_tipo", String(40), index=True),  # 'votacao' | 'deputado'
    Column("entidade_id", String(40), index=True),
    Column("modelo", String(60)),
    Column("texto", Text),
    Column("gerado_em", DateTime, server_default=func.now()),
)


def init_db() -> None:
    """Cria as tabelas se não existirem e aplica migrações leves de colunas."""
    metadata.create_all(engine)
    _ensure_columns(votacoes, ["votos_sim", "votos_nao", "votos_outros", "objeto", "ementa", "titulo_ia"])
    _ensure_columns(deputados, ["telefone"])
    _ensure_columns(proposicoes, ["situacao"])


_COL_SQL = {
    "votos_sim": "INTEGER", "votos_nao": "INTEGER", "votos_outros": "INTEGER",
    "objeto": "VARCHAR(60)", "ementa": "TEXT", "telefone": "VARCHAR(40)",
    "titulo_ia": "VARCHAR(180)", "situacao": "VARCHAR(120)",
}


def _ensure_columns(table: Table, cols: list[str]) -> None:
    """Adiciona colunas que ainda não existem (SQLite e Postgres)."""
    from sqlalchemy import inspect as _inspect

    insp = _inspect(engine)
    try:
        existing = {c["name"] for c in insp.get_columns(table.name)}
    except Exception:
        return
    with engine.begin() as conn:
        for col in cols:
            if col not in existing:
                conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN {col} {_COL_SQL[col]}'))


def bulk_insert(table: Table, rows: Sequence[dict], chunk: int = 1000) -> int:
    """Insere linhas em lotes. Funciona em SQLite e Postgres."""
    rows = list(rows)
    if not rows:
        return 0
    with engine.begin() as conn:
        for i in range(0, len(rows), chunk):
            conn.execute(insert(table), rows[i : i + chunk])
    return len(rows)


def replace_table(table: Table, rows: Iterable[dict], chunk: int = 1000) -> int:
    """Apaga tudo e regrava (usado em ingestões idempotentes pequenas)."""
    rows = list(rows)
    with engine.begin() as conn:
        conn.execute(table.delete())
    return bulk_insert(table, rows, chunk)


def delete_where(table: Table, **eq) -> None:
    """Apaga linhas que casam com igualdades simples (idempotência por ano etc.)."""
    cond = None
    for k, v in eq.items():
        c = table.c[k] == v
        cond = c if cond is None else (cond & c)
    with engine.begin() as conn:
        conn.execute(table.delete().where(cond) if cond is not None else table.delete())


def replace_where_atomic(table: Table, where_eq: dict, rows: Iterable[dict], chunk: int = 2000) -> int:
    """Apaga as linhas que casam com `where_eq` e insere `rows` numa ÚNICA transação.

    Atômico: se a iteração de `rows` falhar no meio (download truncado, 404,
    linha malformada), a transação inteira é desfeita e os dados antigos
    permanecem. Elimina tanto a janela em que a tabela fica vazia entre o delete
    e o insert quanto o risco de apagar um ano e não conseguir reinseri-lo.
    `rows` pode ser um gerador (streaming) — só é materializado em lotes de `chunk`.
    """
    cond = None
    for k, v in where_eq.items():
        c = table.c[k] == v
        cond = c if cond is None else (cond & c)
    n = 0
    with engine.begin() as conn:
        conn.execute(table.delete().where(cond) if cond is not None else table.delete())
        batch: list[dict] = []
        for row in rows:
            batch.append(row)
            if len(batch) >= chunk:
                conn.execute(insert(table), batch)
                n += len(batch)
                batch = []
        if batch:
            conn.execute(insert(table), batch)
            n += len(batch)
    return n


def merge_by_pk(table: Table, rows: Sequence[dict], pk: str = "id",
                update_cols: set[str] | None = None) -> int:
    """Upsert portável (SQLite/Postgres): atualiza as linhas existentes e insere as novas.

    Nas linhas que já existem, só escreve as colunas em `update_cols` (ou todas,
    menos a PK, se None), PRESERVANDO as demais — ex.: ementa/objeto/titulo_ia de
    uma votação enriquecida por outro processo não são sobrescritas. Usado na
    atualização incremental diária para não destruir o histórico.
    """
    rows = [r for r in rows if r.get(pk) is not None]
    if not rows:
        return 0
    ids = [r[pk] for r in rows]
    with engine.begin() as conn:
        existing: set = set()
        for i in range(0, len(ids), 500):
            res = conn.execute(select(table.c[pk]).where(table.c[pk].in_(ids[i : i + 500])))
            existing.update(r[0] for r in res)
        to_insert = []
        for r in rows:
            if r[pk] in existing:
                vals = {k: v for k, v in r.items()
                        if k != pk and (update_cols is None or k in update_cols)}
                if vals:
                    conn.execute(table.update().where(table.c[pk] == r[pk]).values(**vals))
            else:
                to_insert.append(r)
        for i in range(0, len(to_insert), 1000):
            conn.execute(insert(table), to_insert[i : i + 1000])
    return len(rows)
