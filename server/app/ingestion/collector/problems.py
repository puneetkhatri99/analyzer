"""Problems a person has to look at: a site that changed, blocked the collector, or was down."""

from collections import defaultdict
from collections.abc import Mapping
from typing import Any

ADVICE = {
    "site changed": "The site no longer looks the way the collector expects. Open the address above in a browser "
                    "to see what changed, then update the '{source}' source in app/ingestion/collector/.",
    "blocked": "The site refused the collector. It may have added bot protection or changed its robots.txt. Check that "
               "it still allows crawling (JOB_SITES.md) before trying again.",
    "site down": "The site didn't answer or had a server error. Usually temporary: the next run tries again. "
                 "If it keeps happening for days, check the site.",
    "database": "Saving to the database failed. Check DATABASE_URL and that the database is up.",
}  # fmt: skip


class SiteProblem(Exception):
    """A failure a person has to look at. kind is one of ADVICE's keys."""

    def __init__(self, kind: str, url: str | None, detail: str) -> None:
        super().__init__(f"{kind}: {detail} ({url})")
        self.kind, self.url, self.detail = kind, url, detail


def http_problem(status: int) -> str | None:
    """An HTTP status -> the kind of problem it means, or None when it's fine."""
    if status < 400:
        return None
    if status in (401, 403, 429):
        return "blocked"
    if status >= 500:
        return "site down"
    return "site changed"  # 404, 410 and other 4xx: the address or API no longer works as it did


def source_health(name: str, st: Mapping[str, int], last: int | None, days: int) -> list[tuple[str, str]]:
    """Signs that a source broke even though no request failed. st: this run's counts; last: last run's listed count."""
    out = []
    if st["listed"] == 0 and name != "employers":
        out.append(
            (
                "site changed",
                f"listed 0 jobs. The collector no longer finds jobs where it looks "
                f"(or the site had none in the last {days} days)",
            )
        )
    elif last and last >= 20 and st["listed"] < last * 0.2:
        out.append(("site changed", f"listed only {st['listed']} jobs, down from {last} on the last run"))
    if (
        st["listed"] >= 5
        and st["listed_no_title"] > st["listed"] / 2
        and name not in ("churchstaffing", "ministrylist")
    ):
        out.append(("site changed", f"{st['listed_no_title']} of {st['listed']} listed jobs have no title"))
    read = st["read"]
    if read >= 5:
        if st["no_details"] >= read / 2:
            out.append(("site changed", f"{st['no_details']} of {read} job pages had no job details (no title found)"))
        if st["blocked"] >= read / 2:
            out.append(("blocked", f"{st['blocked']} of {read} job pages were blocked"))
        if st["failed"] >= read / 2:
            out.append(("site down", f"{st['failed']} of {read} job pages failed to load"))
    return out


def platform_problems(churches: list[dict[str, Any]]) -> list[SiteProblem]:
    """A hiring system whose every church failed the same way is one problem (its API changed), not many."""
    out = []
    by_platform: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in churches:
        by_platform[c["platform"]].append(c)
    for platform, cs in by_platform.items():
        failed = [c["problem"] for c in cs if c["problem"]]
        if len(cs) >= 3 and len(failed) == len(cs):
            kinds = {p.kind for p in failed}
            out.append(
                SiteProblem(
                    kinds.pop() if len(kinds) == 1 else "site changed",
                    failed[0].url,
                    f"{platform}: all {len(cs)} churches failed ({failed[0].detail})",
                )
            )
    return out
