from collections import defaultdict

from pipeline.collect_jobs import (SiteProblem, _bamboohr, _breezy, _lever, _workday, employer_sites, http_problem, is_us,
                                   platform_problems, source_health, split_place, state_code)
from pipeline.fetch_jobs import parse_page


def test_http_problem_kinds():
    assert http_problem(200) is None and http_problem(301) is None
    assert http_problem(404) == http_problem(410) == "site changed"
    assert http_problem(403) == http_problem(429) == "blocked"
    assert http_problem(503) == "site down"


def test_source_health_spots_silent_breakage():
    st = lambda **kw: defaultdict(int, kw)
    assert source_health("sbc", st(listed=300), last=310, days=45) == []
    assert source_health("efca", st(listed=0), last=None, days=45)[0][0] == "site changed"
    assert source_health("employers", st(listed=0), last=None, days=45) == []  # no churches is not a site change
    assert "down from 400" in source_health("churchstaffing", st(listed=30), last=400, days=45)[0][1]
    assert [k for k, _ in source_health("sbc", st(listed=50, read=10, no_details=8, blocked=6), None, 45)] == ["site changed", "blocked"]
    assert source_health("churchstaffing", st(listed=50, listed_no_title=50), None, 45) == []  # titles come from its pages


def test_platform_problems_only_when_every_church_fails():
    gone = SiteProblem("site changed", "https://x.bamboohr.com/careers/list", "HTTP 404")
    churches = [{"platform": "BambooHR", "problem": gone}] * 3 + [{"platform": "Breezy", "problem": gone}, {"platform": "Breezy", "problem": None}]
    out = platform_problems(churches)
    assert len(out) == 1 and out[0].kind == "site changed" and "BambooHR: all 3" in out[0].detail


def test_places():
    assert split_place("Macomb, IL") == ("Macomb", "IL", "US")
    assert split_place("Austin, Texas, United States") == ("Austin", "TX", "US")
    assert split_place("724 West 11th Street, Alma, GA") == ("Alma", "GA", "US")
    assert split_place("Alma GA 31510") == ("Alma", "GA", "US")
    assert split_place("Lincolnton, GA, 30817, US") == ("Lincolnton", "GA", "US")
    assert split_place("Toronto, ON") == ("Toronto", None, None)
    assert split_place("2 Locations") == ("2 Locations", None, None)
    assert split_place(None) == (None, None, None)
    assert state_code("texas") == "TX" and state_code("ON") is None


def test_is_us():
    assert is_us("TX", "US") and is_us("TX", None) and is_us(None, None)  # unknown places are kept
    assert is_us(None, "United States") and is_us("Florida", None)
    assert not is_us(None, "CA") and not is_us("ON", "Canada") and not is_us("Ontario", None)


def test_employer_sites_keeps_one_per_church_and_skips_non_churches():
    rows = [
        ("Church of the Highlands", "https://church-of-the-highlands.breezy.hr/p/1-audio"),
        ("Church of the Highlands", "https://church-of-the-highlands.breezy.hr/p/2-pastor"),
        ("Alive Church", "https://alivechurch.bamboohr.com/careers/67"),
        ("LCBC Church", "https://jobs.lever.co/lcbcchurch/abc-123"),
        ("Gateway Church", "https://gatewaystaff.wd5.myworkdayjobs.com/en-US/GatewayStaff/job/Southlake/Pastor_R1"),
        ("National Church Residences", "https://nationalchurchresidences.wd5.myworkdayjobs.com/en-US/NCR/job/X/Y_R2"),
        ("Houston Methodist", "https://houstonmethodist.wd1.myworkdayjobs.com/en-US/HM/job/X/Nurse_R3"),
        ("Grace Church", "https://paycomonline.net/v4/ats/web.php/jobs/123"),  # no public API
    ]
    sites = employer_sites(rows)
    assert [(f, org) for f, _, org in sites] == [(_breezy, "Church of the Highlands"), (_bamboohr, "Alive Church"),
                                               (_lever, "LCBC Church"), (_workday, "Gateway Church")]
    assert sites[2][1] == "lcbcchurch"


def test_parse_page_reads_who_where_when():
    html = """<script type="application/ld+json">{"@type":"JobPosting","title":"Worship Leader","datePosted":"2026-11-02",
      "hiringOrganization":{"@type":"Organization","name":"Life Church"},
      "jobLocation":[{"@type":"Place","address":{"addressLocality":"Livonia","addressRegion":"MI","addressCountry":{"name":"US"}}}]}</script>"""
    p = parse_page(html, None)
    assert (p["title"], p["org"], p["city"], p["state"], p["country"], p["date_posted"]) == \
        ("Worship Leader", "Life Church", "Livonia", "MI", "US", "2026-11-02")
