"""Public: sign-up before the report (brief P2) and what the visitor does next (P10).
Admin: the leads dashboard and each lead's history (A3, A4)."""

import json
import logging
from datetime import timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from app.auth.dependencies import require_admin
from app.core.config import get_settings
from app.core.db import get_conn
from app.leads import HOT_AT_REPORTS, daily_report
from app.shared.email import is_valid_email, normalize_email

log = logging.getLogger("admin")

router = APIRouter(prefix="/api/leads", tags=["leads"])
admin_router = APIRouter(prefix="/api/admin", tags=["leads"])


class Lead(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(max_length=320)
    organization: str = Field(min_length=1, max_length=300)
    role: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    attendance: str | None = Field(default=None, max_length=100)
    shared: bool = False  # signed up to open a report someone shared with them


# What the public site records (features/site/lead.js `track`); "signup" is recorded here, on the server.
# share_link / share_email: older rows only; those clicks are now plain "click" events.
EventType = Literal["report", "offer", "share_link", "share_email", "download", "cta", "click"]
MERGE_REPORTS_WITHIN = "30 seconds"  # a report right after another replaces it: one search, not a burst of rows
MAX_DETAILS = 2000  # characters of JSON; an event's details are a few filters or one amount


class Event(BaseModel):
    email: str = Field(max_length=320)
    type: EventType
    details: dict[str, Any] = Field(default_factory=dict)


def is_internal(email: str) -> bool:
    """The MinistryHub team (or anyone testing) signing up: their activity would pass for real leads."""
    domains = {d.strip().lower() for d in get_settings().ignored_lead_domains.split(",") if d.strip()}
    return email.rpartition("@")[2] in domains


@router.post("")
def save_lead(lead: Lead) -> dict[str, bool]:
    """A returning email updates its row instead of adding one. Internal emails get the report but aren't stored,
    so none of their activity is either (events are kept only for stored leads)."""
    email = normalize_email(lead.email)
    if not is_valid_email(email):
        raise HTTPException(422, "Please enter a valid email address.")
    if is_internal(email):
        return {"ok": True}
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO public.leads (email, name, organization, role, location, attendance)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name, organization = EXCLUDED.organization,
                 role = EXCLUDED.role, location = EXCLUDED.location, attendance = EXCLUDED.attendance,
                 last_seen_at = now()""",
            (email, lead.name.strip(), lead.organization.strip(), lead.role, lead.location, lead.attendance),
        )
        search = {"role": lead.role, "location": lead.location, "attendance": lead.attendance, "shared": lead.shared}
        conn.execute(
            "INSERT INTO public.lead_events (email, type, details) VALUES (%s, 'signup', %s)",
            (email, Jsonb({**search, "organization": lead.organization.strip()})),
        )
    return {"ok": True}


@router.post("/events")
def record_event(event: Event) -> dict[str, bool]:
    """Kept only for an email that has signed up; the reply is the same either way, so it can't be used to test
    which emails are leads. shortcut: no rate limit (it only adds rows to known leads); add one if it's abused."""
    if len(json.dumps(event.details)) > MAX_DETAILS:
        raise HTTPException(422, "Event details are too long.")
    email = normalize_email(event.email)
    with get_conn() as conn:
        if event.type == "report":
            merged = conn.execute(
                f"""UPDATE public.lead_events SET details = %s, created_at = now()
                    WHERE id = (SELECT id FROM public.lead_events WHERE email = %s
                                ORDER BY created_at DESC, id DESC LIMIT 1)
                      AND type = 'report' AND created_at > now() - interval '{MERGE_REPORTS_WITHIN}'""",
                (Jsonb(event.details), email),
            ).rowcount
            if merged:
                return {"ok": True}
        added = conn.execute(
            """INSERT INTO public.lead_events (email, type, details)
               SELECT %s, %s, %s WHERE EXISTS (SELECT 1 FROM public.leads WHERE email = %s)""",
            (email, event.type, Jsonb(event.details), email),
        ).rowcount
        if added and event.type == "report":  # the report that makes a lead hot: noted once, for the daily report
            conn.execute(
                """UPDATE public.leads SET hot_at = now() WHERE email = %s AND hot_at IS NULL
                   AND (SELECT count(*) FROM public.lead_events WHERE email = %s AND type = 'report') >= %s""",
                (email, email, HOT_AT_REPORTS),
            )
    return {"ok": True}


BOOKING_HOST = "bookme.ministryhub.org"  # a click through to the booking page marks the lead "Booked a call"


@admin_router.get("/leads", dependencies=[Depends(require_admin)], response_model=None)
def leads_report() -> dict[str, Any]:
    """Everyone who signed up, newest first, with totals and the roles and places they search most.
    shortcut: every lead in one reply; page it once there are tens of thousands."""
    with get_conn() as conn:
        cur = conn.cursor(row_factory=dict_row)
        totals = cur.execute(
            """SELECT count(*) AS total,
                      count(*) FILTER (WHERE created_at >= now() - interval '7 days') AS this_week,
                      count(*) FILTER (WHERE created_at >= date_trunc('month', now())) AS this_month,
                      (SELECT count(DISTINCT email) FROM public.lead_events
                       WHERE created_at >= now() - interval '7 days') AS active_week,
                      count(DISTINCT lower(organization)) AS organizations,
                      count(hot_at) AS hot
               FROM public.leads"""
        ).fetchone()
        top = """SELECT {col} AS name, count(*) AS leads FROM public.leads WHERE {col} IS NOT NULL
                 GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 8"""
        by_role = cur.execute(top.format(col="role")).fetchall()
        by_location = cur.execute(top.format(col="location")).fetchall()
        leads = cur.execute(
            """SELECT l.email, l.name, l.organization, l.role, l.location, l.attendance, l.created_at, l.last_seen_at,
                      e.events, e.last_active, coalesce(e.reports, 0) AS reports, l.hot_at IS NOT NULL AS hot,
                      l.hot_at, coalesce(e.booked, false) AS booked
               FROM public.leads l
               LEFT JOIN (SELECT email, count(*) AS events, max(created_at) AS last_active,
                                 count(*) FILTER (WHERE type = 'report') AS reports,
                                 bool_or(type = 'cta' AND details->>'url' LIKE %s) AS booked
                          FROM public.lead_events GROUP BY email) e USING (email)
               ORDER BY l.created_at DESC""",
            (f"%{BOOKING_HOST}%",),
        ).fetchall()
    return {"totals": totals, "by_role": by_role, "by_location": by_location, "leads": leads}


@admin_router.get("/leads/{email}", dependencies=[Depends(require_admin)], response_model=None)
def lead_history(email: str) -> dict[str, Any]:
    """One lead and everything they did, newest first."""
    with get_conn() as conn:
        cur = conn.cursor(row_factory=dict_row)
        lead = cur.execute(
            """SELECT email, name, organization, role, location, attendance, created_at, last_seen_at,
                      hot_at IS NOT NULL AS hot, hot_at
               FROM public.leads WHERE email = %s""",
            (normalize_email(email),),
        ).fetchone()
        if not lead:
            raise HTTPException(404, "No lead with that email")
        events = cur.execute(
            """SELECT type, details, created_at FROM public.lead_events
               WHERE email = %s ORDER BY created_at DESC, id DESC""",
            (lead["email"],),
        ).fetchall()
    return {"lead": {**lead, "reports": sum(e["type"] == "report" for e in events)}, "events": events}


# ---- Settings: who gets the daily lead report ----------------------------------------------------------------

MAX_RECIPIENTS = 10


class ReportSettings(BaseModel):
    hot_lead_emails: list[str] = Field(max_length=MAX_RECIPIENTS)


def _settings() -> dict[str, Any]:
    return {
        "hot_lead_emails": daily_report.get_recipients(),
        "email_ready": daily_report.email_ready(),
        # Resend's shared test sender only delivers to the Resend account's own address
        "test_sender": "@resend.dev" in (get_settings().alert_from_email or ""),
    }


@admin_router.get("/settings", dependencies=[Depends(require_admin)], response_model=None)
def get_report_settings() -> dict[str, Any]:
    return _settings()


@admin_router.patch("/settings", response_model=None)
def save_report_settings(body: ReportSettings, admin: str = Depends(require_admin)) -> dict[str, Any]:
    emails: list[str] = []
    for raw in body.hot_lead_emails:
        email = normalize_email(raw)
        if not is_valid_email(email):
            raise HTTPException(422, f"{raw.strip() or 'An empty entry'} isn't an email address.")
        if email not in emails:
            emails.append(email)
    daily_report.set_setting(daily_report.RECIPIENTS, emails, by=admin)
    log.info("Daily report recipients changed by %s: %d address(es)", admin, len(emails))
    return _settings()


@admin_router.post("/settings/test-email", response_model=None)
def send_test_report(admin: str = Depends(require_admin)) -> dict[str, Any]:
    """Yesterday's report, sent now to the saved addresses. Doesn't count as the day's report."""
    recipients = daily_report.get_recipients()
    if not recipients:
        raise HTTPException(400, "Add at least one address and save first.")
    if not daily_report.email_ready():
        raise HTTPException(400, "Email sending isn't set up: RESEND_API_KEY and ALERT_FROM_EMAIL are needed.")
    today, _ = daily_report.eastern_now()
    try:
        daily_report.send_report(today - timedelta(days=1))
    except daily_report.EmailError as e:
        log.warning("Test daily report by %s not sent: %s", admin, e)
        raise HTTPException(502, f"The email wasn't sent: {e}") from e
    log.info("Test daily report sent by %s to %d address(es)", admin, len(recipients))
    return {"ok": True, "sent_to": len(recipients)}
