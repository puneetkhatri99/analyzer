"""Add a job from any URL: read the page, have an LLM extract the job, check it, and look up a missing church size."""

import logging
import re
from datetime import date
from typing import Any

from openai import OpenAI

from app.ai_usage.service import BudgetReached, ensure_budget, record
from app.core.config import get_settings
from app.extraction.page import read_page
from app.extraction.prompts import CHURCH_PROMPT, FENCE_RE, INJECTION_RE, INSTRUCTIONS, WEB_SEARCH_PROMPT
from app.extraction.schemas import ChurchFacts, JobExtraction
from app.extraction.validation import validate
from app.shared.web import UnsafeURLError

log = logging.getLogger("admin")


class ExtractionError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code, self.detail = status_code, detail


MAX_FIGURE_AGE = 8  # years: older attendance figures say little about a church today
LOOKUP_FAILED = "Church size lookup failed"  # starts the note when the search itself broke (retry later)


def figure_doubt(facts: ChurchFacts) -> str | None:
    """Why a looked-up attendance figure can't be trusted, or None. The model sometimes reports a number that isn't
    in its own quote (a typo, or a figure from another sentence), or one from a decades-old article."""
    numbers = {int(n.replace(",", "")) for n in re.findall(r"\d{1,3}(?:,\d{3})+|\d+", facts.evidence or "")}
    size = facts.church_size or 0
    if size not in numbers and not any(abs(n / 52 - size) <= 1 for n in numbers):  # a yearly total / 52 is fine
        return "the number isn't in the quoted source text"
    if facts.year and facts.year < date.today().year - MAX_FIGURE_AGE:
        return f"the figure is from {facts.year}"
    return None


def lookup_church(
    client: Any, job: JobExtraction, url: str = "", admin_email: str | None = None
) -> tuple[JobExtraction, str | None, list[str]]:
    """Fill a missing church size (and denomination) by web search. Returns the job, the source URL, and notes."""
    model = get_settings().openai_model
    place = ", ".join(p for p in (job.city, job.state) if p)
    prompt = CHURCH_PROMPT.format(
        org=job.org_name,
        place=f" in {place}" if place else "",
        site=f" (website: {job.org_website})" if job.org_website else "",
    )
    try:
        ensure_budget()
        response = client.responses.parse(
            model=model, input=prompt, text_format=ChurchFacts, tools=[{"type": "web_search"}], max_tool_calls=3
        )
        record(response, purpose="church_lookup", url=url, model=model, admin_email=admin_email)
        facts = response.output_parsed
    except BudgetReached as e:  # a "failed" lookup: callers try the church again once the limit allows
        log.warning("Church size lookup for %s skipped: %s", job.org_name, e)
        return job, None, [f"{LOOKUP_FAILED} (monthly AI limit reached)."]
    except Exception as e:  # network, quota, bad answer...: extraction carries on without a size
        log.exception("Church size lookup failed for %s (%s)", job.org_name, url)
        return job, None, [f"{LOOKUP_FAILED} ({e.__class__.__name__})."]
    source = (
        facts.source_url if facts and facts.source_url and re.match(r"https?://[^\s]+$", facts.source_url) else None
    )
    # a denomination found online is worth keeping even when attendance isn't
    if facts and facts.denomination and not job.denomination:
        job = job.model_copy(update={"denomination": facts.denomination})
    doubt = facts and facts.church_size is not None and source and figure_doubt(facts)
    if doubt:
        log.warning("Church size lookup for %s: %s not used (%s)", job.org_name, facts.church_size, doubt)
    if not facts or facts.church_size is None or not source or doubt:
        log.info("Church size lookup for %s: not found online", job.org_name)
        return (
            job,
            None,
            ["Church size isn't stated in the posting, and no source online states the church's attendance."],
        )
    log.info("Church size lookup for %s: %s weekly, from %s", job.org_name, f"{facts.church_size:,}", source)
    update: dict[str, Any] = {"church_size": facts.church_size}
    quote = re.sub(r"[\x00-\x1f<>]", " ", facts.evidence or "")[:200]
    notes = [
        f"Church size {facts.church_size:,} was found online, not in the posting: {source}"
        + (f" (“{quote}”)" if quote else "")
        + ". Check it."
    ]
    if facts.church_size > 5000:
        notes.append(
            "That is a very large church. Make sure the figure is weekly attendance, not a yearly total or membership."
        )
    return job.model_copy(update=update), source, notes


def extract(url: str, admin_email: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.openai_api_key:
        raise ExtractionError(503, "OPENAI_API_KEY is not set on the server")
    try:
        ensure_budget()
    except BudgetReached as e:
        raise ExtractionError(429, f"{e}. Raise the limit in Admin → AI costs to add jobs this way.") from e
    log.info("Extract requested by %s: %s", admin_email, url)
    try:
        page = read_page(url)  # every hop of a redirect is checked against private networks
    except UnsafeURLError as e:
        raise ExtractionError(400, str(e)) from e
    log.info(
        "Page %s: %s",
        url,
        f"read directly ({len(page):,} characters)"
        if page
        else "unreadable (blocked or JavaScript-only), using web search",
    )
    warnings = []
    if page:
        method = "page"
        if INJECTION_RE.search(page):
            warnings.append(
                "This page contains text that tries to give instructions to AI tools. Check every value carefully."
            )
        # No tools in this mode: injected text has nothing to act on, and the output is a fixed schema.
        request: dict[str, Any] = {
            "input": f"URL: {url}\n\n<untrusted_page>\n{FENCE_RE.sub(' ', page)}\n</untrusted_page>"
        }
    else:
        # Blocked or JavaScript-only page: let the model read it through web search.
        method = "web_search"
        warnings.append("Read through web search, not directly from the page. Compare with the original before saving.")
        request = {"input": WEB_SEARCH_PROMPT.format(url=url), "tools": [{"type": "web_search"}], "max_tool_calls": 4}
    client = OpenAI(api_key=settings.openai_api_key)
    try:
        result = client.responses.parse(
            model=settings.openai_model, instructions=INSTRUCTIONS, text_format=JobExtraction, **request
        )
        record(result, purpose="extract", url=url, model=settings.openai_model, admin_email=admin_email)
    except Exception as e:  # network, quota, invalid key...
        log.exception("AI extraction failed for %s", url)
        raise ExtractionError(502, f"The AI service failed: {e.__class__.__name__}") from e
    if result.output_parsed is None:
        log.error("AI extraction for %s returned no result", url)
        raise ExtractionError(502, "The AI service returned no result")
    job, checks = validate(result.output_parsed, page)
    church_size_source = None
    if job.page_type == "job_posting" and job.category == "church" and job.church_size is None and job.org_name:
        job, church_size_source, notes = lookup_church(client, job, url, admin_email)
        job, _ = validate(job)  # same range and denomination checks for the looked-up values
        if job.church_size is None:
            church_size_source = None
        warnings += notes
    log.info(
        "Extracted %s via %s: %s | %s | %s | %s | %s%s",
        url,
        method,
        job.page_type,
        job.job_title,
        job.org_name,
        ", ".join(x for x in (job.city, job.state) if x) or "no location",
        f"{job.salary_min}-{job.salary_max}/{job.salary_period}" if job.salary_min else "no pay",
        "".join(f"\n    warning: {w}" for w in warnings + checks),
    )
    return {
        "url": url,
        "method": method,
        "job": job.model_dump(),
        "church_size_source": church_size_source,
        "warnings": warnings + checks,
    }
