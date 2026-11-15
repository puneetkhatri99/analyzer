"""Database connections.

The API opens a connection pool at startup (open_pool); scripts and tests run without one and get a fresh connection
per get_conn(). Connections are in autocommit mode: wrap multi-statement writes in `conn.transaction()`.

Tables are always schema-qualified (public.x): through Neon's transaction pooler a shared session can carry another
client's search_path, and unqualified names then fail.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg_pool import ConnectionPool

from app.core.config import get_settings

_pool: ConnectionPool | None = None


def _database_url() -> str:
    url = get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is not set. Copy server/.env.example to server/.env and fill it in.")
    return url


def connect(url: str | None = None) -> psycopg.Connection:
    """A new autocommit connection, outside the pool."""
    return psycopg.connect(url or _database_url(), autocommit=True)


def open_pool(max_size: int = 10) -> None:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            _database_url(),
            kwargs={"autocommit": True},
            min_size=1,
            max_size=max_size,
            check=ConnectionPool.check_connection,  # Neon drops idle connections; test each one before use
            open=True,
        )


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    if _pool is not None:
        with _pool.connection() as conn:
            yield conn
    else:
        with connect() as conn:
            yield conn
