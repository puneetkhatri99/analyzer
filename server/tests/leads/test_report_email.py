"""'Email me this report' on the sign-up form: the report goes out once, links back, and has a daily limit."""

from app.core.db import get_conn
from app.leads import report_email

EMAIL = "test-report-email@example.invalid"
LEAD = {"name": "Mail Person", "email": EMAIL, "organization": "Mail Church", "role": "Worship/Music"}
QUERY = "role=Worship%2FMusic&state=Ohio&type=part-time&bogus=1"


def test_parse_filters():
    f = report_email.parse_filters(QUERY)
    assert f == {"role": ["Worship/Music"], "state": ["Ohio"], "size": [], "denomination": [], "type": "part-time"}
    assert report_email.parse_filters("type=weekly")["type"] == "full-time"


def test_only_real_filters_and_a_plain_name_go_into_the_email():
    jobs = [{"role": "Worship/Music", "denomination": "Baptist", "salary_min": None, "salary_max": None,
             "salary_period": None, "hours": None, "church_size": None, "state": "Ohio",
             "company_name": "Grace", "source": "json", "pull_date": None}]  # fmt: skip
    f = report_email.parse_filters("role=Worship%2FMusic&role=Call+now+evil.example&state=OH&state=Narnia"
                                   "&denomination=Baptist&denomination=%3Cb%3Ehi")  # fmt: skip
    f = report_email.known_filters(f, jobs)
    assert (f["role"], f["state"], f["denomination"]) == (["Worship/Music"], ["Ohio"], ["Baptist"])
    assert report_email.greeting("Mary O’Neil-Smith") == "Mary O’Neil-Smith"
    assert report_email.greeting("J. Smith") == "J. Smith"
    for odd in ("Your account is locked, visit evil.example", "Call 555 0100", "x" * 61, "http://x", ""):
        assert report_email.greeting(odd) == "there"


def test_report_is_emailed_only_when_asked(client, resend):
    try:
        assert client.post("/api/leads", json={**LEAD, "report": QUERY}).status_code == 200
        assert resend.sent == []  # switch off: nothing sent
        assert client.post("/api/leads", json={**LEAD, "report": QUERY, "email_report": True}).status_code == 200
        (mail,) = resend.sent
        assert mail["to"] == [EMAIL] and "Worship/Music in Ohio" in mail["subject"]
        assert "/report?role=Worship%2FMusic&state=Ohio&type=part-time" in mail["text"]
        assert "Hi Mail Person" in mail["text"]
        with get_conn() as conn:
            (n,) = conn.execute(
                "SELECT count(*) FROM public.lead_events WHERE email = %s AND type = 'report_email'", (EMAIL,)
            ).fetchone()
        assert n == 1
    finally:
        with get_conn() as conn:
            conn.execute("DELETE FROM public.leads WHERE email = %s", (EMAIL,))


def statuses():
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT details->>'status', details->>'reason' FROM public.lead_events
               WHERE email = %s AND type = 'report_email' ORDER BY id""",
            (EMAIL,),
        ).fetchall()
    return rows


def test_every_outcome_is_recorded_and_limited(client, resend, monkeypatch):
    ask = {**LEAD, "report": QUERY, "email_report": True}
    try:
        resend.fail = True  # a refused send still opens the report, and is recorded with Resend's reason
        assert client.post("/api/leads", json=ask).status_code == 200
        assert statuses() == [("failed", "Resend refused the email (422): domain not verified")]
        resend.fail = False
        for _ in range(report_email.MAX_PER_DAY + 1):
            client.post("/api/leads", json=ask)
        assert len(resend.sent) == report_email.MAX_PER_DAY  # the failed try counts towards the limit
        rows = statuses()
        assert [s for s, _ in rows] == ["failed"] + ["sent"] * (report_email.MAX_PER_DAY - 1) + ["skipped"] * 2
        assert "daily limit" in rows[-1][1]

        # many addresses from one script: this address has sent none, but the whole site has reached its limit
        site_limit = report_email.MAX_ALL_PER_DAY
        monkeypatch.setattr(report_email, "_sent_today", lambda email=None: 0 if email else site_limit)
        before = len(resend.sent)
        client.post("/api/leads", json=ask)
        assert len(resend.sent) == before and "site-wide" in statuses()[-1][1]

        monkeypatch.setattr(report_email, "email_ready", lambda: False)
        client.post("/api/leads", json=ask)
        assert "isn't set up" in statuses()[-1][1]

        r = client.get("/api/admin/leads")  # signed out; the list itself is checked below with an admin
        assert r.status_code == 401
    finally:
        with get_conn() as conn:
            conn.execute("DELETE FROM public.leads WHERE email = %s", (EMAIL,))


def test_leads_list_shows_the_latest_outcome(client, resend, make_user, sign_in):
    make_user("test-report-email-admin@example.invalid", "a-strong-pass-1")
    try:
        client.post("/api/leads", json={**LEAD, "report": QUERY, "email_report": True})
        admin, _ = sign_in("test-report-email-admin@example.invalid", "a-strong-pass-1")
        row = next(x for x in admin.get("/api/admin/leads").json()["leads"] if x["email"] == EMAIL)
        assert row["report_email"] == "sent"
    finally:
        with get_conn() as conn:
            conn.execute("DELETE FROM public.leads WHERE email = %s", (EMAIL,))
