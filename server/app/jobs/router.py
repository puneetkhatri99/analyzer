"""Admin-only views of the postings, per source, with links and counts (brief A1, A2)."""

import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import require_editor, require_viewer
from app.jobs import repository, service
from app.jobs.repository import Source

router = APIRouter(tags=["jobs"])
viewer_only = [Depends(require_viewer)]
log = logging.getLogger("admin")


def job_filters(
    role: str | None = None,
    denomination: str | None = None,
    region: str | None = None,
    country: str | None = None,
    hours: str | None = None,
    status: Literal["open", "expired", "unverified"] | None = None,
    origin: Literal["feed", "excel", "admin", "collector"] | None = None,
    remote: str | None = None,
    search: str | None = None,
    has_pay: bool = False,
    min_salary: float = 0,
    min_church_size: float = 0,
) -> dict[str, Any]:
    return {
        "role": role, "denomination": denomination, "region": region, "country": country,
        "hours": hours, "status": status, "origin": origin, "remote": remote, "search": search, "has_pay": has_pay,
        "min_salary": min_salary, "min_church_size": min_church_size,
    }  # fmt: skip


@router.get("/api/sources", dependencies=viewer_only, response_model=None)
def sources() -> list[dict[str, Any]]:
    return repository.source_counts()


@router.get("/api/filter-options", dependencies=viewer_only, response_model=None)
def filter_options(source: Source = "json") -> dict[str, Any]:
    return service.build_filter_options(repository.load_jobs(source))


@router.get("/api/jobs", dependencies=viewer_only, response_model=None)
def list_jobs(source: Source = "json", filters: dict = Depends(job_filters)) -> dict[str, Any]:
    rows = service.apply_filters(repository.load_jobs(source), filters)
    return {"total": len(rows), "rows": rows}


@router.get("/api/summary", dependencies=viewer_only, response_model=None)
def summary(source: Source = "json", filters: dict = Depends(job_filters)) -> dict[str, Any]:
    jobs = repository.load_jobs(source)
    return service.build_summary(
        service.apply_filters(jobs, filters),
        service.apply_filters(jobs, filters, skip=("role",)),
        service.apply_filters(jobs, filters, skip=("region",)),
    )


@router.delete("/api/admin/jobs")
def delete_job(source: Source, id: str, admin_email: str = Depends(require_editor)) -> dict[str, bool]:  # noqa: A002
    """Remove one job for good. `id` is the row's post_uuid in /api/jobs (the url_key for the BizDev sheets).
    A job still in the feed or the Excel sheet comes back the next time that is imported."""
    if not repository.delete_job(source, id):
        raise HTTPException(404, "No such job")
    log.info("Deleted by %s from %s: %s", admin_email, source, id)
    return {"deleted": True}
