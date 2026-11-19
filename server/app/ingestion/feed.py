"""Loading one church-jobs feed posting, with its pay, into companies and postings. The daily feed job
(daily_feed.py) is the only caller: it downloads the feed and skips postings already loaded or rejected before.

A posting already loaded is left as it was. The dashboard works out each job's
role from its title (app/jobs/roles.py) when it loads.
"""

import json
import re
from typing import Any

import psycopg

from app.job_pages.parser import sane_pay

# "85000-100000 per year", "17-22.5 per hour", "42000", "19-23", "4000 per month", "1e+05-1.2e+05 per year"
_NUMBER = r"\$?([\d,]*\.?\d+(?:e\+?\d+)?)"
_PAY_RE = re.compile(rf"^\s*{_NUMBER}\s*(?:-\s*{_NUMBER})?\s*(?:per\s+([a-z]+))?\s*$", re.I)
TIMES_A_YEAR = {"year": 1, "month": 12, "biweekly": 26, "week": 52}  # a day rate or a project fee isn't a wage

UPSERT_COMPANY = """
    INSERT INTO public.companies (company_uuid, company_name, company_url, logo_url, company_categories)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (company_uuid) DO UPDATE
      SET company_name = EXCLUDED.company_name, company_url = EXCLUDED.company_url,
          logo_url = EXCLUDED.logo_url, company_categories = EXCLUDED.company_categories"""

# A posting already loaded is left as it was.
INSERT_POSTING = """
    INSERT INTO public.postings (post_uuid, company_uuid, job_name_raw, department, hours, seniority, education,
        remote, board_source, post_url, job_location, city, region, country, language, first_indexed,
        last_indexed, pull_date, comp_range_raw, comp_est_raw, salary_min, salary_max, salary_period)
    VALUES (%(post_uuid)s, %(company_uuid)s, %(job_name_raw)s, %(department)s, %(hours)s, %(seniority)s,
        %(education)s, %(remote)s, %(board_source)s, %(post_url)s, %(job_location)s, %(city)s, %(region)s,
        %(country)s, %(language)s, %(first_indexed)s, %(last_indexed)s, %(pull_date)s, %(comp_range_raw)s,
        %(comp_est_raw)s, %(salary_min)s, %(salary_max)s, %(salary_period)s)
    ON CONFLICT (post_uuid) DO NOTHING"""

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
    "last_indexed",
)


def parse_salary(comp_range: str | None) -> dict[str, Any]:
    """The feed's pay text -> salary_min, salary_max, salary_period (year or hour), or all None.

    Monthly, bi-weekly and weekly pay becomes yearly. Without a unit, under 200 is hourly. Day rates, project fees and
    figures that aren't a believable wage (sane_pay) give no pay."""
    none = {"salary_min": None, "salary_max": None, "salary_period": None}
    m = _PAY_RE.match(str(comp_range or ""))
    if not m:
        return none
    try:
        lo = float(m[1].replace(",", ""))
        hi = float(m[2].replace(",", "")) if m[2] else lo
    except ValueError:
        return none
    unit = (m[3] or "").lower()
    if unit == "hour":
        period = "hour"
    elif unit in TIMES_A_YEAR:
        lo, hi, period = lo * TIMES_A_YEAR[unit], hi * TIMES_A_YEAR[unit], "year"
    elif unit:
        return none
    else:
        period = "hour" if hi < 200 else "year"
    pay = sane_pay(lo, hi, period)
    return dict(zip(none, pay, strict=True)) if pay else none


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
            "pull_date": pull_date,
            "comp_range_raw": job.get("comp_range"),
            "comp_est_raw": job.get("comp_est"),
            **parse_salary(job.get("comp_range")),
        },
    )
