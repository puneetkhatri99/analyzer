"""Reading and writing jobs across the three sources.

json        the church jobs JSON feed (postings + companies + latest snapshot + latest page check)
churches    BizDev churches sheet, plus jobs added by admins and the collector (church_jobs)
nonprofits  BizDev nonprofits sheet (nonprofit_jobs)
"""

import decimal
from typing import Any, Literal

import psycopg

from app.core.db import get_conn
from app.jobs.roles import bucket_role
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
    "first_indexed", "pull_date", "check_status", "last_live_at", "expired_at", "origin", "added_at",
    "church_size_source",
]  # fmt: skip

# Latest check of the job's URL (job_pages.check) -> what the dashboard shows.
# unknown / blocked / error / never checked all mean the same to a reader: not verified.
STATUS = {"ok": "open", "expired": "expired"}

_FEED_SQL = """
    SELECT p.post_uuid, p.job_name_raw, p.department, p.hours,
           p.seniority, p.remote, p.board_source, p.post_url, p.city, p.region, p.country,
           c.company_name, c.denomination, c.church_size,
           s.salary_min, s.salary_max, s.salary_period,
           p.first_indexed, s.pull_date, k.check_status, k.last_live_at, k.expired_at, 'feed', p.created_at, NULL
    FROM public.postings p
    LEFT JOIN public.companies c USING (company_uuid)
    LEFT JOIN public.posting_checks k USING (post_uuid)
    LEFT JOIN LATERAL (
        SELECT * FROM public.posting_snapshots ps
        WHERE ps.post_uuid = p.post_uuid
        ORDER BY ps.pull_date DESC
        LIMIT 1
    ) s ON true
"""

# The BizDev tables mapped onto the feed's columns. Contact names and emails are never selected.
_BIZDEV_SQL = """
    SELECT url_key, job_title, NULL, hours, NULL, remote, split_part(url_key, '/', 1), job_url,
           city, state, 'US', org_name, denomination, church_size,
           salary_min, salary_max, salary_period, date_posted, fetched_at::date,
           fetch_status, last_live_at, expired_at, added_via, imported_at, church_size_source
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
    """Every posting of one source as a flat dict, plus derived role, status and annual pay.

    Re-queried per request: at a few thousand rows this takes a few ms, so there's no
    cache to invalidate when the pipeline re-runs.
    """
    with get_conn() as conn:
        rows = conn.execute(SOURCES[source]["sql"]).fetchall()

    jobs = []
    for row in rows:
        d = {c: _json_value(v) for c, v in zip(COLUMNS, row, strict=True)}
        d["role"] = bucket_role(d["job_name"])
        d["status"] = STATUS.get(d.pop("check_status"), "unverified")
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
            postings, paid, fetched, open_, expired = conn.execute(
                "SELECT count(*), count(salary_min), count(pull_date), count(*) FILTER (WHERE check_status = 'ok'),"
                f" count(*) FILTER (WHERE check_status = 'expired') FROM ({s['sql']}) j({', '.join(COLUMNS)})"
            ).fetchone()
            out.append(
                {
                    "key": key,
                    "label": s["label"],
                    "postings": postings,
                    "paid": paid,
                    "fetched": fetched,
                    "open": open_,
                    "expired": expired,
                }
            )
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
                (url_key, job_url, {cols}, sheets, fetch_status, fetched_at, last_live_at, added_via, added_by)
            VALUES (%(url_key)s, %(job_url)s, {values}, ARRAY['Added by admin'], 'ok', now(), now(),
                    %(added_via)s, %(added_by)s)
            ON CONFLICT (url_key) DO UPDATE SET {updates},
                fetch_status = 'ok', fetched_at = now(), last_live_at = now(),
                sheets = CASE WHEN 'Added by admin' = ANY(t.sheets) THEN t.sheets
                              ELSE array_append(t.sheets, 'Added by admin') END""",
        row,
    )


def delete_job(source: Source, job_id: str) -> bool:
    """Remove one job for good; False when there was no such job."""
    with get_conn() as conn, conn.transaction():
        if source == "json":
            conn.execute("DELETE FROM public.posting_checks WHERE post_uuid = %s", (job_id,))
            conn.execute("DELETE FROM public.posting_snapshots WHERE post_uuid = %s", (job_id,))
            gone = conn.execute("DELETE FROM public.postings WHERE post_uuid = %s RETURNING 1", (job_id,)).fetchone()
        else:
            table = BIZDEV_TABLES[source]
            gone = conn.execute(f"DELETE FROM public.{table} WHERE url_key = %s RETURNING 1", (job_id,)).fetchone()
    return gone is not None
