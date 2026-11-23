"""Reposts and copies count once (brief D3), and different openings stay apart."""

from app.report.reposts import group_openings, merge_reposts


def job(n, employer="Grace Church", title="Worship Pastor", city="Columbus", state="Ohio", day="2026-10-01", **extra):
    return {
        "post_uuid": f"j{n}", "source": "json", "company_name": employer, "job_name": title, "city": city,
        "state": state, "first_indexed": day, "added_at": None, "post_url": f"https://jobs.example/{n}",
        "salary_min": None, "salary_max": None, "salary_period": None, "church_size": None, "denomination": None,
        **extra,
    }  # fmt: skip


def openings(*jobs):
    return len(merge_reposts(list(jobs)))


def test_wording_and_employer_variants_are_one_opening():
    assert openings(job(1), job(2, title="Pastor of Worship (Full-Time)")) == 1
    assert openings(job(1), job(2, title="Worship Pastor - Columbus, OH")) == 1  # the job's own place
    assert openings(job(1), job(2, title="Worship Pastor - Grace Church")) == 1  # the employer's own name
    assert openings(job(1, employer="First Baptist Church"), job(2, employer="First Baptist Church, Inc.")) == 1
    assert openings(job(1, title="Assoc. Pastor of Students"), job(2, title="Associate Pastor - Student")) == 1
    # one word shared with the employer's name is part of the title: these are two jobs
    worship_center = {"employer": "Worship Center Church"}
    assert openings(job(1, title="Worship Pastor", **worship_center), job(2, title="Pastor", **worship_center)) == 2


def test_the_same_title_twice_at_the_same_church_and_time_counts_once():
    assert openings(job(1), job(2)) == 1  # the client's choice


def test_a_feed_and_sheet_copy_with_the_same_link_are_one():
    feed = job(1, post_url="https://www.jobs.example/view/7/")
    sheet = job(2, employer="Grace", title="Worship Leader", source="churches", post_url="http://jobs.example/view/7")
    assert openings(feed, sheet) == 1


def test_one_link_in_two_states_is_two_openings():
    careers = "https://steiger.example/careers"
    mn = job(1, title="Church Engagement Officer", city="Minneapolis", state="Minnesota", post_url=careers)
    tx = job(2, title="Church Engagement Officer - Texas", city="Houston", state="Texas", post_url=careers)
    assert openings(mn, tx) == 2
    assert openings(mn, job(3, title="Engagement", city=None, state=None, post_url=careers)) == 1  # no state: one


def test_links_that_differ_only_by_query_are_different_jobs():
    a = job(1, title="Youth Pastor", post_url="https://board.example/view?id=1")
    b = job(2, title="Kids Pastor", post_url="https://board.example/view?id=2")
    assert openings(a, b) == 2


def test_reposts_chain_within_90_days():
    assert openings(job(1, day="2026-01-01"), job(2, day="2026-03-22"), job(3, day="2026-06-10")) == 1  # 0, 80, 160
    assert openings(job(1, day="2026-01-01"), job(2, day="2026-07-20")) == 2  # 200 days apart: a new opening


def test_cities():
    assert openings(job(1, city="Dallas", state="Texas"), job(2, city="Austin", state="Texas")) == 2
    assert openings(job(1), job(2, city=None)) == 1  # no city: joins the only city its group has
    # no city, and the group has two cities: it can't tell which, so it stays apart from both
    assert openings(job(1), job(2, city="Dayton"), job(3, city=None)) == 3
    assert openings(job(1, state="Ohio"), job(2, state="Indiana", city="Columbus")) == 2


def test_no_employer_is_only_matched_by_its_link():
    assert openings(job(1, employer=None), job(2, employer=None)) == 2
    assert openings(job(1, employer=None), job(2, employer=None, post_url="https://jobs.example/1")) == 1


def test_the_kept_row_has_the_newest_pay_and_fills_gaps():
    old = job(1, day="2026-01-01", salary_min=50000, salary_max=50000, salary_period="year", church_size=400)
    new = job(2, day="2026-02-01", salary_min=55000, salary_max=55000, salary_period="year", denomination="Baptist")
    newest = job(3, day="2026-03-01")  # no pay
    (kept,) = merge_reposts([old, new, newest])
    assert kept["post_uuid"] == "j2" and kept["salary_min"] == 55000  # the raised salary
    assert kept["church_size"] == 400 and kept["denomination"] == "Baptist"


def test_groups_say_why_they_were_linked():
    groups = {frozenset(d["post_uuid"] for d in copies): reasons for copies, reasons in group_openings(
        [job(1, day="2026-01-01"), job(2, day="2026-01-31"), job(3, title="Other Job", post_url="https://jobs.example/1")]
    )}  # fmt: skip
    assert groups == {frozenset({"j1", "j2", "j3"}): {"same job within 30 days", "same link"}}


def test_a_malformed_link_does_not_break_the_merge():
    bad = ["http://[::1", "javascript:alert(1)", "not a url", "", "https://a.com/\x00"]
    jobs = [job(i, post_url=u) for i, u in enumerate(bad)]
    assert openings(*jobs) >= 1  # no ValueError; one bad scraped address must not take the whole report down
    assert openings(job(1, post_url="http://[bad"), job(2, post_url="http://[bad")) == 1  # the same text still matches
