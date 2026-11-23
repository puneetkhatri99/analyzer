"""A report search that has too little pay data is never answered with "not enough data": it is loosened one step at a
time and the report says what was combined.

Each filter has levels, from what the visitor chose to wider ones:
  location      chosen states -> plus the states that border them -> their region(s) -> nationwide
  church size   chosen bands -> plus the neighbouring bands -> any size
  denomination  chosen -> plus similar denominations (groups.py) -> any
  role          chosen -> plus similar roles (groups.py) -> any
The first widening moves location, church size and denomination one level together (nearby states with neighbouring
sizes and the denomination family); if that is still too thin the area grows to its region, then church size is dropped
(before going nationwide, so the answer stays local), then nationwide, denomination, and role last, so role is kept the
longest. It stops the moment there is enough pay.
The same idea combines thin rows of the report's bar charts (merge_thin).
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from app.shared.geo import NEIGHBOURS, REGION_OF

LOOSEN_ORDER = ("state", "size", "denomination", "role")
LABELS = {"state": "Location", "size": "Church size", "denomination": "Denomination", "role": "Role"}


def join_names(items: Iterable[str]) -> str:
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


@dataclass(frozen=True)
class Level:
    allowed: frozenset[str] | None  # the values a job may have; None = any
    text: str | None = None  # what the visitor is told when this level is used (None for the level they chose)
    scope: str = ""  # location levels only: "state", "region" or "national"
    area: str = ""  # location levels only: the place's name
    shown: str = ""  # what the report now covers, in a few words ("Midwest region", "All roles")


ANY = Level(None)


def location_levels(states: list[str]) -> list[Level]:
    if not states:
        return [Level(None, scope="national", area="nationwide")]
    regions = sorted({REGION_OF[s] for s in states})
    nearby = frozenset(states).union(*(NEIGHBOURS.get(s, ()) for s in states))
    own = frozenset(s for s, r in REGION_OF.items() if r in regions)
    in_regions = own | nearby  # never narrower than nearby

    def text(where: str) -> str:
        return (
            f"Showing {where}. {join_names(states)} data for this role is still limited, "
            "so we widened the search to give you a reliable range."
        )

    levels = [Level(frozenset(states), scope="state", area=join_names(states))]
    if nearby != set(states):
        levels.append(
            Level(
                nearby,
                text(f"{join_names(states)} and the states that border it"),
                "nearby",
                f"{join_names(states)} and nearby states",
                f"{join_names(states)} and nearby states",
            )
        )
    if in_regions != nearby:
        extra = " and nearby states" if in_regions - own else ""
        levels.append(
            Level(
                in_regions,
                text(f"{join_names(regions)} figures"),
                "region",
                join_names(regions) + extra,
                f"{join_names(regions)} {'region' if len(regions) == 1 else 'regions'}{extra}",
            )
        )
    levels.append(Level(None, text("national figures"), "national", "nationwide", "Nationwide"))
    return levels


def size_levels(chosen: list[str], bands: list[str]) -> list[Level]:
    if not chosen:
        return [ANY]
    wider = {
        bands[j]
        for i in (bands.index(c) for c in chosen if c in bands)
        for j in (i - 1, i, i + 1)
        if 0 <= j < len(bands)
    }
    extra = sorted(wider - set(chosen), key=bands.index)
    levels = [Level(frozenset(chosen))]
    if extra and set(wider) != set(bands):  # with two bands the neighbour is every band: skip to "any"
        levels.append(
            Level(
                frozenset(wider | set(chosen)),
                f"We also included neighbouring church sizes ({join_names(extra)}) because too few openings "
                f"list pay for {join_names(chosen)} alone.",
                shown=join_names(sorted(wider, key=bands.index)),
            )
        )
    levels.append(
        Level(
            None,
            f"We left out the church size ({join_names(chosen)}) because too few openings list pay for it.",
            shown="Any church size",
        )
    )
    return levels


def group_levels(chosen: list[str], group_of: Callable[[str], str], present: Iterable[str], what: str) -> list[Level]:
    """Levels for denominations or roles. `what` is the plural noun in the sentence ("denominations", "roles")."""
    if not chosen:
        return [ANY]
    groups = list(dict.fromkeys(group_of(c) for c in chosen))
    wider = frozenset(v for v in present if group_of(v) in groups) | frozenset(chosen)
    levels = [Level(frozenset(chosen))]
    if wider != frozenset(chosen):
        levels.append(
            Level(
                wider,
                f"We combined {join_names(chosen)} with similar {what} ({join_names(groups)}) because too few "
                f"openings list pay for {join_names(chosen)} alone.",
                shown=join_names(groups),
            )
        )
    levels.append(
        Level(
            None,
            f"We included all {what} because too few openings list pay for {join_names(chosen)} alone.",
            shown=f"All {what}",
        )
    )
    return levels


def loosen(levels: dict[str, list[Level]], enough: Callable[[dict[str, Level]], bool]) -> dict[str, Level]:
    """The levels to use, widened in the order described at the top of this file until `enough` says the search has
    data (or every filter is as wide as it goes)."""
    pos = dict.fromkeys(LOOSEN_ORDER, 0)

    def current() -> dict[str, Level]:
        return {k: levels[k][pos[k]] for k in LOOSEN_ORDER}

    def bump(kind: str) -> None:
        pos[kind] = min(pos[kind] + 1, len(levels[kind]) - 1)

    if enough(current()):
        return current()
    # First widening: the nearby states together with the neighbouring church sizes and the denomination family, since
    # a nearby state is no help if the size or denomination is still too narrow to find anything there.
    for kind in ("state", "size", "denomination"):
        if kind != "denomination" or len(levels[kind]) > 2:  # a chosen family has no wider step but "any": keep it
            bump(kind)
    # Then the area grows up to its region; church size is dropped before the search goes nationwide, so the answer
    # stays local; then nationwide, denomination, and role last.
    last_area = len(levels["state"]) - 1
    while not enough(current()) and pos["state"] < last_area - 1:
        bump("state")
    while not enough(current()) and pos["size"] < len(levels["size"]) - 1:
        bump("size")
    while not enough(current()) and pos["state"] < last_area:
        bump("state")
    for kind in ("denomination", "role"):
        while not enough(current()) and pos[kind] < len(levels[kind]) - 1:
            bump(kind)
    return current()


def merge_thin(
    groups: dict[str, list[Any]],
    stats: Callable[[list[Any]], Any],
    parent_of: Callable[[str], str],
    other: str,
) -> list[dict[str, Any]]:
    """Rows [{name, typical, merged, n}] for a bar chart: a group with enough pay stands alone; thin groups that share
    a parent (role group, denomination family, region) are combined under it; what is still thin is combined into one
    `other` row; a combination that still has too little pay is left out. `merged` lists the combined groups and `n`
    (jobs, for ordering only) is not sent to the public."""
    rows: list[dict[str, Any]] = []
    thin: dict[str, list[str]] = {}
    for name, jobs in groups.items():
        if s := stats(jobs):
            rows.append({"name": name, "typical": s["typical"], "merged": [], "n": len(jobs)})
        else:
            thin.setdefault(parent_of(name), []).append(name)
    leftovers: list[str] = []
    for parent, names in thin.items():
        jobs = [j for n in names for j in groups[n]]
        if len(names) > 1 and (s := stats(jobs)):
            rows.append({"name": parent, "typical": s["typical"], "merged": names, "n": len(jobs)})
        else:
            leftovers += names
    if leftovers:
        jobs = [j for n in leftovers for j in groups[n]]
        if s := stats(jobs):
            rows.append({"name": other, "typical": s["typical"], "merged": leftovers, "n": len(jobs)})
    return rows
