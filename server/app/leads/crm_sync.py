"""crm-sync: once a week, send the sign-ups who ticked "Send me the MinistryHub newsletter" to Mailchimp, with what
they did on the site (tags, and a note listing their activity since the last sync). Nobody who didn't tick the box is
ever sent. Loxo is not here yet: it waits for the client's Loxo API docs.

Off until MAILCHIMP_API_KEY and MAILCHIMP_LIST_ID are set: each run then only logs "skipped: no key".

  python -m app.cli crm-sync               # once a week (first check of a new week, after FEED_HOUR_UTC)
  python -m app.cli crm-sync --force       # now
  python -m app.cli crm-sync --dry-run     # log what would be sent; send nothing

A lead is sent again when they've done something since their last sync. A failed send is retried the next day. Email
addresses are never logged: a lead shows as the first 8 characters of its Mailchimp member ID (an MD5 of the email).
"""

import argparse
import hashlib
import logging
import re
import threading
from datetime import UTC, datetime
from typing import Any

import requests
from psycopg.rows import dict_row

from app.core.config import get_settings
from app.core.db import get_conn
from app.core.logs import script_log
from app.core.settings_store import get_setting, set_setting
from app.shared.alerts import alert_admin

log = logging.getLogger("crm_sync")

STATUS_KEY = "mailchimp_sync_status"
DONE_KEY = "mailchimp_sync_done_for"  # the ISO week ("2026-W47") that was sent
TRIED_KEY = "mailchimp_sync_tried_on"  # the last day a run was tried, so a failure is retried tomorrow
CHECK_EVERY = 60 * 60
TIMEOUT = (10, 30)
MAX_NOTE = 1000  # characters; Mailchimp's limit for a member note
DATA_CENTRE = re.compile(r"^[a-z]+\d+$")
SITE_TAG = "MinistryHub salary tool"

_running = threading.Lock()


class MailchimpError(Exception):
    pass


def ready() -> bool:
    s = get_settings()
    return bool(s.mailchimp_api_key and s.mailchimp_list_id)


def api_base(key: str) -> str:
    """Mailchimp's address for this key: the key ends in its data centre ("…-us21")."""
    dc = key.rpartition("-")[2]
    if not DATA_CENTRE.match(dc):
        raise MailchimpError("MAILCHIMP_API_KEY doesn't end in a data centre like -us21")
    return f"https://{dc}.api.mailchimp.com/3.0"


def member_id(email: str) -> str:
    return hashlib.md5(email.lower().encode()).hexdigest()  # Mailchimp's own member ID, not a security use


TO_SEND = """
    SELECT l.email, l.name, l.organization, l.role, l.location, l.hot_at, l.synced_mailchimp_at
    FROM public.leads l
    WHERE l.newsletter_at IS NOT NULL
      AND (l.synced_mailchimp_at IS NULL
           OR EXISTS (SELECT 1 FROM public.lead_events e
                      WHERE e.email = l.email AND e.created_at > l.synced_mailchimp_at))
    ORDER BY l.created_at"""

EVENTS = """
    SELECT type, details, created_at FROM public.lead_events
    WHERE email = %s AND (%s::timestamptz IS NULL OR created_at > %s) ORDER BY created_at"""


def _line(e: dict[str, Any]) -> str:
    """One activity in words, for the Mailchimp note. Event details come from the public site, so only short known
    fields are used."""
    d, day = e["details"] or {}, f"{e['created_at']:%Y-%m-%d}"
    what = {
        "signup": "Signed up",
        "report": f"Viewed a report: {str(d.get('shown') or '')[:80]}",
        "offer": f"Checked an offer of {str(d.get('amount'))[:12]} ({str(d.get('unit') or 'year')[:5]})",
        "download": "Downloaded the report",
        "cta": f"Clicked through to MinistryHub: {str(d.get('label') or '')[:60]}",
        "click": f"Clicked {str(d.get('label') or '')[:60]}",
        "suggest": f"Suggested a denomination: {str(d.get('denomination') or '')[:60]}",
        "report_email": "Got the report by email",
    }.get(e["type"], e["type"])
    return f"{day} {what}"


def member_update(lead: dict[str, Any], events: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str], str]:
    """(the member's fields, its tags, its note) for one lead."""
    first, _, last = (lead["name"] or "").strip().partition(" ")
    member = {
        "email_address": lead["email"],
        "status_if_new": "subscribed",  # they ticked the newsletter box; an unsubscribed member stays unsubscribed
        "merge_fields": {"FNAME": first[:100], "LNAME": last[:100]},
    }
    types = {e["type"] for e in events}
    tags = [SITE_TAG]
    tags += ["Hot lead"] * bool(lead["hot_at"])
    tags += ["Checked an offer"] * ("offer" in types)
    tags += ["Booked a call"] * any(
        e["type"] == "cta" and "bookme.ministryhub.org" in str((e["details"] or {}).get("url")) for e in events
    )
    head = (
        f"MinistryHub salary tool. Organization: {lead['organization']}. "
        f"First search: {lead['role'] or 'any role'} in {lead['location'] or 'any state'}."
    )
    note = "\n".join([head, *map(_line, events)])
    return member, tags, note[:MAX_NOTE]


def _call(method: str, url: str, key: str, body: dict[str, Any]) -> None:
    try:
        r = requests.request(method, url, auth=("ministryhub", key), json=body, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise MailchimpError(f"Couldn't reach Mailchimp ({e.__class__.__name__})") from e
    if not r.ok:
        try:
            detail = r.json().get("detail") or r.text
        except ValueError:
            detail = r.text
        raise MailchimpError(f"Mailchimp answered {r.status_code}: {str(detail)[:200]}")


def send(lead: dict[str, Any], events: list[dict[str, Any]]) -> None:
    s = get_settings()
    key, list_id = s.mailchimp_api_key or "", s.mailchimp_list_id or ""
    url = f"{api_base(key)}/lists/{list_id}/members/{member_id(lead['email'])}"
    member, tags, note = member_update(lead, events)
    _call("PUT", url, key, member)  # add, or update an existing member
    _call("POST", f"{url}/tags", key, {"tags": [{"name": t, "status": "active"} for t in tags]})
    _call("POST", f"{url}/notes", key, {"note": note})


def run(*, dry_run: bool = False) -> dict[str, Any]:
    """Send every lead due. Returns the status saved for the admin."""
    status: dict[str, Any] = {"at": datetime.now(UTC).isoformat(), "ok": True, "sent": 0, "failed": 0}
    if not ready():
        log.info("Mailchimp sync skipped: no key (set MAILCHIMP_API_KEY and MAILCHIMP_LIST_ID)")
        return {**status, "skipped": "no key"}
    with get_conn() as conn:
        cur = conn.cursor(row_factory=dict_row)
        leads = cur.execute(TO_SEND).fetchall()
        for lead in leads:
            since = lead["synced_mailchimp_at"]
            lead["events"] = cur.execute(EVENTS, (lead["email"], since, since)).fetchall()
    log.info("Mailchimp: %d leads who asked for the newsletter have something new to send", len(leads))
    for lead in leads:
        who = f"member {member_id(lead['email'])[:8]}"
        if dry_run:
            _, tags, note = member_update(lead, lead["events"])
            log.info("Would send %s: tags %s; note of %d characters", who, tags, len(note))
            continue
        try:
            send(lead, lead["events"])
        except MailchimpError as e:
            status["failed"] += 1
            log.error("Mailchimp: %s not sent: %s", who, e)
            continue
        with get_conn() as conn:
            conn.execute("UPDATE public.leads SET synced_mailchimp_at = now() WHERE email = %s", (lead["email"],))
        status["sent"] += 1
        log.info("Mailchimp: %s sent (%d new activities)", who, len(lead["events"]))
    status["ok"] = status["failed"] == 0
    log.info("Mailchimp sync done: %d sent, %d failed%s", status["sent"], status["failed"], " (dry run)" * dry_run)
    return status


def run_and_record(*, force: bool = False, dry_run: bool = False) -> int:
    """0 = fine or nothing due, 1 = a lead failed. Without force, once per ISO week (retried daily after a failure)."""
    now = datetime.now(UTC)
    week = f"{now.isocalendar().year}-W{now.isocalendar().week:02d}"
    done = get_setting(DONE_KEY) == week or get_setting(TRIED_KEY) == now.date().isoformat()
    if done and not force and not dry_run:
        return 0
    if not _running.acquire(blocking=False):
        return 0
    try:
        status = run(dry_run=dry_run)
        if dry_run or status.get("skipped"):
            return 0
        set_setting(STATUS_KEY, status, by="crm-sync")
        set_setting(TRIED_KEY, now.date().isoformat(), by="crm-sync")
        if status["ok"]:
            set_setting(DONE_KEY, week, by="crm-sync")
        else:
            alert_admin(
                "MinistryHub newsletter sync failed",
                f"{status['failed']} sign-up(s) couldn't be sent to Mailchimp this week; it tries again tomorrow. "
                "The server log has Mailchimp's reason (search for crm_sync).",
            )
        return 0 if status["ok"] else 1
    finally:
        _running.release()


def run_if_due() -> int:
    if not ready() or datetime.now(UTC).hour < get_settings().feed_hour_utc:
        return 0
    return run_and_record()


def register(commands: argparse._SubParsersAction) -> None:
    parser = commands.add_parser("crm-sync", help="send newsletter sign-ups and their activity to Mailchimp")
    parser.add_argument("--force", action="store_true", help="send now, even if this week was already sent")
    parser.add_argument("--dry-run", action="store_true", help="log what would be sent; send nothing")
    parser.set_defaults(handler=_run)


def _run(args: argparse.Namespace) -> int:
    script_log("crm_sync")
    return run_and_record(force=args.force, dry_run=args.dry_run)


def start_scheduler() -> threading.Event:
    """Check every CHECK_EVERY seconds, inside the API process, whether this week's sync is due. Set the returned
    event to stop. shortcut: one timer per server process, like bizdev_sync's; move to a cron job before scaling out."""
    stop = threading.Event()

    def loop() -> None:
        while True:
            try:
                run_if_due()
            except Exception:
                log.exception("Mailchimp sync check failed")
            if stop.wait(CHECK_EVERY):
                return

    threading.Thread(target=loop, name="crm-sync", daemon=True).start()
    log.info("Mailchimp sync: %s", "once a week" if ready() else "off (no MAILCHIMP_API_KEY / MAILCHIMP_LIST_ID)")
    return stop
