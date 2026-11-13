"""The public report: one blended dataset, pay ranges with a confidence label, and automatic widening
(state -> region -> nationwide) so every search gets an answer.

Nothing here returns counts, employer names, sources or links: the public must not see how the data is gathered.
"""
from app.jobs import HOURS_PER_YEAR, load_jobs
from app.roles import ROLE_RULES

MIN_PAID = 5  # below this many jobs with pay, a figure isn't shown and the search widens
CONFIDENCE = [(30, "Strong"), (10, "Moderate"), (MIN_PAID, "Limited")]  # proposal; tune once the data grows
HIDDEN_ROLES = {"Healthcare"}  # the brief removes medical jobs from the public tool

STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
    "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
    "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}
_STATE_NAMES = {name.lower(): name for name in STATES.values()}

# The brief's six regions, plus Mountain West so every state has one (proposal, client to confirm).
REGIONS = {
    "North East": "CT ME MA NH RI VT NY NJ PA DE MD DC",
    "South East": "VA WV NC SC GA FL KY TN AL MS AR LA",
    "Midwest": "OH IN IL MI WI MN IA MO ND SD NE KS",
    "Southwest": "TX OK NM AZ",
    "West Coast": "CA HI",
    "Pacific Northwest": "WA OR ID AK",
    "Mountain West": "CO UT WY MT NV",
}
REGION_OF = {STATES[code]: region for region, codes in REGIONS.items() for code in codes.split()}

SIZES = [("Under 250", 0, 250), ("250 to 999", 250, 1000), ("1,000 to 4,999", 1000, 5000), ("5,000 or more", 5000, None)]
JOB_TYPES = {"full-time": "year", "part-time": "hour"}
ROLE_ORDER = [label for _, label in ROLE_RULES if label not in HIDDEN_ROLES] + ["Other"]


def state_name(value):
    """'OH', 'oh' or 'Ohio' -> 'Ohio'; anything that isn't a US state ('Cook', 'N/A', 'Varies') -> None."""
    v = (value or "").strip()
    return STATES.get(v.upper()) or _STATE_NAMES.get(v.lower())


def _pay(d, job_type):
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


def blended_jobs():
    """Every US job from every source as one list (brief P5), with the state normalised and medical roles removed."""
    out = []
    for source in ("json", "churches", "nonprofits"):
        for d in load_jobs(source):
            if d["country"] not in ("US", "United States") or d["role"] in HIDDEN_ROLES:
                continue
            d["state"] = state_name(d["region"])
            out.append(d)
    return out


def _size_label(size):
    if size is None:
        return None
    for label, lo, hi in SIZES:
        if size >= lo and (hi is None or size < hi):
            return label


def _matches(d, f, skip=()):
    return all(
        not f[key] or key in skip or value in f[key]
        for key, value in (("role", d["role"]), ("state", d["state"]), ("size", _size_label(d["church_size"])),
                           ("denomination", d["denomination"]))
    )


def _stats(jobs, job_type):
    pay = sorted(p for p in (_pay(d, job_type) for d in jobs) if p is not None)
    if len(pay) < MIN_PAID:
        return None
    digits = 2 if job_type == "part-time" else 0  # hourly rates keep cents
    q = lambda x: round(_quantile(pay, x), digits)
    return {"typical": q(0.5), "low": q(0.25), "high": q(0.75),
            "confidence": next(label for n, label in CONFIDENCE if len(pay) >= n)}


def _quantile(sorted_vals, q):
    """jobs.quantile without its rounding to whole dollars, which would break hourly rates."""
    pos = (len(sorted_vals) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def _rows(jobs, key, job_type, order=None, limit=None):
    """[{name, typical}] per value of `key`, only values with enough pay to benchmark."""
    groups = {}
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


def _join(items):
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def openings_label(n):
    """'4,000+': a rounded figure for the 'drawn from …' line (brief P7: no exact counts)."""
    step = 1000 if n >= 1000 else 100
    return f"{n // step * step:,}+" if n >= step else "hundreds of"


def build_report(f, jobs=None):
    """f = {role, state, size, denomination: [values], type: 'full-time' | 'part-time'}."""
    jobs = blended_jobs() if jobs is None else jobs
    job_type = f["type"] if f.get("type") in JOB_TYPES else "full-time"
    f = {k: [v for v in (f.get(k) or []) if v] for k in ("role", "state", "size", "denomination")}
    f["state"] = [s for s in (state_name(x) for x in f["state"]) if s]

    # Widen until there's enough pay: the chosen states, then their regions, then nationwide.
    areas = []
    if f["state"]:
        areas.append(("state", _join(f["state"]), set(f["state"])))
        regions = sorted({REGION_OF[s] for s in f["state"]})
        areas.append(("region", _join(regions), {s for s, r in REGION_OF.items() if r in regions}))
    areas.append(("national", "nationwide", None))

    base = [d for d in jobs if _matches(d, f, skip=("state",))]
    for scope, area_name, states in areas:
        in_area = [d for d in base if states is None or d["state"] in states]
        pay = _stats(in_area, job_type)
        if pay:
            break
    area_states = states

    note = None
    if not pay:
        note = "Too few current openings list pay for this search to benchmark yet. Try another role or job type."
    elif scope != "state" and f["state"]:
        where = "national figures" if scope == "national" else f"{area_name} figures"
        note = (f"Showing {where}. {_join(f['state'])} data for this role is still limited, "
                "so we widened the search to give you a reliable range.")

    in_area_jobs = lambda skip: [d for d in jobs if _matches(d, f, skip=("state", *skip))
                                 and (area_states is None or d["state"] in area_states)]

    # Area vs nationwide, all roles of this job type.
    vs_national = None
    if f["state"]:
        local = _stats([d for d in jobs if d["state"] in set(f["state"])], job_type)
        national = _stats(jobs, job_type)
        if local and national:
            diff = round((local["typical"] - national["typical"]) / national["typical"] * 100)
            vs_national = {"area": _join(f["state"]), "area_typical": local["typical"],
                           "national_typical": national["typical"], "percent": diff}

    share = None
    if f["role"]:
        share = round(sum(1 for d in jobs if d["role"] in f["role"]) / max(len(jobs), 1) * 100)

    by_size = []
    for label, _, _ in SIZES:
        s = _stats([d for d in in_area_jobs(("size",)) if _size_label(d["church_size"]) == label], job_type)
        by_size.append({"name": label, "typical": s["typical"] if s else None})

    as_of = max((d["pull_date"] for d in jobs if d["pull_date"]), default=None)
    roles = f["role"] or ["Ministry"]
    return {
        "title": {"role": _join(roles), "area": _join(f["state"]) if f["state"] else "the United States"},
        "filters": {**f, "type": job_type},
        "scope": scope,
        "area_name": area_name,
        "note": note,
        "unit": JOB_TYPES[job_type],
        "pay": pay,
        "vs_national": vs_national,
        "share_percent": share,
        "days_open": None,   # needs first/last-seen history (data work)
        "insight": None,     # written by the MinistryHub team (data work)
        "by_role": _rows(in_area_jobs(("role",)), "role", job_type, order=ROLE_ORDER),
        "by_size": by_size,
        "by_state": _rows([d for d in jobs if _matches(d, f, skip=("state",))], "state", job_type, limit=8),
        "by_denomination": _rows(in_area_jobs(("denomination",)), "denomination", job_type, limit=6),
        "openings_label": openings_label(len(jobs)),
        "as_of": as_of,
    }


def report_options(jobs=None):
    """Choices for the landing form and report filters, plus the landing page's headline stats. No counts (P7)."""
    jobs = blended_jobs() if jobs is None else jobs
    present = {d["role"] for d in jobs}
    denoms = {}
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
            "avg_attendance": None,  # church size is known for too few jobs yet (data work)
            "days_open": None,
            "openings_label": openings_label(len(jobs)),
            "as_of": max((d["pull_date"] for d in jobs if d["pull_date"]), default=None),
        },
    }
