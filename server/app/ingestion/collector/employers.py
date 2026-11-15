"""Every church already in the database that hires through Workday, Breezy, BambooHR, Lever, Greenhouse,
SmartRecruiters, Recruitee or Workable: all of its open jobs, from that hiring system's public jobs API."""

import logging
import re
from collections import defaultdict
from collections.abc import Callable, Iterator
from datetime import date
from typing import Any
from urllib.parse import urlsplit

from app.core.db import get_conn
from app.ingestion.collector.http import FORMAT_ERRORS, CollectorSession, as_json, format_problem, get
from app.ingestion.collector.problems import SiteProblem
from app.job_pages.fetcher import workday_api_url
from app.shared.dates import to_date
from app.shared.geo import split_place, state_code
from app.shared.web import with_scheme

log = logging.getLogger("collect_jobs")

Job = dict[str, Any]
Lister = Callable[[CollectorSession, str], Iterator[Job]]

# An employer counts as a church by name; the second pattern drops look-alikes (hospitals, schools, senior housing).
CHURCH_RE = re.compile(r"church|chapel|parish|cathedral|fellowship|congregation|diocese|ministr|tabernacle|bible", re.I)
NOT_CHURCH_RE = re.compile(r"residence|hospital|health|senior living|universit|college|school|academy", re.I)

EMPLOYERS_SQL = """SELECT org_name, job_url FROM public.church_jobs
                   UNION SELECT c.company_name, p.post_url
                   FROM public.postings p JOIN public.companies c USING (company_uuid)"""


# Each lister: (session, base) -> jobs; base is the employer's job site host or account name.
def breezy(s: CollectorSession, host: str) -> Iterator[Job]:
    for j in as_json(get(s, f"https://{host}/json")):
        loc = j.get("location") or {}
        yield {
            "url": j["url"],
            "title": j.get("name"),
            "city": loc.get("city"),
            "state": (loc.get("state") or {}).get("id"),
            "country": (loc.get("country") or {}).get("id"),
            "hours": (j.get("type") or {}).get("name"),
            "date_posted": to_date((j.get("published_date") or "")[:10] or None),
        }


def bamboohr(s: CollectorSession, host: str) -> Iterator[Job]:
    for j in as_json(get(s, f"https://{host}/careers/list")).get("result", []):
        loc = j.get("location") or {}
        ats = j.get("atsLocation") or {}
        yield {
            "url": f"https://{host}/careers/{j['id']}",
            "title": j.get("jobOpeningName"),
            "city": loc.get("city") or ats.get("city"),
            "state": state_code(loc.get("state") or ats.get("state")),
            "country": ats.get("country"),
            "hours": j.get("employmentStatusLabel"),
        }


def lever(s: CollectorSession, account: str) -> Iterator[Job]:
    for j in as_json(get(s, f"https://api.lever.co/v0/postings/{account}", params={"mode": "json"})):
        city, st, _ = split_place((j.get("categories") or {}).get("location"))
        yield {
            "url": j["hostedUrl"],
            "title": j.get("text"),
            "city": city,
            "state": st,
            "country": j.get("country"),
            "hours": (j.get("categories") or {}).get("commitment"),
        }


def greenhouse(s: CollectorSession, account: str) -> Iterator[Job]:
    for j in as_json(get(s, f"https://boards-api.greenhouse.io/v1/boards/{account}/jobs")).get("jobs", []):
        city, st, country = split_place((j.get("location") or {}).get("name"))
        yield {"url": j["absolute_url"], "title": j.get("title"), "city": city, "state": st, "country": country}


def smartrecruiters(s: CollectorSession, account: str) -> Iterator[Job]:
    offset = 0
    while True:
        d = as_json(
            get(
                s,
                f"https://api.smartrecruiters.com/v1/companies/{account}/postings",
                params={"limit": 100, "offset": offset},
            )
        )
        for j in d.get("content", []):
            loc = j.get("location") or {}
            yield {
                "url": f"https://jobs.smartrecruiters.com/{account}/{j['id']}",
                "title": j.get("name"),
                "city": loc.get("city"),
                "state": state_code(loc.get("region")),
                "country": loc.get("country"),
            }
        offset += 100
        if offset >= d.get("totalFound", 0):
            return


def recruitee(s: CollectorSession, host: str) -> Iterator[Job]:
    for j in as_json(get(s, f"https://{host}/api/offers/")).get("offers", []):
        yield {
            "url": j["careers_url"],
            "title": j.get("title"),
            "city": j.get("city"),
            "state": j.get("state_code"),
            "country": j.get("country_code"),
            "date_posted": to_date((j.get("published_at") or "")[:10] or None),
        }


def workable(s: CollectorSession, account: str) -> Iterator[Job]:
    for j in as_json(get(s, f"https://apply.workable.com/api/v1/widget/accounts/{account}")).get("jobs", []):
        yield {
            "url": j["url"],
            "title": j.get("title"),
            "city": j.get("city"),
            "state": state_code(j.get("state")),
            "country": j.get("country"),
            "hours": j.get("employment_type"),
            "date_posted": to_date(j.get("published_on")),
        }


def workday(s: CollectorSession, base: str) -> Iterator[Job]:
    """base = an existing job URL of this employer; the site name is taken from it."""
    api = workday_api_url(base)
    host = urlsplit(base).netloc
    site = api.split("/")[6]
    offset = 0
    while True:
        d = as_json(
            get(
                s,
                api.split("/job/")[0] + "/jobs",
                method="POST",
                headers={"Accept": "application/json"},
                json={"limit": 20, "offset": offset, "searchText": "", "appliedFacets": {}},
            )
        )
        for j in d.get("jobPostings", []):
            city, st, country = split_place(j.get("locationsText"))
            yield {
                "url": f"https://{host}/{site}{j['externalPath']}",
                "title": j.get("title"),
                "city": city,
                "state": st,
                "country": country,
            }
        offset += 20
        if offset >= d.get("total", 0) or not d.get("jobPostings"):
            return


PLATFORMS: dict[Lister, str] = {
    breezy: "Breezy", bamboohr: "BambooHR", recruitee: "Recruitee", lever: "Lever", greenhouse: "Greenhouse",
    smartrecruiters: "SmartRecruiters", workable: "Workable", workday: "Workday",
}  # fmt: skip


def _lister_for(url: str) -> tuple[Lister, str] | None:
    p = urlsplit(url)
    host, first = p.netloc.lower(), ([x for x in p.path.split("/") if x] or [""])[0]
    if host.endswith(".breezy.hr"):
        return breezy, host
    if host.endswith(".bamboohr.com"):
        return bamboohr, host
    if host.endswith(".recruitee.com"):
        return recruitee, host
    if host == "jobs.lever.co" and first:
        return lever, first
    if "greenhouse.io" in host and first:
        return greenhouse, first
    if host == "jobs.smartrecruiters.com" and first:
        return smartrecruiters, first
    if host == "apply.workable.com" and first:
        return workable, first
    if ".myworkdayjobs.com" in host and workday_api_url(url):
        return workday, url
    return None


def employer_sites(rows: list[tuple[str | None, str | None]]) -> list[tuple[Lister, str, str]]:
    """[(lister, base, org)] for church employers on a hiring system with a public jobs API, one per employer."""
    seen, out = set(), []
    for org, url in rows:
        if not url or not org or not CHURCH_RE.search(org) or NOT_CHURCH_RE.search(org):
            continue
        url = with_scheme(url)  # feed links are stored without a scheme
        if not (hit := _lister_for(url)):
            continue
        lister, base = hit
        key = (lister, urlsplit(url).netloc.lower() if lister is workday else base)
        if key not in seen:
            seen.add(key)
            out.append((lister, base, org))
    return out


def employers(s: CollectorSession, since: date, report: dict[str, Any]) -> Iterator[Job]:
    """One church failing doesn't stop the rest; each failure is logged and kept in report['churches']."""
    with get_conn() as conn:
        sites = employer_sites(conn.execute(EMPLOYERS_SQL).fetchall())
    count: dict[str, int] = defaultdict(int)
    for lister, _, _ in sites:
        count[PLATFORMS[lister]] += 1
    log.info(
        "[employers] %d churches with a public jobs API: %s",
        len(sites),
        ", ".join(f"{n} {p}" for p, n in sorted(count.items(), key=lambda x: -x[1])),
    )
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
            log.warning(
                "[employers] %s (%s): skipped, %s: %s, %s", org, platform, problem.kind, problem.detail, problem.url
            )
        else:
            log.info("[employers] %s (%s): %d open job%s", org, platform, jobs, "" if jobs == 1 else "s")
        churches.append({"org": org, "platform": platform, "jobs": jobs, "problem": problem})
