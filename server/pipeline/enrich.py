"""Salary parsing for the church jobs feed's comp_range text."""
import re

_RANGE_RE = re.compile(r"([\d,.]+)\s*-\s*([\d,.]+)\s*per\s*(year|hour)", re.I)
_SINGLE_RE = re.compile(r"([\d,.]+)\s*per\s*(year|hour)", re.I)


def parse_salary(comp_range: str | None) -> dict:
    """Parse '85000-100000 per year' / '17-22.5 per hour' / '70304 per year' into min/max/period."""
    if not comp_range:
        return {"salary_min": None, "salary_max": None, "salary_period": None}
    comp_range = str(comp_range)

    m = _RANGE_RE.search(comp_range)
    if m:
        lo, hi, period = m.groups()
        return {
            "salary_min": float(lo.replace(",", "")),
            "salary_max": float(hi.replace(",", "")),
            "salary_period": period.lower(),
        }

    m = _SINGLE_RE.search(comp_range)
    if m:
        val, period = m.groups()
        val = float(val.replace(",", ""))
        return {"salary_min": val, "salary_max": val, "salary_period": period.lower()}

    return {"salary_min": None, "salary_max": None, "salary_period": None}
