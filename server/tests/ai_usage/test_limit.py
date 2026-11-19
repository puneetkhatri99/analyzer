"""The monthly AI spending limit: an admin sets it, and once this month's estimated spend reaches it no OpenAI call is
made by any of the four places that make them. The AI itself is replaced (and must never be reached)."""

import pytest

from app.ai_usage import service
from app.core.config import get_settings
from app.core.db import get_conn
from app.extraction.schemas import JobExtraction
from app.extraction.service import LOOKUP_FAILED, ExtractionError, extract, lookup_church
from app.ingestion import bizdev_enrich as be
from app.ingestion import daily_feed as df
from tests.ingestion.test_daily_feed import FUTURE, clean, fake_ai  # noqa: F401  (the daily feed's fixtures)

ADMIN = "test-limit-admin@example.invalid"


@pytest.fixture
def limit():
    """Puts back the saved limit, and removes the spend a test adds."""
    before = service.get_limit()
    yield
    service.set_limit(before, "test")
    with get_conn() as conn:
        conn.execute("DELETE FROM public.ai_usage WHERE purpose = 'test-limit'")


def spend(dollars: float) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO public.ai_usage (purpose, url, model, input_tokens, cached_tokens, output_tokens,
                   web_searches, cost_usd) VALUES ('test-limit', 'https://test-limit.invalid', 'gpt-5.4-mini', 1, 0, 1, 0, %s)""",
            (dollars,),
        )


def reach_the_limit() -> None:
    """A limit this month's spend has just reached."""
    spend(1.0)
    service.set_limit(service.month_spend() - 0.5, "test")


class Untouched:
    """An OpenAI client that fails the test if it is ever called."""

    class responses:
        @staticmethod
        def parse(**kw):
            pytest.fail("OpenAI was called although the monthly limit is reached")


def test_admin_sets_and_removes_the_limit(limit, make_user, sign_in):
    make_user(ADMIN, "a-strong-pass-1", role="editor")
    editor, _ = sign_in(ADMIN, "a-strong-pass-1")
    assert editor.patch("/api/admin/costs/limit", json={"limit_usd": 25}).status_code == 403
    make_user(ADMIN, "a-strong-pass-1")
    admin, _ = sign_in(ADMIN, "a-strong-pass-1")

    for bad in ({"limit_usd": 0}, {"limit_usd": -5}, {"limit_usd": 1e9}, {"limit_usd": "lots"}, {}):
        assert admin.patch("/api/admin/costs/limit", json=bad).status_code == 422, bad

    saved = admin.patch("/api/admin/costs/limit", json={"limit_usd": 25}).json()
    assert saved["limit_usd"] == 25 and saved["reached"] is False
    assert admin.get("/api/admin/costs").json()["budget"]["limit_usd"] == 25
    assert admin.patch("/api/admin/costs/limit", json={"limit_usd": None}).json()["limit_usd"] is None
    assert admin.get("/api/admin/costs").json()["budget"] == {**saved, "limit_usd": None, "reached": False}


def test_no_limit_or_room_left_lets_calls_through(limit):
    service.set_limit(None, "test")
    service.ensure_budget()
    service.set_limit(service.month_spend() + 5, "test")
    service.ensure_budget()
    assert service.budget()["reached"] is False


def test_nothing_calls_openai_once_the_limit_is_reached(limit, monkeypatch):
    reach_the_limit()
    assert service.budget()["reached"] is True
    with pytest.raises(service.BudgetReached, match="monthly AI limit"):
        service.ensure_budget()

    # the daily JSON review, the BizDev pay search, the church lookup and "Add a job"
    with pytest.raises(service.BudgetReached):
        df.ask_review(Untouched, {"post_url": "https://x.invalid", "post_html": "<p>job</p>"})
    with pytest.raises(service.BudgetReached):
        be.read_job(Untouched, ("k", "https://x.invalid/job", "Pastor", "Grace Church"))
    job = JobExtraction(
        page_type="job_posting", reason="r", category="church", job_title=None, org_name="Grace", org_website=None,
        city=None, state=None, country=None, date_posted=None, salary_min=None, salary_max=None, salary_period=None,
        hours=None, remote=None, denomination=None, church_size=None,
    )  # fmt: skip
    _, source, notes = lookup_church(Untouched, job, "https://x.invalid")
    assert source is None and notes[0].startswith(LOOKUP_FAILED)  # "failed": the church is tried again later
    monkeypatch.setattr(get_settings(), "openai_api_key", "test-key")
    with pytest.raises(ExtractionError) as e:
        extract("https://x.invalid/job", ADMIN)
    assert e.value.status_code == 429 and "Raise the limit" in e.value.detail


def test_the_bizdev_ai_step_pauses_and_says_why(limit, monkeypatch):
    reach_the_limit()
    monkeypatch.setattr(get_settings(), "openai_api_key", "test-key")
    monkeypatch.setattr(be, "OpenAI", lambda api_key: Untouched)
    monkeypatch.setattr(be, "share_known_values", lambda table: None)  # the free steps would touch real rows
    monkeypatch.setattr(be, "name_denominations", lambda table: 0)
    alerts = []
    monkeypatch.setattr(be.daily_feed, "alert_admin", lambda subject, text: alerts.append(subject))
    result = be.run()
    assert "monthly AI limit" in result["skipped"] and result["employers"] == result["pay_searched"] == 0
    assert alerts == ["MinistryHub monthly AI limit reached"]


def test_the_daily_json_run_pauses_and_says_why(clean, fake_ai, limit, monkeypatch):  # noqa: F811
    reach_the_limit()
    monkeypatch.setattr(df, "download", lambda url: [])
    df.set_setting(df.URL_KEY, FUTURE)
    alerts = []
    monkeypatch.setattr(df, "alert_admin", lambda subject, text: alerts.append(subject))
    assert df.run_and_record(force=True) == 0
    status = df.get_setting(df.STATUS_KEY)
    assert status["ok"] and "monthly AI limit" in status["message"]
    assert fake_ai.review == 0 and fake_ai.church == 0 and "MinistryHub monthly AI limit reached" in alerts
