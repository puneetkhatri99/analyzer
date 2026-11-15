"""push-data: copy the BizDev tables and job-status checks from the local database to the hosted one (Neon).

  NEON_URL="postgresql://..." python -m app.cli push-data      # Neon's direct URL, not the -pooler one

Local rows are inserted or replace the hosted row with the same key; rows that exist only in the hosted database
(jobs admins added there, collector runs there) are kept. Run `migrate` against both databases first: they must be on
the same migration. Everything runs in one transaction: if any step fails, the hosted database is left unchanged.
The feed tables (postings, companies, posting_snapshots) are not copied; their counts are compared in the log.
"""

import argparse
import logging
from urllib.parse import urlsplit

import psycopg

from app.core.config import get_settings
from app.core.db import connect
from app.core.logs import script_log

TABLES = {"church_jobs": "url_key", "nonprofit_jobs": "url_key", "posting_checks": "post_uuid"}  # table -> primary key
FEED_TABLES = ["postings", "companies", "posting_snapshots"]

log = logging.getLogger("push_data")


def _count(conn: psycopg.Connection, table: str) -> int:
    return conn.execute(f"SELECT count(*) FROM public.{table}").fetchone()[0]


def _columns(conn: psycopg.Connection, table: str) -> list[str]:
    rows = conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s"
        " ORDER BY ordinal_position",
        (table,),
    ).fetchall()
    return [r[0] for r in rows]


def _schema_version(conn: psycopg.Connection) -> int:
    """The newest migration applied to this database; 0 before migrations were set up."""
    if conn.execute("SELECT to_regclass('public.schema_migrations')").fetchone()[0] is None:
        return 0
    return conn.execute("SELECT coalesce(max(version), 0) FROM public.schema_migrations").fetchone()[0]


def register(commands: argparse._SubParsersAction) -> None:
    parser = commands.add_parser("push-data", help="copy BizDev tables and job checks to the hosted database")
    parser.set_defaults(handler=_run)


def _run(args: argparse.Namespace) -> int:
    script_log("push_data")
    target_url = get_settings().neon_url
    if not target_url:
        log.error("Set NEON_URL to the hosted database's direct connection string.")
        return 1
    log.info(
        "Copying %s to %s (one transaction: nothing changes there if any step fails)",
        ", ".join(TABLES),
        urlsplit(target_url).hostname,
    )

    with connect() as src, psycopg.connect(target_url) as dst:  # dst: one transaction, committed on success
        local_version, hosted_version = _schema_version(src), _schema_version(dst)
        if local_version != hosted_version:
            log.error(
                "The databases are on different migrations (local %04d, hosted %04d). "
                "Run `python -m app.cli migrate` against both first.",
                local_version,
                hosted_version,
            )
            return 1
        for table, key in TABLES.items():
            cols = _columns(src, table)
            col_list = ", ".join(cols)
            staging = f"incoming_{table}"
            dst.execute(f"CREATE TEMP TABLE {staging} (LIKE public.{table} INCLUDING DEFAULTS) ON COMMIT DROP")
            with (
                src.cursor().copy(f"COPY public.{table} ({col_list}) TO STDOUT") as out,
                dst.cursor().copy(f"COPY {staging} ({col_list}) FROM STDIN") as into,
            ):
                for chunk in out:
                    into.write(chunk)
            updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != key)
            dst.execute(
                f"INSERT INTO public.{table} ({col_list}) SELECT {col_list} FROM {staging} "
                f"ON CONFLICT ({key}) DO UPDATE SET {updates}"
            )
            local, copied = _count(src, table), dst.execute(f"SELECT count(*) FROM {staging}").fetchone()[0]
            if local != copied:
                raise RuntimeError(f"{table}: copied {copied} rows but local has {local}")
            hosted_only = dst.execute(
                f"SELECT count(*) FROM public.{table} WHERE {key} NOT IN (SELECT {key} FROM {staging})"
            ).fetchone()[0]
            log.info("%s: %d rows copied; %d rows only in the hosted database kept", table, copied, hosted_only)
        for table in FEED_TABLES:
            local, hosted = _count(src, table), _count(dst, table)
            (log.info if local == hosted else log.warning)(
                "%s (not copied): local %d, hosted %d%s",
                table,
                local,
                hosted,
                "" if local == hosted else ": they differ",
            )
    log.info("Done: hosted database updated.")
    return 0
