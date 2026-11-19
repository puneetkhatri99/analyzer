"""Turning a job page into prompt text: structured JobPosting data first, then the visible text, hidden text removed."""

import json

import requests
from bs4 import BeautifulSoup

from app.extraction.prompts import HIDDEN
from app.job_pages.fetcher import MIN_READABLE_CHARS, is_workday, workday_api_url
from app.job_pages.parser import job_postings
from app.shared.web import BLOCKED_RE, HEADERS, get_public

MAX_PAGE_CHARS = 15_000  # enough for any job description; keeps the prompt cheap
NOISE_TAGS = ["script", "style", "noscript", "svg", "nav", "header", "footer", "form", "template", "iframe"]


def page_text(html: str) -> str | None:
    """Prompt text for an HTML page; None if it is too thin to read."""
    soup = BeautifulSoup(html, "html.parser")
    structured = list(job_postings(soup))
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    for tag in soup.select(HIDDEN) + soup(NOISE_TAGS):  # hidden text is where instructions for AI readers hide
        tag.decompose()
    text = " ".join(soup.get_text(" ").split())
    if len(text) < MIN_READABLE_CHARS and not structured:
        return None
    parts = [f"Page title: {title}"]
    if structured:
        parts.append(f"Structured JobPosting data:\n{json.dumps(structured, default=str)[: MAX_PAGE_CHARS // 2]}")
    parts.append(f"Visible page text:\n{text[:MAX_PAGE_CHARS]}")
    return "\n\n".join(parts)


def read_page(url: str) -> str | None:
    """The page as prompt text, or None when it can't be read directly (blocked, JavaScript-only, error).
    Raises UnsafeURLError when the URL, or any page it redirects to, is in a private network."""
    workday = workday_api_url(url) if is_workday(url) else None
    accept = "application/json" if workday else "text/html,*/*"
    try:
        r = get_public(workday or url, headers={**HEADERS, "Accept": accept}, timeout=20)
    except requests.RequestException:
        return None
    if r.status_code >= 400 or BLOCKED_RE.search(r.text[:3000]):
        return None
    if workday:
        return f"Workday job data (JSON):\n{r.text[:MAX_PAGE_CHARS]}"
    return page_text(r.text)
