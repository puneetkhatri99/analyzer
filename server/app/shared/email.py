import re

import requests

from app.core.config import get_settings

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value: str) -> str:
    """Emails are stored trimmed and lowercase."""
    return value.strip().lower()


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_RE.match(value))


# ---- sending (Resend) ------------------------------------------------------------------------------------------

RESEND_URL = "https://api.resend.com/emails"


class EmailError(Exception):
    pass


def email_ready() -> bool:
    s = get_settings()
    return bool(s.resend_api_key and s.alert_from_email)


def send_email(to: list[str], subject: str, text: str) -> None:
    s = get_settings()
    try:
        r = requests.post(
            RESEND_URL,
            headers={"Authorization": f"Bearer {s.resend_api_key}"},
            json={"from": s.alert_from_email, "to": to, "subject": subject, "text": text},
            timeout=10,
        )
    except requests.RequestException as e:
        raise EmailError(f"couldn't reach Resend ({e.__class__.__name__})") from e
    if not r.ok:
        raise EmailError(f"Resend refused the email ({r.status_code}): {r.text[:200]}")
