"""classify-roles: a one-off catch-up. The daily review now asks the AI for each new posting's role (it reads the whole
text, not only the title), but postings reviewed before that change have none. This asks for theirs.

Only postings in today's feed download can be done: the posting text is never stored (DATA_INVENTORY.md). Postings
that left the feed keep the role their title gives. Run --estimate first: it prints how many postings and the
estimated cost, and calls nothing.

  python -m app.cli classify-roles --estimate     # count and price; no AI calls
  python -m app.cli classify-roles [--limit N]    # ask the AI, save each answer in postings.ai_role
"""

import argparse
import logging
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from openai import OpenAI

from app.ai_usage.service import MODEL, PROFILES, budget, current_run, estimate_cost
from app.core.config import get_settings
from app.core.db import get_conn
from app.core.logs import script_log
from app.extraction.prompts import ROLE_INSTRUCTIONS
from app.extraction.schemas import RoleReview
from app.ingestion.daily_feed import FeedError, ai_map, ask_about_posting, download, feed_url, log_role, run_cost
from app.jobs.roles import bucket_role, pick_role

log = logging.getLogger("classify_roles")

TO_CLASSIFY = "SELECT post_uuid FROM public.postings WHERE ai_role IS NULL AND scope_checked_at IS NOT NULL"


def postings_to_classify(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The feed's postings that are reviewed, have no AI role yet and have text to read; each once."""
    with get_conn() as conn:
        pending = {r[0] for r in conn.execute(TO_CLASSIFY).fetchall()}
    unique = {j["post_uuid"]: j for j in jobs if j.get("post_uuid") in pending}
    return [j for j in unique.values() if j.get("post_html")]


def ask_role(client: Any, job: dict[str, Any]) -> str:
    return ask_about_posting(client, job, ROLE_INSTRUCTIONS, RoleReview, "role_review").role


def run(*, estimate: bool, limit: int | None) -> int:
    url = feed_url()
    if not url:
        log.error("No feed link: paste one in Admin → Settings")
        return 1
    try:
        jobs = download(url)
    except FeedError as e:
        log.error("Couldn't download the feed: %s", e)
        return 1
    todo = postings_to_classify(jobs)[:limit]
    model = MODEL
    each = estimate_cost(model, *PROFILES["role_review"])
    cost = f"about ${each * len(todo):.2f}" if each is not None else f"unknown (no price for {model})"
    log.info("%d postings in the feed; %d need a role. Estimated cost on %s: %s", len(jobs), len(todo), model, cost)
    if estimate or not todo:
        return 0
    if not get_settings().openai_api_key:
        log.error("OPENAI_API_KEY isn't set")
        return 1
    if budget()["reached"]:
        log.error("The monthly AI limit is reached; raise it in Admin → AI costs")
        return 1

    run_id = f"roles-{datetime.now(UTC):%Y%m%d-%H%M%S}"
    token = current_run.set(run_id)  # every AI call below is stored with this ID (Admin → AI costs)
    client = OpenAI(api_key=get_settings().openai_api_key)
    saved, failed, changed = 0, 0, Counter()
    try:
        answers = ai_map(lambda j: ask_role(client, j), todo)
        for n, (job, (role, error)) in enumerate(zip(todo, answers, strict=True), 1):
            if error:  # network, quota, the monthly limit, a refusal: left for another run
                failed += 1
                log.error("%d/%d %s: the AI call failed: %s", n, len(todo), job["post_uuid"], error)
                continue
            with get_conn() as conn:
                conn.execute(
                    "UPDATE public.postings SET ai_role = %s WHERE post_uuid = %s AND ai_role IS NULL",
                    (role, job["post_uuid"]),
                )
            saved += 1
            log_role(job["post_uuid"], job.get("job_name"), role)
            before, after = bucket_role(job.get("job_name")), pick_role(job.get("job_name"), role)
            if before != after:
                changed[f"{before} -> {after}"] += 1
    finally:
        current_run.reset(token)
    spent, calls = run_cost(run_id)
    log.info(
        "Done: %d roles saved, %d failed, %d postings moved to another group; %d AI calls cost about $%.4f (run %s)",
        saved, failed, sum(changed.values()), calls, spent, run_id,
    )  # fmt: skip
    for move, count in changed.most_common():
        log.info("  %4d  %s", count, move)
    return 1 if failed and not saved else 0


def register(commands: argparse._SubParsersAction) -> None:
    parser = commands.add_parser("classify-roles", help="one-off: ask the AI for the role of feed postings without one")
    parser.add_argument("--estimate", action="store_true", help="count and price only; no AI calls")
    parser.add_argument("--limit", type=int, help="at most this many postings")
    parser.set_defaults(handler=_run)


def _run(args: argparse.Namespace) -> int:
    script_log("classify_roles")
    return run(estimate=args.estimate, limit=args.limit)
