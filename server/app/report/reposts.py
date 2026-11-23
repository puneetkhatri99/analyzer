"""One opening, counted once (brief D3): the same job posted twice, reposted after it closed, or listed by two sources
becomes one row before any figure is worked out.

Two jobs are the same opening when either
  * their links are the same (scheme, "www" and a trailing slash ignored; the query kept, because several feed jobs
    share one page and differ only by their query) and so is the state (or one has none), or
  * the employer, the title and the state match, so does the city (a job without a city joins the only city its
    group has), and the copies were posted within REPOST_DAYS of each other. A chain counts as one opening that
    renewed: copies 0, 80 and 160 days apart are one.
Employers and titles are compared as sets of words, so "Pastor of Worship (Full-Time)" and "Worship Pastor", or
"First Baptist Church, Inc." and "First Baptist Church", match. A job with no employer is only matched by its link.

shortcut: two genuinely separate openings with the same title at the same church at the same time count once (the
client chose this); matching is on cleaned-up words, not meaning ("Worship Leader" and "Worship Director" differ).
"""

import re
from collections import defaultdict
from datetime import date
from itertools import pairwise
from typing import Any
from urllib.parse import urlsplit

from app.shared.geo import STATES

Job = dict[str, Any]

REPOST_DAYS = 90  # the brief: a copy that appears within 90 days of the last is the same opening
_ABBREVIATIONS = {
    "assoc": "associate", "asst": "assistant", "dir": "director", "coord": "coordinator", "exec": "executive",
    "mgr": "manager", "sr": "senior", "jr": "junior", "st": "saint",
}  # fmt: skip
_EMPLOYER_FILLER = {"the", "of", "inc", "llc", "corp", "co", "church"}
_TITLE_FILLER = {
    "full", "part", "time", "fulltime", "parttime", "ft", "pt", "position", "opening", "hiring", "needed",
    "remote", "hybrid", "job", "of", "the", "and", "for", "to", "a", "at", "in",
}  # fmt: skip
_BRACKETS = re.compile(r"\([^)]*\)|\[[^\]]*\]")
_CODE_OF = {name: code for code, name in STATES.items()}


def _singular(word: str) -> str:
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def _words(text: str | None) -> list[str]:
    text = _BRACKETS.sub(" ", (text or "").lower()).replace("&", " and ")
    return [_singular(_ABBREVIATIONS.get(w, w)) for w in re.findall(r"[a-z0-9]+", text)]


def employer_key(name: str | None) -> frozenset[str]:
    return frozenset(w for w in _words(name) if w not in _EMPLOYER_FILLER)


def _without_name(words: list[str], name: set[str]) -> list[str]:
    """`words` without the employer's name written into them: runs of 2+ words that are all from the name (or 1 word,
    for a one-word name). A single shared word stays: "Worship Pastor" at "Worship Center Church" keeps "worship"."""
    shortest = min(2, len(name)) or 1
    out, run = [], []
    for w in [*words, None]:
        if w is not None and w in name:
            run.append(w)
            continue
        if len(run) < shortest:
            out += run
        run = []
        if w is not None:
            out.append(w)
    return out


def title_key(d: Job) -> frozenset[str]:
    """The title's words without filler, without the job's own place ("Youth Pastor - Dallas, TX") and without the
    employer's name ("Lead Pastor - Sandhills Alliance Church")."""
    place = set(_words(d.get("city"))) | set(_words(d.get("state")))
    if code := _CODE_OF.get(d.get("state")):
        place.add(code.lower())
    words = _without_name(_words(d.get("job_name")), set(_words(d.get("company_name"))))
    return frozenset(w for w in words if w not in _TITLE_FILLER | place)


def link_key(url: str | None) -> str | None:
    if not url:
        return None
    try:
        p = urlsplit(url.strip().lower())
    except ValueError:  # a scraped address like "http://[bad": one such row must not take the whole report down
        return url.strip().lower() or None
    key = p.netloc.removeprefix("www.") + p.path.rstrip("/")
    return f"{key}?{p.query}" if p.query else key or None


def _day(d: Job) -> date | None:
    """When the copy was posted: the posting date, else when we first saw it."""
    for value in (d.get("first_indexed"), d.get("added_at")):
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            continue
    return None


def _city(d: Job) -> str | None:
    return " ".join(_words(d.get("city"))) or None


def group_openings(jobs: list[Job]) -> list[tuple[list[Job], set[str]]]:
    """Every opening as (its copies, newest first; why they were linked). Single jobs are a group of one."""
    parent = list(range(len(jobs)))
    reasons: dict[int, set[str]] = defaultdict(set)

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def link(i: int, j: int, reason: str) -> None:
        a, b = root(i), root(j)
        if a != b:
            parent[b] = a
            reasons[a] |= reasons.pop(b, set())
        reasons[a].add(reason)

    with_link: dict[str, list[int]] = defaultdict(list)
    by_text: dict[tuple, list[int]] = defaultdict(list)
    for i, d in enumerate(jobs):
        if key := link_key(d.get("post_url")):
            # one link in two states is a careers page listing two openings (the client's call), not one job
            for j in with_link[key]:
                if not d.get("state") or not jobs[j].get("state") or d["state"] == jobs[j]["state"]:
                    link(j, i, "same link")
            with_link[key].append(i)
        employer = employer_key(d.get("company_name"))
        title = title_key(d)
        if employer and title:
            by_text[(employer, title, d.get("state"))].append(i)

    for members in by_text.values():
        cities = {_city(jobs[i]) for i in members} - {None}
        only = next(iter(cities)) if len(cities) == 1 else None
        by_city: dict[str | None, list[int]] = defaultdict(list)
        for i in members:
            by_city[_city(jobs[i]) or only].append(i)
        for same_place in by_city.values():
            same_place.sort(key=lambda i: _day(jobs[i]) or date.min)
            for a, b in pairwise(same_place):
                da, db = _day(jobs[a]), _day(jobs[b])
                gap = (db - da).days if da and db else 0  # no date: can't tell them apart, so they're one
                if gap <= REPOST_DAYS:
                    link(a, b, f"same job within {gap} days")

    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(len(jobs)):
        groups[root(i)].append(i)
    out = []
    for r, members in groups.items():
        copies = sorted((jobs[i] for i in members), key=lambda d: _day(d) or date.min, reverse=True)
        out.append((copies, reasons.get(r, set())))
    return out


def one_row(copies: list[Job]) -> Job:
    """The opening as one job: pay from the newest copy that lists pay (a raised salary wins), else the newest copy;
    church size, denomination and city from any copy that has them."""
    kept = dict(next((d for d in copies if d.get("salary_min") is not None), copies[0]))
    for field in ("church_size", "denomination", "city"):
        if kept.get(field) is None:
            kept[field] = next((d[field] for d in copies if d.get(field) is not None), None)
    return kept


def merge_reposts(jobs: list[Job]) -> list[Job]:
    return [one_row(copies) for copies, _ in group_openings(jobs)]
