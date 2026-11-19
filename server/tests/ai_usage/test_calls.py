"""The AI costs page's calls list: filters, paging, and deleting rows, which must change every total."""

import pytest

from app.core.db import get_conn

ADMIN = "test-calls-admin@example.invalid"
MARK = "https://calls.example.invalid/"


@pytest.fixture
def calls(make_user, sign_in):
    """Five test calls: 3 in run r1 (2 pay, 1 church), 2 outside any run. Removed afterwards."""
    make_user(ADMIN, "a-strong-pass-1")
    admin, _ = sign_in(ADMIN, "a-strong-pass-1")
    rows = [
        ("pay_extract", "test-run-1", "a"), ("pay_extract", "test-run-1", "b"), ("church_lookup", "test-run-1", "c"),
        ("extract", None, "d"), ("extract", None, "e"),
    ]  # fmt: skip
    with get_conn() as conn:
        for purpose, run, name in rows:
            conn.execute(
                """INSERT INTO public.ai_usage (purpose, url, model, input_tokens, output_tokens, cost_usd, run_id)
                   VALUES (%s, %s, 'gpt-5.4-mini', 100, 10, 0.5, %s)""",
                (purpose, MARK + name, run),
            )
    yield admin
    with get_conn() as conn:
        conn.execute("DELETE FROM public.ai_usage WHERE url LIKE %s", (MARK + "%",))


def listing(admin, **params):
    return admin.get("/api/admin/costs/calls", params={"q": MARK, **params}).json()


def test_filters_and_paging(calls):
    assert listing(calls)["total"] == 5
    assert listing(calls, purpose="pay_extract")["total"] == 2
    assert listing(calls, run="test-run-1")["total"] == 3
    assert listing(calls, run="none")["total"] == 2
    assert listing(calls, run="test-run-1", purpose="extract")["total"] == 0
    assert listing(calls, date_from="2999-01-01")["total"] == 0
    assert listing(calls, q=MARK + "a")["total"] == 1
    assert float(listing(calls)["cost"]) == 2.5
    assert len(listing(calls, page=1)["rows"]) == 5 and listing(calls, page=2)["rows"] == []
    assert calls.get("/api/admin/costs/calls", params={"date_from": "nonsense"}).status_code == 422


def test_deleting_changes_every_total(calls):
    before = calls.get("/api/admin/costs").json()
    ids = [r["id"] for r in listing(calls, purpose="pay_extract")["rows"]]
    assert calls.post("/api/admin/costs/calls/delete", json={"ids": ids}).json() == {"deleted": 2}
    after = calls.get("/api/admin/costs").json()
    assert after["totals"]["calls"] == before["totals"]["calls"] - 2
    assert float(before["totals"]["total"]) - float(after["totals"]["total"]) == pytest.approx(1.0)
    run = next(r for r in after["by_run"] if r["run_id"] == "test-run-1")
    assert run["calls"] == 1  # the run's own total dropped too

    out = calls.post("/api/admin/costs/calls/delete-matching", json={"run": "test-run-1", "q": MARK})
    assert out.json() == {"deleted": 1}
    assert not any(r["run_id"] == "test-run-1" for r in calls.get("/api/admin/costs").json()["by_run"])
    assert listing(calls)["total"] == 2  # the calls outside the run are untouched


def test_admin_only(client):
    assert client.get("/api/admin/costs/calls").status_code == 401
    assert client.post("/api/admin/costs/calls/delete", json={"ids": [1]}).status_code == 401
    assert client.post("/api/admin/costs/calls/delete-matching", json={}).status_code == 401


def test_pricing_lists_every_model_and_a_profile_for_each_kind_of_call(calls):
    p = calls.get("/api/admin/costs").json()["pricing"]
    assert {"gpt-5.4-nano", "gpt-5.4-mini", "gpt-5.4", "gpt-5.5"} <= set(p["models"])
    assert p["models"]["gpt-5.4-mini"] == {"input": 0.75, "cached": 0.075, "output": 4.5} and p["web_search"] == 0.01
    assert {"posting_review", "church_lookup", "bizdev_pay"} <= set(p["profiles"])
    assert all(set(v) >= {"input", "cached", "output", "searches", "measured"} for v in p["profiles"].values())
