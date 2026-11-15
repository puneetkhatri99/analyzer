"""Logged requests for the collector: every failure becomes a SiteProblem saying what a person should check."""

import json
import logging
import time
import warnings
from datetime import date
from typing import Any

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from app.ingestion.collector.problems import SiteProblem, http_problem
from app.shared.dates import to_date
from app.shared.web import HEADERS

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)  # sitemaps are simple enough for html.parser

# A reply missing what a parser expects.
FORMAT_ERRORS = (KeyError, IndexError, TypeError, AttributeError, ValueError)

log = logging.getLogger("collect_jobs")


class CollectorSession(requests.Session):
    """A session that remembers the last address it asked for, so a parse error can say where it happened."""

    def __init__(self) -> None:
        super().__init__()
        self.headers.update(HEADERS)
        self.last_url: str | None = None


def get(s: CollectorSession, url: str, method: str = "GET", **kw: Any) -> requests.Response:
    """One logged request; raises SiteProblem for anything but a normal answer."""
    s.last_url = url
    started = time.time()
    try:
        r = s.request(method, url, timeout=30, **kw)  # job lists and sitemaps are bigger than a job page
    except requests.RequestException as e:
        log.debug("%s %s -> no answer (%s)", method, url, e.__class__.__name__)
        raise SiteProblem("site down", url, f"no answer ({e.__class__.__name__})") from e
    log.debug(
        "%s %s -> HTTP %s, %s bytes, %.1fs", method, r.url, r.status_code, f"{len(r.content):,}", time.time() - started
    )
    if kind := http_problem(r.status_code):
        raise SiteProblem(kind, r.url, f"HTTP {r.status_code}")
    return r


def as_json(r: requests.Response) -> Any:
    try:
        return json.loads(r.content.decode("utf-8-sig"))  # some replies start with a byte-order mark
    except ValueError as e:
        raise SiteProblem("site changed", r.url, "the reply is no longer JSON") from e


def sitemap(s: CollectorSession, url: str) -> list[tuple[str, date | None]]:
    """[(loc, lastmod date or None)] from one sitemap file."""
    soup = BeautifulSoup(get(s, url).text, "html.parser")
    urls = soup.find_all("url")
    log.debug("sitemap %s: %d links", url, len(urls))
    return [(u.loc.text.strip(), to_date((u.lastmod.text if u.lastmod else "")[:10] or None)) for u in urls if u.loc]


def format_problem(s: CollectorSession, e: Exception) -> SiteProblem:
    detail = (
        f"the reply no longer has the field {e}"
        if isinstance(e, KeyError)
        else f"the reply's format changed ({e.__class__.__name__}: {e})"
    )
    return SiteProblem("site changed", s.last_url, detail)
