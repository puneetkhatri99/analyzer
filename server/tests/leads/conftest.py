"""Shared by the email tests: no mail server is ever called, smtplib.SMTP / SMTP_SSL are replaced."""

import smtplib
from types import SimpleNamespace

import pytest

from app.core.config import get_settings
from app.leads import daily_report as dr


@pytest.fixture
def outbox(monkeypatch):
    """Records every email 'sent' (to, from, subject, text); set .fail = True to make the server refuse."""
    box = SimpleNamespace(sent=[], fail=False)

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self):
            pass

        def login(self, user, password):
            pass

        def send_message(self, message):
            box.sent.append(  # an attempt is recorded even when the server then refuses it
                {
                    "to": [a.strip() for a in message["To"].split(",")],
                    "from": message["From"],
                    "subject": message["Subject"],
                    "text": message.get_content(),
                }
            )
            if box.fail:
                raise smtplib.SMTPResponseException(550, b"domain not verified")

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTP)
    monkeypatch.setattr(get_settings(), "smtp_host", "smtp.example.invalid")
    monkeypatch.setattr(get_settings(), "alert_from_email", "Leads <alerts@example.invalid>")
    monkeypatch.setattr(dr, "script_log", lambda name: "")  # keep test runs out of the log files and Axiom
    return box
