from pipeline.fetch_jobs import parse_page, salary_from_text


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
    p = parse_page("<p>Grace Church Denomination Baptist -- SBC Church/Company Size 1001 to 1500 Job Type Full Time</p>", "Grace Church")
    assert p["church_size"] == 1001 and p["denomination"] == "Southern Baptist"
    assert parse_page("<p>Our sidebar mentions Presbyterian news</p>", "Grace Church")["denomination"] is None


def test_expiry_tracking_sql():
    """A job seen open, then closed, keeps both times; a later closed check doesn't move expired_at."""
    from app.db import get_conn
    from pipeline.fetch_jobs import UPDATE
    with get_conn() as conn:
        conn.execute("CREATE TEMP TABLE t_jobs (LIKE public.church_jobs INCLUDING DEFAULTS)")
        conn.execute("INSERT INTO t_jobs (url_key, job_url) VALUES ('k', 'u')")
        sql = UPDATE.format(table="t_jobs").replace("public.t_jobs", "t_jobs")
        base = {"key": "k", "lo": None, "hi": None, "period": None, "hours": None, "remote": None, "denomination": None, "church_size": None}
        conn.execute(sql, {**base, "status": "ok", "lo": 50000, "hi": 60000, "period": "year"})
        conn.execute(sql, {**base, "status": "expired"})
        first = conn.execute("SELECT last_live_at, expired_at, salary_min FROM t_jobs").fetchone()
        conn.execute(sql, {**base, "status": "expired"})
        again = conn.execute("SELECT last_live_at, expired_at, salary_min, fetch_status FROM t_jobs").fetchone()
    assert first[0] and first[1] and first[2] == 50000   # pay kept after the page closed
    assert again[:3] == first and again[3] == "expired"
