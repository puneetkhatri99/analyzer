"""Church job boards whose robots.txt allows collecting (COLLECTOR_HOW_IT_WORKS.md).

Each source: (session, since, report) -> listed jobs. A job may carry "updated" (a date): the run drops it when older
than --days.
"""

import html
import logging
import time
from collections.abc import Iterator
from datetime import date
from typing import Any

from bs4 import BeautifulSoup

from app.ingestion.collector.http import CollectorSession, as_json, get, sitemap
from app.shared.dates import to_date
from app.shared.geo import split_place

CRAWL_DELAY = {"ministrylist.com": 10.0}  # from the site's robots.txt

log = logging.getLogger("collect_jobs")

Job = dict[str, Any]


def sbc(s: CollectorSession, since: date, report: dict[str, Any]) -> Iterator[Job]:
    """jobs.sbc.net job API (WordPress)."""
    page = 1
    while True:
        r = get(
            s,
            "https://jobs.sbc.net/wp-json/wp/v2/job-listings",
            params={"per_page": 100, "page": page, "after": f"{since}T00:00:00", "orderby": "date"},
        )
        items = as_json(r)
        log.info("[sbc] API page %d of %s: %d jobs", page, r.headers.get("X-WP-TotalPages", "?"), len(items))
        for j in items:
            m = j.get("meta") or {}
            if m.get("_filled"):
                log.debug("[sbc] skipped, marked filled: %s", j["link"])
                continue
            city, st, country = split_place(m.get("_job_location"))
            yield {
                "url": j["link"],
                "title": html.unescape(j["title"]["rendered"]),
                "org": m.get("_company_name"),
                "org_website": m.get("_company_website"),
                "city": city,
                "state": st,
                "country": country,
                "date_posted": to_date(j["date"][:10]),
                "denomination": "Southern Baptist",
            }  # the SBC's own board
        if page >= int(r.headers.get("X-WP-TotalPages", 1)):
            return
        page += 1


def churchstaffing(s: CollectorSession, since: date, report: dict[str, Any]) -> Iterator[Job]:
    """churchstaffing.com sitemap."""
    for loc, mod in sitemap(s, "https://www.churchstaffing.com/sitemap.xml"):
        if "/job/" in loc:
            yield {"url": loc, "updated": mod}


def ministrylist(s: CollectorSession, since: date, report: dict[str, Any]) -> Iterator[Job]:
    """ministrylist.com job sitemaps (Crawl-delay 10 s)."""
    index = BeautifulSoup(get(s, "https://ministrylist.com/sitemap_index.xml").text, "html.parser")
    maps = [sm.text.strip() for sm in index.find_all("loc") if "job_listing-sitemap" in sm.text]
    log.info("[ministrylist] %d job sitemaps", len(maps))
    for sm in maps:
        time.sleep(CRAWL_DELAY["ministrylist.com"])
        for loc, mod in sitemap(s, sm):
            if "/job/" in loc:
                yield {"url": loc, "updated": mod}


def efca(s: CollectorSession, since: date, report: dict[str, Any]) -> Iterator[Job]:
    """jobs.efca.org job board."""
    soup = BeautifulSoup(get(s, "https://jobs.efca.org/").text, "html.parser")
    for card in soup.select('a.job[href^="/jobs/"]'):
        bits = list(card.stripped_strings)  # title, category, job type, church, "City, ST"
        city, st, country = split_place(bits[-1] if len(bits) >= 5 else "")
        yield {
            "url": "https://jobs.efca.org" + card["href"],
            "title": bits[0] if bits else None,
            "org": bits[-2] if len(bits) >= 5 else None,
            "city": city,
            "state": st,
            "country": country,
            "denomination": "Evangelical Free",
        }  # the EFCA's own job board
