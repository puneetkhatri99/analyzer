"""The weekly BizDev sync: new rows are added and old ones left alone, the week marker stops a second run, a failing
link is reported, and Google Sheets links become downloads. The download is replaced; test rows are removed."""

import shutil

import openpyxl
import pytest

from app.core.db import get_conn
from app.ingestion import bizdev_sync as bs
from app.leads.daily_report import get_setting, set_setting

ADMIN = "test-sync-admin@example.invalid"
HEADER = ["First Name", "Last Name", "Contact's Job Title", "Email", "Church/ Organization Name", "City",
          "State (abbreviate)", "Job Title", "Job Post URL", "Church Website URL", "Job Date Posted", "Note"]  # fmt: skip
KEYS = (*bs.URL_KEYS.values(), bs.STATUS_KEY, bs.DONE_KEY, bs.TRIED_KEY)


def workbook(path, n):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(HEADER)
    for i in range(1, n + 1):
        ws.append(["Pat", "Lee", "Pastor", f"pat{i}@test-sync.invalid", f"Test Sync Church {i}", "Dallas", "TX",
                   "Youth Pastor", f"https://jobs.test-sync.invalid/job/{i}", "https://test-sync.invalid", None, None])  # fmt: skip
    wb.save(path)


@pytest.fixture
def clean():
    before = {k: get_setting(k) for k in KEYS}

    def wipe():
        with get_conn() as conn:
            conn.execute("DELETE FROM public.church_jobs WHERE url_key LIKE 'jobs.test-sync.invalid/%'")
            conn.execute("DELETE FROM public.nonprofit_jobs WHERE url_key LIKE 'jobs.test-sync.invalid/%'")
            conn.execute("DELETE FROM public.app_settings WHERE key = ANY(%s)", (list(KEYS),))

    wipe()
    yield
    wipe()
    for key, value in before.items():
        if value is not None:
            set_setting(key, value, by="test")


def count(table="church_jobs"):
    with get_conn() as conn:
        return conn.execute(
            f"SELECT count(*) FROM public.{table} WHERE url_key LIKE 'jobs.test-sync.invalid/%'"
        ).fetchone()[0]


def serve(monkeypatch, tmp_path, sizes):
    """fetch() copies a workbook with sizes[kind] jobs, or raises when the size is an error message."""

    def fake_fetch(link, dest):
        kind = "churches" if "church" in link else "nonprofits"
        size = sizes[kind]
        if isinstance(size, str):
            raise bs.SyncError(size)
        src = tmp_path / f"{kind}-{size}.xlsx"
        workbook(src, size)
        shutil.copy(src, dest)

    monkeypatch.setattr(bs, "fetch", fake_fetch)


def test_new_rows_are_added_once_and_the_week_marker_stops_a_second_run(clean, monkeypatch, tmp_path):
    set_setting(bs.URL_KEYS["churches"], "https://sheets.example.invalid/church", by="test")
    serve(monkeypatch, tmp_path, {"churches": 3})
    assert bs.run_and_record() == 0
    assert count() == 3 and get_setting(bs.STATUS_KEY)["kinds"]["churches"] == {"ok": True, "new": 3, "updated": 0}

    serve(monkeypatch, tmp_path, {"churches": 5})  # the sheet grew; but this week was already synced
    assert bs.run_and_record() == 0 and count() == 3
    assert bs.run_and_record(force=True) == 0 and count() == 5  # Run now adds only the 2 new rows
    assert get_setting(bs.STATUS_KEY)["kinds"]["churches"] == {"ok": True, "new": 2, "updated": 3}


def test_a_failing_link_is_reported_and_does_not_stop_the_other_sheet(clean, monkeypatch, tmp_path):
    set_setting(bs.URL_KEYS["churches"], "https://sheets.example.invalid/church", by="test")
    set_setting(bs.URL_KEYS["nonprofits"], "https://sheets.example.invalid/nonprofit", by="test")
    serve(monkeypatch, tmp_path, {"churches": "The link was refused", "nonprofits": 2})
    alerts = []
    monkeypatch.setattr(bs.daily_feed, "alert_admin", lambda subject, text: alerts.append(subject))
    assert bs.run_and_record() == 1
    kinds = get_setting(bs.STATUS_KEY)["kinds"]
    assert kinds["churches"]["ok"] is False and kinds["nonprofits"]["new"] == 2 and count("nonprofit_jobs") == 2
    assert len(alerts) == 1
    assert get_setting(bs.DONE_KEY) is None  # the week isn't done...
    assert bs.run_and_record() == 0 and len(alerts) == 1  # ...but it isn't retried until tomorrow


def test_nothing_happens_without_a_link(clean, monkeypatch):
    monkeypatch.setattr(bs, "fetch", lambda *a: pytest.fail("fetched without a link"))
    assert bs.run_and_record() == 0 and get_setting(bs.STATUS_KEY) is None


def test_links_and_downloads():
    sheet = "https://docs.google.com/spreadsheets/d/AbC-123_x/edit?gid=0#gid=0"
    assert bs.download_url(sheet) == "https://docs.google.com/spreadsheets/d/AbC-123_x/export?format=xlsx"
    assert bs.download_url(" https://x.invalid/a.xlsx ") == "https://x.invalid/a.xlsx"
    assert bs.safe_link("https://x.invalid/a.xlsx?key=secret") == "https://x.invalid/a.xlsx"
    with pytest.raises(ValueError):
        bs.check_link("http://x.invalid/a.xlsx")


def test_fetch_refuses_a_page_that_is_not_an_excel_file(monkeypatch, tmp_path):
    from types import SimpleNamespace

    def respond(content, status=200):
        monkeypatch.setattr(
            bs, "get_public", lambda *a, **k: SimpleNamespace(content=content, status_code=status, ok=status < 400)
        )

    respond(b"<html>Sign in</html>")
    with pytest.raises(bs.SyncError, match="Excel"):
        bs.fetch("https://x.invalid/a", tmp_path / "a.xlsx")
    respond(b"", 403)
    with pytest.raises(bs.SyncError, match="refused"):
        bs.fetch("https://x.invalid/a", tmp_path / "a.xlsx")
    respond(b"PK\x03\x04data")
    bs.fetch("https://x.invalid/a", tmp_path / "a.xlsx")
    assert (tmp_path / "a.xlsx").read_bytes() == b"PK\x03\x04data"


def test_admin_endpoints(clean, make_user, sign_in):
    make_user(ADMIN, "a-strong-pass-1", role="viewer")
    viewer, _ = sign_in(ADMIN, "a-strong-pass-1")
    assert viewer.get("/api/admin/bizdev-sync").status_code == 403
    make_user(ADMIN, "a-strong-pass-1")
    admin, _ = sign_in(ADMIN, "a-strong-pass-1")
    assert admin.post("/api/admin/bizdev-sync/run").status_code == 400  # no link yet
    assert (
        admin.post("/api/admin/bizdev-sync", json={"kind": "churches", "url": "http://x.invalid/a"}).status_code == 422
    )
    saved = admin.post(
        "/api/admin/bizdev-sync", json={"kind": "churches", "url": "https://x.invalid/a.xlsx?key=s"}
    ).json()
    assert saved["links"] == {"churches": "https://x.invalid/a.xlsx", "nonprofits": None}  # the key is never shown
    cleared = admin.post("/api/admin/bizdev-sync", json={"kind": "churches", "url": ""}).json()
    assert cleared["links"]["churches"] is None
