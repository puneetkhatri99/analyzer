import decimal
import math

from app.db import get_conn
from app.roles import bucket_role

HOURS_PER_YEAR = 2080
HISTOGRAM_BIN = 10_000
HISTOGRAM_CAP = 150_000
CHURCH_SIZE_BANDS = [  # (label, min attendance inclusive, max exclusive)
    ("Under 250", 0, 250),
    ("250–999", 250, 1000),
    ("1,000–4,999", 1000, 5000),
    ("5,000+", 5000, math.inf),
]


def _conv(v):
    if isinstance(v, decimal.Decimal):
        return float(v)
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


_COLS = [
    "post_uuid", "job_name", "department", "hours", "seniority", "remote",
    "board_source", "post_url", "city", "region", "country", "company_name",
    "denomination", "church_size", "salary_min", "salary_max", "salary_period",
    "first_indexed", "pull_date", "check_status", "last_live_at", "expired_at", "origin", "added_at",
]

# Latest check of the job's URL (pipeline/fetch_jobs.py) -> what the dashboard shows.
# unknown / blocked / error / never checked all mean the same to a reader: not verified.
STATUS = {"ok": "open", "expired": "expired"}


# Tables are schema-qualified: through a transaction pooler (Neon's -pooler host) a
# shared session can carry another client's search_path, and unqualified names then fail.
_FEED_SQL = """
    SELECT p.post_uuid, p.job_name_raw, p.department, p.hours,
           p.seniority, p.remote, p.board_source, p.post_url, p.city, p.region, p.country,
           c.company_name, c.denomination, c.church_size,
           s.salary_min, s.salary_max, s.salary_period,
           p.first_indexed, s.pull_date, k.check_status, k.last_live_at, k.expired_at, 'feed', p.created_at
    FROM public.postings p
    LEFT JOIN public.companies c USING (company_uuid)
    LEFT JOIN public.posting_checks k USING (post_uuid)
    LEFT JOIN LATERAL (
        SELECT * FROM public.posting_snapshots ps
        WHERE ps.post_uuid = p.post_uuid
        ORDER BY ps.pull_date DESC
        LIMIT 1
    ) s ON true
"""

# The BizDev tables mapped onto the feed's columns. Contact names and emails are never selected:
# the API is public.
_BIZDEV_SQL = """
    SELECT url_key, job_title, NULL, hours, NULL, remote, split_part(url_key, '/', 1), job_url,
           city, state, 'US', org_name, denomination, church_size,
           salary_min, salary_max, salary_period, date_posted, fetched_at::date,
           fetch_status, last_live_at, expired_at, added_via, imported_at
    FROM public.{table}
"""

SOURCES = {
    "json": {"label": "Church jobs feed", "sql": _FEED_SQL},
    "churches": {"label": "BizDev churches", "sql": _BIZDEV_SQL.format(table="church_jobs")},
    "nonprofits": {"label": "BizDev nonprofits", "sql": _BIZDEV_SQL.format(table="nonprofit_jobs")},
}


def load_jobs(source="json"):
    """Every posting of one source as a flat dict, plus derived role and annual pay.

    Re-queried per request: at a few thousand rows this takes a few ms, so there's no
    cache to invalidate when the pipeline re-runs.
    """
    with get_conn() as conn:
        rows = conn.execute(SOURCES[source]["sql"]).fetchall()

    out = []
    for row in rows:
        d = {c: _conv(v) for c, v in zip(_COLS, row)}
        d["role"] = bucket_role(d["job_name"])
        d["status"] = STATUS.get(d.pop("check_status"), "unverified")
        lo, hi, period = d["salary_min"], d["salary_max"], d["salary_period"]
        annual = None
        if lo is not None and hi is not None:
            mid = (lo + hi) / 2
            annual = round(mid * HOURS_PER_YEAR) if period == "hour" else round(mid)
        d["salary_annual_mid"] = annual
        if d["post_url"] and not d["post_url"].startswith("http"):
            d["post_url"] = "https://" + d["post_url"]
        out.append(d)
    return out


def apply_filters(jobs, f, skip=()):
    """Keep postings matching every filter in `f`, ignoring the keys listed in `skip`."""
    f = {k: v for k, v in f.items() if k not in skip}
    search = (f.get("search") or "").lower()
    min_salary = f.get("min_salary") or 0
    min_size = f.get("min_church_size") or 0

    def keep(d):
        if f.get("role") and d["role"] != f["role"]:
            return False
        if f.get("denomination") and d["denomination"] != f["denomination"]:
            return False
        if f.get("region") and d["region"] != f["region"]:
            return False
        if f.get("country") and d["country"] != f["country"]:
            return False
        if f.get("origin") and not d["origin"].startswith(f["origin"]):
            return False
        if f.get("status") and d["status"] != f["status"]:
            return False
        if f.get("hours") and d["hours"] != f["hours"]:
            return False
        if f.get("remote") and str(d["remote"]) != f["remote"]:
            return False
        if f.get("has_pay") and d["salary_annual_mid"] is None:
            return False
        if min_salary and not (d["salary_annual_mid"] is not None and d["salary_annual_mid"] >= min_salary):
            return False
        if min_size and not (d["church_size"] is not None and d["church_size"] >= min_size):
            return False
        if search and search not in (d["job_name"] or "").lower() and search not in (d["company_name"] or "").lower():
            return False
        return True

    return [d for d in jobs if keep(d)]


def count_by(jobs, key):
    counts = {}
    for d in jobs:
        v = d.get(key)
        if v is None or v == "":
            continue
        counts[v] = counts.get(v, 0) + 1
    return sorted(counts.items(), key=lambda p: -p[1])


def quantile(sorted_vals, q):
    """Linear-interpolated quantile of an already sorted list; None when empty."""
    if not sorted_vals:
        return None
    pos = (len(sorted_vals) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    return round(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo))


def pay_stats(jobs):
    pay = sorted(d["salary_annual_mid"] for d in jobs if d["salary_annual_mid"] is not None)
    return {
        "postings": len(jobs),
        "paid": len(pay),
        "p25": quantile(pay, 0.25),
        "median": quantile(pay, 0.5),
        "p75": quantile(pay, 0.75),
    }


def group_pay(jobs, key):
    groups = {}
    for d in jobs:
        v = d.get(key)
        if v:
            groups.setdefault(v, []).append(d)
    return [{"name": name, **pay_stats(rows)} for name, rows in groups.items()]


def build_summary(jobs, jobs_any_role, jobs_any_state):
    """`jobs` matches every filter. The role and state ladders are built from rows that
    ignore their own filter, so every role or state stays comparable while one is selected."""
    overall = pay_stats(jobs)

    by_role = sorted(group_pay(jobs_any_role, "role"), key=lambda r: -(r["median"] or -1))

    by_state = sorted(group_pay(jobs_any_state, "region"), key=lambda r: -r["postings"])[:10]

    by_denomination = sorted(group_pay(jobs, "denomination"), key=lambda r: -r["postings"])

    by_church_size = []
    for label, lo, hi in CHURCH_SIZE_BANDS:
        rows = [d for d in jobs if d["church_size"] is not None and lo <= d["church_size"] < hi]
        by_church_size.append({"name": label, **pay_stats(rows)})

    pay = [d["salary_annual_mid"] for d in jobs if d["salary_annual_mid"] is not None]
    histogram = []
    if pay:
        top_bin = min(int(max(pay) // HISTOGRAM_BIN) * HISTOGRAM_BIN, HISTOGRAM_CAP)
        counts = {b: 0 for b in range(0, top_bin + HISTOGRAM_BIN, HISTOGRAM_BIN)}
        for v in pay:
            counts[min(int(v // HISTOGRAM_BIN) * HISTOGRAM_BIN, HISTOGRAM_CAP)] += 1
        histogram = [{"from": b, "count": c} for b, c in sorted(counts.items())]

    pull_dates = [d["pull_date"] for d in jobs if d["pull_date"]]

    return {
        "stats": {
            **overall,
            "employers": len({d["company_name"] for d in jobs if d["company_name"]}),
            "denominations": len({d["denomination"] for d in jobs if d["denomination"]}),
            "no_denomination": sum(1 for d in jobs if not d["denomination"]),
            "no_church_size": sum(1 for d in jobs if d["church_size"] is None),
            "as_of": max(pull_dates) if pull_dates else None,
        },
        "by_role": by_role,
        "by_state": by_state,
        "by_denomination": by_denomination,
        "by_church_size": by_church_size,
        "histogram": histogram,
        "histogram_bin": HISTOGRAM_BIN,
        "histogram_cap": HISTOGRAM_CAP,
    }


def source_counts():
    """Postings, pay and fetch progress per source, for the source switcher."""
    out = []
    with get_conn() as conn:
        for key, s in SOURCES.items():
            postings, paid, fetched, open_, expired = conn.execute(
                "SELECT count(*), count(salary_min), count(pull_date), count(*) FILTER (WHERE check_status = 'ok'),"
                f" count(*) FILTER (WHERE check_status = 'expired') FROM ({s['sql']}) j(" + ", ".join(_COLS) + ")"
            ).fetchone()
            out.append({"key": key, "label": s["label"], "postings": postings, "paid": paid, "fetched": fetched,
                        "open": open_, "expired": expired})
    return out


def build_filter_options(jobs):
    return {
        "roles": count_by(jobs, "role"),
        "denominations": count_by(jobs, "denomination"),
        "regions": count_by(jobs, "region"),
        "countries": count_by(jobs, "country"),
        "hours": count_by(jobs, "hours"),
    }
