"""Fill the empty columns of church_jobs / nonprofit_jobs by fetching each job_url.

Usage (from the server/ directory):
  python -m pipeline.fetch_jobs churches [--limit 30] [--retry]
  python -m pipeline.fetch_jobs nonprofits

Reads the page's schema.org JobPosting data first (salary, job type, remote), then falls
back to the visible text. Sets fetch_status to ok | expired | blocked | error.
Rows already fetched are skipped; --retry also re-fetches blocked and error rows.
A site that blocks 10 requests in a row is skipped for the rest of the run; its rows stay unfetched.
"""
import argparse
import json
import re
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup

from app.db import get_conn
from pipeline.import_bizdev import TABLES

TIMEOUT = 15
HOST_DELAY = 1.0           # seconds between requests to the same site
MAX_BLOCKED_IN_A_ROW = 10
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MinistryJobsAnalyser/1.0)", "Accept-Language": "en-US,en;q=0.9"}

EXPIRED_RE = re.compile(
    r"no longer (accepting|available|active|open)|position has been filled|job (posting )?(has )?expired|"
    r"this job (is|has been) (closed|removed)|job not found|posting is closed", re.I)
BLOCKED_RE = re.compile(r"just a moment\.\.\.|cf-chl|attention required|access denied|captcha|are you a robot", re.I)

MONEY = r"\$\s?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s?([kK])?"
RANGE_RE = re.compile(MONEY + r"\s*(?:-|–|—|to)\s*" + MONEY + r"(?:\s*(?:per|/|an|a)?\s*(year|yr|annual|annually|hour|hr|hourly))?", re.I)
SINGLE_RE = re.compile(MONEY + r"\s*(?:per|/|an|a)\s*(year|yr|hour|hr)", re.I)

HOURS_RE = [(re.compile(r"\bfull[- ]?time\b", re.I), "Full-Time"), (re.compile(r"\bpart[- ]?time\b", re.I), "Part-Time"),
            (re.compile(r"\bintern(ship)?\b", re.I), "Intern"), (re.compile(r"\bcontract(or)?\b", re.I), "Contract")]
EMPLOYMENT_TYPES = {"FULL_TIME": "Full-Time", "PART_TIME": "Part-Time", "INTERN": "Intern", "CONTRACTOR": "Contract",
                    "TEMPORARY": "Temp", "VOLUNTEER": "Volunteer", "PER_DIEM": "Hourly"}
REMOTE_RE = re.compile(r"\b(fully remote|100% remote|remote position|work from home|remote-first)\b", re.I)

# Matched against the organisation name, then the page text. Names follow the JSON feed's labels.
DENOMINATIONS = [
    (r"southern baptist|\bsbc\b", "Southern Baptist"), (r"\bbaptist", "Baptist"),
    (r"roman catholic|\bcatholic|\bdiocese|\barchdiocese|\bparish\b", "Catholic"),
    (r"\bpresbyterian|\bpc\(usa\)|\bpca\b", "Presbyterian"), (r"missouri synod|\blcms\b", "Lutheran Church-Missouri Synod"),
    (r"\blutheran|\belca\b", "Lutheran"), (r"united methodist|\bumc\b", "United Methodist"), (r"\bmethodist", "Methodist"),
    (r"\bepiscopal|\banglican", "Episcopal"), (r"assembl(y|ies) of god", "Assemblies of God"),
    (r"calvary chapel", "Calvary Chapel"), (r"\bnazarene", "Nazarene"), (r"seventh[- ]day adventist", "Seventh-day Adventist"),
    (r"salvation army", "Salvation Army"), (r"evangelical free|\befca\b", "Evangelical Free"),
    (r"christian and missionary alliance|\bc&ma\b", "Christian and Missionary Alliance"),
    (r"church of christ", "Church of Christ"), (r"\bwesleyan", "Wesleyan Church"), (r"\breformed\b", "Reformed"),
    (r"non-?denominational", "Non-denominational"),
]
DENOMINATIONS = [(re.compile(p, re.I), name) for p, name in DENOMINATIONS]
DENOM_LABEL_RE = re.compile(r"\bDenomination:?\s+(.{0,60})", re.I)
_SIZE = r"\b(?:Church|Congregation)(?:/Company)? Size:?\s+"
SIZE_RANGE_RE = re.compile(_SIZE + r"(\d[\d,]*)\s*(?:to|-|–)\s*(\d[\d,]*)", re.I)
SIZE_OVER_RE = re.compile(_SIZE + r"(?:over|more than)\s+(\d[\d,]*)|" + _SIZE + r"(\d[\d,]*)\+", re.I)


def church_size_from_text(text):
    """Lower bound of a stated attendance band ("Church/Company Size 1001 to 1500" -> 1001)."""
    m = SIZE_RANGE_RE.search(text) or SIZE_OVER_RE.search(text)
    if not m:
        return None
    n = int(next(g for g in m.groups() if g).replace(",", ""))
    return n if 0 < n < 100_000 else None


def _num(v, k):
    n = float(str(v).replace(",", ""))
    return n * 1000 if k else n


def _period(lo, unit):
    unit = (unit or "").lower()
    if unit.startswith("h"):
        return "hour"
    if unit:
        return "year"
    return "hour" if lo < 200 else "year"


def _sane(lo, hi, period):
    """Drop numbers that are plainly not a wage (a budget, a donation goal, a typo)."""
    if lo is None or hi is None or hi < lo:
        return None
    ok = 7 <= lo <= 200 and hi <= 250 if period == "hour" else 12_000 <= lo <= 400_000 and hi <= 500_000
    return (lo, hi, period) if ok else None


def salary_from_text(text):
    m = RANGE_RE.search(text)
    if m:
        lo, lk, hi, hk, unit = m.groups()
        lo, hi = _num(lo, lk), _num(hi, hk)
        return _sane(lo, hi, _period(lo, unit))
    m = SINGLE_RE.search(text)
    if m:
        v, k, unit = m.groups()
        v = _num(v, k)
        return _sane(v, v, _period(v, unit))
    return None


def _job_postings(soup):
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


def salary_from_ld(jp):
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
        lo, hi, unit = lo * (12 if unit.upper() == "MONTH" else 52), hi * (12 if unit.upper() == "MONTH" else 52), "YEAR"
    return _sane(lo, hi, _period(lo, unit))


def parse_page(html, org_name):
    soup = BeautifulSoup(html, "html.parser")
    out = {"structured": False}
    for jp in _job_postings(soup):
        out["structured"] = True
        if "salary" not in out and (s := salary_from_ld(jp)):
            out["salary"] = s
        et = jp.get("employmentType")
        et = et[0] if isinstance(et, list) and et else et
        if et and "hours" not in out:
            out["hours"] = EMPLOYMENT_TYPES.get(str(et).upper().replace("-", "_"))
        if str(jp.get("jobLocationType", "")).upper() == "TELECOMMUTE":
            out["remote"] = "true"
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
    out["denomination"] = next((name for rx, name in DENOMINATIONS if rx.search(org_name or "")), None) or \
        (next((name for rx, name in DENOMINATIONS if rx.search(label.group(1))), None) if label else None)
    out["church_size"] = church_size_from_text(text)
    out["text"] = text
    return out


def workday_api_url(url):
    """Workday job pages are JavaScript shells; the same job is served as JSON at /wday/cxs/<tenant>/<site>/job/..."""
    p = urlsplit(url)
    parts = [x for x in p.path.split("/") if x]
    if parts and re.fullmatch(r"[a-z]{2}-[A-Z]{2}", parts[0]):  # locale prefix, e.g. en-US
        parts = parts[1:]
    if len(parts) < 2 or "job" not in parts:
        return None
    return f"https://{p.netloc}/wday/cxs/{p.netloc.split('.')[0]}/{parts[0]}/" + "/".join(parts[parts.index("job"):])


def check_workday(url):
    api = workday_api_url(url)
    if not api:
        return "unknown", {}
    try:
        r = requests.get(api, headers={**HEADERS, "Accept": "application/json"}, timeout=TIMEOUT)
    except requests.RequestException:
        return "error", {}
    if r.status_code in (404, 410):
        return "expired", {}
    if r.status_code != 200:
        return ("blocked" if r.status_code in (401, 403, 429) else "error"), {}
    try:
        info = r.json().get("jobPostingInfo") or {}
    except ValueError:
        return "unknown", {}
    if not info:
        return "expired", {}
    return ("expired" if info.get("canApply") is False else "ok"), {}


def fetch_one(url, org_name):
    """Returns (fetch_status, parsed fields)."""
    url = url if url.startswith("http") else "https://" + url
    if ".myworkdayjobs.com/" in url:
        return check_workday(url)
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException:
        return "error", {}
    if r.status_code in (404, 410):
        return "expired", {}
    if r.status_code in (401, 403, 429, 503) or (r.status_code == 200 and BLOCKED_RE.search(r.text[:3000]) and len(r.text) < 30000):
        return "blocked", {}
    if r.status_code >= 400:
        return "error", {}
    page = parse_page(r.text, org_name)
    if EXPIRED_RE.search(page["text"][:5000]) and not page["salary"]:
        return "expired", page
    if len(page["text"]) < 400 and not page["structured"]:
        return "unknown", page  # a JavaScript shell (Paycom, ADP, HRM Direct...): open or closed can't be told
    return "ok", page


# Seen-open and seen-closed times are kept apart so the expiry window survives later checks.
_TRACK = """last_live_at = CASE WHEN %(status)s = 'ok' THEN now() ELSE {t}last_live_at END,
    expired_at = CASE WHEN %(status)s = 'expired' THEN coalesce({t}expired_at, now()) ELSE {t}expired_at END"""

# BizDev rows: a re-check never erases details found earlier (an expired page has none).
UPDATE = """UPDATE public.{table} SET fetch_status = %(status)s, fetched_at = now(),
    salary_min = coalesce(%(lo)s, salary_min), salary_max = coalesce(%(hi)s, salary_max),
    salary_period = coalesce(%(period)s, salary_period),
    hours = coalesce(%(hours)s, hours), remote = coalesce(%(remote)s, remote),
    denomination = coalesce(%(denomination)s, denomination), church_size = coalesce(%(church_size)s, church_size),
    """ + _TRACK.format(t="") + " WHERE url_key = %(key)s"

# Feed rows: only the check result; pay and details come from the feed itself.
UPSERT_FEED = """INSERT INTO public.posting_checks AS t (post_uuid, check_status, checked_at, last_live_at, expired_at)
    VALUES (%(key)s, %(status)s, now(), CASE WHEN %(status)s = 'ok' THEN now() END, CASE WHEN %(status)s = 'expired' THEN now() END)
    ON CONFLICT (post_uuid) DO UPDATE SET check_status = %(status)s, checked_at = now(),
    """ + _TRACK.format(t="t.")

KINDS = {**TABLES, "json": "posting_checks"}
SELECT = {
    "json": """SELECT p.post_uuid, p.post_url, c.company_name FROM public.postings p
               LEFT JOIN public.companies c USING (company_uuid)
               LEFT JOIN public.posting_checks k USING (post_uuid)
               WHERE p.post_url IS NOT NULL AND ({where})""",
    "excel": "SELECT url_key, job_url, org_name FROM public.{table} WHERE {where}",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=KINDS, help="json = the church jobs feed; churches / nonprofits = the BizDev tables")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--retry", action="store_true", help="also re-fetch rows that were blocked or errored")
    ap.add_argument("--recheck", action="store_true", help="re-check every job not already expired, to catch newly closed ones")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--no-skip", action="store_true", help="keep trying a site even after it blocks 10 in a row")
    args = ap.parse_args()
    table = KINDS[args.kind]
    is_feed = args.kind == "json"
    status_col = "k.check_status" if is_feed else "fetch_status"

    if args.recheck:
        where = f"{status_col} IS DISTINCT FROM 'expired'"
    else:
        where = f"{status_col} IS NULL" + (f" OR {status_col} IN ('blocked', 'error')" if args.retry else "")
    sql = (SELECT["json"] if is_feed else SELECT["excel"]).format(table=table, where=where)
    with get_conn() as conn:
        rows = conn.execute(sql + " ORDER BY random()" + (f" LIMIT {int(args.limit)}" if args.limit else "")).fetchall()

    by_host = defaultdict(list)
    for r in rows:
        by_host[urlsplit(r[1] if r[1].startswith("http") else "https://" + r[1]).netloc.lower()].append(r)
    print(f"{table}: fetching {len(rows)} pages from {len(by_host)} sites")

    tally = defaultdict(int)
    lock = threading.Lock()
    skipped_hosts = {}

    def run_host(host, items):
        blocked_in_a_row = 0
        with get_conn() as conn:
            for i, (key, url, org) in enumerate(items):
                if blocked_in_a_row >= MAX_BLOCKED_IN_A_ROW and not args.no_skip:
                    skipped_hosts[host] = len(items) - i
                    return
                status, page = fetch_one(url, org)
                blocked_in_a_row = blocked_in_a_row + 1 if status == "blocked" else 0
                lo, hi, period = page.get("salary") or (None, None, None)
                params = {"status": status, "key": key, "lo": lo, "hi": hi, "period": period,
                          **{f: page.get(f) for f in ("hours", "remote", "denomination", "church_size")}}
                conn.execute(UPSERT_FEED if is_feed else UPDATE.format(table=table), params)
                with lock:
                    tally[status] += 1
                    tally["with pay"] += bool(page.get("salary"))
                    done = sum(tally[s] for s in ("ok", "expired", "unknown", "blocked", "error"))
                    if done % 50 == 0:
                        print(f"  {done}/{len(rows)} {dict(tally)}", flush=True)
                time.sleep(HOST_DELAY)

    with ThreadPoolExecutor(args.workers) as pool:
        # biggest sites first so the long queues start early
        for host, items in sorted(by_host.items(), key=lambda p: -len(p[1])):
            pool.submit(run_host, host, items).add_done_callback(lambda f: f.exception() and print('  worker failed:', f.exception()))

    print(f"{table}: done {dict(tally)}")
    for host, n in skipped_hosts.items():
        print(f"  skipped {n} rows on {host}: it blocked {MAX_BLOCKED_IN_A_ROW} requests in a row")


if __name__ == "__main__":
    main()
