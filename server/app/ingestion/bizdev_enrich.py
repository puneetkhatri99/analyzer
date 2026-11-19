"""bizdev-enrich: after the sheets are synced, fill in what they leave empty, with a cap per run so a backlog
drains over several days instead of costing a lot at once.

  employers   church size and denomination, once per employer (all its jobs share them): the name first (free), then
              a web search for weekly attendance, as for the JSON jobs (daily_feed.look_up_church). Church sheet:
              every employer. Nonprofit sheet: only names that look like a church.
  pay         a job whose page couldn't be read (SimplyHired and others block every request) is read through web
              search. Pages that were read and state no pay are left alone: a search wouldn't find it either.

  python -m app.cli bizdev-enrich [--limit 50]       # employers and jobs per sheet; default ENRICH_MAX_PER_RUN
"""

import argparse
import logging
import re
from typing import Any

from openai import OpenAI

from app.ai_usage.service import budget, ensure_budget, record
from app.core.config import get_settings
from app.core.db import get_conn
from app.core.logs import script_log
from app.extraction.prompts import INSTRUCTIONS, WEB_SEARCH_PROMPT
from app.extraction.schemas import JobExtraction
from app.extraction.service import LOOKUP_FAILED
from app.extraction.validation import validate
from app.ingestion import daily_feed
from app.ingestion.daily_feed import ai_map, look_up_church
from app.job_pages.parser import denomination_in
from app.jobs.repository import BIZDEV_TABLES

log = logging.getLogger("bizdev_enrich")

# Nonprofit employers worth a church lookup: the name says it is a congregation.
CHURCH_NAME = (
    r"\y(church|churches|baptist|methodist|presbyterian|lutheran|episcopal|catholic|parish|cathedral|chapel"
    r"|congregation)\y"  # not "fellowship": Mission Aviation Fellowship is a mission agency, not a church
)
NO_PAY_PAGE = ("blocked", "error", "unknown")  # fetch_status values where the page's own pay was never seen
MAX_AGE_DAYS = 180  # an older posting is probably closed: not worth a search
WORD = re.compile(r"[a-z]{4,}")


def clean_denomination(value: str | None) -> str | None:
    """A denomination name, or None when the AI answered with a sentence or a remark ("... (not a church)")."""
    if not value or len(value) > 40 or re.search(r'[()/;"]', value):
        return None
    return value


def share_known_values(table: str, prefix: str = "") -> None:
    """A job synced after its employer was looked up gets the employer's size and denomination, free.
    `prefix` limits every function below to jobs whose url_key starts with it (the tests use it)."""
    with get_conn() as conn:
        conn.execute(
            f"""UPDATE public.{table} t SET denomination = coalesce(t.denomination, s.denomination),
                   church_size = coalesce(t.church_size, s.church_size),
                   church_size_source = CASE WHEN t.church_size IS NULL THEN s.church_size_source
                                             ELSE t.church_size_source END,
                   employer_checked_at = s.employer_checked_at
                FROM (SELECT DISTINCT ON (lower(org_name)) lower(org_name) AS k, denomination, church_size,
                             church_size_source, employer_checked_at
                      FROM public.{table} WHERE employer_checked_at IS NOT NULL AND org_name IS NOT NULL
                      ORDER BY lower(org_name), church_size IS NULL, employer_checked_at DESC) s
                WHERE lower(t.org_name) = s.k AND t.employer_checked_at IS NULL AND t.url_key LIKE %s""",
            (prefix + "%",),
        )


def name_denominations(table: str, prefix: str = "") -> int:
    """Free: a denomination the employer's own name gives away ("First Baptist Church"). Returns rows updated."""
    with get_conn() as conn:
        names = [
            r[0]
            for r in conn.execute(
                f"SELECT DISTINCT org_name FROM public.{table} "
                "WHERE denomination IS NULL AND org_name IS NOT NULL AND url_key LIKE %s",
                (prefix + "%",),
            )
        ]
        done = 0
        for name in names:
            if found := denomination_in(name):
                done += conn.execute(
                    f"UPDATE public.{table} SET denomination = %s "
                    "WHERE denomination IS NULL AND lower(org_name) = lower(%s)",
                    (found, name),
                ).rowcount
    return done


def employers_to_look_up(kind: str, limit: int, prefix: str = "") -> list[tuple]:
    table = BIZDEV_TABLES[kind]
    only_churches = "" if kind == "churches" else f"AND org_name ~* '{CHURCH_NAME}'"
    with get_conn() as conn:
        return conn.execute(
            f"""SELECT min(org_name), min(org_website), min(city), min(state) FROM public.{table}
                WHERE employer_checked_at IS NULL AND org_name IS NOT NULL AND url_key LIKE %s {only_churches}
                GROUP BY lower(org_name) HAVING max(church_size) IS NULL  -- one job with a size is enough
                ORDER BY count(*) DESC, lower(org_name) LIMIT %s""",
            (prefix + "%", limit),
        ).fetchall()


def enrich_employers(client: Any, kind: str, limit: int, prefix: str = "") -> int:
    """Church size and denomination for employers not looked up yet. Returns how many were stamped."""
    table = BIZDEV_TABLES[kind]
    share_known_values(table, prefix)
    name_denominations(table, prefix)
    rows = employers_to_look_up(kind, limit, prefix)
    log.info("%s: looking up %d employers (weekly attendance, denomination)", table, len(rows))
    done = 0
    for row, (result, failed) in zip(rows, ai_map(lambda r: look_up_church(client, *r), rows), strict=True):
        name = row[0]
        job, source, notes = result or (None, None, [])
        if failed or (notes and notes[0].startswith(LOOKUP_FAILED)):
            log.warning("%s: lookup failed, will retry next run", name)
            continue  # the search itself broke (network, quota): leave it for the next run
        job, _ = validate(job)
        denomination = clean_denomination(job.denomination)
        with get_conn() as conn:
            conn.execute(
                f"""UPDATE public.{table} SET denomination = coalesce(denomination, %s),
                       church_size_source = CASE WHEN church_size IS NULL THEN %s ELSE church_size_source END,
                       church_size = coalesce(church_size, %s), employer_checked_at = now()
                    WHERE lower(org_name) = lower(%s)""",
                (denomination, source if job.church_size else None, job.church_size, name),
            )
        done += 1
        log.info("%s: %s, %s", name, denomination or "denomination unknown",
                 f"{job.church_size:,} weekly" if job.church_size else "attendance not found online")  # fmt: skip
    return done


def jobs_to_read(kind: str, limit: int, prefix: str = "") -> list[tuple]:
    with get_conn() as conn:
        return conn.execute(
            f"""SELECT url_key, job_url, job_title, org_name FROM public.{BIZDEV_TABLES[kind]}
                WHERE salary_min IS NULL AND pay_checked_at IS NULL
                  AND (fetch_status IS NULL OR fetch_status = ANY(%s))
                  AND (date_posted IS NULL OR date_posted > current_date - %s) AND url_key LIKE %s
                ORDER BY date_posted DESC NULLS LAST LIMIT %s""",
            (list(NO_PAY_PAGE), MAX_AGE_DAYS, prefix + "%", limit),
        ).fetchall()


def same_employer(asked: str | None, found: str | None) -> bool:
    """The page the search found is for the employer in the sheet: they share a word of 4+ letters."""
    return bool(asked and found and set(WORD.findall(asked.lower())) & set(WORD.findall(found.lower())))


def read_job(client: Any, row: tuple) -> JobExtraction | None:
    """One web-search read of a job whose page can't be fetched. None when it isn't the sheet's job."""
    _, url, _, org = row
    model = get_settings().openai_model
    ensure_budget()
    response = client.responses.parse(
        model=model, instructions=INSTRUCTIONS, input=WEB_SEARCH_PROMPT.format(url=url), text_format=JobExtraction,
        tools=[{"type": "web_search"}], max_tool_calls=4,
    )  # fmt: skip
    record(response, purpose="bizdev_pay", url=url, model=model, admin_email=None)
    job = response.output_parsed
    if job is None or job.page_type != "job_posting" or not same_employer(org, job.org_name):
        return None
    return validate(job)[0]


def enrich_pay(client: Any, kind: str, limit: int, prefix: str = "") -> tuple[int, int]:
    """Pay (and job type) for jobs whose page can't be read. Returns (jobs searched, jobs where pay was found)."""
    table = BIZDEV_TABLES[kind]
    rows = jobs_to_read(kind, limit, prefix)
    log.info("%s: reading %d jobs through web search", table, len(rows))
    searched = found = 0
    for row, (job, failed) in zip(rows, ai_map(lambda r: read_job(client, r), rows), strict=True):
        if failed:
            log.warning("%s: the search failed (%s), will retry next run", row[1], failed)
            continue
        has_pay = bool(job and job.salary_min is not None)
        with get_conn() as conn:
            conn.execute(
                f"""UPDATE public.{table} SET pay_checked_at = now(),
                       salary_min = coalesce(salary_min, %s), salary_max = coalesce(salary_max, %s),
                       salary_period = coalesce(salary_period, %s),
                       salary_source = CASE WHEN salary_min IS NULL AND %s THEN 'ai' ELSE salary_source END,
                       hours = coalesce(hours, %s), remote = coalesce(remote, %s)
                    WHERE url_key = %s""",
                (job and job.salary_min, job and job.salary_max, job and job.salary_period, has_pay,
                 job and job.hours, job and (None if job.remote is None else str(job.remote).lower()), row[0]),
            )  # fmt: skip
        searched += 1
        found += has_pay
    return searched, found


def run(limit: int | None = None) -> dict[str, Any]:
    """Enrich both sheets. Free steps always run; the AI steps need OPENAI_API_KEY."""
    settings = get_settings()
    limit = limit or settings.enrich_max_per_run
    result: dict[str, Any] = {"employers": 0, "pay_searched": 0, "pay_found": 0}
    b = budget() if settings.openai_api_key else None
    if not settings.openai_api_key or b["reached"]:  # the free steps still run
        for kind in BIZDEV_TABLES:
            share_known_values(BIZDEV_TABLES[kind])
            name_denominations(BIZDEV_TABLES[kind])
        if b:
            result["skipped"] = f"the monthly AI limit (${b['limit_usd']:.2f}) is reached"
            daily_feed.alert_admin(
                "MinistryHub monthly AI limit reached",
                f"The BizDev AI step is paused: {result['skipped']}. "
                f"Raise it in Admin → AI costs: {daily_feed._admin_link()}",
            )
        else:
            result["skipped"] = "OPENAI_API_KEY isn't set"
        return result
    client = OpenAI(api_key=settings.openai_api_key)
    for kind in BIZDEV_TABLES:
        result["employers"] += enrich_employers(client, kind, limit)
        searched, found = enrich_pay(client, kind, limit)
        result["pay_searched"] += searched
        result["pay_found"] += found
    return result


def register(commands: argparse._SubParsersAction) -> None:
    parser = commands.add_parser("bizdev-enrich", help="fill in church size, denomination and pay on the BizDev jobs")
    parser.add_argument(
        "--limit", type=int, help="employers and jobs to look up per sheet (default ENRICH_MAX_PER_RUN)"
    )
    parser.set_defaults(handler=_run)


def _run(args: argparse.Namespace) -> int:
    script_log("bizdev_enrich")
    log.info("Done: %s", run(args.limit))
    return 0
