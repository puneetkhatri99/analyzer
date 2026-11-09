"""Copy the BizDev tables and job-status checks from the local database to the hosted one (Neon).

Usage (from the server/ directory; use Neon's direct URL, not the -pooler one):
  NEON_URL="postgresql://..." python -m pipeline.push_data

Creates the tables if missing (database/sources.sql), then replaces their rows with the local rows.
Everything runs in one transaction: if any step fails, the hosted database is left unchanged.
The feed tables (postings, companies, posting_snapshots) are not touched; they must already match.
"""
import os
import sys
from pathlib import Path

import psycopg

from app.db import get_conn

TABLES = ["church_jobs", "nonprofit_jobs", "posting_checks"]
SCHEMA = Path(__file__).resolve().parent.parent / "database" / "sources.sql"


def main():
    target_url = os.environ.get("NEON_URL")
    if not target_url:
        sys.exit("Set NEON_URL to the hosted database's direct connection string.")

    with get_conn() as src, psycopg.connect(target_url) as dst:  # dst: one transaction, committed on success
        dst.execute(SCHEMA.read_text(encoding="utf-8"))
        for table in TABLES:
            cols = [r[0] for r in src.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s"
                " ORDER BY ordinal_position", (table,))]
            col_list = ", ".join(cols)
            dst.execute(f"TRUNCATE public.{table}")
            with src.cursor().copy(f"COPY public.{table} ({col_list}) TO STDOUT") as out, \
                 dst.cursor().copy(f"COPY public.{table} ({col_list}) FROM STDIN") as into:
                for chunk in out:
                    into.write(chunk)
            local = src.execute(f"SELECT count(*) FROM public.{table}").fetchone()[0]
            remote = dst.execute(f"SELECT count(*) FROM public.{table}").fetchone()[0]
            if local != remote:
                raise RuntimeError(f"{table}: copied {remote} rows but local has {local}")
            print(f"{table}: {remote} rows")
        for table in ("postings", "companies", "posting_snapshots"):
            print(f"{table} (not copied): local {src.execute(f'SELECT count(*) FROM public.{table}').fetchone()[0]},"
                  f" hosted {dst.execute(f'SELECT count(*) FROM public.{table}').fetchone()[0]}")
    print("Done: hosted database updated.")


if __name__ == "__main__":
    main()
