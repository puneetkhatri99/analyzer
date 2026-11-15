"""Reading a job page's HTML: pay, job type, remote, denomination, church size, and who/where/when.

schema.org JobPosting data (JSON-LD) is read first; the visible text fills what it doesn't give.
"""

import json
import re
from collections.abc import Iterator
from typing import Any

from bs4 import BeautifulSoup

Pay = tuple[float, float, str]  # (min, max, "year" | "hour")

EXPIRED_RE = re.compile(
    r"no longer (accepting|available|active|open)|position has been filled|job (posting )?(has )?expired|"
    r"this job (is|has been) (closed|removed)|job not found|posting is closed",
    re.I,
)

MONEY = r"\$\s?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s?([kK])?"
RANGE_RE = re.compile(
    MONEY + r"\s*(?:-|–|—|to)\s*" + MONEY + r"(?:\s*(?:per|/|an|a)?\s*(year|yr|annual|annually|hour|hr|hourly))?", re.I
)
SINGLE_RE = re.compile(MONEY + r"\s*(?:per|/|an|a)\s*(year|yr|hour|hr)", re.I)

HOURS_RE = [
    (re.compile(r"\bfull[- ]?time\b", re.I), "Full-Time"),
    (re.compile(r"\bpart[- ]?time\b", re.I), "Part-Time"),
    (re.compile(r"\bintern(ship)?\b", re.I), "Intern"),
    (re.compile(r"\bcontract(or)?\b", re.I), "Contract"),
]
EMPLOYMENT_TYPES = {
    "FULL_TIME": "Full-Time", "PART_TIME": "Part-Time", "INTERN": "Intern", "CONTRACTOR": "Contract",
    "TEMPORARY": "Temp", "VOLUNTEER": "Volunteer", "PER_DIEM": "Hourly",
}  # fmt: skip
REMOTE_RE = re.compile(r"\b(fully remote|100% remote|remote position|work from home|remote-first)\b", re.I)

# Matched against the organisation name, then a labelled field. Names follow the JSON feed's labels.
DENOMINATIONS = [
    (re.compile(pattern, re.I), name)
    for pattern, name in [
        (r"southern baptist|\bsbc\b", "Southern Baptist"),
        (r"\bbaptist", "Baptist"),
        (r"roman catholic|\bcatholic|\bdiocese|\barchdiocese|\bparish\b", "Catholic"),
        (r"\bpresbyterian|\bpc\(usa\)|\bpca\b", "Presbyterian"),
        (r"missouri synod|\blcms\b", "Lutheran Church-Missouri Synod"),
        (r"\blutheran|\belca\b", "Lutheran"),
        (r"united methodist|\bumc\b", "United Methodist"),
        (r"\bmethodist", "Methodist"),
        (r"\bepiscopal|\banglican", "Episcopal"),
        (r"assembl(y|ies) of god", "Assemblies of God"),
        (r"calvary chapel", "Calvary Chapel"),
        (r"\bnazarene", "Nazarene"),
        (r"seventh[- ]day adventist", "Seventh-day Adventist"),
        (r"salvation army", "Salvation Army"),
        (r"evangelical free|\befca\b", "Evangelical Free"),
        (r"christian and missionary alliance|\bc&ma\b", "Christian and Missionary Alliance"),
        (r"church of christ", "Church of Christ"),
        (r"\bwesleyan", "Wesleyan Church"),
        (r"\breformed\b", "Reformed"),
        (r"non-?denominational", "Non-denominational"),
    ]
]
DENOM_LABEL_RE = re.compile(r"\bDenomination:?\s+(.{0,60})", re.I)

_SIZE = r"\b(?:Church|Congregation)(?:/Company)? Size:?\s+"
SIZE_RANGE_RE = re.compile(_SIZE + r"(\d[\d,]*)\s*(?:to|-|–)\s*(\d[\d,]*)", re.I)
SIZE_OVER_RE = re.compile(_SIZE + r"(?:over|more than)\s+(\d[\d,]*)|" + _SIZE + r"(\d[\d,]*)\+", re.I)


def denomination_in(text: str | None) -> str | None:
    """The site's denomination name mentioned in `text` (e.g. an organisation name), or None."""
    return next((name for rx, name in DENOMINATIONS if rx.search(text or "")), None)


def church_size_from_text(text: str) -> int | None:
    """Lower bound of a stated attendance band ("Church/Company Size 1001 to 1500" -> 1001)."""
    m = SIZE_RANGE_RE.search(text) or SIZE_OVER_RE.search(text)
    if not m:
        return None
    n = int(next(g for g in m.groups() if g).replace(",", ""))
    return n if 0 < n < 100_000 else None


def _number(value: str, thousands: str | None) -> float:
    n = float(str(value).replace(",", ""))
    return n * 1000 if thousands else n


def _period(lo: float, unit: str | None) -> str:
    unit = (unit or "").lower()
    if unit.startswith("h"):
        return "hour"
    if unit:
        return "year"
    return "hour" if lo < 200 else "year"


def sane_pay(lo: float | None, hi: float | None, period: str) -> Pay | None:
    """Drop numbers that are plainly not a wage (a budget, a donation goal, a typo)."""
    if lo is None or hi is None or hi < lo:
        return None
    ok = 7 <= lo <= 200 and hi <= 250 if period == "hour" else 12_000 <= lo <= 400_000 and hi <= 500_000
    return (lo, hi, period) if ok else None


def salary_from_text(text: str) -> Pay | None:
    if m := RANGE_RE.search(text):
        lo_s, lo_k, hi_s, hi_k, unit = m.groups()
        lo, hi = _number(lo_s, lo_k), _number(hi_s, hi_k)
        return sane_pay(lo, hi, _period(lo, unit))
    if m := SINGLE_RE.search(text):
        value_s, k, unit = m.groups()
        value = _number(value_s, k)
        return sane_pay(value, value, _period(value, unit))
    return None


def job_postings(soup: BeautifulSoup) -> Iterator[dict[str, Any]]:
    """Every schema.org JobPosting in the page's JSON-LD, including ones nested in an @graph."""
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            d = stack.pop()
            if isinstance(d, dict):
                if d.get("@type") == "JobPosting":
                    yield d
                stack.extend(d.get("@graph", []) if isinstance(d.get("@graph"), list) else [])


def salary_from_ld(jp: dict[str, Any]) -> Pay | None:
    base = jp.get("baseSalary") or jp.get("estimatedSalary")
    if isinstance(base, list):
        base = base[0] if base else None
    if not isinstance(base, dict):
        return None
    val = base.get("value", base)
    if not isinstance(val, dict):
        val = {"value": val}
    try:
        lo = float(val.get("minValue") or val.get("value"))
        hi = float(val.get("maxValue") or val.get("value") or lo)
    except (TypeError, ValueError):
        return None
    unit = str(val.get("unitText") or base.get("unitText") or "")
    if unit.upper() in ("MONTH", "WEEK"):  # convert to annual
        factor = 12 if unit.upper() == "MONTH" else 52
        lo, hi, unit = lo * factor, hi * factor, "YEAR"
    return sane_pay(lo, hi, _period(lo, unit))


def _who_where_when(jp: dict[str, Any], out: dict[str, Any]) -> None:
    """Title, employer and place from a JobPosting: used by the collector for pages it found itself."""
    org = jp.get("hiringOrganization")
    loc = jp.get("jobLocation")
    loc = loc[0] if isinstance(loc, list) and loc else loc
    addr = loc.get("address") if isinstance(loc, dict) else None
    if isinstance(addr, str):  # some boards give one line: "Lincolnton, GA, 30817, US"
        out.setdefault("place", addr.strip())
    addr = addr if isinstance(addr, dict) else {}
    country = addr.get("addressCountry")
    for key, value in (
        ("title", jp.get("title")),
        ("org", org.get("name") if isinstance(org, dict) else org),
        ("org_website", org.get("url") if isinstance(org, dict) else None),
        ("city", addr.get("addressLocality")),
        ("state", addr.get("addressRegion")),
        ("country", country.get("name") if isinstance(country, dict) else country),
        ("date_posted", jp.get("datePosted")),
    ):
        if value and isinstance(value, str) and key not in out:
            out[key] = value.strip()


def parse_page(html: str, org_name: str | None) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    out: dict[str, Any] = {"structured": False}
    for jp in job_postings(soup):
        out["structured"] = True
        if "salary" not in out and (pay := salary_from_ld(jp)):
            out["salary"] = pay
        et = jp.get("employmentType")
        et = et[0] if isinstance(et, list) and et else et
        if et and "hours" not in out:
            out["hours"] = EMPLOYMENT_TYPES.get(str(et).upper().replace("-", "_"))
        if str(jp.get("jobLocationType", "")).upper() == "TELECOMMUTE":
            out["remote"] = "true"
        _who_where_when(jp, out)
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ").split())
    out.setdefault("salary", salary_from_text(text))
    if not out.get("hours"):
        out["hours"] = next((label for rx, label in HOURS_RE if rx.search(text)), None)
    if "remote" not in out and REMOTE_RE.search(text):
        out["remote"] = "true"
    # Only the org name or a labelled "Denomination" field: matching the whole page picks up navigation text.
    label = DENOM_LABEL_RE.search(text)
    out["denomination"] = denomination_in(org_name) or (denomination_in(label.group(1)) if label else None)
    out["church_size"] = church_size_from_text(text)
    out["text"] = text
    return out
