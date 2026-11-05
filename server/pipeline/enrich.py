import re

from anthropic import Anthropic

from app.config import ANTHROPIC_API_KEY
from app.roles import CANONICAL_ROLES

MODEL = "claude-haiku-5-5"
_client = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def _tool_call(system: str, user: str, tool_name: str, tool_schema: dict) -> dict:
    client = _get_client()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=system,
        messages=[{"role": "user", "content": user}],
        tools=[{"name": tool_name, "input_schema": tool_schema}],
        tool_choice={"type": "tool", "name": tool_name},
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input
    return {}


def classify_title(raw_title: str) -> tuple[str, float]:
    """Map a raw job title to one of CANONICAL_ROLES."""
    result = _tool_call(
        system=(
            "You classify church job titles into a fixed taxonomy. "
            f"Valid roles: {', '.join(CANONICAL_ROLES)}. "
            "Pick the closest match; use 'Other' only if nothing fits."
        ),
        user=f"Job title: {raw_title}",
        tool_name="classify_role",
        tool_schema={
            "type": "object",
            "properties": {
                "canonical_role": {"type": "string", "enum": CANONICAL_ROLES},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["canonical_role", "confidence"],
        },
    )
    role = result.get("canonical_role", "Other")
    if role not in CANONICAL_ROLES:
        role = "Other"
    return role, float(result.get("confidence", 0.0))


def extract_church_info(company_name: str, job_description_text: str, website_text: str | None) -> dict:
    """Infer denomination and church size (avg weekly attendance) from available text.
    Returns {"denomination": str|None, "church_size": int|None, "church_size_source": "stated"|"inferred"|None}.
    """
    context = f"Church/organization name: {company_name}\n\nJob posting text:\n{job_description_text[:3000]}"
    if website_text:
        context += f"\n\nChurch website text:\n{website_text[:3000]}"

    result = _tool_call(
        system=(
            "You extract two facts about a church from the provided text: its denomination "
            "(e.g. Baptist, Methodist, Non-denominational, Catholic, Lutheran, Presbyterian, Pentecostal, "
            "Assemblies of God, etc.) and its approximate size (average weekly attendance, as a single integer). "
            "Only report what is explicitly stated or very strongly implied (e.g. the church name contains the "
            "denomination). If you cannot determine a fact confidently, return null for it -- do not guess."
        ),
        user=context,
        tool_name="report_church_info",
        tool_schema={
            "type": "object",
            "properties": {
                "denomination": {"type": ["string", "null"]},
                "church_size": {"type": ["integer", "null"]},
                "church_size_source": {
                    "type": ["string", "null"],
                    "enum": ["stated", "inferred", None],
                },
            },
            "required": ["denomination", "church_size", "church_size_source"],
        },
    )
    return result


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
