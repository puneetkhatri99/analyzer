"""The whole sheet-link flow through the API, with a real web server serving the workbook: save a link, Run now (download,
add the new jobs, fill the gaps with the AI step), read the jobs and a contact, then a changed sheet, a redirect, a page
that isn't an Excel file, a missing file, and removing the link. Only OpenAI is replaced, and it only sees the test's rows."""

import http.server
import threading
from datetime import date
from types import SimpleNamespace

import openpyxl
import pytest

import app.shared.web as web
from app.core.config import get_settings
from app.core.db import get_conn
from app.extraction.schemas import ChurchFacts, JobExtraction
from app.ingestion import bizdev_enrich as be
from app.ingestion import bizdev_sync as bs
from app.leads.daily_report import get_setting, set_setting
from tests.ingestion.test_bizdev_sync import HEADER

PREFIX = "jobs.test-flow.invalid/"
ADMIN = "test-flow-admin@example.invalid"
KEYS = (*bs.URL_KEYS.values(), bs.STATUS_KEY, bs.DONE_KEY, bs.TRIED_KEY, bs.ENRICH_KEY, bs.ENRICH_DONE_KEY)


def write_sheet(path, n):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(HEADER)
    for i in range(1, n + 1):
        ws.append(["Pat", f"Lee{i}", "Lead Pastor", f"pat{i}@test-flow.invalid", f"Zzz Flow Church {i}", "Dallas", "TX",
                   "Youth Pastor", f"https://{PREFIX}{i}", "https://test-flow.invalid", date(2026, 11, 10), None])  # fmt: skip
    wb.save(path)


@pytest.fixture
def site(tmp_path, monkeypatch):
    """A real web server: /sheet.xlsx, /redirect (to the sheet), /page.html (not Excel), anything else is a 404."""
    write_sheet(tmp_path / "sheet.xlsx", 3)
    (tmp_path / "page.html").write_text("<html>Please sign in</html>")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(tmp_path), **k)

        def do_GET(self):
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "/sheet.xlsx")
                self.end_headers()
            else:
                super().do_GET()

        def log_message(self, *a):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(web, "check_public_url", lambda url: None)  # the guard refuses loopback; this is a test server
    monkeypatch.setattr(bs, "check_link", lambda link: None)  # real links must be https
    yield SimpleNamespace(
        url=lambda p: f"http://127.0.0.1:{server.server_address[1]}/{p}", sheet=tmp_path / "sheet.xlsx"
    )
    server.shutdown()


@pytest.fixture
def ai(monkeypatch):
    """OpenAI replaced, and the AI step limited to the test's rows (it would otherwise see your real jobs)."""
    calls = SimpleNamespace(church=0, pay=0)

    def parse(**kw):
        if kw["text_format"] is ChurchFacts:
            calls.church += 1
            return SimpleNamespace(output_parsed=ChurchFacts(
                church_size=350, year=date.today().year, denomination="Baptist",
                source_url="https://flow.invalid/about", evidence="About 350 people attend weekly"))  # fmt: skip
        calls.pay += 1
        return SimpleNamespace(output_parsed=JobExtraction(
            page_type="job_posting", reason="a job posting", category="church", job_title="Youth Pastor",
            org_name="Zzz Flow Church", org_website=None, city=None, state=None, country=None, date_posted=None,
            salary_min=52000, salary_max=60000, salary_period="year", hours="Full-Time", remote=None,
            denomination=None, church_size=None))  # fmt: skip

    monkeypatch.setattr(be, "OpenAI", lambda api_key: SimpleNamespace(responses=SimpleNamespace(parse=parse)))
    monkeypatch.setattr(get_settings(), "openai_api_key", "test-key")
    employers, pay = be.enrich_employers, be.enrich_pay
    monkeypatch.setattr(be, "enrich_employers", lambda client, kind, limit: employers(client, kind, limit, PREFIX))
    monkeypatch.setattr(be, "enrich_pay", lambda client, kind, limit: pay(client, kind, limit, PREFIX))
    return calls


@pytest.fixture
def clean():
    before = {k: get_setting(k) for k in KEYS}

    def wipe():
        with get_conn() as conn:
            conn.execute("DELETE FROM public.church_jobs WHERE url_key LIKE %s", (PREFIX + "%",))
            conn.execute("DELETE FROM public.app_settings WHERE key = ANY(%s)", (list(KEYS),))

    wipe()
    yield
    wipe()
    for key, value in before.items():
        if value is not None:
            set_setting(key, value, by="test")


def test_adding_a_sheet_link_end_to_end(clean, site, ai, make_user, sign_in):
    make_user(ADMIN, "a-strong-pass-1")
    admin, _ = sign_in(ADMIN, "a-strong-pass-1")
    api = "/api/admin/bizdev-sync"

    # nothing to run before a link is saved, and the timer does nothing either
    assert admin.post(f"{api}/run").status_code == 400 and bs.run_if_due() == 0 and not ai.church

    # the link is saved, but shown without its query string (which can hold the share key)
    saved = admin.post(api, json={"kind": "churches", "url": site.url("sheet.xlsx") + "?key=secret"}).json()
    assert saved["links"]["churches"] == site.url("sheet.xlsx") and saved["status"] is None

    # Run now: download, add the jobs, then the AI step
    assert admin.post(f"{api}/run").status_code == 200
    state = admin.get(api).json()
    assert state["running"] is False
    assert state["status"]["ok"] and state["status"]["kinds"] == {"churches": {"ok": True, "new": 3, "updated": 0}}
    assert state["enrich"]["ok"] and state["enrich"]["employers"] == 3 and state["enrich"]["pay_found"] == 3

    # the jobs are in the list, with what the AI found, and no contact details
    listed = admin.get("/api/jobs", params={"source": "churches", "search": "Zzz Flow"})
    jobs = listed.json()["rows"]
    assert len(jobs) == 3
    assert all(j["salary_min"] == 52000 and j["denomination"] == "Baptist" and j["church_size"] == 350 for j in jobs)
    assert "@test-flow.invalid" not in listed.text and "Lead Pastor" not in listed.text

    # an editor sees the person to contact in the job's detail
    contact = admin.get("/api/admin/jobs/contact", params={"source": "churches", "id": f"{PREFIX}1"}).json()
    assert contact == {
        "first_name": "Pat",
        "last_name": "Lee1",
        "title": "Lead Pastor",
        "email": "pat1@test-flow.invalid",
    }

    # the sheet grew by two jobs; through a redirect: only the new ones are added, the AI step looks up only them
    write_sheet(site.sheet, 5)
    asked = (ai.church, ai.pay)
    admin.post(api, json={"kind": "churches", "url": site.url("redirect")})
    admin.post(f"{api}/run")
    state = admin.get(api).json()
    assert state["status"]["kinds"]["churches"] == {"ok": True, "new": 2, "updated": 3}
    assert (ai.church - asked[0], ai.pay - asked[1]) == (2, 2)  # nothing already looked up is paid for again

    # a page that isn't an Excel file, and a missing file, are reported; the data stays as it was
    for path, words in (("page.html", "Excel file"), ("missing.xlsx", "refused")):
        admin.post(api, json={"kind": "churches", "url": site.url(path)})
        admin.post(f"{api}/run")
        failed = admin.get(api).json()["status"]
        assert failed["ok"] is False and words in failed["kinds"]["churches"]["message"]
    with get_conn() as conn:
        assert (
            conn.execute("SELECT count(*) FROM public.church_jobs WHERE url_key LIKE %s", (PREFIX + "%",)).fetchone()[0]
            == 5
        )

    # removing the link
    gone = admin.post(api, json={"kind": "churches", "url": ""}).json()
    assert gone["links"]["churches"] is None and admin.post(f"{api}/run").status_code == 400
