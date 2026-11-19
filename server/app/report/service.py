"""The public report: one blended dataset, pay ranges with a confidence label, and automatic widening
(state -> region -> nationwide) so every search gets an answer.

Nothing here returns counts, employer names, sources or links: the public must not see how the data is gathered.
"""

from collections.abc import Callable, Iterable
from statistics import median
from typing import Any

from app.jobs.repository import HOURS_PER_YEAR, load_jobs
from app.jobs.roles import ROLE_RULES
from app.shared.geo import REGION_OF, STATES, state_name
from app.shared.stats import quantile

Job = dict[str, Any]

MIN_PAID = 5  # below this many jobs with pay, a figure isn't shown and the search widens
CONFIDENCE = [(30, "Strong"), (10, "Moderate"), (MIN_PAID, "Limited")]  # proposal; tune once the data grows
MIN_SAMPLE = 30  # churches needed before the landing attendance figure is shown
HIDDEN_ROLES = {"Healthcare"}  # the brief removes medical jobs from the public tool

SIZES = [
    ("Under 250", 0, 250),
    ("250 to 999", 250, 1000),
    ("1,000 to 4,999", 1000, 5000),
    ("5,000 or more", 5000, None),
]
JOB_TYPES = {"full-time": "year", "part-time": "hour"}
ROLE_ORDER = [label for _, label in ROLE_RULES if label not in HIDDEN_ROLES] + ["Other"]
FILTER_KEYS = ("role", "state", "size", "denomination")


def _pay(d: Job, job_type: str) -> float | None:
    """The pay to benchmark: yearly for full-time jobs, hourly for part-time. None when it doesn't fit the type."""
    lo, hi, period = d["salary_min"], d["salary_max"], d["salary_period"]
    if lo is None or hi is None:
        return None
    mid = (lo + hi) / 2
    if job_type == "part-time":
        return mid if period == "hour" and d["hours"] in ("Part-Time", "Hourly") else None
    if d["hours"] == "Full-Time" or (d["hours"] is None and period == "year"):
        return mid * HOURS_PER_YEAR if period == "hour" else mid
    return None


def blended_jobs() -> list[Job]:
    """Every US job from every source as one list (brief P5), with the state normalised and medical roles removed.
    Feed postings judged out of scope aren't in the job tables at all (rejected_postings); ones not reviewed yet are
    left out until the AI (or an admin) has judged them."""
    out = []
    for source in ("json", "churches", "nonprofits"):
        for d in load_jobs(source):
            if d["country"] not in ("US", "United States") or d["role"] in HIDDEN_ROLES or not d["reviewed"]:
                continue
            d["state"] = state_name(d["region"])
            out.append(d)
    return out


def _size_label(size: float | None) -> str | None:
    if size is None:
        return None
    return next((label for label, lo, hi in SIZES if size >= lo and (hi is None or size < hi)), None)


def _matches(d: Job, f: dict[str, list[str]], skip: Iterable[str] = ()) -> bool:
    values = {
        "role": d["role"],
        "state": d["state"],
        "size": _size_label(d["church_size"]),
        "denomination": d["denomination"],
    }
    return all(not f[key] or key in skip or value in f[key] for key, value in values.items())


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


def _rows(jobs: list[Job], key: str, job_type: str, order: list[str] | None = None, limit: int | None = None) -> list:
    """[{name, typical}] per value of `key`, only values with enough pay to benchmark."""
    groups: dict[str, list[Job]] = {}
    for d in jobs:
        if d.get(key):
            groups.setdefault(d[key], []).append(d)
    rows = [{"name": name, "typical": s["typical"]} for name, rows in groups.items() if (s := _stats(rows, job_type))]
    if order:
        rows.sort(key=lambda r: order.index(r["name"]) if r["name"] in order else len(order))
    else:  # most data first, then cut, then highest pay first; no counts leave the server
        rows.sort(key=lambda r: -len(groups[r["name"]]))
        rows = sorted(rows[:limit], key=lambda r: -r["typical"])
    return rows


def _join(items: Iterable[str]) -> str:
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def openings_label(n: int) -> str:
    """'4,000+': a rounded figure for the 'drawn from …' line (brief P7: no exact counts)."""
    step = 1000 if n >= 1000 else 100
    return f"{n // step * step:,}+" if n >= step else "hundreds of"


def distinct_openings(jobs: list[Job]) -> int:
    """How many openings the figures are drawn from: a repost (same employer, title and state) counts once.
    shortcut: reposts matched on exact text only; switch to the openings table once reposts are linked (brief D3)."""
    seen = set()
    for d in jobs:
        employer = (d.get("company_name") or "").strip().lower()
        title = (d.get("job_name") or "").strip().lower()
        seen.add((employer, title, d["state"]) if employer and title else id(d))  # no employer: can't spot a repost
    return len(seen)


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


def _as_of(jobs: list[Job]) -> str | None:
    return max((d["pull_date"] for d in jobs if d["pull_date"]), default=None)


def build_report(filters: dict[str, Any], jobs: list[Job] | None = None) -> dict[str, Any]:
    """filters = {role, state, size, denomination: [values], type: 'full-time' | 'part-time'}."""
    jobs = blended_jobs() if jobs is None else jobs
    job_type = filters["type"] if filters.get("type") in JOB_TYPES else "full-time"
    f = {k: [v for v in (filters.get(k) or []) if v] for k in FILTER_KEYS}
    f["state"] = [s for s in (state_name(x) for x in f["state"]) if s]

    # Widen until there's enough pay: the chosen states, then their regions, then nationwide.
    areas: list[tuple[str, str, set[str] | None]] = []
    if f["state"]:
        areas.append(("state", _join(f["state"]), set(f["state"])))
        regions = sorted({REGION_OF[s] for s in f["state"]})
        areas.append(("region", _join(regions), {s for s, r in REGION_OF.items() if r in regions}))
    areas.append(("national", "nationwide", None))

    base = [d for d in jobs if _matches(d, f, skip=("state",))]
    for scope, area_name, area_states in areas:  # noqa: B007 - the area where the loop stops is used below
        pay = _stats([d for d in base if area_states is None or d["state"] in area_states], job_type)
        if pay:
            break

    note = None
    if not pay:
        note = "Too few current openings list pay for this search to benchmark yet. Try another role or job type."
    elif scope != "state" and f["state"]:
        where = "national figures" if scope == "national" else f"{area_name} figures"
        note = (
            f"Showing {where}. {_join(f['state'])} data for this role is still limited, "
            "so we widened the search to give you a reliable range."
        )

    def in_area(skip: tuple[str, ...]) -> list[Job]:
        return [
            d
            for d in jobs
            if _matches(d, f, skip=("state", *skip)) and (area_states is None or d["state"] in area_states)
        ]

    # Area vs nationwide, all roles of this job type.
    vs_national = None
    if f["state"]:
        local = _stats([d for d in jobs if d["state"] in set(f["state"])], job_type)
        national = _stats(jobs, job_type)
        if local and national:
            diff = round((local["typical"] - national["typical"]) / national["typical"] * 100)
            vs_national = {
                "area": _join(f["state"]),
                "area_typical": local["typical"],
                "national_typical": national["typical"],
                "percent": diff,
            }

    share = None
    if f["role"]:
        share = round(sum(1 for d in jobs if d["role"] in f["role"]) / max(len(jobs), 1) * 100)

    by_size = []
    for label, _, _ in SIZES:
        s = _stats([d for d in in_area(("size",)) if _size_label(d["church_size"]) == label], job_type)
        by_size.append({"name": label, "typical": s["typical"] if s else None})

    return {
        "title": {
            "role": _join(f["role"] or ["Ministry"]),
            "area": _join(f["state"]) if f["state"] else "the United States",
        },
        "filters": {**f, "type": job_type},
        "scope": scope,
        "area_name": area_name,
        "note": note,
        "unit": JOB_TYPES[job_type],
        "pay": pay,
        "vs_national": vs_national,
        "share_percent": share,
        "by_role": _rows(in_area(("role",)), "role", job_type, order=ROLE_ORDER),
        "by_size": by_size,
        "by_state": _rows([d for d in jobs if _matches(d, f, skip=("state",))], "state", job_type, limit=8),
        "by_denomination": _rows(in_area(("denomination",)), "denomination", job_type, limit=6),
        "openings_label": openings_label(distinct_openings(jobs)),
        "as_of": _as_of(jobs),
    }


def report_options(jobs: list[Job] | None = None) -> dict[str, Any]:
    """Choices for the landing form and report filters, plus the landing page's headline stats. No counts (P7)."""
    jobs = blended_jobs() if jobs is None else jobs
    present = {d["role"] for d in jobs}
    denoms: dict[str, int] = {}
    for d in jobs:
        if d["denomination"]:
            denoms[d["denomination"]] = denoms.get(d["denomination"], 0) + 1
    national = _stats(jobs, "full-time")
    return {
        "roles": [r for r in ROLE_ORDER if r in present],
        "states": sorted(STATES.values()),
        "sizes": [label for label, _, _ in SIZES],
        "denominations": sorted(denoms, key=lambda k: -denoms[k]),
        "job_types": [{"key": "full-time", "label": "Full-time"}, {"key": "part-time", "label": "Part-time (hourly)"}],
        "landing": {
            "typical": national and national["typical"],
            "low": national and national["low"],
            "high": national and national["high"],
            "attendance": typical_attendance(jobs),
            "openings_label": openings_label(distinct_openings(jobs)),
            "as_of": _as_of(jobs),
        },
    }
