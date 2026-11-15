"""Public report: widening, confidence, part-time kept apart, and nothing private leaving the server."""

from app.report import service as report
from app.shared.geo import state_name


def job(role="Worship/Music", state="Ohio", pay=50000, period="year", hours="Full-Time", size=None, denom=None):
    return {
        "role": role,
        "state": state,
        "region": state,
        "country": "US",
        "hours": hours,
        "church_size": size,
        "denomination": denom,
        "salary_min": pay,
        "salary_max": pay,
        "salary_period": period,
        "pull_date": "2026-11-05",
    }


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
    assert state_name("oh") == "Ohio" and state_name("Ohio") == "Ohio"
    assert state_name("Cook") is None and state_name("N/A") is None


def _keys(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from _keys(v)
    elif isinstance(value, list):
        for v in value:
            yield from _keys(v)


def test_public_api_hides_counts_sources_and_links(client):
    c = client
    replies = [
        c.get("/api/report/options").json(),
        c.get("/api/report?role=Worship/Music&state=Ohio&state=Indiana").json(),
    ]
    for reply in replies:
        assert not {"postings", "paid", "total", "post_url", "company_name", "origin", "board_source"} & set(
            _keys(reply)
        )
        assert "http" not in str(reply)
    for path in ("/api/jobs", "/api/summary", "/api/sources", "/api/filter-options"):
        assert c.get(path).status_code == 401
