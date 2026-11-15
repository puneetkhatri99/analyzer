"""ingest-feed: load a church-jobs JSON feed into companies, postings, and a pay snapshot per pull date.

  python -m app.cli ingest-feed data/raw/church_jobs_feed_02.10.26.json [--pull-date 2026-11-04] [--limit 500]

Re-running is safe: companies are updated, a posting already loaded is left as it was, and its pay for the pull date
is replaced. The dashboard works out each job's role from its title (app/jobs/roles.py) when it loads.
"""

import argparse
import json
import logging
import re
from datetime import date
from typing import Any

import psycopg

from app.core.db import connect
from app.core.logs import script_log

log = logging.getLogger("ingest")

_RANGE_RE = re.compile(r"([\d,.]+)\s*-\s*([\d,.]+)\s*per\s*(year|hour)", re.I)
_SINGLE_RE = re.compile(r"([\d,.]+)\s*per\s*(year|hour)", re.I)

UPSERT_COMPANY = """
    INSERT INTO public.companies (company_uuid, company_name, company_url, logo_url, company_categories)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (company_uuid) DO UPDATE
      SET company_name = EXCLUDED.company_name, company_url = EXCLUDED.company_url,
          logo_url = EXCLUDED.logo_url, company_categories = EXCLUDED.company_categories"""

# A posting already loaded is left as it was; its pay changes arrive as a new snapshot.
INSERT_POSTING = """
    INSERT INTO public.postings (post_uuid, company_uuid, job_name_raw, department, hours, seniority, education,
        remote, board_source, post_url, job_location, city, region, country, language, first_indexed)
    VALUES (%(post_uuid)s, %(company_uuid)s, %(job_name_raw)s, %(department)s, %(hours)s, %(seniority)s,
        %(education)s, %(remote)s, %(board_source)s, %(post_url)s, %(job_location)s, %(city)s, %(region)s,
        %(country)s, %(language)s, %(first_indexed)s)
    ON CONFLICT (post_uuid) DO NOTHING"""

UPSERT_SNAPSHOT = """
    INSERT INTO public.posting_snapshots (post_uuid, pull_date, comp_range_raw, comp_est_raw,
        salary_min, salary_max, salary_period, last_indexed, is_active)
    VALUES (%(post_uuid)s, %(pull_date)s, %(comp_range_raw)s, %(comp_est_raw)s,
        %(salary_min)s, %(salary_max)s, %(salary_period)s, %(last_indexed)s, %(is_active)s)
    ON CONFLICT (post_uuid, pull_date) DO UPDATE
      SET comp_range_raw = EXCLUDED.comp_range_raw, comp_est_raw = EXCLUDED.comp_est_raw,
          salary_min = EXCLUDED.salary_min, salary_max = EXCLUDED.salary_max,
          salary_period = EXCLUDED.salary_period, last_indexed = EXCLUDED.last_indexed,
          is_active = EXCLUDED.is_active"""

POSTING_FIELDS = (
    "department",
    "hours",
    "seniority",
    "education",
    "remote",
    "board_source",
    "post_url",
    "job_location",
    "city",
    "region",
    "country",
    "language",
    "first_indexed",
)


def parse_salary(comp_range: str | None) -> dict[str, Any]:
    """'85000-100000 per year' / '17-22.5 per hour' / '70304 per year' -> salary_min, salary_max, salary_period."""
    none = {"salary_min": None, "salary_max": None, "salary_period": None}
    if not comp_range:
        return none
    text = str(comp_range)
    if m := _RANGE_RE.search(text):
        lo, hi, period = m.groups()
        return {
            "salary_min": float(lo.replace(",", "")),
            "salary_max": float(hi.replace(",", "")),
            "salary_period": period.lower(),
        }
    if m := _SINGLE_RE.search(text):
        value, period = m.groups()
        v = float(value.replace(",", ""))
        return {"salary_min": v, "salary_max": v, "salary_period": period.lower()}
    return none


def load_posting(conn: psycopg.Connection, job: dict[str, Any], pull_date: str) -> None:
    post_uuid, company_uuid = job["post_uuid"], job.get("company_uuid")
    if company_uuid:
        conn.execute(
            UPSERT_COMPANY,
            (
                company_uuid,
                job.get("company_name"),
                job.get("company_url"),
                job.get("logo_url"),
                json.dumps(job.get("company_categories")),
            ),
        )
    conn.execute(
        INSERT_POSTING,
        {
            "post_uuid": post_uuid,
            "company_uuid": company_uuid,
            "job_name_raw": job.get("job_name") or "",
            **{f: job.get(f) for f in POSTING_FIELDS},
        },
    )
    conn.execute(
        UPSERT_SNAPSHOT,
        {
            "post_uuid": post_uuid,
            "pull_date": pull_date,
            "comp_range_raw": job.get("comp_range"),
            "comp_est_raw": job.get("comp_est"),
            **parse_salary(job.get("comp_range")),
            "last_indexed": job.get("last_indexed"),
            "is_active": True,
        },
    )


def register(commands: argparse._SubParsersAction) -> None:
    parser = commands.add_parser("ingest-feed", help="load a church jobs JSON feed")
    parser.add_argument("json_file")
    parser.add_argument("--pull-date", default=date.today().isoformat())
    parser.add_argument("--limit", type=int, default=None)
    parser.set_defaults(handler=_run)


def _run(args: argparse.Namespace) -> int:
    script_log("ingest")
    with open(args.json_file, encoding="utf-8") as f:
        jobs = json.load(f)
    if args.limit is not None:  # --limit 0 means none, not all
        jobs = jobs[: args.limit]
    log.info("Loading %d postings from %s (pull date %s)", len(jobs), args.json_file, args.pull_date)

    loaded = 0
    with connect() as conn:
        for i, job in enumerate(jobs, 1):
            if not job.get("post_uuid"):
                log.warning("Posting %d skipped: it has no post_uuid (%s)", i, job.get("job_name") or "untitled")
                continue
            with conn.transaction():  # a posting's company, row and snapshot land together or not at all
                load_posting(conn, job, args.pull_date)
            loaded += 1
            log.debug(
                "Posting %s: %s | %s | pay %s",
                job["post_uuid"],
                job.get("job_name") or "",
                job.get("company_name") or "-",
                job.get("comp_range") or "-",
            )
            if i % 100 == 0:
                log.info("%d/%d postings processed", i, len(jobs))
    log.info("Done. %d postings loaded.", loaded)
    return 0
