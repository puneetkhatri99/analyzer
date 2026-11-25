"""The daily feed job: new postings are loaded, unreviewed ones are judged in or out of scope, only churches are looked
up, an admin's call stands, an expired link tells the admin, and the admin endpoints. The feed download and OpenAI are replaced; rows are removed afterwards."""

from types import SimpleNamespace

import pytest

from app.core.config import get_settings
from app.core.db import get_conn
from app.extraction.schemas import ChurchFacts, PostingReview
from app.ingestion import daily_feed as df
from app.ingestion.feed import load_posting
from app.shared import alerts

ADMIN = "test-feed-admin@example.invalid"
FUTURE = "https://feed.example.invalid/f.json?Expires=4102444800&Signature=abc&Key-Pair-Id=K"
PAST = "https://feed.example.invalid/f.json?Expires=1000000000&Signature=abc&Key-Pair-Id=K"
KEYS = (df.URL_KEY, df.DONE_KEY, df.STATUS_KEY, alerts.ALERT_KEY)


def job(n: int, **extra):
    return {
        "post_uuid": f"test-feed-p{n}", "company_uuid": f"test-feed-c{n}", "company_name": f"First Baptist Church {n}",
        "company_url": "https://church.example.invalid",
        "post_url": f"https://jobs.example.invalid/view?id={n}", "job_name": "Youth Pastor", "city": "Dallas", "region": "TX",
        "country": "US", "first_indexed": "2026-11-17 10:00:00", "last_indexed": "2026-11-18 00:00:00", **extra,
    }  # fmt: skip


@pytest.fixture
def clean():
    """Puts back the feed settings and removes the test rows afterwards."""
    before = {k: df.get_setting(k) for k in KEYS}

    def wipe():
        with get_conn() as conn:
            conn.execute("DELETE FROM public.rejected_postings WHERE post_uuid LIKE 'test-feed-%'")
            conn.execute("DELETE FROM public.postings WHERE post_uuid LIKE 'test-feed-%'")
            conn.execute("DELETE FROM public.companies WHERE company_uuid LIKE 'test-feed-%'")
            conn.execute("DELETE FROM public.app_settings WHERE key = ANY(%s)", (list(KEYS),))

    wipe()
    yield
    wipe()
    for key, value in before.items():
        if value is not None:
            df.set_setting(key, value)


@pytest.fixture
def fake_ai(monkeypatch):
    calls = SimpleNamespace(review=0, church=0, churches=[])

    def parse(**kw):
        if kw["text_format"] is ChurchFacts:
            calls.church += 1
            calls.churches.append(kw["input"])
            facts = ChurchFacts(
                church_size=350,
                year=2025,
                denomination="Baptist",
                source_url="https://church.example.invalid/about",
                evidence="About 350 people worship with us each week",
            )
            return SimpleNamespace(output_parsed=facts)
        calls.review += 1
        if "Refused" in kw["input"]:  # the model refuses or answers nothing
            return SimpleNamespace(output_parsed=None)
        if "Cafe" in kw["input"]:  # "Church Street Cafe": the word church, but not a church
            review = PostingReview(
                employer_type="other", listed_employer_is_hiring=True, keep=False,
                exclude_reason="A cafe on Church Street, not a church", salary_min=15, salary_max=None,
                salary_period="hour", role="Other",
            )  # fmt: skip
        else:  # a church job; "Search Group" postings are listed by a search firm on the church's behalf
            review = PostingReview(
                employer_type="church", listed_employer_is_hiring="Search Group" not in kw["input"], keep=True,
                exclude_reason=None, salary_min=52000, salary_max=60000, salary_period="year",
                role="Youth & Student",
            )  # fmt: skip
        return SimpleNamespace(output_parsed=review)

    client = SimpleNamespace(responses=SimpleNamespace(parse=parse))
    monkeypatch.setattr(df, "OpenAI", lambda api_key: client)
    monkeypatch.setattr(get_settings(), "openai_api_key", "sk-test")
    monkeypatch.setattr(get_settings(), "enrich_max_per_run", 5)
    only_test = df.CHURCHES_TO_ENRICH.replace(
        "WHERE c.company_name", "WHERE c.company_uuid LIKE 'test-feed-%%' AND c.company_name"
    )
    assert only_test != df.CHURCHES_TO_ENRICH  # or the test would look up (and change) real churches
    monkeypatch.setattr(df, "CHURCHES_TO_ENRICH", only_test)
    return calls


HTML = (
    "<html><body>"
    + "Youth pastor wanted, pay $52,000 to $60,000 a year; cafe shifts $15 an hour. " * 20
    + "</body></html>"
)
NO_PAY = "<html><body>" + "Youth pastor wanted. Competitive salary and benefits. " * 20 + "</body></html>"


def scopes():
    """post_uuid -> (judged, salary_source, salary_min, employer_type, church_size, church_size_url) for test postings."""
    with get_conn() as conn:
        return {
            r[0]: r[1:]
            for r in conn.execute(
                """SELECT p.post_uuid, p.scope_checked_at IS NOT NULL, p.salary_source, p.salary_min, c.employer_type,
                          c.church_size, c.church_size_url
                   FROM public.postings p JOIN public.companies c USING (company_uuid)
                   WHERE p.post_uuid LIKE 'test-feed-%'"""
            ).fetchall()
        }


def rejected():
    with get_conn() as conn:
        return dict(
            conn.execute(
                "SELECT post_uuid, reason FROM public.rejected_postings WHERE post_uuid LIKE 'test-feed-%'"
            ).fetchall()
        )


def test_new_postings_are_loaded_and_unreviewed_ones_reviewed(clean, fake_ai, monkeypatch):
    with get_conn() as conn:
        load_posting(conn, job(1), "2026-11-04")  # already in the database, never reviewed
    feed = [
        job(1, post_html=HTML),
        job(2, comp_range="50000-60000 per year", post_html=HTML),
        job(3, post_html=HTML),
        job(4, company_name="Church Street Cafe", post_html=HTML),
    ]
    monkeypatch.setattr(df, "download", lambda url: feed)
    df.set_setting(df.URL_KEY, FUTURE)

    assert df.run_and_record(force=True) == 0

    status = df.get_setting(df.STATUS_KEY)
    assert status["ok"] and status["new"] == 3 and status["reviewed"] == 4 and status["excluded"] == 1
    assert status["pay"] == 3  # jobs 1, 3 and 4 (kept, should an admin include it again); job 2's feed states its pay
    s = scopes()
    assert s["test-feed-p1"][:2] == (True, "ai")  # job 1, loaded before without pay, gets it
    assert s["test-feed-p2"][1] is None and s["test-feed-p2"][2] == 50000
    # the cafe left the job tables for rejected_postings, with the reason
    assert "test-feed-p4" not in s and rejected() == {"test-feed-p4": "A cafe on Church Street, not a church"}
    # only churches are looked up; the cafe never is
    assert fake_ai.church == 3 and not any("Cafe" in i for i in fake_ai.churches)
    assert s["test-feed-p3"][4:] == (350, "https://church.example.invalid/about")
    assert status["run_id"].startswith("feed-") and status["calls"] == 0  # the fake calls have no usage
    with get_conn() as conn:  # the AI's role is kept beside the posting; the cafe's went with it to rejected_postings
        roles = dict(conn.execute("SELECT post_uuid, ai_role FROM public.postings WHERE post_uuid LIKE 'test-feed-%'"))
    assert roles == {f"test-feed-p{n}": "Youth & Student" for n in (1, 2, 3)}


def test_go_betweens_unparsed_feed_pay_and_unreviewed_postings(clean, fake_ai, monkeypatch):
    from app.report.service import blended_jobs

    with get_conn() as conn:
        load_posting(conn, job(6), "2026-11-04")  # in the database, not reviewed, and gone from the feed
    feed = [
        job(1, company_name="AGORA Search Group", post_html=HTML),  # a search firm listing a church's job
        job(2, comp_range="Competitive", post_html=HTML),  # feed pay text that isn't a figure: the AI's pay is used
        job(3, comp_range="42000", post_html=HTML),  # a bare figure: the feed's own pay
        job(5, post_html=NO_PAY),  # the AI answers 52,000, but the posting states no pay: a guess, not saved
    ]
    monkeypatch.setattr(df, "download", lambda url: feed)
    df.set_setting(df.URL_KEY, FUTURE)
    df.run_and_record(force=True)

    s = scopes()
    assert s["test-feed-p1"][3] is None  # the search firm isn't typed as a church...
    assert not any("AGORA" in i for i in fake_ai.churches)  # ...so its "attendance" is never looked up
    assert s["test-feed-p2"][1:3] == ("ai", 52000)
    assert s["test-feed-p3"][1:3] == (None, 42000)
    assert s["test-feed-p5"][:3] == (True, None, None)
    public = {d["post_uuid"] for d in blended_jobs()}
    assert {"test-feed-p1", "test-feed-p2", "test-feed-p3"} <= public and "test-feed-p6" not in public  # unreviewed


def test_a_failing_save_skips_that_posting_and_a_crash_still_ends_the_day(clean, fake_ai, monkeypatch):
    def broken(conn, post_uuid, reason, by):
        raise RuntimeError("database hiccup")

    monkeypatch.setattr(df, "reject_posting", broken)
    cafe = job(4, company_name="Church Street Cafe", post_html=HTML)
    refused = job(7, company_name="Refused Church", post_html=HTML)
    monkeypatch.setattr(df, "download", lambda url: [cafe, refused, job(1, post_html=HTML)])
    df.set_setting(df.URL_KEY, FUTURE)
    assert df.run_and_record(force=True) == 0  # the cafe's save failed and the AI refused job 7; the run went on
    status = df.get_setting(df.STATUS_KEY)
    assert status["reviewed"] == 1 and fake_ai.church == 1  # job 1 reviewed, and its church looked up
    assert scopes()["test-feed-p4"][0] is False and scopes()["test-feed-p7"][0] is False  # both retried next run

    def crash(url):
        raise RuntimeError("out of memory")

    monkeypatch.setattr(df, "download", crash)
    df.forget_today()
    assert df.run_and_record() == 1  # an unexpected error: recorded as today's run...
    assert df.get_setting(df.DONE_KEY) is not None and "RuntimeError" in df.get_setting(df.STATUS_KEY)["message"]
    assert df.run_and_record() == 0  # ...so the 15-minute timer doesn't run (and pay for) it again


def test_rejected_jobs_are_skipped_when_they_come_again(clean, fake_ai, monkeypatch, make_user, sign_in):
    from app.report.service import blended_jobs

    cafe = job(4, company_name="Church Street Cafe", post_html=HTML)
    monkeypatch.setattr(df, "download", lambda url: [job(1, post_html=HTML), cafe])
    df.set_setting(df.URL_KEY, FUTURE)
    df.run_and_record(force=True)
    public = {d["post_uuid"] for d in blended_jobs()}
    assert "test-feed-p1" in public and "test-feed-p4" not in public  # rejected postings leave every public figure

    # the same cafe job again, and re-posted under a new id: neither is loaded nor sent to the AI
    reposted = {**cafe, "post_uuid": "test-feed-p5"}
    monkeypatch.setattr(df, "download", lambda url: [job(1, post_html=HTML), cafe, reposted])
    df.run_and_record(force=True)
    status = df.get_setting(df.STATUS_KEY)
    assert status["new"] == 0 and status["skipped_rejected"] == 2 and fake_ai.review == 2
    assert set(rejected()) == {"test-feed-p4"} and "test-feed-p5" not in scopes()

    make_user(ADMIN, "a-strong-pass-1", role="viewer")
    viewer, _ = sign_in(ADMIN, "a-strong-pass-1")
    listed = viewer.get("/api/admin/rejected").json()["rows"]
    assert any(r["post_uuid"] == "test-feed-p4" and r["company_name"] == "Church Street Cafe" for r in listed)
    assert viewer.post("/api/admin/rejected/restore", json={"id": "test-feed-p4"}).status_code == 403
    make_user(ADMIN, "a-strong-pass-1")
    admin, _ = sign_in(ADMIN, "a-strong-pass-1")

    # an admin includes the cafe again: it comes back whole, pay included, and the AI never re-judges it
    assert admin.post("/api/admin/rejected/restore", json={"id": "test-feed-p4"}).json() == {"restored": True}
    assert scopes()["test-feed-p4"][:3] == (True, "ai", 15) and rejected() == {}
    assert admin.post("/api/admin/rejected/restore", json={"id": "test-feed-p4"}).status_code == 404
    # a feed job can't be deleted (the next run would add it back): it is rejected instead
    assert admin.delete("/api/admin/jobs", params={"source": "json", "id": "test-feed-p1"}).status_code == 400
    # and rejects job 1 by hand, with no reason given
    assert admin.post("/api/admin/jobs/reject", json={"id": "test-feed-p1", "reason": " "}).json() == {"rejected": True}
    assert rejected() == {"test-feed-p1": "Rejected by an admin"}
    assert admin.post("/api/admin/jobs/reject", json={"id": "nope"}).status_code == 404

    monkeypatch.setattr(df, "download", lambda url: [job(1, post_html=HTML), cafe])
    df.run_and_record(force=True)  # the restored cafe isn't re-judged; the rejected job 1 isn't reloaded
    assert "test-feed-p4" in scopes() and fake_ai.review == 2 and "test-feed-p1" not in scopes()
    assert df.get_setting(df.STATUS_KEY)["skipped_rejected"] == 1


def test_runs_once_a_day_unless_forced(clean, fake_ai, monkeypatch):
    seen = []
    monkeypatch.setattr(df, "download", lambda url: seen.append(url) or [])
    df.set_setting(df.URL_KEY, FUTURE)
    assert df.run_and_record() == 0 and df.run_and_record() == 0
    assert len(seen) == 1
    df.run_and_record(force=True)
    assert len(seen) == 2


def test_a_church_without_a_size_is_looked_up_again_after_90_days(clean, fake_ai):
    with get_conn() as conn:
        for n in (1, 2, 3):
            load_posting(conn, job(n), "2026-11-04")
        days = {1: df.RETRY_SIZE_AFTER_DAYS + 10, 2: 10, 3: df.RETRY_SIZE_AFTER_DAYS + 10}
        for n, ago in days.items():  # 1: missed long ago; 2: missed recently; 3: found long ago
            conn.execute(
                "UPDATE public.companies SET employer_type = 'church', enriched_at = now() - make_interval(days => %s),"
                " church_size = %s WHERE company_uuid = %s",
                (ago, 800 if n == 3 else None, f"test-feed-c{n}"),
            )
    assert df.enrich_churches(df.OpenAI(api_key="x"), 10) == 1  # fake_ai made OpenAI return its fake client
    assert fake_ai.church == 1 and "First Baptist Church 1" in fake_ai.churches[0]


def test_expired_link_alerts_the_admin_once_and_changes_nothing(clean, monkeypatch):
    sent = []
    monkeypatch.setattr(alerts, "get_recipients", lambda: ["a@example.invalid"])
    monkeypatch.setattr(alerts, "email_ready", lambda: True)
    monkeypatch.setattr(alerts, "send_email", lambda to, subject, text: sent.append(subject))
    monkeypatch.setattr(df, "download", lambda url: pytest.fail("an expired link must not be downloaded"))
    df.set_setting(df.URL_KEY, PAST)
    assert df.run_and_record(force=True) == 1
    assert df.run_and_record(force=True) == 1
    assert len(sent) == 1 and "expired" in sent[0]
    assert "expired" in df.get_setting(df.STATUS_KEY)["message"]


def test_refused_link_is_reported(clean, monkeypatch):
    def refuse(url):
        raise df.FeedError("The feed refused the link: it has expired or is wrong.")

    monkeypatch.setattr(df, "download", refuse)
    monkeypatch.setattr(alerts, "get_recipients", lambda: [])
    df.set_setting(df.URL_KEY, FUTURE)
    assert df.run_and_record(force=True) == 1
    assert df.get_setting(df.STATUS_KEY)["ok"] is False


def test_feed_link_is_checked():
    assert df.check_feed_url(FUTURE).year == 2100
    for bad in ("http://x.example.invalid/f.json?Expires=4102444800", "https://x.example.invalid/f.json", "nonsense"):
        with pytest.raises(ValueError):
            df.check_feed_url(bad)
    assert "Signature" not in str(df.link_state(FUTURE))


def test_admin_endpoints(clean, make_user, sign_in, client, monkeypatch):
    assert client.get("/api/admin/feed").status_code == 401
    make_user(ADMIN, "a-strong-pass-1")
    admin, _ = sign_in(ADMIN, "a-strong-pass-1")
    assert admin.post("/api/admin/feed", json={"url": "https://x.example.invalid/f.json"}).status_code == 422
    r = admin.post("/api/admin/feed", json={"url": FUTURE})
    assert r.status_code == 200 and r.json()["expires_at"].startswith("2100") and "Signature" not in r.text
    assert admin.get("/api/admin/feed").json()["url"] == "https://feed.example.invalid/f.json"
    monkeypatch.setattr(df, "run_and_record", lambda **kw: 0)
    assert admin.post("/api/admin/feed/run").status_code == 200


def test_ai_calls_in_a_run_carry_its_id(clean):
    from app.ai_usage.service import current_run, record

    usage = SimpleNamespace(input_tokens=1000, output_tokens=100, input_tokens_details=SimpleNamespace(cached_tokens=0))
    token = current_run.set("feed-test-run")
    try:
        record(
            SimpleNamespace(usage=usage, output=[]),
            purpose="pay_extract",
            url="u",
            model="gpt-5.4-mini",
            admin_email=None,
        )
        record(
            SimpleNamespace(usage=usage, output=[]),
            purpose="pay_extract",
            url="u",
            model="gpt-5.4-mini",
            admin_email=None,
        )
        cost, calls = df.run_cost("feed-test-run")
    finally:
        current_run.reset(token)
        record(
            SimpleNamespace(usage=usage, output=[]), purpose="extract", url="u", model="gpt-5.4-mini", admin_email="x"
        )
    try:
        assert calls == 2 and cost > 0
        assert df.run_cost("feed-test-run")[1] == 2  # the later call, made outside the run, isn't counted
    finally:
        with get_conn() as conn:
            conn.execute(
                "DELETE FROM public.ai_usage WHERE run_id = 'feed-test-run' OR (url = 'u' AND admin_email = 'x') OR url = 'u'"
            )


def test_parallel_ai_calls_keep_the_run_id_and_order():
    from app.ai_usage.service import current_run

    def work(n):
        if n == 3:
            raise TimeoutError("slow")
        return n, current_run.get()

    token = current_run.set("feed-parallel-test")
    try:
        got = list(df.ai_map(work, [1, 2, 3, 4, 5]))
    finally:
        current_run.reset(token)
    assert [r for r, _ in got] == [(1, "feed-parallel-test"), (2, "feed-parallel-test"), None,
                                    (4, "feed-parallel-test"), (5, "feed-parallel-test")]  # fmt: skip
    assert got[2][1].startswith("TimeoutError")


def test_odd_entries_in_the_feed_are_ignored_not_fatal(monkeypatch):
    class Reply:
        ok, status_code = True, 200

        @staticmethod
        def json():
            return [None, "x", 5, [], {"post_uuid": ["a"]}, {"post_uuid": "ok-1", "post_url": 5}]

    monkeypatch.setattr(df, "get_public", lambda url, **kw: Reply())
    assert df.download("https://feed.example/x") == [{"post_uuid": "ok-1", "post_url": 5}]
    assert df._url({"post_url": 5}) == "5"  # a non-text address no longer breaks the "seen before" check
