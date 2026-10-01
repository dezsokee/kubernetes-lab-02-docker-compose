"""PostgreSQL persistence layer.

The connection string comes from ``SNIPBOX_DATABASE_URL``. In Docker Compose the
host part is the database's container name (``snipbox-db``), which Docker's
embedded DNS resolves on the shared ``database`` network.

A small connection pool is opened once at startup: FastAPI runs synchronous
endpoints in a thread pool, and each request borrows its own connection.
"""

import os
from datetime import UTC, datetime

from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

DEFAULT_DATABASE_URL = "postgresql://snipbox:snipbox@snipbox-db:5432/snipbox"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snippets (
    id         TEXT PRIMARY KEY,
    title      TEXT NOT NULL,
    language   TEXT NOT NULL,
    content    TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS snippets_created_at ON snippets (created_at DESC);
"""

_pool: ConnectionPool | None = None


def database_url() -> str:
    return os.environ.get("SNIPBOX_DATABASE_URL", DEFAULT_DATABASE_URL)


def database_target() -> str:
    """``host:port/dbname`` only, so /health never leaks the password."""
    info = conninfo_to_dict(database_url())
    return f"{info.get('host')}:{info.get('port', 5432)}/{info.get('dbname')}"


def connect() -> ConnectionPool:
    """Open (once) the pool and make sure the schema exists."""
    global _pool
    if _pool is None:
        pool = ConnectionPool(
            database_url(),
            min_size=1,
            max_size=int(os.environ.get("SNIPBOX_DB_POOL_SIZE", "5")),
            kwargs={"row_factory": dict_row},
            open=False,
        )
        # Blocks until the first connection succeeds, so a database that is
        # still starting up delays the app instead of crashing it.
        pool.open(wait=True, timeout=30)
        with pool.connection() as conn:
            conn.execute(_SCHEMA)
        _pool = pool
    return _pool


def close() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def _as_dict(row: dict) -> dict:
    return {**row, "created_at": row["created_at"].isoformat(timespec="seconds")}


def insert(snippet_id: str, title: str, language: str, content: str) -> dict:
    created_at = datetime.now(UTC).replace(microsecond=0)
    with connect().connection() as conn:
        row = conn.execute(
            "INSERT INTO snippets (id, title, language, content, created_at)"
            " VALUES (%s, %s, %s, %s, %s) RETURNING *",
            (snippet_id, title, language, content, created_at),
        ).fetchone()
    return _as_dict(row)


def get(snippet_id: str) -> dict | None:
    with connect().connection() as conn:
        row = conn.execute(
            "SELECT * FROM snippets WHERE id = %s", (snippet_id,)
        ).fetchone()
    return _as_dict(row) if row is not None else None


def list_all(limit: int, offset: int) -> list[dict]:
    with connect().connection() as conn:
        rows = conn.execute(
            "SELECT * FROM snippets ORDER BY created_at DESC, id"
            " LIMIT %s OFFSET %s",
            (limit, offset),
        ).fetchall()
    return [_as_dict(row) for row in rows]


def delete(snippet_id: str) -> bool:
    with connect().connection() as conn:
        cursor = conn.execute("DELETE FROM snippets WHERE id = %s", (snippet_id,))
    return cursor.rowcount > 0


def count() -> int:
    with connect().connection() as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM snippets").fetchone()["n"]
