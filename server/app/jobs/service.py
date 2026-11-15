"""Admin dashboard figures: filtering postings and summarising their pay."""

import math
from collections.abc import Iterable
from typing import Any

from app.shared.stats import quantile

Job = dict[str, Any]

HISTOGRAM_BIN = 10_000
HISTOGRAM_CAP = 150_000
CHURCH_SIZE_BANDS = [  # (label, min attendance inclusive, max exclusive)
    ("Under 250", 0, 250),
    ("250–999", 250, 1000),
    ("1,000–4,999", 1000, 5000),
    ("5,000+", 5000, math.inf),
]


def apply_filters(jobs: list[Job], f: dict[str, Any], skip: Iterable[str] = ()) -> list[Job]:
    """Keep postings matching every filter in `f`, ignoring the keys listed in `skip`."""
    f = {k: v for k, v in f.items() if k not in skip}
    search = (f.get("search") or "").lower()
    min_salary = f.get("min_salary") or 0
    min_size = f.get("min_church_size") or 0
    exact = [(key, key) for key in ("role", "denomination", "region", "country", "status", "hours")]

    def keep(d: Job) -> bool:
        if any(f.get(key) and d[field] != f[key] for key, field in exact):
            return False
        if f.get("origin") and not d["origin"].startswith(f["origin"]):
            return False
        if f.get("remote") and str(d["remote"]) != f["remote"]:
            return False
        pay = d["salary_annual_mid"]
        if f.get("has_pay") and pay is None:
            return False
        if min_salary and not (pay is not None and pay >= min_salary):
            return False
        if min_size and not (d["church_size"] is not None and d["church_size"] >= min_size):
            return False
        return not search or search in (d["job_name"] or "").lower() or search in (d["company_name"] or "").lower()

    return [d for d in jobs if keep(d)]


def count_by(jobs: list[Job], key: str) -> list[tuple[Any, int]]:
    counts: dict[Any, int] = {}
    for d in jobs:
        v = d.get(key)
        if v is None or v == "":
            continue
        counts[v] = counts.get(v, 0) + 1
    return sorted(counts.items(), key=lambda p: -p[1])


def _rounded_quantile(values: list[float], q: float) -> int | None:
    v = quantile(values, q)
    return None if v is None else round(v)


def pay_stats(jobs: list[Job]) -> dict[str, Any]:
    pay = sorted(d["salary_annual_mid"] for d in jobs if d["salary_annual_mid"] is not None)
    return {
        "postings": len(jobs),
        "paid": len(pay),
        "p25": _rounded_quantile(pay, 0.25),
        "median": _rounded_quantile(pay, 0.5),
        "p75": _rounded_quantile(pay, 0.75),
    }


def group_pay(jobs: list[Job], key: str) -> list[dict[str, Any]]:
    groups: dict[Any, list[Job]] = {}
    for d in jobs:
        if v := d.get(key):
            groups.setdefault(v, []).append(d)
    return [{"name": name, **pay_stats(rows)} for name, rows in groups.items()]


def _histogram(pay: list[float]) -> list[dict[str, int]]:
    if not pay:
        return []
    top_bin = min(int(max(pay) // HISTOGRAM_BIN) * HISTOGRAM_BIN, HISTOGRAM_CAP)
    counts = dict.fromkeys(range(0, top_bin + HISTOGRAM_BIN, HISTOGRAM_BIN), 0)
    for v in pay:
        counts[min(int(v // HISTOGRAM_BIN) * HISTOGRAM_BIN, HISTOGRAM_CAP)] += 1
    return [{"from": b, "count": c} for b, c in sorted(counts.items())]


def build_summary(jobs: list[Job], jobs_any_role: list[Job], jobs_any_state: list[Job]) -> dict[str, Any]:
    """`jobs` matches every filter. The role and state ladders are built from rows that
    ignore their own filter, so every role or state stays comparable while one is selected."""
    by_church_size = []
    for label, lo, hi in CHURCH_SIZE_BANDS:
        rows = [d for d in jobs if d["church_size"] is not None and lo <= d["church_size"] < hi]
        by_church_size.append({"name": label, **pay_stats(rows)})

    pull_dates = [d["pull_date"] for d in jobs if d["pull_date"]]
    return {
        "stats": {
            **pay_stats(jobs),
            "employers": len({d["company_name"] for d in jobs if d["company_name"]}),
            "denominations": len({d["denomination"] for d in jobs if d["denomination"]}),
            "no_denomination": sum(1 for d in jobs if not d["denomination"]),
            "no_church_size": sum(1 for d in jobs if d["church_size"] is None),
            "as_of": max(pull_dates) if pull_dates else None,
        },
        "by_role": sorted(group_pay(jobs_any_role, "role"), key=lambda r: -(r["median"] or -1)),
        "by_state": sorted(group_pay(jobs_any_state, "region"), key=lambda r: -r["postings"])[:10],
        "by_denomination": sorted(group_pay(jobs, "denomination"), key=lambda r: -r["postings"]),
        "by_church_size": by_church_size,
        "histogram": _histogram([d["salary_annual_mid"] for d in jobs if d["salary_annual_mid"] is not None]),
        "histogram_bin": HISTOGRAM_BIN,
        "histogram_cap": HISTOGRAM_CAP,
    }


def build_filter_options(jobs: list[Job]) -> dict[str, list[tuple[Any, int]]]:
    return {
        "roles": count_by(jobs, "role"),
        "denominations": count_by(jobs, "denomination"),
        "regions": count_by(jobs, "region"),
        "countries": count_by(jobs, "country"),
        "hours": count_by(jobs, "hours"),
    }
