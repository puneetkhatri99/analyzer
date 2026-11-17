"""Public report: widening, confidence, part-time kept apart, and nothing private leaving the server."""

from datetime import date

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


def test_attendance_counts_each_church_once_and_needs_enough_churches():
    churches = [{"church_size": 101, "company_name": f"Church {i}", "source": "json"} for i in range(29)]
    mega = [{"church_size": 15001, "company_name": "Mega Church", "source": "churches"}] * 40  # one church, many jobs
    nonprofit = [{"church_size": 9001, "company_name": f"Charity {i}", "source": "nonprofits"} for i in range(50)]
    assert report.typical_attendance(churches + nonprofit) is None  # 29 churches: too few
    assert report.typical_attendance(churches + mega + nonprofit) == 100  # 30 churches; the megachurch counts once


def test_days_open_uses_only_closures_pinned_to_two_weeks():
    def closed(start, live, gone):
        return {"first_indexed": start, "last_live_at": live, "expired_at": gone}

    pinned = [closed("2026-09-01", "2026-10-01T09:00:00+00:00", "2026-10-11")] * 30  # 30 + 10/2 = 35 days
    vague = [closed("2026-01-01", None, "2026-11-06")] * 100  # never seen open by a check: when it closed is unknown
    reopened = [closed("2026-09-01", "2026-11-10", "2026-10-11")] * 100  # seen open again after closing
    assert report.typical_days_open(pinned[:29] + vague + reopened) is None
    assert report.typical_days_open(pinned + vague + reopened) == 35


def test_active_openings_skip_expired_stale_and_reposts():
    today = date(2026, 11, 17)

    def posting(status, first_seen="2026-11-01", employer="Grace Church", title="Worship Pastor", state="Ohio"):
        return {
            "status": status,
            "first_indexed": first_seen,
            "company_name": employer,
            "job_name": title,
            "state": state,
        }

    jobs = [
        posting("open", "2024-01-01"),  # old, but a check saw it live
        posting("open", employer=" grace church "),  # the same job reposted: counted once
        posting("open", state="Indiana"),  # same title elsewhere: a different opening
        posting("unverified", title="Youth Pastor"),  # never checked, but recent
        posting("unverified", "2026-01-01", title="Organist"),  # never checked and old: likely closed
        posting("expired", title="Choir Director"),
        posting("unverified", employer=None),  # no employer: counted on its own
        posting("unverified", employer=None),
    ]
    assert report.active_openings(jobs, today) == 5


def test_figures_are_rounded():
    assert report.build_report({}, [job(pay=66260)] * 5)["pay"]["typical"] == 66500
    hourly = [job(pay=17.12, period="hour", hours="Part-Time")] * 5
    assert report.build_report({"type": "part-time"}, hourly)["pay"]["typical"] == 17.0
