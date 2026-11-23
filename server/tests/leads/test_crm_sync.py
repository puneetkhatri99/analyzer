"""The weekly newsletter sync: only sign-ups who ticked the box are sent, with their activity; nothing is sent without
keys; a lead is sent again only after new activity. Mailchimp is never called: requests.request is replaced."""

from types import SimpleNamespace

import pytest

from app.core.config import get_settings
from app.core.db import get_conn
from app.leads import crm_sync

WANTS = "test-crm-wants@example.invalid"
NO = "test-crm-no@example.invalid"


@pytest.fixture
def mailchimp(monkeypatch):
    """Keys set, and every Mailchimp call recorded instead of sent."""
    calls = []

    def request(method, url, auth, json, timeout):
        calls.append((method, url, json))
        return SimpleNamespace(ok=True, status_code=200, text="")

    monkeypatch.setattr(crm_sync.requests, "request", request)
    monkeypatch.setattr(get_settings(), "mailchimp_api_key", "abc123-us21")
    monkeypatch.setattr(get_settings(), "mailchimp_list_id", "list1")
    yield calls
    with get_conn() as conn:
        conn.execute("DELETE FROM public.leads WHERE email = ANY(%s)", ([WANTS, NO],))


def sign_up(client, email, newsletter):
    lead = {"name": "Ann Lee Smith", "email": email, "organization": "Grace Church", "role": "Worship",
            "location": "Ohio", "newsletter": newsletter}  # fmt: skip
    assert client.post("/api/leads", json=lead).status_code == 200


def test_only_leads_who_ticked_the_box_are_sent_with_their_activity(client, mailchimp):
    sign_up(client, WANTS, True)
    sign_up(client, NO, False)
    offer = {"email": WANTS, "type": "offer", "details": {"amount": 52000, "unit": "year"}}
    assert client.post("/api/leads/events", json=offer).status_code == 200

    status = crm_sync.run()
    assert status["sent"] == 1 and status["failed"] == 0
    member = f"https://us21.api.mailchimp.com/3.0/lists/list1/members/{crm_sync.member_id(WANTS)}"
    (put, tags, note) = [c for c in mailchimp if c[1].startswith(member)]
    assert put[0] == "PUT" and put[2]["email_address"] == WANTS and put[2]["status_if_new"] == "subscribed"
    assert put[2]["merge_fields"] == {"FNAME": "Ann", "LNAME": "Lee Smith"}
    assert tags[1].endswith("/tags") and {t["name"] for t in tags[2]["tags"]} == {crm_sync.SITE_TAG, "Checked an offer"}
    assert (
        note[1].endswith("/notes")
        and "Grace Church" in note[2]["note"]
        and "Checked an offer of 52000" in note[2]["note"]
    )
    assert not any(crm_sync.member_id(NO) in url for _, url, _ in mailchimp)  # never asked: never sent

    mailchimp.clear()
    assert crm_sync.run()["sent"] == 0 and mailchimp == []  # nothing new since
    client.post("/api/leads/events", json={**offer, "type": "download", "details": {}})
    assert crm_sync.run()["sent"] == 1  # something new: sent again, with only the new activity
    assert "Downloaded the report" in mailchimp[-1][2]["note"] and "offer" not in mailchimp[-1][2]["note"]


def test_the_tick_is_kept_when_they_come_back(client, mailchimp):
    sign_up(client, WANTS, True)
    sign_up(client, WANTS, False)  # unsubscribing is done in Mailchimp, not by leaving the box unticked next time
    with get_conn() as conn:
        (at,) = conn.execute("SELECT newsletter_at FROM public.leads WHERE email = %s", (WANTS,)).fetchone()
    assert at is not None


def test_no_keys_sends_nothing_and_a_dry_run_sends_nothing(client, mailchimp, monkeypatch):
    sign_up(client, WANTS, True)
    assert crm_sync.run(dry_run=True)["sent"] == 0 and mailchimp == []
    monkeypatch.setattr(get_settings(), "mailchimp_api_key", None)
    assert crm_sync.run()["skipped"] == "no key" and mailchimp == []


def test_a_refused_send_is_counted_and_retried(client, mailchimp, monkeypatch):
    sign_up(client, WANTS, True)
    monkeypatch.setattr(
        crm_sync.requests, "request",
        lambda *a, **k: SimpleNamespace(ok=False, status_code=400, text="", json=lambda: {"detail": "Invalid Resource"}),
    )  # fmt: skip
    status = crm_sync.run()
    assert status["failed"] == 1 and not status["ok"]
    with get_conn() as conn:
        (synced,) = conn.execute("SELECT synced_mailchimp_at FROM public.leads WHERE email = %s", (WANTS,)).fetchone()
    assert synced is None  # so the next run sends it again


def test_the_key_names_its_data_centre():
    assert crm_sync.api_base("abc-us21") == "https://us21.api.mailchimp.com/3.0"
    with pytest.raises(crm_sync.MailchimpError):
        crm_sync.api_base("no-data-centre-here.example")
