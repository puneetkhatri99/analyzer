"""The daily lead report: settings, the cron command's once-a-day rule, and failures that must be retried.
Resend is never called: requests.post is replaced."""

from datetime import timedelta

import pytest

from app.cli import main
from app.core.db import get_conn
from app.leads import daily_report as dr

LEAD = "test-daily-lead@example.invalid"
ADMIN = "test-daily-admin@example.invalid"


@pytest.fixture
def saved_settings():
    """Puts back the report's settings (recipients, last day sent) after the test."""
    before = {k: dr.get_setting(k) for k in (dr.RECIPIENTS, dr.SENT_FOR)}
    yield
    with get_conn() as conn:
        conn.execute("DELETE FROM public.app_settings WHERE key = ANY(%s)", (list(before),))
    for key, value in before.items():
        if value is not None:
            dr.set_setting(key, value)


def test_settings_are_admin_only_and_checked(make_user, sign_in, saved_settings):
    make_user(ADMIN, "a-strong-pass-1")
    admin, _ = sign_in(ADMIN, "a-strong-pass-1")
    r = admin.patch(
        "/api/admin/settings", json={"hot_lead_emails": ["Jordan@Church.org", "jordan@church.org", "b@x.org"]}
    )
    assert r.status_code == 200 and r.json()["hot_lead_emails"] == ["jordan@church.org", "b@x.org"]
    assert admin.get("/api/admin/settings").json()["hot_lead_emails"] == ["jordan@church.org", "b@x.org"]
    assert admin.patch("/api/admin/settings", json={"hot_lead_emails": ["not-an-email"]}).status_code == 422
    too_many = [f"p{i}@x.org" for i in range(11)]
    assert admin.patch("/api/admin/settings", json={"hot_lead_emails": too_many}).status_code == 422


def test_hot_at_is_set_on_the_third_report(client):
    try:
        client.post("/api/leads", json={"name": "D", "email": LEAD, "organization": "O"})
        for i in range(3):
            client.post("/api/leads/events", json={"email": LEAD, "type": "report", "details": {"n": i}})
            client.post("/api/leads/events", json={"email": LEAD, "type": "click", "details": {}})  # no merging
            with get_conn() as conn:
                hot_at = conn.execute("SELECT hot_at FROM public.leads WHERE email = %s", (LEAD,)).fetchone()[0]
            assert (hot_at is not None) == (i == 2)
    finally:
        with get_conn() as conn:
            conn.execute("DELETE FROM public.leads WHERE email = %s", (LEAD,))


def test_cron_sends_once_from_8am_retries_a_failure_and_catches_up(client, monkeypatch, resend, saved_settings):
    try:
        client.post("/api/leads", json={"name": "Dana Daily", "email": LEAD, "organization": "Daily Church"})
        with get_conn() as conn:  # hot since noon yesterday, New York time
            conn.execute(
                """UPDATE public.leads SET hot_at = ((now() AT TIME ZONE 'America/New_York')::date - 1
                       + time '12:00') AT TIME ZONE 'America/New_York' WHERE email = %s""",
                (LEAD,),
            )
        today, _ = dr.eastern_now()
        dr.set_setting(dr.RECIPIENTS, ["team@example.invalid"])
        with get_conn() as conn:
            conn.execute("DELETE FROM public.app_settings WHERE key = %s", (dr.SENT_FOR,))

        monkeypatch.setattr(dr, "eastern_now", lambda: (today, 7))
        assert main(["daily-report"]) == 0 and resend.sent == []  # 7 AM: not yet

        monkeypatch.setattr(dr, "eastern_now", lambda: (today, 8))
        resend.fail = True
        assert main(["daily-report"]) == 1  # Resend refused: the day stays unsent, so the next run retries
        assert dr.get_setting(dr.SENT_FOR) is None

        resend.fail, resend.sent = False, []
        monkeypatch.setattr(dr, "eastern_now", lambda: (today, 9))  # the retry run
        assert main(["daily-report"]) == 0
        assert len(resend.sent) == 1 and resend.sent[0]["to"] == ["team@example.invalid"]
        assert "Dana Daily, Daily Church" in resend.sent[0]["text"]
        assert dr.get_setting(dr.SENT_FOR) == str(today.fromordinal(today.toordinal() - 1))
        assert main(["daily-report"]) == 0 and len(resend.sent) == 1  # another check the same day: already sent
        monkeypatch.setattr(dr, "eastern_now", lambda: (today, 15))
        assert main(["daily-report"]) == 0 and len(resend.sent) == 1  # later that day: still sent once

        # the server slept through two mornings: both missed days go out, oldest first, then nothing more
        monkeypatch.setattr(dr, "eastern_now", lambda: (today + timedelta(days=2), 14))
        assert main(["daily-report"]) == 0 and len(resend.sent) == 3
        assert dr.get_setting(dr.SENT_FOR) == str(today + timedelta(days=1))
        assert main(["daily-report"]) == 0 and len(resend.sent) == 3

        # re-sending an old day by hand, or a future one, leaves the marker alone: no catch-up storm, no skipped days
        assert main(["daily-report", "--day", str(today - timedelta(days=20))]) == 0 and len(resend.sent) == 4
        assert main(["daily-report", "--day", str(today + timedelta(days=30))]) == 0 and len(resend.sent) == 5
        assert dr.get_setting(dr.SENT_FOR) == str(today + timedelta(days=1))
        assert main(["daily-report"]) == 0 and len(resend.sent) == 5
    finally:
        with get_conn() as conn:
            conn.execute("DELETE FROM public.leads WHERE email = %s", (LEAD,))


def test_a_day_without_hot_leads_still_reports(monkeypatch):
    monkeypatch.setattr(
        dr, "report_data", lambda day: {"day": day, "hot": [], "signups": 2, "reports": 5, "active": 3, "hot_total": 9}
    )
    from datetime import date

    subject, text = dr.render(dr.report_data(date(2026, 11, 16)))
    assert subject == "MinistryHub daily leads: 0 new hot leads (Nov 16)"
    assert "No new hot leads that day." in text and "New sign-ups: 2" in text


def test_an_odd_offer_from_the_public_site_never_breaks_the_email():
    assert dr._offer({"amount": 52000, "unit": "year", "verdict": "In range."}) == "$52,000 a year (In range)"
    assert dr._offer({"amount": "18.5", "unit": "hour"}) == "$18.50 an hour"
    for odd in ({}, {"amount": "85k"}, {"amount": None}, {"amount": 50000, "verdict": 7}):
        assert dr._offer(odd) in ("an offer", "$50,000 a year")


def test_the_api_timer_checks_until_stopped(monkeypatch):
    calls = []
    monkeypatch.setattr(dr, "CHECK_EVERY", 0.01)
    monkeypatch.setattr(dr, "send_if_due", lambda: calls.append(1) or (_ for _ in ()).throw(RuntimeError("db down")))
    stop = dr.start_scheduler()
    import time

    time.sleep(0.2)
    stop.set()
    seen = len(calls)
    assert seen >= 2  # a failed check (here: an error every time) doesn't end the timer
    time.sleep(0.1)
    assert len(calls) <= seen + 1  # stopped
