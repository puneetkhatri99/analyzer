"""An editor fills in a church's size and denomination by hand: every job of that employer gets it, viewers can't."""

from app.core.db import get_conn
from app.ingestion.feed import load_posting

KEY = "test-facts.invalid/job/"
EMAIL = "test-facts-editor@example.invalid"


def add_sheet_job(n, org="Zzz Facts Church", city="Dallas"):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO public.church_jobs (url_key, job_url, job_title, org_name, city, state) "
            "VALUES (%s, %s, 'Youth Pastor', %s, %s, 'TX')",
            (f"{KEY}{n}", f"https://{KEY}{n}", org, city),
        )


def sheet(n):
    with get_conn() as conn:
        return conn.execute(
            "SELECT church_size, denomination, church_size_source FROM public.church_jobs WHERE url_key = %s",
            (f"{KEY}{n}",),
        ).fetchone()


def wipe():
    with get_conn() as conn:
        conn.execute("DELETE FROM public.church_jobs WHERE url_key LIKE %s", (KEY + "%",))
        conn.execute("DELETE FROM public.postings WHERE post_uuid LIKE 'test-facts-%'")
        conn.execute("DELETE FROM public.companies WHERE company_uuid LIKE 'test-facts-%'")


def test_an_editor_sets_size_and_denomination_for_every_job_of_the_employer(make_user, sign_in):
    wipe()
    add_sheet_job(1)
    add_sheet_job(2)  # same church
    add_sheet_job(3, city="Austin")  # same name, another city: another church
    try:
        make_user(EMAIL, "a-strong-pass-1", role="viewer")
        viewer, _ = sign_in(EMAIL, "a-strong-pass-1")
        body = {"source": "churches", "id": f"{KEY}1", "church_size": 450, "denomination": "Southern Baptist"}
        assert viewer.patch("/api/admin/employer", json=body).status_code == 403

        make_user(EMAIL, "a-strong-pass-1", role="editor")
        editor, _ = sign_in(EMAIL, "a-strong-pass-1")
        assert editor.patch("/api/admin/employer", json=body).json() == {"jobs": 2}
        # the denomination is stored under its merged name; the size records who entered it
        assert sheet(1) == sheet(2) == (450, "Baptist", f"entered by {EMAIL}")
        assert sheet(3) == (None, None, None)

        only_size = {"source": "churches", "id": f"{KEY}2", "church_size": 500}
        assert editor.patch("/api/admin/employer", json=only_size).status_code == 200
        assert sheet(1)[:2] == (500, "Baptist")  # the denomination stays

        assert editor.patch("/api/admin/employer", json={"source": "churches", "id": f"{KEY}1"}).status_code == 422
        assert editor.patch("/api/admin/employer", json={**body, "id": "nope"}).status_code == 404
        assert editor.patch("/api/admin/employer", json={**body, "church_size": 0}).status_code == 422

        with get_conn() as conn:  # a feed job: its company gets the facts
            load_posting(conn, {"post_uuid": "test-facts-p1", "company_uuid": "test-facts-c1",
                                "company_name": "Zzz Facts Feed Church", "job_name": "Worship Pastor",
                                "region": "TX", "country": "US"}, "2026-11-04")  # fmt: skip
        feed = {"source": "json", "id": "test-facts-p1", "church_size": 1200}
        assert editor.patch("/api/admin/employer", json=feed).json() == {"jobs": 1}
        with get_conn() as conn:
            row = conn.execute(
                "SELECT church_size, church_size_url FROM public.companies WHERE company_uuid = 'test-facts-c1'"
            ).fetchone()
        assert row == (1200, f"entered by {EMAIL}")
    finally:
        wipe()
