"""Telling the admin: the saved "daily report" addresses, and a once-a-day alert email to them.
Lives in shared/ because both the daily lead report (leads) and the jobs feed / syncs (ingestion) use it."""

import logging
from datetime import UTC, datetime

from app.core.config import get_settings
from app.core.settings_store import get_setting, set_setting
from app.shared.email import EmailError, email_ready, send_email

log = logging.getLogger("alerts")

RECIPIENTS = "hot_lead_emails"  # app_settings key: Admin → Settings → Daily lead report
ALERT_KEY = "daily_feed_alert_for"  # the day an alert last went out (name kept from when it lived in daily_feed)


def get_recipients() -> list[str]:
    return get_setting(RECIPIENTS, [])


def admin_link() -> str:
    return f"{get_settings().site_url.rstrip('/')}/admin#settings"


def alert_admin(subject: str, text: str) -> None:
    """Email the daily-report addresses, at most once a day. Never raises: the run's own result matters more."""
    today = datetime.now(UTC).date().isoformat()
    if get_setting(ALERT_KEY) == today:
        return
    recipients = get_recipients()
    if not recipients or not email_ready():
        log.warning("Admin not emailed (%s): no addresses in Admin → Settings, or email isn't set up", subject)
        return
    try:
        send_email(recipients, subject, text)
    except EmailError as e:
        log.error("Admin not emailed (%s): %s", subject, e)
        return
    set_setting(ALERT_KEY, today, by="daily-feed")
