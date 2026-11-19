"""daily-feed: once a day, download the church jobs feed, add the postings that aren't in the database yet, and let the
AI review every posting not judged yet: is the employer in scope (a church, Christian school or ministry; see
SCOPE_RULES), what kind of employer is it, and what pay does the text state. Then churches get their denomination and
size (web search). DAILY_FEED.md explains the setup.

  python -m app.cli daily-feed             # runs once a day, after FEED_HOUR_UTC
  python -m app.cli daily-feed --force     # run now
  python -m app.cli daily-feed --dry-run   # download and count the new postings; change nothing

The feed link is signed and expires. An admin pastes the new one in Admin → Settings; when the link has expired
(or is 7 days from it) the addresses that get the daily lead report are emailed, once a day, until it is replaced.
Postings already in the database are left alone: no new AI calls.
"""

import argparse
import contextvars
import logging
import re
import threading
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import parse_qs, urlsplit

import requests
from openai import OpenAI

from app.ai_usage.service import budget, current_run, ensure_budget, record
from app.core.config import get_settings
from app.core.db import get_conn
from app.core.logs import script_log
from app.core.settings_store import delete_setting, get_setting, set_setting
from app.extraction.page import page_text
from app.extraction.prompts import FENCE_RE, INJECTION_RE, REVIEW_INSTRUCTIONS
from app.extraction.schemas import JobExtraction, PostingReview
from app.extraction.service import LOOKUP_FAILED, lookup_church
from app.extraction.validation import complete_pay, found_on_page, validate
from app.ingestion.feed import load_posting
from app.job_pages.parser import denomination_in
from app.jobs.repository import reject_posting
from app.leads.daily_report import get_recipients
from app.shared.email import EmailError, email_ready, send_email
from app.shared.web import UnsafeURLError, get_public

log = logging.getLogger("daily_feed")

URL_KEY = "feed_url"
DONE_KEY = "daily_feed_done_for"
STATUS_KEY = "daily_feed_status"
ALERT_KEY = "daily_feed_alert_for"
WARN_DAYS = 7  # email this many days before the link expires
CHECK_EVERY = 15 * 60  # seconds, for the API's own timer
MAX_POST_CHARS = 12_000  # of one posting's text sent to the AI

_running = threading.Lock()  # a run takes minutes; two at once would do the same work twice

# What the current run is doing, for Admin → Settings to show while it runs. In memory: only this process runs it.
MAX_LINES = 60
live: dict[str, Any] = {}


def note(text: str, **counts: Any) -> None:
    """One line of progress: to the log, and to the admin page (the latest MAX_LINES lines, with running counts)."""
    log.info(text)
    live.update(counts)
    if run_id := live.get("run_id"):
        live["cost"], live["calls"] = run_cost(run_id)
    live["lines"] = [*live.get("lines", []), f"{datetime.now(UTC):%H:%M:%S} {text}"][-MAX_LINES:]


def run_cost(run_id: str) -> tuple[float, int]:
    """What one run's AI calls have cost so far (estimated, USD) and how many calls it made."""
    with get_conn() as conn:
        cost, calls = conn.execute(
            "SELECT coalesce(sum(cost_usd), 0), count(*) FROM public.ai_usage WHERE run_id = %s", (run_id,)
        ).fetchone()
    return float(cost), calls


class FeedError(Exception):
    pass


# ---- the feed link ---------------------------------------------------------------------------------------------


def feed_url() -> str | None:
    return get_setting(URL_KEY) or get_settings().feed_url


def check_feed_url(url: str) -> datetime | None:
    """Raise ValueError unless `url` looks like a signed https feed link; returns when it expires."""
    parts = urlsplit(url.strip())
    if parts.scheme != "https" or not parts.hostname:
        raise ValueError("The feed link must start with https://")
    expires = expires_at(url)
    if expires is None:
        raise ValueError("The link has no Expires= value: copy the whole signed link.")
    return expires


def expires_at(url: str | None) -> datetime | None:
    """When a signed link stops working (its Expires= value, a Unix time), or None."""
    try:
        value = parse_qs(urlsplit(url or "").query).get("Expires", [""])[0]
        return datetime.fromtimestamp(int(value), UTC)
    except (ValueError, OverflowError, OSError):
        return None


def link_state(url: str | None) -> dict[str, Any]:
    """What the admin page shows about the saved link; never the signature itself."""
    expires = expires_at(url)
    safe = None
    if url:
        p = urlsplit(url)
        safe = f"{p.scheme}://{p.netloc}{p.path}"
    return {
        "url": safe,
        "expires_at": expires.isoformat() if expires else None,
        "days_left": (expires - datetime.now(UTC)).days if expires else None,
        "expired": bool(expires and expires <= datetime.now(UTC)),
    }


def download(url: str) -> list[dict[str, Any]]:
    try:
        r = get_public(url, timeout=(10, 180))
    except UnsafeURLError as e:
        raise FeedError(str(e)) from e
    except requests.RequestException as e:
        raise FeedError(f"Couldn't reach the feed ({e.__class__.__name__})") from e
    if r.status_code in (401, 403):
        raise FeedError("The feed refused the link: it has expired or is wrong. Paste a new one in Admin → Settings.")
    if not r.ok:
        raise FeedError(f"The feed answered {r.status_code}")
    try:
        jobs = r.json()
    except ValueError as e:
        raise FeedError("The feed isn't JSON") from e
    if not isinstance(jobs, list):
        raise FeedError("The feed isn't a list of postings")
    return jobs


# ---- telling the admin ----------------------------------------------------------------------------------------


def alert_admin(subject: str, text: str) -> None:
    """Email the daily-report addresses, at most once a day. Never raises: the run's own result matters more."""
    today = datetime.now(UTC).date().isoformat()
    if get_setting(ALERT_KEY) == today:
        return
    recipients = get_recipients()
    if not recipients or not email_ready():
        log.warning("Admin not emailed (%s): no addresses in Admin → Settings, or email isn't set up", subject)
        return
    try:
        send_email(recipients, subject, text)
    except EmailError as e:
        log.error("Admin not emailed (%s): %s", subject, e)
        return
    set_setting(ALERT_KEY, today, by="daily-feed")


def _admin_link() -> str:
    return f"{get_settings().site_url.rstrip('/')}/admin#settings"


def warn_if_near_expiry(url: str) -> None:
    left = link_state(url)["days_left"]
    if left is not None and 0 <= left <= WARN_DAYS:
        alert_admin(
            f"MinistryHub jobs feed link expires in {left} day{'' if left == 1 else 's'}",
            f"The signed link the daily jobs feed uses stops working in {left} day(s).\n"
            f"Get a new link from the feed provider and paste it in Admin → Settings: {_admin_link()}",
        )


# ---- one run ---------------------------------------------------------------------------------------------------


def _url(job: dict[str, Any]) -> str:
    return (job.get("post_url") or "").strip().lower()  # the whole URL: many job boards differ only in the query


def new_postings(jobs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """The feed's postings that are neither in the database nor rejected before (same post_uuid, or the same job URL
    re-posted under a new one), each once, in feed order; and how many were skipped as rejected."""
    with get_conn() as conn:
        known = {r[0] for r in conn.execute("SELECT post_uuid FROM public.postings").fetchall()}
        rejected = conn.execute("SELECT post_uuid, post_url FROM public.rejected_postings").fetchall()
    rejected_ids, rejected_urls = {r[0] for r in rejected}, {r[1] for r in rejected if r[1]}
    fresh: dict[str, dict[str, Any]] = {}
    skipped = set()
    for job in jobs:
        uuid = job.get("post_uuid")
        if not uuid or uuid in known:
            continue
        if uuid in rejected_ids or _url(job) in rejected_urls:
            skipped.add(uuid)
            continue
        fresh.setdefault(uuid, job)
    return list(fresh.values()), len(skipped)


def load_new(jobs: list[dict[str, Any]], pull_date: date) -> int:
    loaded = 0
    with get_conn() as conn:
        for i, job in enumerate(jobs, 1):
            try:
                with conn.transaction():  # a posting and its company land together or not at all
                    load_posting(conn, job, pull_date.isoformat())
                loaded += 1
            except Exception:
                log.exception("Posting %s (%s) not loaded", job.get("post_uuid"), job.get("job_name"))
            if i % 50 == 0 or i == len(jobs):
                note(f"Saved {i} of {len(jobs)} new postings", step="Saving new postings", new=loaded)
    return loaded


def pay_stated(pay: tuple[float, float, str], text: str) -> bool:
    """The posting itself shows the AI's figure, or its monthly / bi-weekly / weekly form: read, not guessed."""
    return any(found_on_page(v / k, text) for v in set(pay[:2]) for k in (1, 12, 26, 52))


TO_REVIEW = "SELECT post_uuid FROM public.postings WHERE scope_checked_at IS NULL"

# Pay is saved only when the feed itself gave none.
SAVE_PAY = """UPDATE public.postings
    SET salary_min = %s, salary_max = %s, salary_period = %s, salary_source = 'ai'
    WHERE post_uuid = %s AND salary_min IS NULL"""


def ask_review(client: Any, job: dict[str, Any]) -> PostingReview:
    """One AI call: is this feed posting in scope, what kind of employer, and what pay does it state."""
    model = get_settings().openai_model
    page = FENCE_RE.sub(" ", page_text(job.get("post_html") or "") or "")[:MAX_POST_CHARS]
    url = job.get("post_url") or ""
    ensure_budget()
    response = client.responses.parse(
        model=model,
        instructions=REVIEW_INSTRUCTIONS,
        input=f"Employer, as the feed lists it: {job.get('company_name')}\nTitle: {job.get('job_name')}\nURL: {url}\n\n"
        f"<untrusted_page>\n{page}\n</untrusted_page>",
        text_format=PostingReview,
    )
    record(response, purpose="posting_review", url=url, model=model, admin_email=None)
    if response.output_parsed is None:  # a refusal or an empty answer: count it as a failed call, retried next run
        raise ValueError("The AI gave no review")
    return response.output_parsed


AI_WORKERS = 4  # AI calls at once: each mostly waits on OpenAI, so 4 at a time makes a run about 4x shorter


def ai_map(fn: Callable[[Any], Any], items: list[Any]) -> Iterator[tuple[Any, str | None]]:
    """(fn(item), None) or (None, error) for each item, in order, AI_WORKERS at a time. Every call runs in a copy of
    this context, so the AI usage it records keeps the run's ID."""
    context = contextvars.copy_context()

    def call(item: Any) -> tuple[Any, str | None]:
        try:
            return context.copy().run(fn, item), None
        except Exception as e:
            return None, f"{e.__class__.__name__}: {e}"[:300]

    with ThreadPoolExecutor(AI_WORKERS) as pool:
        yield from pool.map(call, items)


def review_postings(client: Any, jobs: list[dict[str, Any]], limit: int) -> dict[str, int]:
    """Postings nobody has judged yet (new ones, and any left over): the AI reads each posting's text, decides whether
    the employer is in scope (SCOPE_RULES), what kind of employer it is, and the pay it states. Returns counts."""
    counts = {"reviewed": 0, "excluded": 0, "pay": 0}
    with get_conn() as conn:
        pending = {r[0] for r in conn.execute(TO_REVIEW).fetchall()}
    todo = [
        j for j in {j["post_uuid"]: j for j in jobs if j.get("post_uuid") in pending}.values() if j.get("post_html")
    ]
    todo = todo[:limit]
    note(f"{len(pending)} postings not reviewed yet; reviewing {len(todo)} (scope and pay)", step="Reviewing postings")
    for n, (job, (review, failed)) in enumerate(
        zip(todo, ai_map(lambda j: ask_review(client, j), todo), strict=True), 1
    ):
        title = f"{job.get('job_name') or 'Posting'} at {job.get('company_name') or '?'}"
        if failed:  # network, quota, odd answer: stays unreviewed and is tried next run
            log.error("Review failed for %s: %s", job.get("post_url"), failed)
            note(f"Reviewed {n}/{len(todo)}: {title}: the AI call failed, will retry next run")
            continue
        reason = None if review.keep else (review.exclude_reason or "Out of scope")[:300]
        pay = complete_pay(review.salary_min, review.salary_max, review.salary_period)
        # Text in the posting that tries to instruct AI tools: keep the scope call, but don't trust the AI's pay.
        if pay and INJECTION_RE.search(job.get("post_html") or ""):
            log.warning("Posting %s contains AI-directed instructions; its AI pay is not saved", job.get("post_url"))
            pay = None
        if pay and not pay_stated(pay, (page_text(job.get("post_html") or "") or "").lower()):
            log.info("AI pay %s for %s isn't in the posting's text; not saved", pay, job.get("post_url"))
            pay = None
        saved_pay = False
        try:
            with get_conn() as conn, conn.transaction():
                judged = conn.execute(
                    "UPDATE public.postings SET scope_checked_at = now() "
                    "WHERE post_uuid = %s AND scope_checked_at IS NULL",
                    (job["post_uuid"],),
                ).rowcount
                if not judged:  # an admin decided while the AI was reading: the admin's call stands
                    continue
                # the AI types the organisation the job is for; the listed employer only when it is that organisation
                if job.get("company_uuid") and review.listed_employer_is_hiring:
                    conn.execute(
                        "UPDATE public.companies SET employer_type = %s "
                        "WHERE company_uuid = %s AND employer_type IS NULL",
                        (review.employer_type, job["company_uuid"]),
                    )
                # SAVE_PAY fills only a posting without pay: the feed's own stated pay always wins
                saved_pay = bool(pay and conn.execute(SAVE_PAY, (*pay, job["post_uuid"])).rowcount)
                if reason:  # out of the job tables, kept whole in rejected_postings
                    reject_posting(conn, job["post_uuid"], reason, "ai")
        except Exception:  # one bad row mustn't stop the run; it stays unreviewed and is tried next run
            log.exception("Saving the review of %s failed", job.get("post_url"))
            note(f"Reviewed {n}/{len(todo)}: {title}: saving failed, will retry next run")
            continue
        counts["pay"] += saved_pay
        counts["reviewed"] += 1
        counts["excluded"] += reason is not None
        found = f", pay ${pay[0]:,.0f}-${pay[1]:,.0f} per {pay[2]}" if saved_pay and pay else ""
        note(
            f"Reviewed {n}/{len(todo)}: {title}: " + (f"rejected ({reason})" if reason else "kept") + found,
            pay=counts["pay"], excluded=counts["excluded"],
        )  # fmt: skip
    return counts


CHURCHES_TO_ENRICH = """
    SELECT c.company_uuid, c.company_name, c.company_url, p.city, p.region
    FROM public.companies c
    LEFT JOIN LATERAL (SELECT city, region FROM public.postings WHERE company_uuid = c.company_uuid
                       ORDER BY first_indexed DESC NULLS LAST LIMIT 1) p ON true
    WHERE c.enriched_at IS NULL AND c.company_name IS NOT NULL AND c.employer_type = 'church'
    ORDER BY c.company_name LIMIT %s"""  # only churches: attendance means nothing for a school or a company
NOT_A_CONGREGATION = re.compile(r"\b(arch)?dioces[ae]\b|\bconference\b", re.I)


def look_up_church(
    client: Any, name: str, site: str | None, city: str | None, region: str | None
) -> tuple[JobExtraction, str | None, list[str]]:
    """Denomination and weekly attendance of one church, by web search (lookup_church). Shared with bizdev_enrich."""
    job = JobExtraction(
        page_type="job_posting", reason="church lookup", category="church", job_title=None, org_name=name,
        org_website=site,
        city=city, state=region, country=None, date_posted=None, salary_min=None, salary_max=None,
        salary_period=None, hours=None, remote=None, denomination=denomination_in(name), church_size=None,
    )  # fmt: skip
    if NOT_A_CONGREGATION.search(name):  # a diocese or denomination office has no weekly attendance to find
        return job, None, ["Not a single congregation: no attendance looked up."]
    return lookup_church(client, job, site or "")


def enrich_churches(client: Any, limit: int) -> int:
    """Denomination and attendance for churches nobody has looked up yet. Returns how many were stamped."""
    with get_conn() as conn:
        rows = conn.execute(CHURCHES_TO_ENRICH, (limit,)).fetchall()
    model, done = get_settings().openai_model, 0
    note(f"Looking up {len(rows)} churches (denomination and weekly attendance)", step="Looking up churches")

    for n, (row, (result, failed)) in enumerate(
        zip(rows, ai_map(lambda r: look_up_church(client, *r[1:]), rows), strict=True), 1
    ):
        uuid, name = row[0], row[1]
        job, source, notes = result or (None, None, [])
        if failed or (notes and notes[0].startswith(LOOKUP_FAILED)):
            note(f"Church {n}/{len(rows)}: {name}: the search failed, will retry next run")
            continue  # the search itself broke (network, quota): leave it for the next run
        job, _ = validate(job)
        try:
            with get_conn() as conn:
                conn.execute(
                    """UPDATE public.companies SET denomination = coalesce(%s, denomination), church_size = %s,
                           church_size_source = %s,
                           church_size_url = %s, enriched_at = now(), enrichment_model = %s WHERE company_uuid = %s""",
                    (
                        job.denomination,
                        job.church_size,
                        "inferred" if job.church_size and source else None,
                        source if job.church_size else None,
                        model,
                        uuid,
                    ),
                )
        except Exception:  # one bad row mustn't stop the run; the church is looked up again next run
            log.exception("Saving the church lookup for %s failed", name)
            continue
        done += 1
        found = f"{job.church_size:,} weekly" if job.church_size else "attendance not found online"
        note(f"Church {n}/{len(rows)}: {name}: {job.denomination or 'denomination unknown'}, {found}", church=done)
    return done


def run(*, run_id: str, dry_run: bool = False) -> dict[str, Any]:
    """Download, add the new postings, enrich them. Returns the status that Admin → Settings shows."""
    status: dict[str, Any] = {
        "at": datetime.now(UTC).isoformat(), "ok": False, "message": "", "new": 0, "church": 0, "pay": 0,
        "reviewed": 0, "excluded": 0, "run_id": run_id,
    }  # fmt: skip
    url = feed_url()
    if not url:
        status["message"] = "No feed link yet: paste one in Admin → Settings."
        return status
    state = link_state(url)
    if state["expired"]:
        status["message"] = "The feed link has expired: paste a new one in Admin → Settings."
        alert_admin(
            "MinistryHub jobs feed link has expired",
            f"The daily jobs feed can't be downloaded because its signed link expired.\n"
            f"Get a new link from the feed provider and paste it in Admin → Settings: {_admin_link()}",
        )
        return status
    warn_if_near_expiry(url)
    live.clear()
    live.update(
        step="Downloading the feed", new=0, pay=0, church=0, excluded=0, cost=0.0, calls=0, lines=[], run_id=run_id
    )
    note("Downloading the feed (about 18 MB; held in memory, never saved as a file)")
    try:
        jobs = download(url)
    except FeedError as e:
        status["message"] = str(e)
        if "refused" in str(e):
            alert_admin(
                "MinistryHub jobs feed link was refused",
                f"{e}\nPaste a new link in Admin → Settings: {_admin_link()}",
            )
        return status
    fresh, skipped = new_postings(jobs)
    status.update(new=len(fresh), skipped_rejected=skipped)
    note(
        f"Downloaded {len(jobs)} postings; {len(fresh)} are not in the database yet; "
        f"{skipped} skipped as rejected before",
        step="Comparing with the database",
    )
    if dry_run:
        status.update(ok=True, message=f"Dry run: {len(jobs)} postings in the feed, {len(fresh)} new.")
        return status
    today = datetime.now(UTC).date()
    loaded = load_new(fresh, today)
    status["new"] = loaded
    settings = get_settings()
    if settings.openai_api_key and budget()["reached"]:
        b = budget()
        ai = f" The monthly AI limit (${b['limit_usd']:.2f}) is reached, so nothing was enriched."
        alert_admin(
            "MinistryHub monthly AI limit reached", f"{ai.strip()} Raise it in Admin → AI costs: {_admin_link()}"
        )
    elif settings.openai_api_key:
        client = OpenAI(api_key=settings.openai_api_key)
        status.update(review_postings(client, jobs, settings.enrich_max_per_run))
        status["church"] = enrich_churches(client, settings.enrich_max_per_run)
        ai = ""
    else:
        ai = " OPENAI_API_KEY isn't set, so nothing was enriched."
    status["cost_usd"], status["calls"] = run_cost(run_id)
    note(f"Done. This run's {status['calls']} AI calls cost about ${status['cost_usd']:.4f}")
    status.update(
        ok=True,
        message=f"{len(jobs)} postings in the feed, {loaded} new ({skipped} skipped as rejected before); "
        f"{status['reviewed']} reviewed ({status['excluded']} rejected), pay found for {status['pay']}, "
        f"{status['church']} churches looked up.{ai}",
    )
    return status


def run_and_record(*, force: bool = False, dry_run: bool = False) -> int:
    """Run once and save the status. 0 = fine (or nothing due), 1 = it failed. Without force, once a day."""
    today = datetime.now(UTC).date().isoformat()
    if not force and not dry_run and get_setting(DONE_KEY) == today:
        log.debug("The feed was already handled today")
        return 0
    if not _running.acquire(blocking=False):
        log.info("A feed run is already in progress")
        return 0
    try:
        run_id = f"feed-{datetime.now(UTC):%Y%m%d-%H%M%S}"
        token = current_run.set(run_id)  # every AI call made below is stored with this ID
        try:
            status = run(run_id=run_id, dry_run=dry_run)
        except Exception as e:  # recorded as today's run: the timer must not redo (and re-pay) it every 15 minutes
            log.exception("Daily feed run failed")
            status = {"at": datetime.now(UTC).isoformat(), "ok": False, "run_id": run_id,
                      "message": f"The run stopped on an error ({e.__class__.__name__}); it runs again tomorrow, "
                                 "or use Run now."}  # fmt: skip
            note(status["message"])
        finally:
            current_run.reset(token)
        log.log(logging.INFO if status["ok"] else logging.ERROR, "Daily feed: %s", status["message"])
        if not dry_run:
            set_setting(STATUS_KEY, status, by="daily-feed")
            set_setting(DONE_KEY, today, by="daily-feed")  # a failure waits for tomorrow, or for a new link
        return 0 if status["ok"] else 1
    finally:
        _running.release()


def is_running() -> bool:
    return _running.locked()


def run_if_due() -> int:
    if datetime.now(UTC).hour < get_settings().feed_hour_utc:
        return 0
    return run_and_record()


# ---- CLI and the API's own timer -------------------------------------------------------------------------------


def register(commands: argparse._SubParsersAction) -> None:
    parser = commands.add_parser("daily-feed", help="download the jobs feed and add the new postings")
    parser.add_argument("--force", action="store_true", help="run now, even if it already ran today")
    parser.add_argument("--dry-run", action="store_true", help="download and count; change nothing")
    parser.set_defaults(handler=_run)


def _run(args: argparse.Namespace) -> int:
    script_log("daily_feed")
    if args.dry_run or args.force:
        return run_and_record(force=args.force, dry_run=args.dry_run)
    return run_if_due()


def start_scheduler() -> threading.Event:
    """Check every CHECK_EVERY seconds, inside the API process, whether today's feed run is due. Set the returned
    event to stop. shortcut: one timer per server process; with several instances two could run at the same moment,
    move to a cron job before scaling out."""
    stop = threading.Event()

    def loop() -> None:
        while True:  # check at once: a free Render service woken by a visit may sleep again within 15 minutes
            try:
                run_if_due()
            except Exception:  # a database hiccup mustn't end the timer for good
                log.exception("Daily feed check failed")
            if stop.wait(CHECK_EVERY):
                return

    threading.Thread(target=loop, name="daily-feed", daemon=True).start()
    log.info("Daily feed: runs once a day after %02d:00 UTC", get_settings().feed_hour_utc)
    return stop


def forget_today() -> None:
    """After a new link is saved: let the timer try again today."""
    delete_setting(DONE_KEY)
