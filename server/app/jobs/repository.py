"""Reading and writing jobs across the three sources.

json        the church jobs JSON feed (postings + companies)
churches    BizDev churches sheet, plus jobs added by admins and the collector (church_jobs)
nonprofits  BizDev nonprofits sheet (nonprofit_jobs)
"""

import decimal
from typing import Any, Literal

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.db import get_conn
from app.job_pages.parser import denomination_in
from app.jobs.roles import pick_role
from app.shared.geo import state_name
from app.shared.web import with_scheme

Source = Literal["json", "churches", "nonprofits"]
BizdevSource = Literal["churches", "nonprofits"]
BIZDEV_TABLES: dict[str, str] = {"churches": "church_jobs", "nonprofits": "nonprofit_jobs"}

HOURS_PER_YEAR = 2080

COLUMNS = [
    "post_uuid", "job_name", "department", "hours", "seniority", "remote",
    "board_source", "post_url", "city", "region", "country", "company_name",
    "denomination", "church_size", "salary_min", "salary_max", "salary_period",
    "first_indexed", "pull_date", "origin", "added_at", "church_size_source", "reviewed", "ai_role",
]  # fmt: skip

# Every SELECT names its columns (AS) exactly as COLUMNS, in the same order: rows are read by name, not by position.
# reviewed: the feed's AI review (or an admin) has judged the posting in scope; the public report waits for it.
_FEED_SQL = """
    SELECT p.post_uuid, p.job_name_raw AS job_name, p.department, p.hours,
           p.seniority, p.remote, p.board_source, p.post_url, p.city, p.region, p.country,
           c.company_name, c.denomination, c.church_size,
           p.salary_min, p.salary_max, p.salary_period,
           p.first_indexed, p.pull_date, 'feed' AS origin, p.created_at AS added_at,
           c.church_size_url AS church_size_source, p.scope_checked_at IS NOT NULL AS reviewed, p.ai_role
    FROM public.postings p
    LEFT JOIN public.companies c USING (company_uuid)
"""

# The BizDev tables mapped onto the feed's columns. Contact names and emails are never selected.
_BIZDEV_SQL = """
    SELECT url_key AS post_uuid, job_title AS job_name, NULL AS department, hours, NULL AS seniority, remote,
           split_part(url_key, '/', 1) AS board_source, job_url AS post_url,
           city, state AS region, 'United States' AS country, org_name AS company_name, denomination, church_size,
           salary_min, salary_max, salary_period, date_posted AS first_indexed, fetched_at::date AS pull_date,
           added_via AS origin, imported_at AS added_at, church_size_source, true AS reviewed,
           NULL::text AS ai_role  -- shortcut: no description is kept for sheet jobs, so their role is the title's
    FROM public.{table}
"""

SOURCES: dict[str, dict[str, str]] = {
    "json": {"label": "Church jobs feed", "sql": _FEED_SQL},
    "churches": {"label": "BizDev churches", "sql": _BIZDEV_SQL.format(table="church_jobs")},
    "nonprofits": {"label": "BizDev nonprofits", "sql": _BIZDEV_SQL.format(table="nonprofit_jobs")},
}


def _json_value(v: Any) -> Any:
    if isinstance(v, decimal.Decimal):
        return float(v)
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


def load_jobs(source: Source = "json") -> list[dict[str, Any]]:
    """Every posting of one source as a flat dict, plus derived role and annual pay.

    Re-queried per request: at a few thousand rows this takes a few ms, so there's no
    cache to invalidate when the pipeline re-runs.
    """
    with get_conn() as conn:
        rows = conn.cursor(row_factory=dict_row).execute(SOURCES[source]["sql"]).fetchall()

    jobs = []
    for row in rows:
        d = {c: _json_value(v) for c, v in row.items()}
        d["role"] = pick_role(d["job_name"], d["ai_role"])
        # stored names from before the merges ("Southern Baptist Convention") read as today's ("Baptist")
        d["denomination"] = denomination_in(d["denomination"]) or d["denomination"]
        lo, hi, period = d["salary_min"], d["salary_max"], d["salary_period"]
        annual = None
        if lo is not None and hi is not None:
            mid = (lo + hi) / 2
            annual = round(mid * HOURS_PER_YEAR) if period == "hour" else round(mid)
        d["salary_annual_mid"] = annual
        if d["post_url"]:
            d["post_url"] = with_scheme(d["post_url"])
        d["region"] = state_name(d["region"]) or d["region"]  # sheets say "TX", the feed "Texas"
        d["source"] = source  # rows from several sources share one table; deleting needs the source
        jobs.append(d)
    return jobs


def load_sources(sources: list[Source]) -> list[dict[str, Any]]:
    """The postings of several sources together."""
    # shortcut: a job listed in two sources counts twice, dedupe by url_key if mixed totals matter
    return [job for s in sources for job in load_jobs(s)]


def source_counts() -> list[dict[str, Any]]:
    """Postings, pay and fetch progress per source, for the source switcher."""
    out = []
    with get_conn() as conn:
        for key, s in SOURCES.items():
            postings, paid, fetched = conn.execute(
                f"SELECT count(*), count(salary_min), count(pull_date) FROM ({s['sql']}) j"
            ).fetchone()
            out.append({"key": key, "label": s["label"], "postings": postings, "paid": paid, "fetched": fetched})
    return out


# Columns an admin-added job fills (extraction.router).
ADMIN_JOB_FIELDS = [
    "job_title", "org_name", "org_website", "city", "state", "date_posted",
    "salary_min", "salary_max", "salary_period", "hours", "remote", "denomination", "church_size", "church_size_source",
]  # fmt: skip


def save_admin_job(conn: psycopg.Connection, source: BizdevSource, row: dict[str, Any]) -> None:
    """Insert or update a job an admin added. A job already imported from Excel keeps its contact details and its
    original origin; newer extracted values win. `row` holds ADMIN_JOB_FIELDS plus url_key, job_url, added_via,
    added_by."""
    cols = ", ".join(ADMIN_JOB_FIELDS)
    values = ", ".join(f"%({f})s" for f in ADMIN_JOB_FIELDS)
    updates = ", ".join(f"{f} = coalesce(EXCLUDED.{f}, t.{f})" for f in ADMIN_JOB_FIELDS)
    conn.execute(
        f"""INSERT INTO public.{BIZDEV_TABLES[source]} AS t
                (url_key, job_url, {cols}, sheets, fetch_status, fetched_at, added_via, added_by)
            VALUES (%(url_key)s, %(job_url)s, {values}, ARRAY['Added by admin'], 'ok', now(),
                    %(added_via)s, %(added_by)s)
            ON CONFLICT (url_key) DO UPDATE SET {updates},
                fetch_status = 'ok', fetched_at = now(),
                sheets = CASE WHEN 'Added by admin' = ANY(t.sheets) THEN t.sheets
                              ELSE array_append(t.sheets, 'Added by admin') END""",
        row,
    )


# ---- rejected feed postings (out of scope): kept whole in rejected_postings, skipped by the daily feed ---------------

# A posting rejected before and somehow back in the job tables is rejected again: the newer copy replaces the old.
_REJECT = """
    INSERT INTO public.rejected_postings
        (post_uuid, post_url, job_title, company_uuid, reason, rejected_by, posting)
    SELECT p.post_uuid, lower(trim(p.post_url)), p.job_name_raw, p.company_uuid, %(reason)s, %(by)s, to_jsonb(p)
    FROM public.postings p WHERE p.post_uuid = %(id)s
    ON CONFLICT (post_uuid) DO UPDATE SET post_url = EXCLUDED.post_url, job_title = EXCLUDED.job_title,
        company_uuid = EXCLUDED.company_uuid, reason = EXCLUDED.reason, rejected_by = EXCLUDED.rejected_by,
        rejected_at = now(), posting = EXCLUDED.posting
    RETURNING 1"""


def reject_posting(conn: psycopg.Connection, post_uuid: str, reason: str, by: str) -> bool:
    """Move a feed posting out of the job tables into rejected_postings (inside the caller's transaction).
    False when there is no such posting."""
    if conn.execute(_REJECT, {"id": post_uuid, "reason": reason, "by": by}).fetchone() is None:
        return False
    conn.execute("DELETE FROM public.postings WHERE post_uuid = %s", (post_uuid,))
    return True


def restore_posting(post_uuid: str) -> bool:
    """Put a rejected posting back exactly as it was, pay included. It stays judged, so the daily job's AI
    never rejects it again. False when it isn't in rejected_postings."""
    with get_conn() as conn, conn.transaction():
        row = conn.execute(
            "DELETE FROM public.rejected_postings WHERE post_uuid = %s RETURNING posting", (post_uuid,)
        ).fetchone()
        if row is None:
            return False
        posting = Jsonb(row[0])
        conn.execute(
            """INSERT INTO public.postings SELECT * FROM jsonb_populate_record(NULL::public.postings, %s)
               ON CONFLICT (post_uuid) DO NOTHING""",
            (posting,),
        )
        conn.execute(
            "UPDATE public.postings SET scope_checked_at = coalesce(scope_checked_at, now()) WHERE post_uuid = %s",
            (post_uuid,),
        )
    return True


def rejected_postings() -> list[dict[str, Any]]:
    """Every rejected feed posting, newest first, for the admin's Rejected jobs tab. The link is the posting's own URL
    (r.post_url is lower-cased for matching, and job sites' paths can be case-sensitive), with its https:// added."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT r.post_uuid, r.job_title, c.company_name, r.posting->>'city', r.posting->>'region',
                      coalesce(r.posting->>'post_url', r.post_url), r.reason, r.rejected_by, r.rejected_at
               FROM public.rejected_postings r LEFT JOIN public.companies c USING (company_uuid)
               ORDER BY r.rejected_at DESC, c.company_name, r.job_title"""
        ).fetchall()
    keys = [
        "post_uuid",
        "job_name",
        "company_name",
        "city",
        "region",
        "post_url",
        "reason",
        "rejected_by",
        "rejected_at",
    ]
    out = [{k: _json_value(v) for k, v in zip(keys, r, strict=True)} for r in rows]
    for d in out:
        d["post_url"] = d["post_url"] and with_scheme(d["post_url"])
    return out


def job_contact(source: BizdevSource, job_id: str) -> dict[str, str | None] | None:
    """The person to contact about one BizDev job (from the sheet), or None when there is no such job. The only place
    contact details leave the database: the endpoint that calls this is for editors and admins."""
    with get_conn() as conn:
        row = conn.execute(
            f"SELECT contact_first_name, contact_last_name, contact_title, contact_email "
            f"FROM public.{BIZDEV_TABLES[source]} WHERE url_key = %s",
            (job_id,),
        ).fetchone()
    return None if row is None else dict(zip(("first_name", "last_name", "title", "email"), row, strict=True))


def set_employer_facts(
    source: Source, job_id: str, church_size: int | None, denomination: str | None, by: str
) -> dict[str, Any] | None:
    """An editor's church size and/or denomination for the employer of one job, applied to all of that employer's jobs
    (feed: the company; sheets: the same name, city and state, as bizdev_enrich matches employers). A value left None
    stays as it is. The size's source becomes "entered by <email>". Returns the employer and its old values, or None
    when there is no such job."""
    entered = f"entered by {by}"
    with get_conn() as conn, conn.transaction():
        if source == "json":
            row = conn.execute(
                """SELECT c.company_uuid, c.company_name, c.church_size, c.denomination
                   FROM public.postings p JOIN public.companies c USING (company_uuid) WHERE p.post_uuid = %s""",
                (job_id,),
            ).fetchone()
            if row is None:
                return None
            jobs = conn.execute(
                """UPDATE public.companies SET church_size = coalesce(%(size)s, church_size),
                       church_size_url = CASE WHEN %(size)s::int IS NULL THEN church_size_url ELSE %(by)s END,
                       church_size_source = CASE WHEN %(size)s::int IS NULL THEN church_size_source ELSE 'manual' END,
                       denomination = coalesce(%(denom)s, denomination), enriched_at = coalesce(enriched_at, now())
                   WHERE company_uuid = %(id)s""",
                {"size": church_size, "denom": denomination, "by": entered, "id": row[0]},
            ).rowcount
        else:
            table = BIZDEV_TABLES[source]
            row = conn.execute(
                f"SELECT url_key, org_name, church_size, denomination, city, state FROM public.{table} "
                "WHERE url_key = %s",
                (job_id,),
            ).fetchone()
            if row is None:
                return None
            jobs = conn.execute(
                f"""UPDATE public.{table} SET church_size = coalesce(%(size)s, church_size),
                       church_size_source = CASE WHEN %(size)s::int IS NULL THEN church_size_source ELSE %(by)s END,
                       denomination = coalesce(%(denom)s, denomination),
                       employer_checked_at = coalesce(employer_checked_at, now())
                    WHERE CASE WHEN %(name)s::text IS NULL THEN url_key = %(id)s
                          ELSE lower(org_name) = lower(%(name)s)
                               AND lower(coalesce(city, '')) = lower(coalesce(%(city)s, ''))
                               AND lower(coalesce(state, '')) = lower(coalesce(%(state)s, '')) END""",
                {"size": church_size, "denom": denomination, "by": entered, "id": row[0], "name": row[1],
                 "city": row[4], "state": row[5]},
            ).rowcount  # fmt: skip
    return {"employer": row[1], "old_size": row[2], "old_denomination": row[3], "jobs": jobs}


def delete_job(source: BizdevSource, job_id: str) -> bool:
    """Remove one BizDev job; False when there was no such job. (A feed job would come back with the next feed run,
    so feed jobs are rejected instead: reject_posting.)"""
    with get_conn() as conn:
        gone = conn.execute(
            f"DELETE FROM public.{BIZDEV_TABLES[source]} WHERE url_key = %s RETURNING 1", (job_id,)
        ).fetchone()
    return gone is not None
