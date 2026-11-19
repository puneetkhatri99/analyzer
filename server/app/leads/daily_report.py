"""daily-report: email yesterday's new hot leads, and the day's other numbers, to the addresses set in
Admin → Settings. Sent through Resend, by the API's own timer (start_scheduler) or a cron job (DAILY_REPORT_CRON.md).

  python -m app.cli daily-report                    # from 8 AM New York time: every day not sent yet, once each
  python -m app.cli daily-report --force            # send yesterday's report now
  python -m app.cli daily-report --dry-run          # print it, send nothing
  python -m app.cli daily-report --day 2026-11-16   # a given day, sent now

From 8 AM in New York, each check sends the reports not sent yet (oldest first, up to a week back); a failed send is
retried by the next check, and a day is never sent twice. Days are midnight to midnight US Eastern, worked out by
Postgres, so no timezone package is needed.
"""

import argparse
import logging
import threading
from datetime import date, timedelta
from typing import Any

from psycopg.rows import dict_row

from app.core.config import get_settings
from app.core.db import get_conn
from app.core.logs import script_log
from app.core.settings_store import get_setting, set_setting
from app.leads import HOT_AT_REPORTS
from app.shared.email import EmailError, email_ready, send_email

log = logging.getLogger("daily_report")

TZ = "America/New_York"
SEND_FROM_HOUR = 8  # New York time: yesterday's report goes out from 8 AM, or as soon as the server is awake after
RECIPIENTS = "hot_lead_emails"  # app_settings keys
SENT_FOR = "daily_report_sent_for"


# ---- settings -------------------------------------------------------------------------------------------------


def get_recipients() -> list[str]:
    return get_setting(RECIPIENTS, [])


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
    """An offer a lead checked, e.g. "$52,000 a year (in range)". Event details come from the public site unchecked,
    so anything odd reads as "an offer" rather than breaking the whole email."""
    try:
        amount, hourly = float(o["amount"]), o.get("unit") == "hour"
        text = f"${amount:,.2f} an hour" if hourly else f"${amount:,.0f} a year"
        verdict = o.get("verdict")
        return f"{text} ({verdict.rstrip('.')})" if isinstance(verdict, str) and verdict else text
    except (KeyError, TypeError, ValueError, AttributeError):
        return "an offer"


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


def _send(day: date) -> int:
    """Send the report for `day` now. 0 = sent, 1 = couldn't (the day stays unsent, so a later run retries)."""
    recipients = get_recipients()
    if not recipients:
        log.error("Not sent: no addresses in Admin → Settings → Daily lead report")
        return 1
    if not email_ready():
        log.error("Not sent: RESEND_API_KEY and ALERT_FROM_EMAIL must both be set")
        return 1
    try:
        n = send_report(day)
    except EmailError as e:  # the day isn't marked sent, so the next check (or --day) sends it
        log.error("Daily report for %s not sent: %s", day, e)
        return 1
    sent = get_setting(SENT_FOR)
    # the marker only moves forward, and never past yesterday: re-sending an old day (--day) or a test of a future
    # day must not make the catch-up resend a week, or skip days
    if (sent is None or day.isoformat() > sent) and day < eastern_now()[0]:
        set_setting(SENT_FOR, day.isoformat(), by="daily-report")
    log.info("Daily report for %s sent to %d address(es): %d new hot lead(s)", day, len(recipients), n)
    return 0


CATCH_UP_DAYS = 7  # a server asleep for longer than this sends only the last week's reports


def send_if_due() -> int:
    """From 8 AM in New York: every report not sent yet, oldest first, up to yesterday. A day missed while the server
    was asleep (or Resend was down) is sent late, not lost; at most CATCH_UP_DAYS back. Used by the cron command and
    by the API's own timer (start_scheduler)."""
    today, hour = eastern_now()
    yesterday = today - timedelta(days=1)
    if hour < SEND_FROM_HOUR:
        log.debug("It's %d:00 in New York, before the 8 AM send; nothing to send", hour)
        return 0
    sent = get_setting(SENT_FOR)
    first = yesterday if sent is None else date.fromisoformat(sent) + timedelta(days=1)
    first = max(first, yesterday - timedelta(days=CATCH_UP_DAYS - 1))
    if first > yesterday:
        log.debug("The report for %s was already sent", yesterday)
        return 0
    for n in range((yesterday - first).days + 1):
        if _send(first + timedelta(days=n)):
            return 1  # stop at the first failure: that day stays unsent and the next check retries it
    return 0


def _run(args: argparse.Namespace) -> int:
    script_log("daily_report")
    if args.dry_run:
        day = args.day or eastern_now()[0] - timedelta(days=1)
        subject, text = render(report_data(day))
        print(f"Subject: {subject}\n\n{text}")
        return 0
    if args.force or args.day:
        return _send(args.day or eastern_now()[0] - timedelta(days=1))
    return send_if_due()


# ---- or no cron at all: the API sends it --------------------------------------------------------------------------

CHECK_EVERY = 10 * 60  # seconds


def start_scheduler() -> threading.Event:
    """Check every CHECK_EVERY seconds, inside the API process, whether a report is due. A free Render service asleep
    at 8 AM sends it once it wakes (an uptime pinger keeps it awake and on time). Set the returned event to stop.
    shortcut: one timer per server process; with several instances two could send the same day at the same moment,
    move to the cron command (DAILY_REPORT_CRON.md) before scaling out."""
    stop = threading.Event()

    def loop() -> None:
        while True:  # check at once: a free Render service woken late may sleep again before the first interval
            try:
                send_if_due()
            except Exception:  # a database hiccup mustn't end the timer for good
                log.exception("Daily report check failed")
            if stop.wait(CHECK_EVERY):
                return

    threading.Thread(target=loop, name="daily-report", daemon=True).start()
    log.info("Daily lead report: sent once a day at 8 AM New York time (checked every %d min)", CHECK_EVERY // 60)
    return stop
