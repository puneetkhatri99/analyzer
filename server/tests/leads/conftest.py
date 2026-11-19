"""Shared by the email tests: Resend is never called, requests.post is replaced."""

from types import SimpleNamespace

import pytest
import requests

from app.core.config import get_settings
from app.leads import daily_report as dr


@pytest.fixture
def resend(monkeypatch):
    """Records every email 'sent'; set .fail = True to make Resend refuse."""
    box = SimpleNamespace(sent=[], fail=False)

    def post(url, headers, json, timeout):
        box.sent.append(json)
        return SimpleNamespace(ok=not box.fail, status_code=422 if box.fail else 200, text="domain not verified")

    monkeypatch.setattr(requests, "post", post)
    monkeypatch.setattr(get_settings(), "resend_api_key", "re_test")
    monkeypatch.setattr(get_settings(), "alert_from_email", "Leads <alerts@example.invalid>")
    monkeypatch.setattr(dr, "script_log", lambda name: "")  # keep test runs out of the log files and Axiom
    return box
