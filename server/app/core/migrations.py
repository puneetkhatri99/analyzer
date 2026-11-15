"""Versioned schema migrations: numbered SQL files in server/migrations/ (0001_name.sql), applied in order, once each.

Each file runs in its own transaction together with its row in public.schema_migrations, under a transaction-level
advisory lock, so two deploys starting at once can't apply the same file twice. That lock (unlike a session lock)
is also safe through Neon's transaction pooler. A file whose text changed after it was applied is refused: write a
new migration instead of editing an old one.
"""

import argparse
import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import psycopg

from app.core.config import SERVER_DIR
from app.core.db import connect
from app.core.logs import script_log

MIGRATIONS_DIR = SERVER_DIR / "migrations"
LOCK_KEY = 7_314_029  # any constant; shared by every process that migrates this database
FILE_RE = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")

log = logging.getLogger("migrate")


class MigrationError(Exception):
    pass


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    sql: str

    @property
    def label(self) -> str:
        return f"{self.version:04d}_{self.name}"

    @property
    def checksum(self) -> str:
        return hashlib.sha256(self.sql.encode()).hexdigest()


def discover(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    migrations = []
    for path in sorted(directory.glob("*.sql")):
        match = FILE_RE.match(path.name)
        if not match:
            raise MigrationError(f"Migration file names look like 0001_name.sql, not {path.name}")
        migrations.append(Migration(int(match[1]), match[2], path.read_text(encoding="utf-8")))
    versions = [m.version for m in migrations]
    if len(versions) != len(set(versions)):
        raise MigrationError("Two migration files share a version number")
    return migrations


def migrate(
    conn: psycopg.Connection, *, dry_run: bool = False, directory: Path = MIGRATIONS_DIR, up_to: int | None = None
) -> list[Migration]:
    """Apply every pending migration; returns them (with dry_run, the ones that would be applied).
    up_to: stop after this version, so a destructive later file waits for a deliberate manual run.
    `conn` must be in autocommit mode so each migration gets its own transaction."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS public.schema_migrations (
               version     integer PRIMARY KEY,
               name        text NOT NULL,
               checksum    text NOT NULL,
               applied_at  timestamptz NOT NULL DEFAULT now()
           )"""
    )
    pending = []
    for migration in discover(directory):
        if up_to is not None and migration.version > up_to:
            log.info("Held back (above --up-to %d): %s", up_to, migration.label)
            continue
        with conn.transaction():
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_KEY,))
            row = conn.execute(
                "SELECT checksum FROM public.schema_migrations WHERE version = %s", (migration.version,)
            ).fetchone()
            if row:
                if row[0] != migration.checksum:
                    raise MigrationError(
                        f"{migration.label}.sql changed after it was applied. Add a new migration instead."
                    )
                continue
            pending.append(migration)
            if dry_run:
                continue
            conn.execute(migration.sql)
            conn.execute(
                "INSERT INTO public.schema_migrations (version, name, checksum) VALUES (%s, %s, %s)",
                (migration.version, migration.name, migration.checksum),
            )
        log.info("%s %s", "Pending:" if dry_run else "Applied:", migration.label)
    return pending


def register(commands: argparse._SubParsersAction) -> None:
    parser = commands.add_parser("migrate", help="apply pending database migrations")
    parser.add_argument("--dry-run", action="store_true", help="list pending migrations without applying them")
    parser.add_argument("--up-to", type=int, metavar="VERSION", help="apply only migrations up to this version")
    parser.set_defaults(handler=_run)


def _run(args: argparse.Namespace) -> int:
    script_log("migrate")
    with connect() as conn:
        done = migrate(conn, dry_run=args.dry_run, up_to=args.up_to)
    log.info("%d migration(s) %s", len(done), "pending" if args.dry_run else "applied")
    return 0
