"""check-duplicates: what the public report's data looks like today, written to the log. Runs at the end of every
daily feed run, and on demand:

  python -m app.cli check-duplicates

Logs every group of job rows merged into one opening (which rows, why, which copy was kept), any merged group whose
cities differ (worth a look), how many openings each role has, and every stored denomination name shown under
another name, and how many jobs a placeholder or missing employer keeps off the report. Employer names and titles
are public job data; no contact details are read.
"""

import argparse
import logging
from collections import Counter
from typing import Any

from app.core.db import get_conn
from app.core.logs import script_log
from app.job_pages.parser import denomination_in
from app.report.reposts import group_openings, one_row
from app.report.service import public_rows

log = logging.getLogger("data_check")


def _describe(d: dict[str, Any]) -> str:
    when = str(d.get("first_indexed") or d.get("added_at") or "?")[:10]
    place = f"{d.get('city')}, {d.get('state')}, {when}"
    return f"{d['source']}:{d['post_uuid']} {d.get('job_name')!r} at {d.get('company_name')!r} ({place})"


def log_data_check() -> dict[str, int]:
    """Log the merged groups and role counts; returns the totals."""
    hidden: Counter[str] = Counter()
    rows = public_rows(hidden)
    log.info(
        "Hidden for their employer: %d jobs%s", sum(hidden.values()),
        "".join(f"; {n} with {reason}" for reason, n in hidden.most_common()),
    )  # fmt: skip
    groups = group_openings(rows)
    merged = [(copies, reasons) for copies, reasons in groups if len(copies) > 1]
    log.info(
        "Duplicates: %d job rows are %d openings; %d groups of 2 or more copies were merged",
        len(rows), len(groups), len(merged),
    )  # fmt: skip
    mixed_cities = 0
    for copies, reasons in sorted(merged, key=lambda g: -len(g[0])):
        kept = one_row(copies)
        log.info(
            "Merged %d copies (%s); kept %s:%s\n    %s",
            len(copies), "; ".join(sorted(reasons)), kept["source"], kept["post_uuid"],
            "\n    ".join(map(_describe, copies)),
        )  # fmt: skip
        cities = {(d.get("city") or "").strip().lower() for d in copies} - {""}
        if len(cities) > 1:
            mixed_cities += 1
            log.warning("Merged group with different cities %s: %s", sorted(cities), _describe(kept))
    roles = Counter(one_row(copies)["role"] for copies, _ in groups)
    log.info("Openings per role: %s", ", ".join(f"{role} {n}" for role, n in roles.most_common()))
    renamed = log_denomination_names()
    return {
        "rows": len(rows), "openings": len(groups), "merged_groups": len(merged), "mixed_cities": mixed_cities,
        "renamed_denominations": renamed,
    }  # fmt: skip


STORED_DENOMINATIONS = """
    SELECT denomination, count(*) FROM (
        SELECT c.denomination FROM public.postings p JOIN public.companies c USING (company_uuid)
        UNION ALL SELECT denomination FROM public.church_jobs
        UNION ALL SELECT denomination FROM public.nonprofit_jobs) d
    WHERE denomination IS NOT NULL GROUP BY denomination ORDER BY count(*) DESC"""


def log_denomination_names() -> int:
    """Every stored denomination that the job lists show under another name (job_pages.parser.DENOMINATIONS)."""
    with get_conn() as conn:
        stored = conn.execute(STORED_DENOMINATIONS).fetchall()
    renamed = [(raw, n, denomination_in(raw)) for raw, n in stored if denomination_in(raw) not in (None, raw)]
    log.info("Denominations: %d stored names, %d shown under another name", len(stored), len(renamed))
    for raw, n, shown in renamed:
        log.info("  %r (%d jobs) is shown as %r", raw, n, shown)
    return len(renamed)


def register(commands: argparse._SubParsersAction) -> None:
    parser = commands.add_parser("check-duplicates", help="log every merged duplicate group and the role counts")
    parser.set_defaults(handler=_run)


def _run(args: argparse.Namespace) -> int:
    script_log("check_duplicates")
    log_data_check()
    return 0
