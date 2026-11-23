"""Public report: widening, confidence, part-time kept apart, and nothing private leaving the server."""

from app.report import service as report
from app.shared.geo import state_name


def job(role="Worship", state="Ohio", pay=50000, period="year", hours="Full-Time", size=None, denom=None):
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


def test_widens_state_then_nearby_then_region_then_national():
    ohio = [job(pay=40000)] * 5
    indiana = [job(state="Indiana", pay=60000)] * 5  # borders Ohio
    iowa = [job(state="Iowa", pay=70000)] * 5  # same region, no border
    texas = [job(state="Texas", pay=80000)] * 20

    r = report.build_report({"role": ["Worship"], "state": ["Ohio"]}, ohio + indiana + texas)
    assert r["scope"] == "state" and r["pay"]["typical"] == 40000 and r["note"] is None

    r = report.build_report({"role": ["Worship"], "state": ["Ohio"]}, ohio[:2] + indiana + iowa + texas)
    assert r["scope"] == "nearby" and r["pay"]["typical"] == 60000  # Ohio + Indiana; Iowa not yet
    assert r["covers"]["area"] == "Ohio and nearby states"

    r = report.build_report({"role": ["Worship"], "state": ["Ohio"]}, ohio[:2] + iowa + texas)
    assert r["scope"] == "region" and r["area_name"] == "Midwest and nearby states" and "Midwest" in r["note"]

    r = report.build_report({"role": ["Worship"], "state": ["Ohio"]}, ohio[:2] + texas)
    assert r["scope"] == "national" and "national" in r["note"]

    r = report.build_report({"role": ["Worship"], "state": ["Ohio"]}, ohio[:2])
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
        c.get("/api/report?role=Worship&state=Ohio&state=Indiana").json(),
    ]
    for reply in replies:
        assert not {"postings", "paid", "total", "post_url", "company_name", "origin", "board_source"} & set(
            _keys(reply)
        )
        assert "http" not in str(reply)
    for path in ("/api/jobs", "/api/summary", "/api/sources", "/api/filter-options"):
        assert c.get(path).status_code == 401


def test_attendance_counts_each_church_once_and_needs_enough_churches():
    churches = [{"church_size": 101, "company_name": f"Church {i}", "source": "json"} for i in range(29)]
    mega = [{"church_size": 15001, "company_name": "Mega Church", "source": "churches"}] * 40  # one church, many jobs
    nonprofit = [{"church_size": 9001, "company_name": f"Charity {i}", "source": "nonprofits"} for i in range(50)]
    assert report.typical_attendance(churches + nonprofit) is None  # 29 churches: too few
    assert report.typical_attendance(churches + mega + nonprofit) == 100  # 30 churches; the megachurch counts once


def test_placeholder_and_missing_employers_stay_off_the_report():
    assert report.hidden_employer("Z. Do Not Use") == "placeholder 'Z. Do Not Use'"
    assert report.hidden_employer(" z. do not use ") is not None
    assert report.hidden_employer(None) == report.hidden_employer("  ") == "no employer"
    assert report.hidden_employer("Grace Church") is None


def test_figures_are_rounded():
    assert report.build_report({}, [job(pay=66260)] * 5)["pay"]["typical"] == 66500
    hourly = [job(pay=17.12, period="hour", hours="Part-Time")] * 5
    assert report.build_report({"type": "part-time"}, hourly)["pay"]["typical"] == 17.0


def test_zero_or_negative_pay_is_not_a_salary():
    rows = [job(pay=0)] * 6 + [job(pay=-100)] * 6
    r = report.build_report({"state": ["Ohio"]}, rows)
    assert r["pay"] is None and r["vs_national"] is None  # no ZeroDivisionError, no figure from bad parses
    rows += [job(pay=60000)] * 6
    assert report.build_report({"state": ["Ohio"]}, rows)["pay"]["typical"] == 60000
