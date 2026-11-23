"""The AI step after the BizDev sync: an employer is looked up once and its jobs share the result, only jobs whose page
couldn't be read are searched for pay, a result for another employer is ignored, and nothing is paid for twice.
OpenAI is replaced; test rows are removed afterwards."""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.core.config import get_settings
from app.core.db import get_conn
from app.extraction.schemas import ChurchFacts, JobExtraction
from app.ingestion import bizdev_enrich as be

KEY = "jobs.test-enrich.invalid/"


def add(n, org="Zzz Test Fellowship Church", status=None, posted=None, **extra):
    row = {"url_key": f"{KEY}{n}", "job_url": f"https://{KEY}{n}", "job_title": "Youth Pastor", "org_name": org,
           "org_website": "https://grace.invalid", "city": "Dallas", "state": "TX", "fetch_status": status,
           "date_posted": posted or date.today(), **extra}  # fmt: skip
    with get_conn() as conn:
        conn.execute(
            f"INSERT INTO public.church_jobs ({', '.join(row)}) VALUES ({', '.join(['%s'] * len(row))})",
            list(row.values()),
        )


def rows():
    with get_conn() as conn:
        return {
            r[0]: r[1:]
            for r in conn.execute(
                """SELECT right(url_key, 1), denomination, church_size, church_size_source, salary_min, salary_source,
                          employer_checked_at IS NOT NULL, pay_checked_at IS NOT NULL
                   FROM public.church_jobs WHERE url_key LIKE %s""",
                (KEY + "%",),
            ).fetchall()
        }


@pytest.fixture
def clean():
    def wipe():
        with get_conn() as conn:
            conn.execute("DELETE FROM public.church_jobs WHERE url_key LIKE %s", (KEY + "%",))

    wipe()
    yield
    wipe()


@pytest.fixture
def ai():
    calls = SimpleNamespace(church=0, jobs=[], org="Zzz Test Fellowship Church Dallas", pay=(52000, 60000))

    def parse(**kw):
        if kw["text_format"] is ChurchFacts:
            calls.church += 1
            facts = ChurchFacts(church_size=350, year=date.today().year, denomination="Baptist",
                                source_url="https://grace.invalid/about", evidence="About 350 people attend weekly")  # fmt: skip
            return SimpleNamespace(output_parsed=facts)
        calls.jobs.append(kw["input"])
        job = JobExtraction(
            page_type="job_posting", reason="a job posting", category="church", job_title="Youth Pastor", org_name=calls.org,
            org_website=None, city=None, state=None, country=None, date_posted=None, salary_min=calls.pay[0],
            salary_max=calls.pay[1], salary_period="year", hours="Full-Time", remote=None, denomination=None,
            church_size=None,
        )  # fmt: skip
        return SimpleNamespace(output_parsed=job)

    calls.client = SimpleNamespace(responses=SimpleNamespace(parse=parse))
    return calls


def test_an_employer_is_looked_up_once_and_its_jobs_share_the_result(clean, ai):
    add(1)
    add(2)
    assert be.enrich_employers(ai.client, "churches", 50, KEY) == 1
    assert ai.church == 1
    first = rows()
    assert first["1"][:3] == ("Baptist", 350, "https://grace.invalid/about") and first["2"][:3] == first["1"][:3]
    assert first["1"][5] and first["2"][5]  # both stamped
    looked_up = ai.church
    add(3)  # synced later
    be.enrich_employers(ai.client, "churches", 50, KEY)
    assert ai.church == looked_up and rows()["3"][:3] == ("Baptist", 350, "https://grace.invalid/about")


def test_pay_is_searched_only_for_unreadable_recent_jobs_and_only_for_the_right_employer(clean, ai):
    add(1, status="blocked")
    add(2, status="ok")  # the page was read and states no pay: a search wouldn't find it
    add(3, status="blocked", posted=date.today() - timedelta(days=400))  # probably closed
    add(4, status="expired")
    assert be.enrich_pay(ai.client, "churches", 50, KEY)[0] == 1
    r = rows()
    assert r["1"][3:5] == (52000, "ai") and r["1"][6]
    assert r["2"][3] is None and not r["2"][6] and not r["3"][6] and not r["4"][6]
    assert not any(f"{KEY}2" in i or f"{KEY}3" in i or f"{KEY}4" in i for i in ai.jobs)

    add(5, status="blocked")
    ai.org = "Totally Different Company"  # the search found another employer's posting
    be.enrich_pay(ai.client, "churches", 50, KEY)
    assert rows()["5"][3] is None and rows()["5"][6]  # no pay saved, but not searched again
    assert [i for i in ai.jobs if f"{KEY}5" in i] and len([i for i in ai.jobs if f"{KEY}1" in i]) == 1


def test_a_denomination_in_the_name_is_free_and_without_a_key_nothing_is_paid(clean, ai, monkeypatch):
    add(1, org="First Baptist Church of Zzz Test")
    monkeypatch.setattr(get_settings(), "openai_api_key", None)
    real = be.name_denominations
    monkeypatch.setattr(be, "name_denominations", lambda table: real(table, KEY))  # only the test rows
    monkeypatch.setattr(be, "share_known_values", lambda table: None)
    result = be.run()
    assert result["skipped"] and rows()["1"][0] == "Baptist" and ai.church == 0 and not ai.jobs


def test_an_employer_without_a_size_is_looked_up_again_after_90_days(clean, ai):
    long_ago = datetime.now(UTC) - timedelta(days=be.RETRY_SIZE_AFTER_DAYS + 10)
    add(1, org="Zzz Old Miss Church", employer_checked_at=long_ago)  # found nothing 100 days ago: tried again
    add(2, org="Zzz Recent Miss Church", employer_checked_at=datetime.now(UTC) - timedelta(days=10))
    add(3, org="Zzz Found Church", church_size=500, employer_checked_at=long_ago)  # has a size: never again
    assert [r[0] for r in be.employers_to_look_up("churches", 50, KEY)] == ["Zzz Old Miss Church"]
    be.enrich_employers(ai.client, "churches", 50, KEY)
    assert ai.church == 1 and rows()["1"][1] == 350


def test_a_size_from_the_job_page_keeps_its_own_source(clean, ai):
    add(1, church_size=120)  # read from the job page: no source recorded
    add(2)  # another job of the same employer
    be.enrich_employers(ai.client, "churches", 50, KEY)
    assert ai.church == 0  # one job with a size is enough: nothing to look up
    assert rows()["1"][1:3] == (120, None)


def test_same_employer():
    assert be.same_employer("Grace Fellowship", "Grace Fellowship Church")
    assert not be.same_employer("Grace Fellowship", "Acme Corp") and not be.same_employer(None, "x")


def test_denomination_answers_that_are_sentences_are_dropped_and_non_churches_are_not_looked_up():
    assert be.clean_denomination("Southern Baptist") == "Southern Baptist"
    assert be.clean_denomination("Christian and Missionary Alliance") == "Christian and Missionary Alliance"
    assert be.clean_denomination('Bible church; doctrinal statement says "requisite for fellowship"') is None
    assert be.clean_denomination("Christian nonprofit (not a church)") is None and be.clean_denomination(None) is None
    with get_conn() as conn:
        match = lambda name: conn.execute("SELECT %s ~* %s", (name, be.CHURCH_NAME)).fetchone()[0]
        assert match("First Baptist Church") and match("Grace Chapel") and not match("Mission Aviation Fellowship")
