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

# States that share a border line (corner-only touches like Four Corners excluded). Used to widen a thin state search to
# the states around it before the whole region; Alaska and Hawaii have none.
_BORDERS = {
    "AL": "FL GA MS TN", "AZ": "CA NM NV UT", "AR": "LA MO MS OK TN TX", "CA": "AZ NV OR", "CO": "KS NE NM OK UT WY",
    "CT": "MA NY RI", "DE": "MD NJ PA", "DC": "MD VA", "FL": "AL GA", "GA": "AL FL NC SC TN", "ID": "MT NV OR UT WA WY",
    "IL": "IN IA KY MO WI", "IN": "IL KY MI OH", "IA": "IL MN MO NE SD WI", "KS": "CO MO NE OK",
    "KY": "IL IN MO OH TN VA WV", "LA": "AR MS TX", "ME": "NH", "MD": "DE DC PA VA WV", "MA": "CT NH NY RI VT",
    "MI": "IN OH WI", "MN": "IA ND SD WI", "MS": "AL AR LA TN", "MO": "AR IL IA KS KY NE OK TN",
    "MT": "ID ND SD WY", "NE": "CO IA KS MO SD WY", "NV": "AZ CA ID OR UT", "NH": "MA ME VT", "NJ": "DE NY PA",
    "NM": "AZ CO OK TX", "NY": "CT MA NJ PA VT", "NC": "GA SC TN VA", "ND": "MN MT SD", "OH": "IN KY MI PA WV",
    "OK": "AR CO KS MO NM TX", "OR": "CA ID NV WA", "PA": "DE MD NJ NY OH WV", "RI": "CT MA", "SC": "GA NC",
    "SD": "IA MN MT ND NE WY", "TN": "AL AR GA KY MS MO NC VA", "TX": "AR LA NM OK", "UT": "AZ CO ID NV WY",
    "VT": "MA NH NY", "VA": "DC KY MD NC TN WV", "WA": "ID OR", "WV": "KY MD OH PA VA", "WI": "IL IA MI MN",
    "WY": "CO ID MT NE SD UT",
}  # fmt: skip
NEIGHBOURS = {STATES[c]: frozenset(STATES[n] for n in ns.split()) for c, ns in _BORDERS.items()}

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
