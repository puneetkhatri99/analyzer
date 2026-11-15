"""US states, the report's regions, and parsing of free-text US places."""

import re

STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
    "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
    "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}  # fmt: skip
# Collected jobs may be in a territory; the public report only covers the states above.
TERRITORIES = {"PR": "Puerto Rico"}

# The brief's six regions, plus Mountain West so every state has one (proposal, client to confirm).
REGIONS = {
    "North East": "CT ME MA NH RI VT NY NJ PA DE MD DC",
    "South East": "VA WV NC SC GA FL KY TN AL MS AR LA",
    "Midwest": "OH IN IL MI WI MN IA MO ND SD NE KS",
    "Southwest": "TX OK NM AZ",
    "West Coast": "CA HI",
    "Pacific Northwest": "WA OR ID AK",
    "Mountain West": "CO UT WY MT NV",
}
REGION_OF = {STATES[code]: region for region, codes in REGIONS.items() for code in codes.split()}

US_NAMES = {"us", "usa", "u.s.", "u.s.a.", "united states", "united states of america"}

_STATE_NAMES = {name.lower(): name for name in STATES.values()}
_CODE_BY_NAME = {name.lower(): code for code, name in (STATES | TERRITORIES).items()}


def state_name(value: str | None) -> str | None:
    """'OH', 'oh' or 'Ohio' -> 'Ohio'; anything that isn't a US state ('Cook', 'N/A', 'Varies') -> None."""
    v = (value or "").strip()
    return STATES.get(v.upper()) or _STATE_NAMES.get(v.lower())


def state_code(value: str | None) -> str | None:
    """'TX', 'Texas' or 'tx' -> 'TX' (territories included); anything else -> None."""
    v = (value or "").strip()
    return v.upper() if v.upper() in STATES or v.upper() in TERRITORIES else _CODE_BY_NAME.get(v.lower())


def split_place(text: str | None) -> tuple[str | None, str | None, str | None]:
    """(city, state code, country) from 'Macomb, IL', '724 W 11th St, Alma, GA 31510' or 'Austin, Texas, USA'."""
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


def is_us(state: str | None, country: str | None) -> bool:
    """False only when the job is known to be outside the US; unknown places are kept (all sources are US-based)."""
    if country and country.strip().lower() not in US_NAMES:
        return False
    return not (state and not state_code(state) and not country)
