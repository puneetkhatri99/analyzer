"""send_email: SSL on 465, STARTTLS otherwise, login only with a user, the old RESEND_API_KEY as a fallback."""

import smtplib

import pytest

from app.core.config import get_settings
from app.shared import email


@pytest.fixture
def server(monkeypatch):
    calls: list = []

    class Fake:
        def __init__(self, kind, host, port, timeout):
            calls.append(("connect", kind, host, port))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self):
            calls.append("starttls")

        def login(self, user, password):
            calls.append(("login", user, password))

        def send_message(self, message):
            calls.append(("send", message["To"], message["Subject"]))

    monkeypatch.setattr(smtplib, "SMTP", lambda h, p, timeout: Fake("plain", h, p, timeout))
    monkeypatch.setattr(smtplib, "SMTP_SSL", lambda h, p, timeout: Fake("ssl", h, p, timeout))
    s = get_settings()
    for name, value in [
        ("smtp_host", "mail.example.invalid"),
        ("smtp_port", 587),
        ("smtp_user", "me"),
        ("smtp_password", "pw"),
        ("resend_api_key", None),
        ("alert_from_email", "A <a@example.invalid>"),
    ]:
        monkeypatch.setattr(s, name, value)
    return calls


def test_port_587_uses_starttls_and_logs_in(server):
    email.send_email(["x@example.invalid", "y@example.invalid"], "Hi", "body")
    assert server == [
        ("connect", "plain", "mail.example.invalid", 587),
        "starttls",
        ("login", "me", "pw"),
        ("send", "x@example.invalid, y@example.invalid", "Hi"),
    ]


def test_port_465_uses_ssl_and_no_login_without_a_user(server, monkeypatch):
    monkeypatch.setattr(get_settings(), "smtp_port", 465)
    monkeypatch.setattr(get_settings(), "smtp_user", None)
    email.send_email(["x@example.invalid"], "Hi", "body")
    assert server == [("connect", "ssl", "mail.example.invalid", 465), ("send", "x@example.invalid", "Hi")]


def test_resend_key_alone_still_works_through_resend(server, monkeypatch):
    monkeypatch.setattr(get_settings(), "smtp_host", None)
    monkeypatch.setattr(get_settings(), "resend_api_key", "re_x")
    assert email.email_ready()
    email.send_email(["x@example.invalid"], "Hi", "body")
    assert server[:2] == [("connect", "ssl", "smtp.resend.com", 465), ("login", "resend", "re_x")]


def test_not_ready_without_host_or_sender(server, monkeypatch):
    assert email.email_ready()
    monkeypatch.setattr(get_settings(), "alert_from_email", None)
    assert not email.email_ready()
    monkeypatch.setattr(get_settings(), "alert_from_email", "A <a@example.invalid>")
    monkeypatch.setattr(get_settings(), "smtp_host", None)
    assert not email.email_ready()


def test_an_unreachable_server_becomes_an_email_error(monkeypatch):
    s = get_settings()
    for name, value in [("smtp_host", "127.0.0.1"), ("smtp_port", 1), ("resend_api_key", None)]:
        monkeypatch.setattr(s, name, value)
    with pytest.raises(email.EmailError, match=r"couldn't send through 127\.0\.0\.1"):
        email.send_email(["x@example.invalid"], "Hi", "body")
