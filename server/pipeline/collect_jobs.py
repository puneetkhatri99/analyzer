"""Collect new US church job postings into church_jobs (the BizDev churches tab), marked added_via = 'collector'.

Usage (from the server/ directory):
  python -m pipeline.collect_jobs                          # every source
  python -m pipeline.collect_jobs --source sbc --dry-run   # list what's new without reading or saving anything
  python -m pipeline.collect_jobs --days 30 --limit 50     # job boards: only jobs posted/updated in the last 30 days
  python -m pipeline.collect_jobs --verbose                # also show every request and listed job on screen

Sources are the sites whose robots.txt allows it (COLLECTOR_HOW_IT_WORKS.md; left-out sites in COLLECTOR_GAPS.md):
  sbc             jobs.sbc.net job API (WordPress)
  churchstaffing  churchstaffing.com sitemap
  ministrylist    ministrylist.com job sitemaps (Crawl-delay 10 s)
  efca            jobs.efca.org job board
  employers       every church already in the database that hires through Workday, Breezy, BambooHR, Lever,
                  Greenhouse, SmartRecruiters, Recruitee or Workable: all of its open jobs, from the public jobs API

Each new job page is read with fetch_jobs.fetch_one for pay, job type, denomination and church size. Jobs outside the
US, expired jobs and pages that are blocked or fail aren't saved (failed ones are tried again next run). Jobs already in
church_jobs (same url_key) are skipped, so it's safe to run every day.

Every run writes a full log to server/logs/collect_jobs-<date>-<time>.log and ends with a summary and a PROBLEMS list that says
when a site seems to have changed, blocked the collector or was down. The exit code is 1 when there are problems.
"""
import argparse
import html
import json
import logging
import re
import sys
import threading
import time
import warnings
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from app.config import DATABASE_URL
from app.db import get_conn
from app.logs import LOG_DIR, script_log
from pipeline.fetch_jobs import DENOMINATIONS, HEADERS, HOST_DELAY, fetch_one, workday_api_url
from pipeline.import_bizdev import to_date, url_key

CRAWL_DELAY = {"ministrylist.com": 10.0}  # from the site's robots.txt
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)  # sitemaps are simple enough for html.parser

log = logging.getLogger("collect_jobs")
LAST_COUNTS = LOG_DIR / "collect_last_counts.json"  # jobs listed per source last run, to spot a sudden drop

STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
    "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming", "PR": "Puerto Rico",
}
_BY_NAME = {v.lower(): k for k, v in STATES.items()}
US_NAMES = {"us", "usa", "u.s.", "u.s.a.", "united states", "united states of america"}

# An employer counts as a church by name; the second pattern drops look-alikes (hospitals, schools, senior housing).
CHURCH_RE = re.compile(r"church|chapel|parish|cathedral|fellowship|congregation|diocese|ministr|tabernacle|bible", re.I)
NOT_CHURCH_RE = re.compile(r"residence|hospital|health|senior living|universit|college|school|academy", re.I)


# ---------- problems ----------

ADVICE = {
    "site changed": "The site no longer looks the way the collector expects. Open the address above in a browser to see "
                    "what changed, then update the '{source}' part of pipeline/collect_jobs.py.",
    "blocked": "The site refused the collector. It may have added bot protection or changed its robots.txt. Check that "
               "it still allows crawling (JOB_SITES.md) before trying again.",
    "site down": "The site didn't answer or had a server error. Usually temporary: the next run tries again. "
                 "If it keeps happening for days, check the site.",
    "database": "Saving to the database failed. Check DATABASE_URL and that the database is up.",
}


class SiteProblem(Exception):
    """A failure a person has to look at. kind is one of ADVICE's keys."""

    def __init__(self, kind, url, detail):
        super().__init__(f"{kind}: {detail} ({url})")
        self.kind, self.url, self.detail = kind, url, detail


def http_problem(status):
    """An HTTP status -> the kind of problem it means, or None when it's fine."""
    if status < 400:
        return None
    if status in (401, 403, 429):
        return "blocked"
    if status >= 500:
        return "site down"
    return "site changed"  # 404, 410 and other 4xx: the address or API no longer works as it did


def source_health(name, st, last, days):
    """Signs that a source broke even though no request failed. st: this run's counts; last: last run's listed count."""
    out = []
    if st["listed"] == 0 and name != "employers":
        out.append(("site changed", f"listed 0 jobs. The collector no longer finds jobs where it looks "
                                    f"(or the site had none in the last {days} days)"))
    elif last and last >= 20 and st["listed"] < last * 0.2:
        out.append(("site changed", f"listed only {st['listed']} jobs, down from {last} on the last run"))
    if st["listed"] >= 5 and st["listed_no_title"] > st["listed"] / 2 and name not in ("churchstaffing", "ministrylist"):
        out.append(("site changed", f"{st['listed_no_title']} of {st['listed']} listed jobs have no title"))
    read = st["read"]
    if read >= 5:
        if st["no_details"] >= read / 2:
            out.append(("site changed", f"{st['no_details']} of {read} job pages had no job details (no title found)"))
        if st["blocked"] >= read / 2:
            out.append(("blocked", f"{st['blocked']} of {read} job pages were blocked"))
        if st["failed"] >= read / 2:
            out.append(("site down", f"{st['failed']} of {read} job pages failed to load"))
    return out


# ---------- US locations ----------

def state_code(value):
    """'TX', 'Texas' or 'tx' -> 'TX'; anything else -> None."""
    v = (value or "").strip()
    return v.upper() if v.upper() in STATES else _BY_NAME.get(v.lower())


def split_place(text):
    """'Macomb, IL' / '724 W 11th St, Alma, GA 31510' / 'Austin, Texas, United States' -> (city, state code, country)."""
    parts = [re.sub(r"\s*\b\d{5}(-\d{4})?$", "", p.strip()) for p in (text or "").split(",")]  # drop ZIP codes
    parts = [p for p in parts if p]
    country = parts.pop() if parts and parts[-1].lower() in US_NAMES else None
    st = None
    if parts:
        st = state_code(parts[-1])
        if st:
            parts.pop()
        else:  # "Dawsonville GA": state code at the end of the last part
            head, _, tail = parts[-1].rpartition(" ")
            if head and tail.isupper() and (st := state_code(tail)):
                parts[-1] = head
    city = (parts[-1] if st else parts[0]) if parts else None  # the city sits just before a US state
    return city, st, ("US" if country or st else None)


def is_us(state, country):
    """False only when the job is known to be outside the US; unknown places are kept (all sources are US-based)."""
    if country and country.strip().lower() not in US_NAMES:
        return False
    return not (state and not state_code(state) and not country)


# ---------- requests ----------

def _req(s, url, method="GET", **kw):
    """One logged request; raises SiteProblem for anything but a normal answer."""
    s.last_url = url
    t = time.time()
    try:
        r = s.request(method, url, timeout=30, **kw)  # job lists and sitemaps are bigger than a job page
    except requests.RequestException as e:
        log.debug("%s %s -> no answer (%s)", method, url, e.__class__.__name__)
        raise SiteProblem("site down", url, f"no answer ({e.__class__.__name__})") from e
    log.debug("%s %s -> HTTP %s, %s bytes, %.1fs", method, r.url, r.status_code, f"{len(r.content):,}", time.time() - t)
    if kind := http_problem(r.status_code):
        raise SiteProblem(kind, r.url, f"HTTP {r.status_code}")
    return r


def _json(r):
    try:
        return json.loads(r.content.decode("utf-8-sig"))  # some replies start with a byte-order mark
    except ValueError as e:
        raise SiteProblem("site changed", r.url, "the reply is no longer JSON") from e


def _sitemap(s, url):
    """[(loc, lastmod date or None)] from one sitemap file."""
    soup = BeautifulSoup(_req(s, url).text, "html.parser")
    urls = soup.find_all("url")
    log.debug("sitemap %s: %d links", url, len(urls))
    return [(u.loc.text.strip(), to_date((u.lastmod.text if u.lastmod else "")[:10] or None)) for u in urls if u.loc]


# ---------- sources: (session, since, report) -> listed jobs ----------
# A job may carry "updated" (a date): the caller drops it when older than --days.

def sbc(s, since, report):
    page = 1
    while True:
        r = _req(s, "https://jobs.sbc.net/wp-json/wp/v2/job-listings",
                 params={"per_page": 100, "page": page, "after": f"{since}T00:00:00", "orderby": "date"})
        items = _json(r)
        log.info("[sbc] API page %d of %s: %d jobs", page, r.headers.get("X-WP-TotalPages", "?"), len(items))
        for j in items:
            m = j.get("meta") or {}
            if m.get("_filled"):
                log.debug("[sbc] skipped, marked filled: %s", j["link"])
                continue
            city, st, country = split_place(m.get("_job_location"))
            yield {"url": j["link"], "title": html.unescape(j["title"]["rendered"]), "org": m.get("_company_name"),
                   "org_website": m.get("_company_website"), "city": city, "state": st, "country": country,
                   "date_posted": to_date(j["date"][:10]), "denomination": "Southern Baptist"}  # the SBC's own job board
        if page >= int(r.headers.get("X-WP-TotalPages", 1)):
            return
        page += 1


def churchstaffing(s, since, report):
    for loc, mod in _sitemap(s, "https://www.churchstaffing.com/sitemap.xml"):
        if "/job/" in loc:
            yield {"url": loc, "updated": mod}


def ministrylist(s, since, report):
    index = BeautifulSoup(_req(s, "https://ministrylist.com/sitemap_index.xml").text, "html.parser")
    maps = [sm.text.strip() for sm in index.find_all("loc") if "job_listing-sitemap" in sm.text]
    log.info("[ministrylist] %d job sitemaps", len(maps))
    for sm in maps:
        time.sleep(CRAWL_DELAY["ministrylist.com"])
        for loc, mod in _sitemap(s, sm):
            if "/job/" in loc:
                yield {"url": loc, "updated": mod}


def efca(s, since, report):
    soup = BeautifulSoup(_req(s, "https://jobs.efca.org/").text, "html.parser")
    for card in soup.select('a.job[href^="/jobs/"]'):
        bits = list(card.stripped_strings)  # title, category, job type, church, "City, ST"
        city, st, country = split_place(bits[-1] if len(bits) >= 5 else "")
        yield {"url": "https://jobs.efca.org" + card["href"], "title": bits[0] if bits else None,
               "org": bits[-2] if len(bits) >= 5 else None, "city": city, "state": st, "country": country,
               "denomination": "Evangelical Free"}  # the EFCA's own job board


# Each lister: (session, base) -> jobs; base is the employer's job site host or account name.
def _breezy(s, host):
    for j in _json(_req(s, f"https://{host}/json")):
        loc = j.get("location") or {}
        yield {"url": j["url"], "title": j.get("name"), "city": loc.get("city"), "state": (loc.get("state") or {}).get("id"),
               "country": (loc.get("country") or {}).get("id"), "hours": (j.get("type") or {}).get("name"),
               "date_posted": to_date((j.get("published_date") or "")[:10] or None)}


def _bamboohr(s, host):
    for j in _json(_req(s, f"https://{host}/careers/list")).get("result", []):
        loc = j.get("location") or {}
        ats = j.get("atsLocation") or {}
        yield {"url": f"https://{host}/careers/{j['id']}", "title": j.get("jobOpeningName"), "city": loc.get("city") or ats.get("city"),
               "state": state_code(loc.get("state") or ats.get("state")), "country": ats.get("country"),
               "hours": j.get("employmentStatusLabel")}


def _lever(s, account):
    for j in _json(_req(s, f"https://api.lever.co/v0/postings/{account}", params={"mode": "json"})):
        city, st, _ = split_place((j.get("categories") or {}).get("location"))
        yield {"url": j["hostedUrl"], "title": j.get("text"), "city": city, "state": st, "country": j.get("country"),
               "hours": (j.get("categories") or {}).get("commitment")}


def _greenhouse(s, account):
    for j in _json(_req(s, f"https://boards-api.greenhouse.io/v1/boards/{account}/jobs")).get("jobs", []):
        city, st, country = split_place((j.get("location") or {}).get("name"))
        yield {"url": j["absolute_url"], "title": j.get("title"), "city": city, "state": st, "country": country}


def _smartrecruiters(s, account):
    offset = 0
    while True:
        d = _json(_req(s, f"https://api.smartrecruiters.com/v1/companies/{account}/postings", params={"limit": 100, "offset": offset}))
        for j in d.get("content", []):
            loc = j.get("location") or {}
            yield {"url": f"https://jobs.smartrecruiters.com/{account}/{j['id']}", "title": j.get("name"), "city": loc.get("city"),
                   "state": state_code(loc.get("region")), "country": loc.get("country")}
        offset += 100
        if offset >= d.get("totalFound", 0):
            return


def _recruitee(s, host):
    for j in _json(_req(s, f"https://{host}/api/offers/")).get("offers", []):
        yield {"url": j["careers_url"], "title": j.get("title"), "city": j.get("city"), "state": j.get("state_code"),
               "country": j.get("country_code"), "date_posted": to_date((j.get("published_at") or "")[:10] or None)}


def _workable(s, account):
    for j in _json(_req(s, f"https://apply.workable.com/api/v1/widget/accounts/{account}")).get("jobs", []):
        yield {"url": j["url"], "title": j.get("title"), "city": j.get("city"), "state": state_code(j.get("state")),
               "country": j.get("country"), "hours": j.get("employment_type"), "date_posted": to_date(j.get("published_on"))}


def _workday(s, base):
    """base = an existing job URL of this employer; the site name is taken from it."""
    api = workday_api_url(base)
    host = urlsplit(base).netloc
    site = api.split("/")[6]
    offset = 0
    while True:
        d = _json(_req(s, api.split("/job/")[0] + "/jobs", method="POST", headers={"Accept": "application/json"},
                       json={"limit": 20, "offset": offset, "searchText": "", "appliedFacets": {}}))
        for j in d.get("jobPostings", []):
            city, st, country = split_place(j.get("locationsText"))
            yield {"url": f"https://{host}/{site}{j['externalPath']}", "title": j.get("title"), "city": city, "state": st, "country": country}
        offset += 20
        if offset >= d.get("total", 0) or not d.get("jobPostings"):
            return


PLATFORMS = {_breezy: "Breezy", _bamboohr: "BambooHR", _recruitee: "Recruitee", _lever: "Lever", _greenhouse: "Greenhouse",
             _smartrecruiters: "SmartRecruiters", _workable: "Workable", _workday: "Workday"}
FORMAT_ERRORS = (KeyError, IndexError, TypeError, AttributeError, ValueError)  # a reply missing what the parser expects


def format_problem(s, e):
    detail = f"the reply no longer has the field {e}" if isinstance(e, KeyError) else \
        f"the reply's format changed ({e.__class__.__name__}: {e})"
    return SiteProblem("site changed", s.last_url, detail)


def employer_sites(rows):
    """[(lister, base, org)] for church employers on a hiring system with a public jobs API, one per employer."""
    seen, out = set(), []
    for org, url in rows:
        if not url or not org or not CHURCH_RE.search(org) or NOT_CHURCH_RE.search(org):
            continue
        url = url if url.startswith("http") else "https://" + url  # feed links are stored without a scheme
        p = urlsplit(url)
        host, first = p.netloc.lower(), ([x for x in p.path.split("/") if x] or [""])[0]
        if host.endswith(".breezy.hr"):
            hit = (_breezy, host)
        elif host.endswith(".bamboohr.com"):
            hit = (_bamboohr, host)
        elif host.endswith(".recruitee.com"):
            hit = (_recruitee, host)
        elif host == "jobs.lever.co" and first:
            hit = (_lever, first)
        elif "greenhouse.io" in host and first:
            hit = (_greenhouse, first)
        elif host == "jobs.smartrecruiters.com" and first:
            hit = (_smartrecruiters, first)
        elif host == "apply.workable.com" and first:
            hit = (_workable, first)
        elif ".myworkdayjobs.com" in host and workday_api_url(url):
            hit = (_workday, url)
        else:
            continue
        key = (hit[0], host if hit[0] is _workday else hit[1])
        if key not in seen:
            seen.add(key)
            out.append((*hit, org))
    return out


EMPLOYERS_SQL = """SELECT org_name, job_url FROM public.church_jobs
                   UNION SELECT c.company_name, p.post_url FROM public.postings p JOIN public.companies c USING (company_uuid)"""


def employers(s, since, report):
    """One church failing doesn't stop the rest; each failure is logged and kept in report['churches']."""
    with get_conn() as conn:
        sites = employer_sites(conn.execute(EMPLOYERS_SQL).fetchall())
    count = defaultdict(int)
    for lister, _, _ in sites:
        count[PLATFORMS[lister]] += 1
    log.info("[employers] %d churches with a public jobs API: %s", len(sites), ", ".join(f"{n} {p}" for p, n in sorted(count.items(), key=lambda x: -x[1])))
    churches = report.setdefault("churches", [])
    for lister, base, org in sites:
        platform, jobs, problem = PLATFORMS[lister], 0, None
        try:
            for job in lister(s, base):
                jobs += 1
                yield {**job, "org": org}
        except SiteProblem as p:
            problem = p
        except FORMAT_ERRORS as e:
            problem = format_problem(s, e)
        if problem:
            log.warning("[employers] %s (%s): skipped, %s: %s, %s", org, platform, problem.kind, problem.detail, problem.url)
        else:
            log.info("[employers] %s (%s): %d open job%s", org, platform, jobs, "" if jobs == 1 else "s")
        churches.append({"org": org, "platform": platform, "jobs": jobs, "problem": problem})


SOURCES = {"sbc": sbc, "churchstaffing": churchstaffing, "ministrylist": ministrylist, "efca": efca, "employers": employers}


def platform_problems(churches):
    """A hiring system whose every church failed the same way is one problem (its API changed), not many."""
    out = []
    by_platform = defaultdict(list)
    for c in churches:
        by_platform[c["platform"]].append(c)
    for platform, cs in by_platform.items():
        failed = [c["problem"] for c in cs if c["problem"]]
        if len(cs) >= 3 and len(failed) == len(cs):
            kinds = {p.kind for p in failed}
            out.append(SiteProblem(kinds.pop() if len(kinds) == 1 else "site changed", failed[0].url,
                                   f"{platform}: all {len(cs)} churches failed ({failed[0].detail})"))
    return out


# ---------- reading and saving ----------

INSERT = """INSERT INTO public.church_jobs (url_key, job_url, job_title, org_name, org_website, city, state, date_posted,
        salary_min, salary_max, salary_period, hours, remote, denomination, church_size,
        sheets, fetch_status, fetched_at, last_live_at, added_via)
    VALUES (%(key)s, %(url)s, %(title)s, %(org)s, %(org_website)s, %(city)s, %(state)s, %(date_posted)s,
        %(lo)s, %(hi)s, %(period)s, %(hours)s, %(remote)s, %(denomination)s, %(church_size)s,
        ARRAY['Auto-collected'], %(status)s, now(), CASE WHEN %(status)s = 'ok' THEN now() END, 'collector')
    ON CONFLICT (url_key) DO NOTHING"""


def read_job(job):
    """Fill a listed job from its own page. Returns (status, row) — row is None when it shouldn't be saved.
    status: ok | unknown (page needs a browser) | expired | blocked | error | not US | no details."""
    status, page = fetch_one(job["url"], job.get("org"))
    if status not in ("ok", "unknown"):
        return status, None
    row = {**{k: job.get(k) for k in ("title", "org", "org_website", "city", "state", "country", "date_posted", "hours")}}
    for k in ("title", "org", "org_website", "city", "state", "country", "hours"):  # the listing wins; the page fills gaps
        row[k] = row[k] or page.get(k)
    if not row["title"]:
        return "no details", None
    if not (row["city"] or row["state"]) and page.get("place"):
        row["city"], row["state"], row["country"] = split_place(page["place"])
    row["date_posted"] = row["date_posted"] or to_date((page.get("date_posted") or "")[:10] or None)
    row["state"] = state_code(row["state"]) or row["state"]
    # The page was read before its church name was known (sitemap sources), so match the name now.
    denomination = job.get("denomination") or page.get("denomination") or \
        next((name for rx, name in DENOMINATIONS if rx.search(row["org"] or "")), None)
    if not is_us(row["state"], row["country"]):
        return "not US", None
    lo, hi, period = page.get("salary") or (None, None, None)
    return status, {**row, "key": url_key(job["url"]), "url": job["url"], "lo": lo, "hi": hi, "period": period,
                    "remote": page.get("remote"), "denomination": denomination, "church_size": page.get("church_size")}


def describe(row):
    """One readable line for the log."""
    pay = f"${row['lo']:,.0f}–{row['hi']:,.0f}/{row['period']}" if row["lo"] is not None else "no pay listed"
    place = ", ".join(x for x in (row["city"], row["state"]) if x) or "no location"
    size = f"{row['church_size']:,}+ attendance" if row["church_size"] else None
    return " | ".join(x for x in (row["title"], row["org"] or "no church name", place, pay, row["hours"], row["denomination"], size) if x)


# ---------- run ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=SOURCES, action="append", help="repeatable; default: every source")
    ap.add_argument("--days", type=int, default=45, help="job boards: skip jobs posted/updated longer ago than this")
    ap.add_argument("--limit", type=int, help="read at most this many new jobs")
    ap.add_argument("--dry-run", action="store_true", help="only list new jobs; don't read their pages or save")
    ap.add_argument("--verbose", action="store_true", help="also show every request and listed job on screen (always in the log file)")
    args = ap.parse_args()
    since = date.today() - timedelta(days=args.days)
    names = args.source or list(SOURCES)
    log_path = script_log("collect_jobs", args.verbose)
    started = time.time()

    log.info("=" * 78)
    log.info("Church job collector: %s", "DRY RUN (nothing is read or saved)" if args.dry_run else "collecting and saving")
    log.info("Sources: %s | job boards look back %d days (since %s)%s", ", ".join(names), args.days, since,
             f" | at most {args.limit} jobs read" if args.limit else "")
    log.info("Database: %s | log file: %s", urlsplit(DATABASE_URL).hostname, log_path)
    log.info("=" * 78)

    problems, report = [], {}
    stats = {n: defaultdict(int) for n in names}
    try:
        with get_conn() as conn:
            known = {r[0] for r in conn.execute("SELECT url_key FROM public.church_jobs").fetchall()}
    except Exception as e:
        log.error("Can't read the database: %s", e)
        log.error(ADVICE["database"])
        sys.exit(1)
    log.info("church_jobs already holds %s jobs; those are skipped", f"{len(known):,}")

    s = requests.Session()
    s.headers.update(HEADERS)
    s.last_url = None
    new = []
    for name in names:
        st, t = stats[name], time.time()
        log.info("-" * 78)
        log.info("[%s] listing jobs", name)
        try:
            for job in SOURCES[name](s, since, report):
                st["listed"] += 1
                st["listed_no_title"] += not job.get("title")
                where = ", ".join(x for x in (job.get("city"), job.get("state"), job.get("country")) if x) or "location not listed"
                if job.get("updated") and job["updated"] < since:
                    st["too_old"] += 1
                    verdict = f"older than {args.days} days ({job['updated']})"
                elif not is_us(job.get("state"), job.get("country")):
                    st["not_us"] += 1
                    verdict = "outside the US"
                elif (key := url_key(job["url"])) in known:
                    st["known"] += 1
                    verdict = "already saved"
                else:
                    known.add(key)
                    st["new"] += 1
                    new.append({**job, "source": name})
                    verdict = "NEW"
                log.debug("[%s] listed: %s | %s | %s | %s -> %s", name, job.get("title") or "(title on its page)",
                          job.get("org") or "-", where, job["url"], verdict)
        except SiteProblem as p:
            problems.append((name, p))
            log.error("[%s] STOPPED: %s: %s, %s", name, p.kind, p.detail, p.url)
        except FORMAT_ERRORS as e:
            p = format_problem(s, e)
            problems.append((name, p))
            log.error("[%s] STOPPED: %s: %s, %s", name, p.kind, p.detail, p.url)
        log.info("[%s] %d listed: %d new, %d already saved, %d older than %d days, %d outside the US (%.0fs)", name,
                 st["listed"], st["new"], st["known"], st["too_old"], args.days, st["not_us"], time.time() - t)

    problems += [("employers", p) for p in platform_problems(report.get("churches", []))]
    skipped_churches = [c for c in report.get("churches", []) if c["problem"]]

    if args.limit and len(new) > args.limit:
        log.info("--limit %d: reading %d of %d new jobs; the rest are picked up next run", args.limit, args.limit, len(new))
        new = new[:args.limit]

    if not args.dry_run and new:
        by_host = defaultdict(list)
        for j in new:
            by_host[urlsplit(j["url"]).netloc.lower().removeprefix("www.")].append(j)
        lock, done = threading.Lock(), [0]
        log.info("-" * 78)
        log.info("Reading %d new job pages from %d sites (1 s apart per site, %s)", len(new), len(by_host),
                 ", ".join(f"{h} {d:.0f} s" for h, d in CRAWL_DELAY.items()))

        def run_host(host, jobs):
            with get_conn() as conn:
                for job in jobs:
                    name = job["source"]
                    try:
                        status, row = read_job(job)
                    except Exception as e:  # a parser bug on one odd page shouldn't stop the site
                        status, row = "error", None
                        log.exception("[%s] crashed reading %s: %s", name, job["url"], e)
                    outcome = status
                    if row:
                        try:
                            outcome = "saved" if conn.execute(INSERT, row).rowcount else "already saved"
                        except Exception as e:
                            outcome = "save failed"
                            log.error("[%s] SAVE FAILED %s: %s", name, job["url"], e)
                    with lock:
                        st = stats[name]
                        st["read"] += 1
                        st[{"saved": "saved", "already saved": "known_late", "save failed": "save_failed", "expired": "expired",
                            "blocked": "blocked", "error": "failed", "not US": "not_us_page", "no details": "no_details"}[outcome]] += 1
                        st["unverified"] += outcome == "saved" and status == "unknown"
                        done[0] += 1
                        if outcome == "saved":
                            log.info("[%s] SAVED%s %s | %s", name, " (open/closed not readable)" if status == "unknown" else "", describe(row), job["url"])
                        else:
                            log.info("[%s] not saved, %s: %s", name, {
                                "expired": "job is expired or filled", "blocked": "page blocked the collector",
                                "error": "page failed to load", "not US": "job is outside the US",
                                "no details": "no job title on the page or in the listing", "already saved": "already saved",
                                "save failed": "database error"}[outcome], job["url"])
                        if done[0] % 50 == 0:
                            log.info("... %d of %d job pages read", done[0], len(new))
                    time.sleep(CRAWL_DELAY.get(host, HOST_DELAY))

        with ThreadPoolExecutor(8) as pool:
            futures = [pool.submit(run_host, h, js) for h, js in sorted(by_host.items(), key=lambda p: -len(p[1]))]
        for f in futures:
            if f.exception():
                log.error("A worker stopped: %s", f.exception())
                problems.append(("all", SiteProblem("database", "-", str(f.exception()))))

    # Health checks: a source can break without any request failing.
    try:
        last = json.loads(LAST_COUNTS.read_text())
    except (OSError, ValueError):
        last = {}
    for name in names:
        if any(n == name for n, _ in problems):
            continue  # already explained
        prev = last.get(name, {})
        for kind, detail in source_health(name, stats[name], prev.get("listed") if prev.get("days") == args.days else None, args.days):
            problems.append((name, SiteProblem(kind, "(see the log for its addresses)", detail)))
        if stats[name]["save_failed"]:
            problems.append((name, SiteProblem("database", "-", f"{stats[name]['save_failed']} jobs could not be saved")))
    last.update({n: {"listed": stats[n]["listed"], "days": args.days, "at": f"{datetime.now():%Y-%m-%d %H:%M}"}
                 for n in names if not any(p for p_n, p in problems if p_n == n)})
    LAST_COUNTS.write_text(json.dumps(last, indent=1))

    # Summary
    log.info("=" * 78)
    log.info("SUMMARY%s (%.0f min)", " (dry run)" if args.dry_run else "", (time.time() - started) / 60)
    head = f"{'source':15}{'listed':>7}{'new':>6}{'saved':>7}{'unverif.':>9}{'expired':>8}{'blocked':>8}{'failed':>7}{'no info':>8}{'not US':>7}"
    log.info(head)
    for n in names:
        st = stats[n]
        # extra= fields: one queryable row per source per run in Axiom (event = "source_summary")
        log.info(f"{n:15}{st['listed']:>7}{st['new']:>6}{st['saved']:>7}{st['unverified']:>9}{st['expired']:>8}"
                 f"{st['blocked']:>8}{st['failed']:>7}{st['no_details']:>8}{st['not_us'] + st['not_us_page']:>7}",
                 extra={"event": "source_summary", "source": n, "dry_run": args.dry_run,
                        **{k: st[k] for k in ("listed", "new", "known", "too_old", "saved", "unverified", "expired",
                                              "blocked", "failed", "no_details", "save_failed")},
                        "not_us": st["not_us"] + st["not_us_page"]})
    log.info("saved = added to the BizDev churches tab; unverif. = saved, but the page needs a browser to tell open/closed; "
             "failed and blocked pages are retried next run")
    if skipped_churches:
        log.info("Churches skipped this run (%d of %d):", len(skipped_churches), len(report["churches"]))
        for c in skipped_churches:
            log.info("  - %s (%s): %s, %s", c["org"], c["platform"], c["problem"].kind, c["problem"].detail)

    log.info("=" * 78)
    if not problems:
        log.info("PROBLEMS: none. Every source answered as expected.")
    else:
        log.warning("PROBLEMS: %d need attention", len(problems))
        for i, (name, p) in enumerate(problems, 1):
            log.warning("%d. [%s] %s: %s", i, name, p.kind.upper(), p.detail,
                        extra={"event": "problem", "source": name, "kind": p.kind, "url": p.url})
            log.warning("   Address: %s", p.url)
            log.warning("   What to do: %s", ADVICE[p.kind].format(source=name))
    log.info("Full log: %s", log_path)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
