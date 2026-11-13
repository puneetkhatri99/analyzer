"""Public report: widening, confidence, part-time kept apart, and nothing private leaving the server."""
from fastapi.testclient import TestClient

from app import report
from app.db import get_conn
from app.main import app


def job(role="Worship/Music", state="Ohio", pay=50000, period="year", hours="Full-Time", size=None, denom=None):
    return {"role": role, "state": state, "region": state, "country": "US", "hours": hours, "church_size": size,
            "denomination": denom, "salary_min": pay, "salary_max": pay, "salary_period": period, "pull_date": "2026-11-05"}


def test_widens_state_then_region_then_national():
    ohio = [job(pay=40000)] * 5
    indiana = [job(state="Indiana", pay=60000)] * 5
    texas = [job(state="Texas", pay=80000)] * 20

    r = report.build_report({"role": ["Worship/Music"], "state": ["Ohio"]}, ohio + indiana + texas)
    assert r["scope"] == "state" and r["pay"]["typical"] == 40000 and r["note"] is None

    r = report.build_report({"role": ["Worship/Music"], "state": ["Ohio"]}, ohio[:2] + indiana + texas)
    assert r["scope"] == "region" and r["area_name"] == "Midwest" and "Midwest" in r["note"]

    r = report.build_report({"role": ["Worship/Music"], "state": ["Ohio"]}, ohio[:2] + texas)
    assert r["scope"] == "national" and "national" in r["note"]

    r = report.build_report({"role": ["Worship/Music"], "state": ["Ohio"]}, ohio[:2])
    assert r["pay"] is None and "Too few" in r["note"]


def test_confidence_labels():
    for n, label in [(5, "Limited"), (10, "Moderate"), (30, "Strong")]:
        assert report.build_report({}, [job()] * n)["pay"]["confidence"] == label


def test_part_time_is_hourly_and_separate():
    jobs = [job(pay=50000)] * 5 + [job(pay=18, period="hour", hours="Part-Time")] * 5
    assert report.build_report({}, jobs)["pay"]["typical"] == 50000
    r = report.build_report({"type": "part-time"}, jobs)
    assert r["unit"] == "hour" and r["pay"]["typical"] == 18


def test_state_names():
    assert report.state_name("oh") == "Ohio" and report.state_name("Ohio") == "Ohio"
    assert report.state_name("Cook") is None and report.state_name("N/A") is None


def _keys(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from _keys(v)
    elif isinstance(value, list):
        for v in value:
            yield from _keys(v)


def test_public_api_hides_counts_sources_and_links():
    c = TestClient(app)
    replies = [c.get("/api/report/options").json(),
               c.get("/api/report?role=Worship/Music&state=Ohio&state=Indiana").json()]
    for reply in replies:
        assert not {"postings", "paid", "total", "post_url", "company_name", "origin", "board_source"} & set(_keys(reply))
        assert "http" not in str(reply)
    for path in ("/api/jobs", "/api/summary", "/api/sources", "/api/filter-options"):
        assert c.get(path).status_code == 401


def test_leads():
    c = TestClient(app)
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
