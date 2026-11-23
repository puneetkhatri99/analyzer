"""The public report: one blended dataset, pay ranges with a confidence label, and automatic widening
(state -> region -> nationwide) so every search gets an answer.

Nothing here returns counts, employer names, sources or links: the public must not see how the data is gathered.
"""

import logging
from collections import Counter
from collections.abc import Callable, Iterable
from statistics import median
from typing import Any

from app.jobs.repository import HOURS_PER_YEAR, load_jobs
from app.jobs.roles import HIDDEN_ROLES, OLD_ROLE_LABELS, ROLE_LABELS
from app.report.groups import FAMILIES, OTHER_ROLES, as_family, role_group
from app.report.merging import (
    LABELS,
    LOOSEN_ORDER,
    Level,
    group_levels,
    join_names,
    location_levels,
    loosen,
    merge_thin,
    size_levels,
)
from app.report.reposts import merge_reposts
from app.shared.geo import REGION_OF, STATES, state_name
from app.shared.stats import quantile

log = logging.getLogger("report")

Job = dict[str, Any]

MIN_PAID = 5  # below this many jobs with pay, a figure isn't shown and the search widens
CONFIDENCE = [(30, "Strong"), (10, "Moderate"), (MIN_PAID, "Limited")]  # as set by the project owner
MIN_SAMPLE = 30  # churches needed before the landing attendance figure is shown

# Two bands, not four: only about 1 in 5 openings state a size, so four bands left each with too few pay figures.
SIZES = [
    ("Under 1,000", 0, 1000),
    ("1,000 or more", 1000, None),
]
OLD_SIZE_LABELS = {  # links and emails made when there were four bands
    "Under 250": "Under 1,000",
    "250 to 999": "Under 1,000",
    "1,000 to 4,999": "1,000 or more",
    "5,000 or more": "1,000 or more",
}
JOB_TYPES = {"full-time": "year", "part-time": "hour"}
ROLE_ORDER = [label for label in ROLE_LABELS if label not in HIDDEN_ROLES]
FILTER_KEYS = ("role", "state", "size", "denomination")


def _pay(d: Job, job_type: str) -> float | None:
    """The pay to benchmark: yearly for full-time jobs, hourly for part-time. None when it doesn't fit the type."""
    lo, hi, period = d["salary_min"], d["salary_max"], d["salary_period"]
    if lo is None or hi is None or lo <= 0 or hi <= 0:  # 0 or negative is a bad parse, not a salary
        return None
    mid = (lo + hi) / 2
    if job_type == "part-time":
        return mid if period == "hour" and d["hours"] in ("Part-Time", "Hourly") else None
    if d["hours"] == "Full-Time" or (d["hours"] is None and period == "year"):
        return mid * HOURS_PER_YEAR if period == "hour" else mid
    return None


# Employer names that mark a placeholder row, not a real job (lower-case). The client picked them from a search of
# the data; admin still lists these jobs.
PLACEHOLDER_EMPLOYERS = {"z. do not use"}


def hidden_employer(name: str | None) -> str | None:
    """Why a job's employer keeps it off the public report, or None."""
    if not (name or "").strip():
        return "no employer"
    return f"placeholder {name!r}" if name.strip().lower() in PLACEHOLDER_EMPLOYERS else None


def public_rows(hidden: Counter[str] | None = None) -> list[Job]:
    """Every US job row from every source, with the state normalised and hidden roles and placeholder employers
    removed; reposts not merged yet. Feed postings judged out of scope aren't in the job tables at all
    (rejected_postings); ones not reviewed yet are left out until the AI (or an admin) has judged them. `hidden`
    counts the jobs left out for their employer, by reason."""
    out = []
    for source in ("json", "churches", "nonprofits"):
        for d in load_jobs(source):
            if d["country"] not in ("US", "United States") or d["role"] in HIDDEN_ROLES or not d["reviewed"]:
                continue
            if reason := hidden_employer(d["company_name"]):
                if hidden is not None:
                    hidden[reason] += 1
                continue
            d["state"] = state_name(d["region"])
            out.append(d)
    return out


def blended_jobs() -> list[Job]:
    """Every opening as one list (brief P5): reposts and copies in several sources count once (brief D3)."""
    rows = public_rows()
    jobs = merge_reposts(rows)
    log.info("Report data: %d job rows, %d openings after merging reposts and duplicates", len(rows), len(jobs))
    return jobs


def _size_label(size: float | None) -> str | None:
    if size is None:
        return None
    return next((label for label, lo, hi in SIZES if size >= lo and (hi is None or size < hi)), None)


def _value(d: Job, kind: str) -> str | None:
    if kind == "size":
        return _size_label(d["church_size"])
    if kind == "denomination":  # the report works with denomination families (groups.py), not single denominations
        return as_family(d["denomination"]) if d["denomination"] else None
    return d[kind]


def _select(jobs: list[Job], levels: dict[str, Level], skip: Iterable[str] = ()) -> list[Job]:
    """The jobs that fit every filter at its current level (a filter in `skip`, or at 'any', lets everything by)."""
    checks = [(k, lv.allowed) for k, lv in levels.items() if k not in skip and lv.allowed is not None]
    return [d for d in jobs if all(_value(d, k) in allowed for k, allowed in checks)]


def _stats(jobs: list[Job], job_type: str) -> dict[str, Any] | None:
    pay = sorted(p for p in (_pay(d, job_type) for d in jobs) if p is not None)
    if len(pay) < MIN_PAID:
        return None
    # Rounded so a figure drawn from a handful of postings doesn't look exact: $500 a year, 50 cents an hour.
    step = 0.5 if job_type == "part-time" else 500
    q: Callable[[float], float] = lambda x: round(quantile(pay, x) / step) * step  # noqa: E731
    return {
        "typical": q(0.5),
        "low": q(0.25),
        "high": q(0.75),
        "confidence": next(label for n, label in CONFIDENCE if len(pay) >= n),
    }


_join = join_names


def _breakdown(
    jobs: list[Job],
    key: str,
    job_type: str,
    parent_of: Callable[[str], str],
    other: str,
    order: list[str] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Bar-chart rows [{name, typical, merged}] for each value of `key`. A value with too little pay is combined with
    similar ones (merging.merge_thin) instead of being left out. Fewer than two rows compare nothing: no rows."""
    groups: dict[str, list[Job]] = {}
    for d in jobs:
        if value := _value(d, key):
            groups.setdefault(value, []).append(d)
    rows = merge_thin(groups, lambda js: _stats(js, job_type), parent_of, other)
    if order:
        rows.sort(
            key=lambda r: min((order.index(m) for m in r["merged"] or [r["name"]] if m in order), default=len(order))
        )
    else:  # most data first, then cut, then highest pay first; no counts leave the server
        rows.sort(key=lambda r: -r["n"])
        rows = sorted(rows[:limit], key=lambda r: -r["typical"])
    rows = [{k: v for k, v in r.items() if k != "n"} for r in rows]
    return rows if len(rows) >= 2 else []


def _size_range(bands: list[str]) -> str:
    """'250 to 4,999' for neighbouring bands; a single band keeps its name."""
    if len(bands) == 1:
        return bands[0]
    lo, hi = next(b[1] for b in SIZES if b[0] == bands[0]), next(b[2] for b in SIZES if b[0] == bands[-1])
    if lo == 0 and hi is None:
        return "All church sizes"
    return f"Under {hi:,}" if lo == 0 else f"{lo:,} or more" if hi is None else f"{lo:,} to {hi - 1:,}"


def _size_breakdown(jobs: list[Job], job_type: str) -> list[dict[str, Any]]:
    """Pay by church size; a band with too little pay is combined with its neighbour until every row has enough."""
    segments = [([label], [d for d in jobs if _size_label(d["church_size"]) == label]) for label, _, _ in SIZES]
    while len(segments) > 1:
        thin = next((i for i, (_, js) in enumerate(segments) if not _stats(js, job_type)), None)
        if thin is None:
            break
        near = min((j for j in (thin - 1, thin + 1) if 0 <= j < len(segments)), key=lambda j: len(segments[j][1]))
        a, b = sorted((thin, near))
        segments[a] = (segments[a][0] + segments[b][0], segments[a][1] + segments[b][1])
        del segments[b]
    rows = [
        {"name": _size_range(names), "typical": s["typical"], "merged": names if len(names) > 1 else []}
        for names, js in segments
        if (s := _stats(js, job_type))
    ]
    return rows if len(rows) >= 2 else []


def openings_label(n: int) -> str:
    """'4,000+': a rounded figure for the 'drawn from …' line (brief P7: no exact counts)."""
    step = 1000 if n >= 1000 else 100
    return f"{n // step * step:,}+" if n >= step else "hundreds of"


def typical_attendance(jobs: list[Job]) -> int | None:
    """Median stated attendance, one value per church (a church with many openings counts once), nonprofits left
    out. Sizes are the bottom of a band ("501 to 750" is 501), so the figure is rounded down to 50 ("500+")."""
    by_church = {}
    for d in jobs:
        if d["church_size"] and d.get("source") != "nonprofits" and d.get("company_name"):
            by_church.setdefault(d["company_name"].strip().lower(), d["church_size"])
    if len(by_church) < MIN_SAMPLE:
        return None
    return int(median(by_church.values())) // 50 * 50


def current_roles(roles: list[str]) -> list[str]:
    """Role names from before the role list changed (in shared links and emailed reports) mapped to today's."""
    return list(dict.fromkeys(OLD_ROLE_LABELS.get(r, r) for r in roles))


def current_sizes(sizes: list[str]) -> list[str]:
    """Church sizes from before the report had two bands (shared links, emailed reports) mapped to today's."""
    return list(dict.fromkeys(OLD_SIZE_LABELS.get(x, x) for x in sizes))


def current_denominations(names: list[str]) -> list[str]:
    """Single denominations from before the report offered families mapped to their family."""
    return list(dict.fromkeys(as_family(x) for x in names))


def _as_of(jobs: list[Job]) -> str | None:
    return max((d["pull_date"] for d in jobs if d["pull_date"]), default=None)


def build_report(filters: dict[str, Any], jobs: list[Job] | None = None) -> dict[str, Any]:
    """filters = {role, state, size, denomination: [values], type: 'full-time' | 'part-time'}.

    A search with too little pay is never answered with "not enough data": merging.loosen widens it one step at a time
    and `merged` says what was combined (location first, then church size, denomination and role last)."""
    jobs = blended_jobs() if jobs is None else jobs
    job_type = filters["type"] if filters.get("type") in JOB_TYPES else "full-time"
    f = {k: [v for v in (filters.get(k) or []) if v] for k in FILTER_KEYS}
    f["state"] = [s for s in (state_name(x) for x in f["state"]) if s]
    f["role"] = current_roles(f["role"])
    f["size"] = current_sizes(f["size"])
    f["denomination"] = current_denominations(f["denomination"])
    # Every band (or every family) ticked is no filter: it would still drop the openings that don't state it.
    if {label for label, _, _ in SIZES} <= set(f["size"]):
        f["size"] = []
    if set(FAMILIES) <= set(f["denomination"]):
        f["denomination"] = []

    ladder = {
        "state": location_levels(f["state"]),
        "size": size_levels(f["size"], [label for label, _, _ in SIZES]),
        "denomination": group_levels(f["denomination"], as_family, FAMILIES, "denominations"),
        "role": group_levels(f["role"], role_group, {d["role"] for d in jobs}, "roles"),
    }
    now = loosen(ladder, lambda levels: _stats(_select(jobs, levels), job_type) is not None)
    pay = _stats(_select(jobs, now), job_type)
    place = now["state"]
    merged = [
        {"kind": k, "label": LABELS[k], "chosen": _join(f[k]), "shown": now[k].shown, "text": now[k].text}
        for k in LOOSEN_ORDER
        if now[k].text
    ]
    note = " ".join(m["text"] for m in merged) or None
    if not pay:  # fewer than MIN_PAID jobs with pay in the whole data
        note = "Too few current openings list pay for this search to benchmark yet. Try another role or job type."

    # The chosen states against nationwide, all roles of this job type; the nearby states or region when the states
    # alone have too little pay. Nothing when the figures are already nationwide.
    vs_national = None
    national = _stats(jobs, job_type)
    for level in ladder["state"][:-1] if f["state"] else []:  # every level but nationwide
        local = _stats([d for d in jobs if d["state"] in level.allowed], job_type)
        if local and national and national["typical"]:
            diff = round((local["typical"] - national["typical"]) / national["typical"] * 100)
            vs_national = {
                "area": level.area,
                "area_typical": local["typical"],
                "national_typical": national["typical"],
                "percent": diff,
            }
            break

    share = None
    if f["role"]:
        share = round(sum(1 for d in jobs if d["role"] in f["role"]) / max(len(jobs), 1) * 100)

    searched_role = _join(f["role"] or ["Ministry"])
    return {
        "title": {"role": searched_role, "area": _join(f["state"]) if f["state"] else "the United States"},
        # What the figures really cover; the page and print headline use it, so a merged search never claims
        # "pay in Wyoming" over nationwide figures. `title` stays what was searched (lead tracking, the email subject).
        "covers": {
            "role": now["role"].shown or searched_role if now["role"].allowed is not None else "Ministry",
            "area": {
                "state": place.area,
                "nearby": place.area,
                "region": f"the {place.area}",
                "national": "the United States",
            }[place.scope],
        },
        "filters": {**f, "type": job_type},
        "scope": place.scope,
        "area_name": place.area,
        "merged": merged,
        "note": note,
        "unit": JOB_TYPES[job_type],
        "pay": pay,
        "vs_national": vs_national,
        "share_percent": share,
        "by_role": _breakdown(
            _select(jobs, now, skip=("role",)), "role", job_type, role_group, OTHER_ROLES, order=ROLE_ORDER
        ),
        "by_size": _size_breakdown(_select(jobs, now, skip=("size",)), job_type),
        "by_state": _breakdown(
            _select(jobs, now, skip=("state",)),
            "state",
            job_type,
            lambda s: REGION_OF.get(s, "Other states"),
            "Other states",
            limit=8,
        ),
        "by_denomination": _breakdown(
            _select(jobs, now, skip=("denomination",)),
            "denomination",
            job_type,
            lambda family: family,  # each family stands alone; thin ones are combined into one row
            "Smaller denominations",
            limit=8,
        ),
        "openings_label": openings_label(len(jobs)),
        "as_of": _as_of(jobs),
    }


def report_options(jobs: list[Job] | None = None) -> dict[str, Any]:
    """Choices for the landing form and report filters, plus the landing page's headline stats. No counts (P7)."""
    jobs = blended_jobs() if jobs is None else jobs
    present = {d["role"] for d in jobs}
    families = {as_family(d["denomination"]) for d in jobs if d["denomination"]}
    national = _stats(jobs, "full-time")
    return {
        "roles": [r for r in ROLE_ORDER if r in present],
        "states": sorted(STATES.values()),
        "sizes": [label for label, _, _ in SIZES],
        "denominations": [f for f in FAMILIES if f in families],
        "job_types": [{"key": "full-time", "label": "Full-time"}, {"key": "part-time", "label": "Part-time (hourly)"}],
        "landing": {
            "typical": national and national["typical"],
            "low": national and national["low"],
            "high": national and national["high"],
            "attendance": typical_attendance(jobs),
            "openings_label": openings_label(len(jobs)),
            "as_of": _as_of(jobs),
        },
    }
