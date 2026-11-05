import psycopg

from app.config import DATABASE_URL


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set. Copy server/.env.example to server/.env and fill it in.")
    return psycopg.connect(DATABASE_URL, autocommit=True)
