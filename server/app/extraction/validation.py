"""Code-side checks on what the model returned: clear impossible values, note anything the admin should double-check."""

import re
from datetime import date, timedelta

from app.extraction.schemas import JobExtraction
from app.job_pages.parser import denomination_in, sane_pay

TEXT_FIELDS = ("job_title", "org_name", "org_website", "city", "state", "country", "denomination", "reason")
GENERIC_DENOMINATIONS = ("christian", "protestant", "evangelical christian")


def found_on_page(value: str | float, text: str) -> bool:
    """Is a value the model returned actually on the page? (Words for text, digits for numbers.)"""
    if isinstance(value, (int, float)):
        n = int(value)
        forms = {str(n), f"{n:,}", f"{n // 1000}k"} if n >= 1000 else {str(n), f"{value:g}"}
        return any(f in text for f in forms)
    words = [w for w in re.findall(r"[a-z0-9]+", value.lower()) if len(w) > 2]
    return not words or sum(w in text for w in words) / len(words) >= 0.6


def complete_pay(lo: float | None, hi: float | None, period: str | None) -> tuple[float, float, str] | None:
    """A model's pay made whole and checked: one figure fills both ends, a missing period is guessed from the top
    figure (under 200 is hourly, as the feed's parser does). None when there's no pay or it isn't a believable wage."""
    lo = lo if lo is not None else hi
    hi = hi if hi is not None else lo
    if lo is None:
        return None
    return sane_pay(lo, hi, period or ("hour" if hi < 200 else "year"))


def validate(job: JobExtraction, page: str | None = None) -> tuple[JobExtraction, list[str]]:
    warnings: list[str] = []
    if job.page_type != "job_posting":
        return job, warnings
    d = job.model_dump()
    for f in TEXT_FIELDS:
        if d[f] is not None:
            d[f] = re.sub(r"[\x00-\x1f\x7f<>]", " ", d[f]).strip()[: 500 if f == "reason" else 200] or None
    if d["org_website"] and not re.match(r"https?://[^\s/]+\.[^\s]+$", d["org_website"]):
        d["org_website"] = None
    if d["salary_min"] is not None or d["salary_max"] is not None:
        pay = complete_pay(d["salary_min"], d["salary_max"], d["salary_period"])
        if pay is None:
            shown = "–".join(f"{v:g}" for v in (d["salary_min"], d["salary_max"]) if v is not None)
            warnings.append(f"Pay ({shown}) is outside a believable range and was removed.")
            d["salary_min"] = d["salary_max"] = d["salary_period"] = None
        else:
            d["salary_min"], d["salary_max"], d["salary_period"] = pay
    if d["church_size"] is not None and not 1 <= d["church_size"] <= 100_000:
        d["church_size"] = None
    if d["date_posted"]:
        try:
            posted = date.fromisoformat(d["date_posted"])
            plausible = date(2000, 1, 1) <= posted <= date.today() + timedelta(days=1)
            d["date_posted"] = posted.isoformat() if plausible else None
        except ValueError:
            d["date_posted"] = None
    if d["denomination"]:  # map onto the site's denomination names; drop generic labels
        generic = d["denomination"].lower() in GENERIC_DENOMINATIONS
        d["denomination"] = denomination_in(d["denomination"]) or (None if generic else d["denomination"])
    if not d["job_title"]:
        warnings.append("No job title was found.")
    if page:
        text = page.lower()
        for f, label in (("job_title", "Job title"), ("org_name", "Organization")):
            if d[f] and not found_on_page(d[f], text):
                warnings.append(f"{label} “{d[f]}” doesn't appear on the page. Check it.")
        if d["salary_min"] is not None and not (
            found_on_page(d["salary_min"], text) or found_on_page(d["salary_max"], text)
        ):
            warnings.append("The pay figure doesn't appear on the page. Check it.")
    return JobExtraction(**d), warnings
