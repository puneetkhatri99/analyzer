"""collect-jobs: collect new US church job postings into church_jobs (the BizDev churches tab), added_via 'collector'.

  python -m app.cli collect-jobs                           # every source
  python -m app.cli collect-jobs --source sbc --dry-run    # list what's new without reading or saving anything
  python -m app.cli collect-jobs --days 30 --limit 50      # job boards: only jobs posted/updated in the last 30 days
  python -m app.cli collect-jobs --verbose                 # also show every request and listed job on screen

Sources (left-out sites in COLLECTOR_GAPS.md): sbc, churchstaffing, ministrylist, efca (boards.py) and employers
(employers.py). Each new job page is read with job_pages.fetch_one for pay, job type, denomination and church size.
Jobs outside the US, expired jobs and pages that are blocked or fail aren't saved (failed ones are tried again next
run). Jobs already in church_jobs (same url_key) are skipped, so it's safe to run every day.

Every run writes a full log to server/logs/collect_jobs-<date>-<time>.log and ends with a summary and a PROBLEMS list
that says when a site seems to have changed, blocked the collector or was down. The exit code is 1 when there are
problems.
"""

import argparse
import json
import logging
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit

from app.core.config import get_settings
from app.core.db import get_conn
from app.core.logs import LOG_DIR, script_log
from app.ingestion.collector.boards import CRAWL_DELAY, churchstaffing, efca, ministrylist, sbc
from app.ingestion.collector.employers import employers
from app.ingestion.collector.http import FORMAT_ERRORS, CollectorSession, format_problem
from app.ingestion.collector.problems import ADVICE, SiteProblem, platform_problems, source_health
from app.job_pages.fetcher import HOST_DELAY, fetch_one
from app.job_pages.parser import denomination_in
from app.shared.dates import to_date
from app.shared.geo import is_us, split_place, state_code
from app.shared.web import url_key

SOURCES = {
    "sbc": sbc,
    "churchstaffing": churchstaffing,
    "ministrylist": ministrylist,
    "efca": efca,
    "employers": employers,
}
LAST_COUNTS = LOG_DIR / "collect_last_counts.json"  # jobs listed per source last run, to spot a sudden drop

log = logging.getLogger("collect_jobs")

INSERT = """INSERT INTO public.church_jobs (url_key, job_url, job_title, org_name, org_website, city, state,
        date_posted, salary_min, salary_max, salary_period, hours, remote, denomination, church_size,
        sheets, fetch_status, fetched_at, last_live_at, added_via)
    VALUES (%(key)s, %(url)s, %(title)s, %(org)s, %(org_website)s, %(city)s, %(state)s, %(date_posted)s,
        %(lo)s, %(hi)s, %(period)s, %(hours)s, %(remote)s, %(denomination)s, %(church_size)s,
        ARRAY['Auto-collected'], %(status)s, now(), CASE WHEN %(status)s = 'ok' THEN now() END, 'collector')
    ON CONFLICT (url_key) DO NOTHING"""

# outcome of reading one job -> (stats key, words for the log)
OUTCOMES = {
    "saved": ("saved", None),
    "already saved": ("known_late", "already saved"),
    "save failed": ("save_failed", "database error"),
    "expired": ("expired", "job is expired or filled"),
    "blocked": ("blocked", "page blocked the collector"),
    "error": ("failed", "page failed to load"),
    "not US": ("not_us_page", "job is outside the US"),
    "no details": ("no_details", "no job title on the page or in the listing"),
}

Job = dict[str, Any]
Stats = dict[str, int]


def read_job(job: Job) -> tuple[str, Job | None]:
    """Fill a listed job from its own page. Returns (status, row); row is None when it shouldn't be saved.
    status: ok | unknown (page needs a browser) | expired | blocked | error | not US | no details."""
    status, page = fetch_one(job["url"], job.get("org"))
    if status not in ("ok", "unknown"):
        return status, None
    row = {k: job.get(k) for k in ("title", "org", "org_website", "city", "state", "country", "date_posted", "hours")}
    for k in (
        "title",
        "org",
        "org_website",
        "city",
        "state",
        "country",
        "hours",
    ):  # the listing wins; the page fills gaps
        row[k] = row[k] or page.get(k)
    if not row["title"]:
        return "no details", None
    if not (row["city"] or row["state"]) and page.get("place"):
        row["city"], row["state"], row["country"] = split_place(page["place"])
    row["date_posted"] = row["date_posted"] or to_date((page.get("date_posted") or "")[:10] or None)
    row["state"] = state_code(row["state"]) or row["state"]
    # The page was read before its church name was known (sitemap sources), so match the name now.
    denomination = job.get("denomination") or page.get("denomination") or denomination_in(row["org"])
    if not is_us(row["state"], row["country"]):
        return "not US", None
    lo, hi, period = page.get("salary") or (None, None, None)
    return status, {
        **row,
        "key": url_key(job["url"]),
        "url": job["url"],
        "lo": lo,
        "hi": hi,
        "period": period,
        "remote": page.get("remote"),
        "denomination": denomination,
        "church_size": page.get("church_size"),
    }


def describe(row: Job) -> str:
    """One readable line for the log."""
    pay = f"${row['lo']:,.0f}–{row['hi']:,.0f}/{row['period']}" if row["lo"] is not None else "no pay listed"
    place = ", ".join(x for x in (row["city"], row["state"]) if x) or "no location"
    size = f"{row['church_size']:,}+ attendance" if row["church_size"] else None
    parts = (row["title"], row["org"] or "no church name", place, pay, row["hours"], row["denomination"], size)
    return " | ".join(x for x in parts if x)


def register(commands: argparse._SubParsersAction) -> None:
    parser = commands.add_parser("collect-jobs", help="collect new church job postings into church_jobs")
    parser.add_argument("--source", choices=SOURCES, action="append", help="repeatable; default: every source")
    parser.add_argument(
        "--days", type=int, default=45, help="job boards: skip jobs posted/updated longer ago than this"
    )
    parser.add_argument("--limit", type=int, help="read at most this many new jobs")
    parser.add_argument("--dry-run", action="store_true", help="only list new jobs; don't read their pages or save")
    parser.add_argument("--verbose", action="store_true", help="also show every request and listed job on screen")
    parser.set_defaults(handler=_run)


def _list_new(
    s: CollectorSession, name: str, st: Stats, since: date, days: int, known: set[str], report: dict[str, Any]
) -> list[Job]:
    """The source's listed jobs that are recent, in the US and not saved yet. Raises SiteProblem."""
    new = []
    for job in SOURCES[name](s, since, report):
        st["listed"] += 1
        st["listed_no_title"] += not job.get("title")
        where = (
            ", ".join(x for x in (job.get("city"), job.get("state"), job.get("country")) if x) or "location not listed"
        )
        if job.get("updated") and job["updated"] < since:
            st["too_old"] += 1
            verdict = f"older than {days} days ({job['updated']})"
        elif not is_us(job.get("state"), job.get("country")):
            st["not_us"] += 1
            verdict = "outside the US"
        elif (key := url_key(job["url"])) in known:
            st["known"] += 1
            verdict = "already saved"
        else:
            known.add(key)
            st["new"] += 1
            new.append({**job, "source": name})
            verdict = "NEW"
        log.debug(
            "[%s] listed: %s | %s | %s | %s -> %s",
            name,
            job.get("title") or "(title on its page)",
            job.get("org") or "-",
            where,
            job["url"],
            verdict,
        )
    return new


def _read_and_save(new: list[Job], stats: dict[str, Stats]) -> list[BaseException]:
    """Read every new job's page and save the good ones; one thread per site. Returns crashed workers' errors."""
    by_host: dict[str, list[Job]] = defaultdict(list)
    for j in new:
        by_host[urlsplit(j["url"]).netloc.lower().removeprefix("www.")].append(j)
    lock, done = threading.Lock(), [0]
    log.info("-" * 78)
    log.info(
        "Reading %d new job pages from %d sites (1 s apart per site, %s)",
        len(new),
        len(by_host),
        ", ".join(f"{h} {d:.0f} s" for h, d in CRAWL_DELAY.items()),
    )

    def run_host(host: str, jobs: list[Job]) -> None:
        with get_conn() as conn:
            for job in jobs:
                name = job["source"]
                try:
                    status, row = read_job(job)
                except Exception as e:  # a parser bug on one odd page shouldn't stop the site
                    status, row = "error", None
                    log.exception("[%s] crashed reading %s: %s", name, job["url"], e)
                outcome = status
                if row:
                    try:
                        outcome = "saved" if conn.execute(INSERT, row).rowcount else "already saved"
                    except Exception as e:  # keep going: the summary reports save failures as a database problem
                        outcome = "save failed"
                        log.error("[%s] SAVE FAILED %s: %s", name, job["url"], e)
                stat_key, why = OUTCOMES[outcome]  # read_job only returns a row for ok/unknown pages
                with lock:
                    st = stats[name]
                    st["read"] += 1
                    st[stat_key] += 1
                    st["unverified"] += outcome == "saved" and status == "unknown"
                    done[0] += 1
                    if outcome == "saved":
                        log.info(
                            "[%s] SAVED%s %s | %s",
                            name,
                            " (open/closed not readable)" if status == "unknown" else "",
                            describe(row),
                            job["url"],
                        )
                    else:
                        log.info("[%s] not saved, %s: %s", name, why, job["url"])
                    if done[0] % 50 == 0:
                        log.info("... %d of %d job pages read", done[0], len(new))
                time.sleep(CRAWL_DELAY.get(host, HOST_DELAY))

    with ThreadPoolExecutor(8) as pool:
        futures = [pool.submit(run_host, h, js) for h, js in sorted(by_host.items(), key=lambda p: -len(p[1]))]
    return [e for f in futures if (e := f.exception())]


def _log_summary(names: list[str], stats: dict[str, Stats], dry_run: bool, started: float) -> None:
    log.info("=" * 78)
    log.info("SUMMARY%s (%.0f min)", " (dry run)" if dry_run else "", (time.time() - started) / 60)
    log.info(
        f"{'source':15}{'listed':>7}{'new':>6}{'saved':>7}{'unverif.':>9}{'expired':>8}{'blocked':>8}"
        f"{'failed':>7}{'no info':>8}{'not US':>7}"
    )
    for n in names:
        st = stats[n]
        # extra= fields: one queryable row per source per run in Axiom (event = "source_summary")
        log.info(
            f"{n:15}{st['listed']:>7}{st['new']:>6}{st['saved']:>7}{st['unverified']:>9}{st['expired']:>8}"
            f"{st['blocked']:>8}{st['failed']:>7}{st['no_details']:>8}{st['not_us'] + st['not_us_page']:>7}",
            extra={
                "event": "source_summary",
                "source": n,
                "dry_run": dry_run,
                **{
                    k: st[k]
                    for k in (
                        "listed",
                        "new",
                        "known",
                        "too_old",
                        "saved",
                        "unverified",
                        "expired",
                        "blocked",
                        "failed",
                        "no_details",
                        "save_failed",
                    )
                },
                "not_us": st["not_us"] + st["not_us_page"],
            },
        )
    log.info(
        "saved = added to the BizDev churches tab; unverif. = saved, but the page needs a browser to tell "
        "open/closed; failed and blocked pages are retried next run"
    )


def _run(args: argparse.Namespace) -> int:
    since = date.today() - timedelta(days=args.days)
    names = args.source or list(SOURCES)
    log_path = script_log("collect_jobs", args.verbose)
    started = time.time()

    log.info("=" * 78)
    log.info(
        "Church job collector: %s", "DRY RUN (nothing is read or saved)" if args.dry_run else "collecting and saving"
    )
    log.info(
        "Sources: %s | job boards look back %d days (since %s)%s",
        ", ".join(names),
        args.days,
        since,
        f" | at most {args.limit} jobs read" if args.limit else "",
    )
    log.info("Database: %s | log: %s", urlsplit(get_settings().database_url or "").hostname, log_path)
    log.info("=" * 78)

    problems: list[tuple[str, SiteProblem]] = []
    report: dict[str, Any] = {}
    stats: dict[str, Stats] = {n: defaultdict(int) for n in names}
    try:
        with get_conn() as conn:
            known = {r[0] for r in conn.execute("SELECT url_key FROM public.church_jobs").fetchall()}
    except Exception as e:  # any connection or query failure: nothing can run without the database
        log.error("Can't read the database: %s", e)
        log.error(ADVICE["database"])
        return 1
    log.info("church_jobs already holds %s jobs; those are skipped", f"{len(known):,}")

    s = CollectorSession()
    new: list[Job] = []
    for name in names:
        st, t = stats[name], time.time()
        log.info("-" * 78)
        log.info("[%s] listing jobs", name)
        try:
            new += _list_new(s, name, st, since, args.days, known, report)
        except SiteProblem as p:
            problems.append((name, p))
            log.error("[%s] STOPPED: %s: %s, %s", name, p.kind, p.detail, p.url)
        except FORMAT_ERRORS as e:
            p = format_problem(s, e)
            problems.append((name, p))
            log.error("[%s] STOPPED: %s: %s, %s", name, p.kind, p.detail, p.url)
        log.info(
            "[%s] %d listed: %d new, %d already saved, %d older than %d days, %d outside the US (%.0fs)",
            name,
            st["listed"],
            st["new"],
            st["known"],
            st["too_old"],
            args.days,
            st["not_us"],
            time.time() - t,
        )

    problems += [("employers", p) for p in platform_problems(report.get("churches", []))]
    skipped_churches = [c for c in report.get("churches", []) if c["problem"]]

    if args.limit and len(new) > args.limit:
        log.info(
            "--limit %d: reading %d of %d new jobs; the rest are picked up next run", args.limit, args.limit, len(new)
        )
        new = new[: args.limit]

    if not args.dry_run and new:
        for error in _read_and_save(new, stats):
            log.error("A worker stopped: %s", error)
            problems.append(("all", SiteProblem("database", "-", str(error))))

    # Health checks: a source can break without any request failing.
    try:
        last = json.loads(LAST_COUNTS.read_text())
    except (OSError, ValueError):
        last = {}
    for name in names:
        if any(n == name for n, _ in problems):
            continue  # already explained
        prev = last.get(name, {})
        previous_listed = prev.get("listed") if prev.get("days") == args.days else None
        for kind, detail in source_health(name, stats[name], previous_listed, args.days):
            problems.append((name, SiteProblem(kind, "(see the log for its addresses)", detail)))
        if stats[name]["save_failed"]:
            problems.append(
                (name, SiteProblem("database", "-", f"{stats[name]['save_failed']} jobs could not be saved"))
            )
    last.update(
        {
            n: {"listed": stats[n]["listed"], "days": args.days, "at": f"{datetime.now():%Y-%m-%d %H:%M}"}
            for n in names
            if not any(p_n == n for p_n, _ in problems)
        }
    )
    LAST_COUNTS.write_text(json.dumps(last, indent=1))

    _log_summary(names, stats, args.dry_run, started)
    if skipped_churches:
        log.info("Churches skipped this run (%d of %d):", len(skipped_churches), len(report["churches"]))
        for c in skipped_churches:
            log.info("  - %s (%s): %s, %s", c["org"], c["platform"], c["problem"].kind, c["problem"].detail)

    log.info("=" * 78)
    if not problems:
        log.info("PROBLEMS: none. Every source answered as expected.")
    else:
        log.warning("PROBLEMS: %d need attention", len(problems))
        for i, (name, p) in enumerate(problems, 1):
            log.warning(
                "%d. [%s] %s: %s",
                i,
                name,
                p.kind.upper(),
                p.detail,
                extra={"event": "problem", "source": name, "kind": p.kind, "url": p.url},
            )
            log.warning("   Address: %s", p.url)
            log.warning("   What to do: %s", ADVICE[p.kind].format(source=name))
    log.info("Full log: %s", log_path)
    return 1 if problems else 0
