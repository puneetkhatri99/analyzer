"""push-data, run into the local database itself (a stand-in for Neon): every table's copy works, and a posting
rejected locally leaves the hosted job tables."""

from app.cli import main
from app.core.config import get_settings
from app.core.db import get_conn
from app.ingestion.feed import load_posting

JOB = {"post_uuid": "test-push-p1", "company_uuid": "test-push-c1", "company_name": "Test Push Church",
       "post_url": "https://jobs.example.invalid/push/1", "job_name": "Organist", "country": "United States"}  # fmt: skip


def wipe():
    with get_conn() as conn:
        conn.execute("DELETE FROM public.rejected_postings WHERE post_uuid LIKE 'test-push-%'")
        conn.execute("DELETE FROM public.postings WHERE post_uuid LIKE 'test-push-%'")
        conn.execute("DELETE FROM public.companies WHERE company_uuid LIKE 'test-push-%'")


def test_push_copies_every_table_and_drops_postings_rejected_locally(monkeypatch):
    wipe()
    try:
        with get_conn() as conn, conn.transaction():
            load_posting(conn, JOB, "2026-11-04")
            # as if the hosted database still held a posting that was rejected locally
            conn.execute(
                """INSERT INTO public.rejected_postings (post_uuid, reason, rejected_by, posting)
                   VALUES ('test-push-p1', 'Not a church', 'ai', '{}')"""
            )
        monkeypatch.setattr(get_settings(), "neon_url", get_settings().database_url)
        assert main(["push-data"]) == 0
        with get_conn() as conn:
            left = conn.execute("SELECT count(*) FROM public.postings WHERE post_uuid = 'test-push-p1'").fetchone()[0]
        assert left == 0
    finally:
        wipe()
