"""daily-report: email yesterday's new hot leads, and the day's other numbers, to the addresses set in
Admin → Settings. Sent through Resend; a cron job runs it (DAILY_REPORT_CRON.md).

  python -m app.cli daily-report                    # sends at 8 AM New York time (9 AM retries), once per day
  python -m app.cli daily-report --force            # send yesterday's report now
  python -m app.cli daily-report --dry-run          # print it, send nothing
  python -m app.cli daily-report --day 2026-11-16   # a given day, sent now

Cron runs it at 12:00, 13:00 and 14:00 UTC, which always includes 8 AM and 9 AM in New York (daylight or standard
time). The 8 AM run sends; the 9 AM run sends only if 8 AM's failed; the day is never sent twice. Days are midnight
to midnight US Eastern, worked out by Postgres, so no timezone package is needed.
"""

import argparse
import logging
from datetime import date, timedelta
from typing import Any

import requests
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import get_settings
from app.core.db import get_conn
from app.core.logs import script_log
from app.leads import HOT_AT_REPORTS

log = logging.getLogger("daily_report")

TZ = "America/New_York"
SEND_HOURS = (8, 9)  # New York time: send at 8, retry at 9 if 8 failed
RESEND_URL = "https://api.resend.com/emails"
RECIPIENTS = "hot_lead_emails"  # app_settings keys
SENT_FOR = "daily_report_sent_for"


class EmailError(Exception):
    pass


# ---- settings -------------------------------------------------------------------------------------------------


def get_setting(key: str, default: Any = None) -> Any:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM public.app_settings WHERE key = %s", (key,)).fetchone()
    return row[0] if row else default


def set_setting(key: str, value: Any, by: str | None = None) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO public.app_settings (key, value, updated_by) VALUES (%s, %s, %s)
               ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now(),
                 updated_by = EXCLUDED.updated_by""",
            (key, Jsonb(value), by),
        )


def get_recipients() -> list[str]:
    return get_setting(RECIPIENTS, [])


def email_ready() -> bool:
    s = get_settings()
    return bool(s.resend_api_key and s.alert_from_email)


def eastern_now() -> tuple[date, int]:
    """Today's date and the hour, in New York."""
    with get_conn() as conn:
        day, hour = conn.execute(
            "SELECT (now() AT TIME ZONE %s)::date, extract(hour FROM now() AT TIME ZONE %s)::int", (TZ, TZ)
        ).fetchone()
    return day, hour


# ---- the report ------------------------------------------------------------------------------------------------

_WINDOW = """WITH w AS (SELECT %(day)s::date::timestamp AT TIME ZONE %(tz)s AS s,
                              (%(day)s::date + 1)::timestamp AT TIME ZONE %(tz)s AS e)"""


def report_data(day: date) -> dict[str, Any]:
    """New hot leads on `day` (US Eastern) with their latest search and offer, plus the day's numbers."""
    params = {"day": day, "tz": TZ}
    with get_conn() as conn:
        cur = conn.cursor(row_factory=dict_row)
        hot = cur.execute(
            _WINDOW
            + """
            SELECT l.name, l.organization, l.email,
                   (SELECT count(*) FROM public.lead_events e WHERE e.email = l.email AND e.type = 'report') AS reports,
                   (SELECT e.details->>'shown' FROM public.lead_events e WHERE e.email = l.email AND e.type = 'report'
                    ORDER BY e.created_at DESC LIMIT 1) AS search,
                   (SELECT e.details FROM public.lead_events e WHERE e.email = l.email AND e.type = 'offer'
                    ORDER BY e.created_at DESC LIMIT 1) AS offer
            FROM public.leads l, w WHERE l.hot_at >= w.s AND l.hot_at < w.e ORDER BY l.hot_at""",
            params,
        ).fetchall()
        numbers = cur.execute(
            _WINDOW
            + """
            SELECT (SELECT count(*) FROM public.leads, w WHERE created_at >= w.s AND created_at < w.e) AS signups,
                   (SELECT count(*) FROM public.lead_events, w
                    WHERE type = 'report' AND created_at >= w.s AND created_at < w.e) AS reports,
                   (SELECT count(DISTINCT email) FROM public.lead_events, w
                    WHERE created_at >= w.s AND created_at < w.e) AS active,
                   (SELECT count(*) FROM public.leads WHERE hot_at IS NOT NULL) AS hot_total""",
            params,
        ).fetchone()
    return {"day": day, "hot": hot, **numbers}


def _offer(o: dict[str, Any]) -> str:
    amount, hourly = float(o["amount"]), o.get("unit") == "hour"
    text = f"${amount:,.2f} an hour" if hourly else f"${amount:,.0f} a year"
    return f"{text} ({o['verdict'].rstrip('.')})" if o.get("verdict") else text


def render(data: dict[str, Any]) -> tuple[str, str]:
    """(subject, plain-text body)."""
    d, hot = data["day"], data["hot"]
    n = len(hot)
    short = f"{d:%b} {d.day}"
    subject = f"MinistryHub daily leads: {n} new hot lead{'' if n == 1 else 's'} ({short})"
    lines = [f"Lead report for {d:%A, %B} {d.day}, {d.year} (US Eastern)", ""]
    if hot:
        lines += [f"{n} new hot lead{'' if n == 1 else 's'} ({HOT_AT_REPORTS} or more reports viewed):", ""]
        for h in hot:
            lines += [f"- {h['name']}, {h['organization']}", f"  {h['email']}"]
            lines.append(f"  Reports viewed: {h['reports']} | Latest search: {h['search'] or 'none'}")
            if h["offer"]:
                lines.append(f"  Offer checked: {_offer(h['offer'])}")
            lines.append("")
    else:
        lines += ["No new hot leads that day.", ""]
    lines += [
        "The day in numbers:",
        f"  New sign-ups: {data['signups']}",
        f"  Reports viewed: {data['reports']}",
        f"  Leads active: {data['active']}",
        f"  Hot leads in total: {data['hot_total']}",
        "",
        f"See every lead and their history: {get_settings().site_url.rstrip('/')}/admin#leads",
    ]
    return subject, "\n".join(lines)


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


def send_report(day: date) -> int:
    """Email the report for `day` to the saved addresses; returns how many new hot leads it listed."""
    data = report_data(day)
    send_email(get_recipients(), *render(data))
    return len(data["hot"])


# ---- the cron command ------------------------------------------------------------------------------------------


def register(commands: argparse._SubParsersAction) -> None:
    parser = commands.add_parser("daily-report", help="email yesterday's new hot leads (run by cron)")
    parser.add_argument("--force", action="store_true", help="send now, whatever the time")
    parser.add_argument("--dry-run", action="store_true", help="print the email; send nothing")
    parser.add_argument("--day", type=date.fromisoformat, help="report this day (YYYY-MM-DD), sent now")
    parser.set_defaults(handler=_run)


def _run(args: argparse.Namespace) -> int:
    script_log("daily_report")
    today, hour = eastern_now()
    day = args.day or today - timedelta(days=1)
    if not (args.force or args.dry_run or args.day):
        if hour not in SEND_HOURS:
            log.info("It's %d:00 in New York, outside the 8-9 AM sending window; nothing to send", hour)
            return 0
        if get_setting(SENT_FOR) == day.isoformat():
            log.info("The report for %s was already sent", day)
            return 0
    if args.dry_run:
        subject, text = render(report_data(day))
        print(f"Subject: {subject}\n\n{text}")
        return 0

    recipients = get_recipients()
    if not recipients:
        log.error("Not sent: no addresses in Admin → Settings → Daily lead report")
        return 1
    if not email_ready():
        log.error("Not sent: RESEND_API_KEY and ALERT_FROM_EMAIL must both be set")
        return 1
    try:
        n = send_report(day)
    except EmailError as e:  # the day isn't marked sent, so the 9 AM run (or --day) sends it
        log.error("Daily report for %s not sent: %s", day, e)
        return 1
    set_setting(SENT_FOR, day.isoformat(), by="daily-report")
    log.info("Daily report for %s sent to %d address(es): %d new hot lead(s)", day, len(recipients), n)
    return 0
