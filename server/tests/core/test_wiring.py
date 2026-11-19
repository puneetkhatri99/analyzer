"""Startup wiring (which timers start where) and where the sign-in lockout takes the visitor's address from."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.ingestion import bizdev_sync, daily_feed
from app.leads import daily_report
from app.main import app


@pytest.fixture
def timers(monkeypatch):
    started: list[str] = []

    class Stop:
        def __init__(self, name):
            self.name = name

        def set(self):
            started.append(f"stopped:{self.name}")

    for name, mod in (("report", daily_report), ("feed", daily_feed), ("bizdev", bizdev_sync)):
        monkeypatch.setattr(mod, "start_scheduler", lambda n=name: started.append(f"started:{n}") or Stop(n))
    monkeypatch.setattr(daily_report, "email_ready", lambda: True)
    return started


@pytest.mark.parametrize(
    ("env", "expected"),
    [("production", {"report", "feed", "bizdev"}), ("development", set())],
)
def test_timers_start_only_in_production_and_stop_on_shutdown(monkeypatch, timers, env, expected):
    monkeypatch.setattr(get_settings(), "app_env", env)
    with TestClient(app):
        assert {t.split(":")[1] for t in timers if t.startswith("started")} == expected
    assert {t.split(":")[1] for t in timers if t.startswith("stopped")} == expected


def test_report_timer_needs_email_set_up(monkeypatch, timers):
    monkeypatch.setattr(get_settings(), "app_env", "production")
    monkeypatch.setattr(daily_report, "email_ready", lambda: False)
    with TestClient(app):
        assert {t.split(":")[1] for t in timers if t.startswith("started")} == {"feed", "bizdev"}


def test_login_lockout_counts_the_connection_address_not_x_forwarded_for():
    c = TestClient(app)
    body = {"email": "nobody@example.invalid", "password": "wrong-password"}
    for i in range(5):
        assert c.post("/api/admin/login", json=body, headers={"X-Forwarded-For": f"10.0.0.{i}"}).status_code == 401
    # the email key blocks too, but a sixth try from a "new" forwarded address must be refused by the IP key as well
    r = c.post(
        "/api/admin/login", json={**body, "email": "other@example.invalid"}, headers={"X-Forwarded-For": "10.9.9.9"}
    )
    assert r.status_code == 429
