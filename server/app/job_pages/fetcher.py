"""Fetching one job page and deciding whether the job is open: ok | expired | unknown | blocked | error."""

import logging
import re
import time
from typing import Any
from urllib.parse import urlsplit

import requests

from app.job_pages.parser import EXPIRED_RE, parse_page
from app.shared.web import BLOCKED_RE, HEADERS, with_scheme

TIMEOUT = 15
HOST_DELAY = 1.0  # seconds between requests to the same site

log = logging.getLogger("job_pages")

Result = tuple[str, dict[str, Any]]  # (status, parsed page fields)


def workday_api_url(url: str) -> str | None:
    """Workday job pages are JavaScript shells; the same job is served as JSON at /wday/cxs/<tenant>/<site>/job/..."""
    p = urlsplit(url)
    parts = [x for x in p.path.split("/") if x]
    if parts and re.fullmatch(r"[a-z]{2}-[A-Z]{2}", parts[0]):  # locale prefix, e.g. en-US
        parts = parts[1:]
    if len(parts) < 2 or "job" not in parts:
        return None
    return f"https://{p.netloc}/wday/cxs/{p.netloc.split('.')[0]}/{parts[0]}/" + "/".join(parts[parts.index("job") :])


def check_workday(url: str) -> Result:
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


def fetch_one(url: str, org_name: str | None) -> Result:
    url = with_scheme(url)
    if ".myworkdayjobs.com/" in url:
        status, page = check_workday(url)
        log.debug("GET %s -> %s (Workday job API)", url, status)
        return status, page
    started = time.time()
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException as e:
        log.debug("GET %s -> error: no answer (%s)", url, e.__class__.__name__)
        return "error", {}
    took = f"HTTP {r.status_code}, {len(r.content):,} bytes, {time.time() - started:.1f}s"
    if r.status_code in (404, 410):
        log.debug("GET %s -> expired (%s: page gone)", url, took)
        return "expired", {}
    bot_check = r.status_code == 200 and BLOCKED_RE.search(r.text[:3000]) and len(r.text) < 30000
    if r.status_code in (401, 403, 429, 503) or bot_check:
        log.debug("GET %s -> blocked (%s%s)", url, took, ", bot-check page" if r.status_code == 200 else "")
        return "blocked", {}
    if r.status_code >= 400:
        log.debug("GET %s -> error (%s)", url, took)
        return "error", {}
    page = parse_page(r.text, org_name)
    if EXPIRED_RE.search(page["text"][:5000]) and not page["salary"]:
        log.debug("GET %s -> expired (%s, page says the job is closed)", url, took)
        return "expired", page
    if len(page["text"]) < 400 and not page["structured"]:
        # a JavaScript shell (Paycom, ADP, HRM Direct...): open or closed can't be told
        log.debug("GET %s -> unknown (%s, JavaScript-only page: open or closed can't be told)", url, took)
        return "unknown", page
    log.debug("GET %s -> ok (%s, %s)", url, took, "structured job data" if page["structured"] else "text only")
    return "ok", page
