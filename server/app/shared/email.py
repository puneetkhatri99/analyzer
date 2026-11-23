import re
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value: str) -> str:
    """Emails are stored trimmed and lowercase."""
    return value.strip().lower()


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_RE.match(value))


# ---- sending (SMTP: Resend, Gmail, SendGrid, any provider; see EMAIL.md) ------------------------------------------


class EmailError(Exception):
    pass


def _smtp() -> tuple[str | None, int, str | None, str | None]:
    """(host, port, user, password). SMTP_* settings; an older RESEND_API_KEY alone still works through Resend."""
    s = get_settings()
    if not s.smtp_host and s.resend_api_key:
        return "smtp.resend.com", 465, "resend", s.resend_api_key
    return s.smtp_host, s.smtp_port, s.smtp_user, s.smtp_password


def email_ready() -> bool:
    return bool(_smtp()[0] and get_settings().alert_from_email)


def send_email(to: list[str], subject: str, text: str) -> None:
    """Send a plain-text email through the SMTP server in the settings. Port 465 = SSL, any other = STARTTLS."""
    host, port, user, password = _smtp()
    message = EmailMessage()
    try:
        message["From"], message["To"], message["Subject"] = get_settings().alert_from_email, ", ".join(to), subject
        message.set_content(text)
        connect = smtplib.SMTP_SSL if port == 465 else smtplib.SMTP
        with connect(host, port, timeout=10) as server:
            if connect is smtplib.SMTP:
                server.starttls()
            if user:
                server.login(user, password or "")
            server.send_message(message)
    except smtplib.SMTPResponseException as e:
        detail = e.smtp_error.decode(errors="replace") if isinstance(e.smtp_error, bytes) else e.smtp_error
        raise EmailError(f"the mail server refused the email ({e.smtp_code}): {detail[:200]}") from e
    except (smtplib.SMTPException, OSError, ValueError) as e:
        raise EmailError(f"couldn't send through {host} ({e.__class__.__name__}: {str(e)[:150]})") from e
