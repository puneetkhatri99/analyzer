"""check-jobs: read each BizDev job's page to fill in missing details (pay, job type, remote, denomination, size).

  python -m app.cli check-jobs churches [--limit 30] [--retry]
  python -m app.cli check-jobs nonprofits

The page's schema.org JobPosting data is read first (salary, job type, remote), then the visible text.
fetch_status records how the read went: ok | expired | unknown | blocked | error. Rows already read are skipped;
--retry also re-reads blocked and failed rows.
A site that blocks 10 requests in a row is skipped for the rest of the run; its rows stay unread.
"""

import argparse
import logging
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import urlsplit

from app.core.db import get_conn
from app.core.logs import script_log
from app.job_pages.fetcher import HOST_DELAY, fetch_one
from app.shared.tables import BIZDEV_TABLES
from app.shared.web import with_scheme

MAX_BLOCKED_IN_A_ROW = 10
STATUSES = ("ok", "expired", "unknown", "blocked", "error")

log = logging.getLogger("check_jobs")

# A re-read never erases details found earlier (an expired page has none).
UPDATE_BIZDEV = """UPDATE public.{table} SET fetch_status = %(status)s, fetched_at = now(),
    salary_min = coalesce(%(lo)s, salary_min), salary_max = coalesce(%(hi)s, salary_max),
    salary_period = coalesce(%(period)s, salary_period),
    hours = coalesce(%(hours)s, hours), remote = coalesce(%(remote)s, remote),
    denomination = coalesce(%(denomination)s, denomination), church_size = coalesce(%(church_size)s, church_size)
    WHERE url_key = %(key)s"""

SELECT_BIZDEV = "SELECT url_key, job_url, org_name FROM public.{table} WHERE {where}"


def register(commands: argparse._SubParsersAction) -> None:
    parser = commands.add_parser("check-jobs", help="read BizDev job pages for missing details")
    parser.add_argument("kind", choices=list(BIZDEV_TABLES), help="churches / nonprofits = the BizDev tables")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--retry", action="store_true", help="also re-read rows that were blocked or failed")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--no-skip", action="store_true", help="keep trying a site even after it blocks 10 in a row")
    parser.set_defaults(handler=_run)


def _select_sql(kind: str, retry: bool) -> str:
    where = "fetch_status IS NULL" + (" OR fetch_status IN ('blocked', 'error')" if retry else "")
    return SELECT_BIZDEV.format(table=BIZDEV_TABLES[kind], where=where)


def _run(args: argparse.Namespace) -> int:
    script_log("check_jobs")
    table = BIZDEV_TABLES[args.kind]
    write_sql = UPDATE_BIZDEV.format(table=table)
    log.info("%s: reading jobs not read yet%s", table, ", plus blocked and failed ones" if args.retry else "")
    limit = f" LIMIT {int(args.limit)}" if args.limit else ""
    with get_conn() as conn:
        rows = conn.execute(_select_sql(args.kind, args.retry) + " ORDER BY random()" + limit).fetchall()

    by_host: dict[str, list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        by_host[urlsplit(with_scheme(row[1])).netloc.lower()].append(row)
    log.info("%s: fetching %d pages from %d sites", table, len(rows), len(by_host))

    tally: dict[str, int] = defaultdict(int)
    lock = threading.Lock()
    skipped_hosts: dict[str, int] = {}

    def run_host(host: str, items: list[tuple[Any, ...]]) -> None:
        blocked_in_a_row = 0
        with get_conn() as conn:
            for i, (key, url, org) in enumerate(items):
                if blocked_in_a_row >= MAX_BLOCKED_IN_A_ROW and not args.no_skip:
                    skipped_hosts[host] = len(items) - i
                    return
                status, page = fetch_one(url, org)
                blocked_in_a_row = blocked_in_a_row + 1 if status == "blocked" else 0
                lo, hi, period = page.get("salary") or (None, None, None)
                params = {
                    "status": status,
                    "key": key,
                    "lo": lo,
                    "hi": hi,
                    "period": period,
                    **{f: page.get(f) for f in ("hours", "remote", "denomination", "church_size")},
                }
                conn.execute(write_sql, params)
                log.debug(
                    "%s %s | %s | pay %s | %s | %s | size %s",
                    status,
                    url,
                    org or "-",
                    f"{lo:g}-{hi:g}/{period}" if lo is not None else "-",
                    params["hours"] or "-",
                    params["denomination"] or "-",
                    params["church_size"] or "-",
                )
                with lock:
                    tally[status] += 1
                    tally["with pay"] += bool(page.get("salary"))
                    done = sum(tally[s] for s in STATUSES)
                    if done % 50 == 0:
                        log.info("  %d/%d %s", done, len(rows), dict(tally))
                time.sleep(HOST_DELAY)

    with ThreadPoolExecutor(args.workers) as pool:
        # biggest sites first so the long queues start early
        futures = [
            pool.submit(run_host, host, items) for host, items in sorted(by_host.items(), key=lambda p: -len(p[1]))
        ]
    failed = [f.exception() for f in futures if f.exception()]
    for error in failed:
        log.error("A worker stopped", exc_info=error)

    log.info("%s: done %s", table, dict(tally))
    for host, n in skipped_hosts.items():
        log.warning("Skipped %d rows on %s: it blocked %d requests in a row", n, host, MAX_BLOCKED_IN_A_ROW)
    return 1 if failed else 0
