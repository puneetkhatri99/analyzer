"""The visitor's report by email, when they tick "Email me this report" on the sign-up form.

The email holds the headline figures and a link back to the full report; it's sent through Resend (daily_report)."""

import logging
import re
from typing import Any
from urllib.parse import parse_qs, urlencode

from psycopg.types.json import Jsonb

from app.core.config import get_settings
from app.core.db import get_conn
from app.report.service import FILTER_KEYS, blended_jobs, build_report, report_options
from app.shared.email import EmailError, email_ready, send_email
from app.shared.geo import state_name

log = logging.getLogger("leads")

MAX_PER_DAY = 5  # report emails per address per 24 hours: the form is public, so it mustn't become a mail cannon
MAX_ALL_PER_DAY = 100  # and for all addresses together: a script posting many addresses can't either
MAX_VALUES = 20  # per filter; more than any real search


def parse_filters(query: str) -> dict[str, Any]:
    """The report's filters from its query string ("role=Worship%2FMusic&state=Ohio"), as the report API reads them."""
    qs = parse_qs(query)
    f: dict[str, Any] = {k: [v.strip() for v in qs.get(k, [])[:MAX_VALUES] if v.strip()] for k in FILTER_KEYS}
    f["type"] = "part-time" if qs.get("type") == ["part-time"] else "full-time"
    return f


def known_filters(f: dict[str, Any], jobs: list[dict[str, Any]]) -> dict[str, Any]:
    """Only values the report really offers: the query string comes from the public form, and its words would
    otherwise go out in an email from our domain ("Your MinistryHub pay report: <anything>")."""
    o = report_options(jobs)
    allowed = {"role": set(o["roles"]), "size": set(o["sizes"]), "denomination": set(o["denominations"])}
    out = {**f, "state": list(dict.fromkeys(s for s in map(state_name, f["state"]) if s))}
    return out | {k: [v for v in f[k] if v in values] for k, values in allowed.items()}


def greeting(name: str) -> str:
    """The visitor's name for "Hi …", or "there" when it looks like more than a name (a link, digits, a message)."""
    plain = all(c.isalpha() or c in " .'’-" for c in name) and not re.search(r"\.\S", name)
    return name if plain and 0 < len(name) <= 60 else "there"


def _money(v: float, unit: str) -> str:
    return f"${v:,.2f}" if unit == "hour" else f"${v:,.0f}"


def render(name: str, f: dict[str, Any], jobs: list[dict[str, Any]] | None = None) -> tuple[str, str]:
    """Subject and plain-text body for one report."""
    r = build_report(f, jobs)
    what = f"{r['title']['role']} in {r['title']['area']}"
    link_query = urlencode(
        {**{k: f[k] for k in FILTER_KEYS}, **({"type": f["type"]} if f["type"] != "full-time" else {})}, doseq=True
    )
    link = f"{get_settings().site_url.rstrip('/')}/report?{link_query}"
    lines = [f"Hi {greeting(name)},", "", f"Here is your MinistryHub pay report for {what} ({f['type']}).", ""]
    if p := r["pay"]:
        per = " an hour" if r["unit"] == "hour" else " a year"
        lines += [
            f"Typical pay: {_money(p['typical'], r['unit'])}{per}",
            f"The middle half of postings pay {_money(p['low'], r['unit'])} to {_money(p['high'], r['unit'])}{per}",
            f"Confidence: {p['confidence']}",
        ]
    if r["note"]:
        lines += ["", r["note"]]
    if v := r["vs_national"]:
        side = "above" if v["percent"] > 0 else "below" if v["percent"] < 0 else "level with"
        pct = f"{abs(v['percent'])}% " if v["percent"] else ""
        lines += ["", f"All ministry roles in {v['area']} pay {pct}{side} the national typical."]
    lines += [
        "",
        "See the full report, with pay by church size, state and denomination:",
        link,
        "",
        "On another device you may be asked for your name and email again before it opens.",
        "",
        "MinistryHub",
    ]
    return f"Your MinistryHub pay report: {what}", "\n".join(lines)


def _sent_today(email: str | None = None) -> int:
    """Report emails that went to Resend in the last 24 hours, for one address or (None) for everyone. Rows from
    before statuses existed count as sent."""
    with get_conn() as conn:
        (n,) = conn.execute(
            """SELECT count(*) FROM public.lead_events
               WHERE (%(email)s::text IS NULL OR email = %(email)s) AND type = 'report_email'
                 AND created_at > now() - interval '24 hours' AND coalesce(details->>'status', 'sent') <> 'skipped'""",
            {"email": email},
        ).fetchone()
    return n


def _record(email: str, f: dict[str, Any], status: str, reason: str | None = None) -> None:
    """The outcome in the lead's history (Admin -> Leads); kept only for stored leads, like every other event."""
    details = {
        "report": f"{', '.join(f['role']) or 'Ministry'} · {', '.join(f['state']) or 'Nationwide'}",
        "status": status,
    }
    if reason:
        details["reason"] = reason
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO public.lead_events (email, type, details)
               SELECT %s, 'report_email', %s WHERE EXISTS (SELECT 1 FROM public.leads WHERE email = %s)""",
            (email, Jsonb(details), email),
        )


def send(email: str, name: str, query: str) -> None:
    """Runs after the sign-up reply (a background task), so a slow or failing send never holds up the report.
    Every outcome is recorded: sent, failed (Resend's reason) or skipped (not set up / daily limit)."""
    jobs = blended_jobs()
    f = known_filters(parse_filters(query), jobs)
    if not email_ready():
        reason = "email isn't set up on the server (RESEND_API_KEY, ALERT_FROM_EMAIL)"
    elif _sent_today(email) >= MAX_PER_DAY:
        reason = f"daily limit reached ({MAX_PER_DAY} report emails per address per 24 hours)"
    elif _sent_today() >= MAX_ALL_PER_DAY:
        reason = f"site-wide daily limit reached ({MAX_ALL_PER_DAY} report emails per 24 hours)"
        log.error("Report emails stopped for today: %d sent in 24 hours (a script abusing the form?)", MAX_ALL_PER_DAY)
    else:
        try:
            send_email([email], *render(name, f, jobs))
        except EmailError as e:
            log.warning("report email failed: %s", e)  # never the address: lead emails stay out of logs
            _record(email, f, "failed", str(e))
            return
        log.info("report email sent")
        _record(email, f, "sent")
        return
    log.warning("report email skipped: %s", reason)
    _record(email, f, "skipped", reason)
