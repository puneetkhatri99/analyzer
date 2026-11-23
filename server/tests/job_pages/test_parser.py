from app.core.db import get_conn
from app.job_pages.check import UPDATE_BIZDEV
from app.job_pages.parser import denomination_in, parse_page, salary_from_text


def test_salary_from_text():
    assert salary_from_text("Pay: $45,000 - $55,000 per year") == (45000, 55000, "year")
    assert salary_from_text("$18 - $22 an hour") == (18, 22, "hour")
    assert salary_from_text("$50k–$60k") == (50000, 60000, "year")
    assert salary_from_text("Salary $62,000/yr") == (62000, 62000, "year")
    assert salary_from_text("Raise $2,000,000 - $3,000,000 for the building") is None
    assert salary_from_text("no pay mentioned") is None


def test_parse_page_json_ld():
    html = """<script type="application/ld+json">{"@type":"JobPosting","employmentType":"PART_TIME",
      "jobLocationType":"TELECOMMUTE","baseSalary":{"value":{"minValue":20,"maxValue":25,"unitText":"HOUR"}}}</script>
      <p>First Baptist Church</p>"""
    p = parse_page(html, "First Baptist Church")
    assert p["salary"] == (20, 25, "hour") and p["hours"] == "Part-Time" and p["remote"] == "true"
    assert p["denomination"] == "Baptist"


def test_church_size_and_label():
    p = parse_page(
        "<p>Grace Church Denomination Baptist -- SBC Church/Company Size 1001 to 1500 Job Type Full Time</p>",
        "Grace Church",
    )
    assert p["church_size"] == 1001 and p["denomination"] == "Baptist"  # the client merged Southern Baptist in
    assert parse_page("<p>Our sidebar mentions Presbyterian news</p>", "Grace Church")["denomination"] is None


def test_one_name_per_denomination():
    """The merges the client chose, applied to names found in the data."""
    same = {
        "Baptist": ["Southern Baptist", "Southern Baptist Convention", "Baptist -- SBC"],
        "Methodist": ["United Methodist", "Grace UMC"],
        "Catholic": ["Roman Catholic"],
        "Salvation Army": ["Evangelical (The Salvation Army)", "The Salvation Army"],
        "Lutheran": ["Lutheran Church-Missouri Synod", "Trinity Lutheran (LCMS)"],
        "Evangelical Covenant": ["Evangelical Covenant Church"],
        "Independent Christian Church": [
            "Independent Christian Churches", "Christian Church (Independent)",
            "Christian Church (disciples/independent)", "Christian churches and churches of Christ",
        ],
        "Friends (Quaker)": ["Friends Southwest"],
    }  # fmt: skip
    for name, values in same.items():
        for value in [name, *values]:
            assert denomination_in(value) == name, value
    assert denomination_in("Church of God in Christ") is None and denomination_in("Friends of the Homeless") is None


def test_dioceses_and_parishes_of_other_churches_are_not_catholic():
    assert denomination_in("Episcopal Diocese of Texas") == "Episcopal"
    assert denomination_in("Anglican Diocese of the Rocky Mountains") == "Episcopal"
    assert denomination_in("St. Paul Lutheran Parish") == "Lutheran"
    assert denomination_in("Grace Methodist Parish") == "Methodist"
    assert denomination_in("United Church of Christ") == "United Church of Christ"
    assert denomination_in("Lakeside Church of Christ") == "Church of Christ"
    assert denomination_in("Diocese of Tucson") == denomination_in("St. Timothy Roman Catholic Parish") == "Catholic"
    assert denomination_in("Acadia Parish Schools") is None  # a Louisiana parish is a county


def test_reread_keeps_details_found_earlier():
    """A page read with pay, then read again once closed (no details), keeps the pay."""
    with get_conn() as conn:
        conn.execute("CREATE TEMP TABLE t_jobs (LIKE public.church_jobs INCLUDING DEFAULTS)")
        conn.execute("INSERT INTO t_jobs (url_key, job_url) VALUES ('k', 'u')")
        sql = UPDATE_BIZDEV.format(table="t_jobs").replace("public.t_jobs", "t_jobs")
        base = {
            "key": "k",
            "lo": None,
            "hi": None,
            "period": None,
            "hours": None,
            "remote": None,
            "denomination": None,
            "church_size": None,
        }
        conn.execute(sql, {**base, "status": "ok", "lo": 50000, "hi": 60000, "period": "year"})
        conn.execute(sql, {**base, "status": "expired"})
        row = conn.execute("SELECT salary_min, fetch_status FROM t_jobs").fetchone()
    assert row == (50000, "expired")
