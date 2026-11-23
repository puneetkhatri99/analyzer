"""Public sign-up: validation, and a returning email updates its row."""

from app.core.db import get_conn


def test_leads(client):
    c = client
    email = "test-lead@example.invalid"
    body = {"name": "Test Person", "email": email.upper(), "organization": "Test Church", "role": "Worship/Music"}
    try:
        assert c.post("/api/leads", json={**body, "email": "not-an-email"}).status_code == 422
        assert c.post("/api/leads", json={**body, "name": ""}).status_code == 422
        assert c.post("/api/leads", json=body).status_code == 200
        assert c.post("/api/leads", json={**body, "organization": "Renamed Church"}).status_code == 200
        with get_conn() as conn:
            rows = conn.execute("SELECT organization FROM public.leads WHERE email = %s", (email,)).fetchall()
        assert rows == [("Renamed Church",)]
    finally:
        with get_conn() as conn:
            conn.execute("DELETE FROM public.leads WHERE email = %s", (email,))


def test_leads_dashboard(client, make_user, sign_in):
    email = "test-dashboard-lead@example.invalid"
    lead = {"name": "Dash Person", "email": email, "organization": "Dash Church", "role": "Worship/Music"}
    make_user("test-leads-admin@example.invalid", "a-strong-pass-1")
    try:
        assert client.post("/api/leads", json={**lead, "location": "Ohio"}).status_code == 200
        assert client.get("/api/admin/leads").status_code == 401  # signed out
        admin, _ = sign_in("test-leads-admin@example.invalid", "a-strong-pass-1")
        r = admin.get("/api/admin/leads").json()
        row = next(x for x in r["leads"] if x["email"] == email)
        assert (row["name"], row["organization"], row["location"]) == ("Dash Person", "Dash Church", "Ohio")
        assert r["totals"]["total"] >= 1 and r["totals"]["this_week"] >= 1
        assert any(x["name"] == "Worship/Music" for x in r["by_role"])
    finally:
        with get_conn() as conn:
            conn.execute("DELETE FROM public.leads WHERE email = %s", (email,))


def test_lead_history(client, make_user, sign_in):
    email = "test-history-lead@example.invalid"
    lead = {"name": "History Person", "email": email, "organization": "History Church", "role": "Executive Pastor"}
    make_user("test-history-admin@example.invalid", "a-strong-pass-1")
    try:
        assert client.post("/api/leads", json={**lead, "location": "Texas", "shared": True}).status_code == 200
        event = {"email": email.upper(), "type": "offer", "details": {"amount": 85000, "unit": "year"}}
        assert client.post("/api/leads/events", json=event).status_code == 200
        cta = {**event, "type": "cta", "details": {"label": "Book a Call", "url": "https://bookme.ministryhub.org/x"}}
        assert client.post("/api/leads/events", json=cta).status_code == 200
        # unknown visitors are accepted but not stored; bad types and oversized details are refused
        assert client.post("/api/leads/events", json={**event, "email": "nobody@example.invalid"}).status_code == 200
        assert client.post("/api/leads/events", json={**event, "type": "hack"}).status_code == 422
        assert client.post("/api/leads/events", json={**event, "details": {"x": "a" * 3000}}).status_code == 422

        assert client.get(f"/api/admin/leads/{email}").status_code == 401
        admin, _ = sign_in("test-history-admin@example.invalid", "a-strong-pass-1")
        h = admin.get(f"/api/admin/leads/{email}").json()
        assert [e["type"] for e in h["events"]] == ["cta", "offer", "signup"]  # newest first
        assert h["events"][2]["details"]["shared"] is True and h["events"][1]["details"]["amount"] == 85000
        row = next(x for x in admin.get("/api/admin/leads").json()["leads"] if x["email"] == email)
        assert row["events"] == 3 and row["last_active"] and row["booked"] is True and row["hot_at"] is None
        assert admin.get("/api/admin/leads/nobody@example.invalid").status_code == 404

        # deleting takes the lead and all their events
        assert client.delete(f"/api/admin/leads/{email}").status_code == 401
        assert admin.delete(f"/api/admin/leads/{email.upper()}").status_code == 200
        assert admin.get(f"/api/admin/leads/{email}").status_code == 404
        with get_conn() as conn:
            assert conn.execute("SELECT count(*) FROM public.lead_events WHERE email = %s", (email,)).fetchone()[0] == 0
        assert admin.delete(f"/api/admin/leads/{email}").status_code == 404
    finally:
        with get_conn() as conn:
            conn.execute("DELETE FROM public.leads WHERE email = %s", (email,))  # its events go too (cascade)


def test_hot_lead_at_three_reports(client, make_user, sign_in):
    email = "test-hot-lead@example.invalid"
    make_user("test-hot-admin@example.invalid", "a-strong-pass-1")
    admin, _ = sign_in("test-hot-admin@example.invalid", "a-strong-pass-1")
    lead = {"name": "Hot Person", "email": email, "organization": "Hot Church"}

    def hot() -> tuple[bool, bool]:
        row = next(x for x in admin.get("/api/admin/leads").json()["leads"] if x["email"] == email)
        return row["hot"], admin.get(f"/api/admin/leads/{email}").json()["lead"]["hot"]

    try:
        assert client.post("/api/leads", json=lead).status_code == 200
        report = {"email": email, "type": "report", "details": {"role": ["Worship/Music"]}}
        click = {**report, "type": "click"}  # between reports, so they aren't merged; clicks don't count
        for _ in range(2):
            assert client.post("/api/leads/events", json=report).status_code == 200
            assert client.post("/api/leads/events", json=click).status_code == 200
        assert hot() == (False, False)  # 2 reports: not yet
        client.post("/api/leads/events", json=report)
        assert hot() == (True, True)
        assert admin.get("/api/admin/leads").json()["totals"]["hot"] >= 1
    finally:
        with get_conn() as conn:
            conn.execute("DELETE FROM public.leads WHERE email = %s", (email,))


def test_quick_reports_merge_and_internal_emails_are_ignored(client, make_user, sign_in):
    email = "test-merge-lead@example.invalid"
    make_user("test-merge-admin@example.invalid", "a-strong-pass-1")
    admin, _ = sign_in("test-merge-admin@example.invalid", "a-strong-pass-1")
    try:
        assert client.post("/api/leads", json={"name": "M", "email": email, "organization": "O"}).status_code == 200
        for state in ("Ohio", "Indiana"):  # two reports seconds apart: one row, holding the latest
            client.post("/api/leads/events", json={"email": email, "type": "report", "details": {"state": [state]}})
        events = admin.get(f"/api/admin/leads/{email}").json()["events"]
        assert [e["type"] for e in events] == ["report", "signup"]
        assert events[0]["details"]["state"] == ["Indiana"]

        staff = "someone@ministryhub.org"  # IGNORED_LEAD_DOMAINS default: the team testing the site
        assert (
            client.post("/api/leads", json={"name": "S", "email": staff, "organization": "MinistryHub"}).status_code
            == 200
        )
        assert admin.get(f"/api/admin/leads/{staff}").status_code == 404
    finally:
        with get_conn() as conn:
            conn.execute("DELETE FROM public.leads WHERE email = %s", (email,))
