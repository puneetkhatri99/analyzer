from datetime import date, datetime
from typing import Any

FORMATS = ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y")


def to_date(value: Any) -> date | None:
    """A date from a spreadsheet cell or text ('10/22/2026', '2026-10-22'); None when unreadable or before 2000."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    for fmt in FORMATS:
        try:
            d = datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
        return d if d.year >= 2000 else None  # typos like 10/22/0202
    return None
