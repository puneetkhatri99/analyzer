"""Admin-only views of the postings, per source, with links and counts (brief A1, A2)."""

import logging
from typing import Any, Literal, get_args

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.dependencies import require_editor, require_viewer
from app.core.db import get_conn
from app.job_pages.parser import denomination_in
from app.jobs import repository, service
from app.jobs.repository import BizdevSource, Source

router = APIRouter(tags=["jobs"])
viewer_only = [Depends(require_viewer)]
log = logging.getLogger("admin")


def job_filters(
    role: str | None = None,
    denomination: str | None = None,
    region: str | None = None,
    country: str | None = None,
    hours: str | None = None,
    origin: Literal["feed", "excel", "admin", "collector"] | None = None,
    remote: str | None = None,
    search: str | None = None,
    has_pay: bool = False,
    min_salary: float = 0,
    min_church_size: float = 0,
) -> dict[str, Any]:
    return {
        "role": role, "denomination": denomination, "region": region, "country": country,
        "hours": hours, "origin": origin, "remote": remote, "search": search,
        "has_pay": has_pay,
        "min_salary": min_salary, "min_church_size": min_church_size,
    }  # fmt: skip


def chosen_sources(source: str = "json") -> list[Source]:
    """`source` is one source or several, comma-separated: "json,churches"."""
    picked = list(dict.fromkeys(s.strip() for s in source.split(",") if s.strip()))
    if not picked or any(s not in get_args(Source) for s in picked):
        raise HTTPException(422, f"source must be one or more of {', '.join(get_args(Source))}")
    return picked


@router.get("/api/sources", dependencies=viewer_only, response_model=None)
def sources() -> list[dict[str, Any]]:
    return repository.source_counts()


@router.get("/api/filter-options", dependencies=viewer_only, response_model=None)
def filter_options(sources: list[Source] = Depends(chosen_sources)) -> dict[str, Any]:
    return service.build_filter_options(repository.load_sources(sources))


@router.get("/api/jobs", dependencies=viewer_only, response_model=None)
def list_jobs(sources: list[Source] = Depends(chosen_sources), filters: dict = Depends(job_filters)) -> dict[str, Any]:
    rows = service.apply_filters(repository.load_sources(sources), filters)
    return {"total": len(rows), "rows": rows}


@router.get("/api/summary", dependencies=viewer_only, response_model=None)
def summary(sources: list[Source] = Depends(chosen_sources), filters: dict = Depends(job_filters)) -> dict[str, Any]:
    jobs = repository.load_sources(sources)
    return service.build_summary(
        service.apply_filters(jobs, filters),
        service.apply_filters(jobs, filters, skip=("role",)),
        service.apply_filters(jobs, filters, skip=("region",)),
    )


class Rejection(BaseModel):
    id: str = Field(min_length=1, max_length=200)  # the feed posting's post_uuid
    reason: str | None = Field(default=None, max_length=300)


class Restore(BaseModel):
    id: str = Field(min_length=1, max_length=200)


@router.get("/api/admin/rejected", dependencies=viewer_only, response_model=None)
def rejected() -> dict[str, Any]:
    """Feed postings judged out of scope, with the reason; the daily feed skips them."""
    rows = repository.rejected_postings()
    return {"total": len(rows), "rows": rows}


@router.post("/api/admin/jobs/reject")
def reject_job(body: Rejection, admin_email: str = Depends(require_editor)) -> dict[str, bool]:
    """Move a feed posting to the rejected jobs: out of every view and figure, skipped if the feed sends it again."""
    reason = (body.reason or "").strip() or "Rejected by an admin"
    with get_conn() as conn, conn.transaction():
        if not repository.reject_posting(conn, body.id, reason, admin_email):
            raise HTTPException(404, "No such feed posting")
    log.info("Rejected by %s: %s (%s)", admin_email, body.id, reason)
    return {"rejected": True}


@router.post("/api/admin/rejected/restore")
def restore_job(body: Restore, admin_email: str = Depends(require_editor)) -> dict[str, bool]:
    """Put a rejected posting back among the jobs; the AI won't reject it again."""
    if not repository.restore_posting(body.id):
        raise HTTPException(404, "No such rejected posting")
    log.info("Included again by %s: %s", admin_email, body.id)
    return {"restored": True}


@router.get("/api/admin/jobs/contact", response_model=None)
def job_contact(source: BizdevSource, id: str, admin_email: str = Depends(require_editor)) -> dict[str, Any]:  # noqa: A002
    """Who to contact about one BizDev job: name, title and email from the sheet. Editors and admins only, and the
    lookup is logged (who and which job, never the contact). Feed jobs have no contact."""
    contact = repository.job_contact(source, id)
    if contact is None:
        raise HTTPException(404, "No such job")
    log.info("Contact of %s job %s viewed by %s", source, id, admin_email)
    return contact


class EmployerFacts(BaseModel):
    source: Source
    id: str = Field(min_length=1, max_length=500)  # any job of the employer: post_uuid in /api/jobs
    church_size: int | None = Field(default=None, ge=1, le=100_000)
    denomination: str | None = Field(default=None, min_length=1, max_length=80)


@router.patch("/api/admin/employer")
def set_employer(body: EmployerFacts, admin_email: str = Depends(require_editor)) -> dict[str, Any]:
    """An editor fills in the church size and/or denomination the AI couldn't find (brief Rec. 2: "manually work
    through ones without church size"). Applies to every job of that employer; logged with the old and new values."""
    if body.church_size is None and body.denomination is None:
        raise HTTPException(422, "Give a church size, a denomination, or both.")
    denomination = body.denomination and (denomination_in(body.denomination) or body.denomination.strip())
    result = repository.set_employer_facts(body.source, body.id, body.church_size, denomination, admin_email)
    if result is None:
        raise HTTPException(404, "No such job")
    log.info(
        "Employer facts set by %s for %r (%s, %d jobs): church size %s -> %s, denomination %r -> %r",
        admin_email, result["employer"], body.source, result["jobs"], result["old_size"],
        body.church_size if body.church_size is not None else result["old_size"], result["old_denomination"],
        denomination or result["old_denomination"],
    )  # fmt: skip
    return {"jobs": result["jobs"]}


@router.delete("/api/admin/jobs")
def delete_job(source: Source, id: str, admin_email: str = Depends(require_editor)) -> dict[str, bool]:  # noqa: A002
    """Remove one BizDev job. `id` is the row's url_key (post_uuid in /api/jobs). A job still in the Excel sheet comes
    back the next time it is imported. Feed jobs can't be deleted (the next feed run would add them back):
    they are rejected instead."""
    if source == "json":
        raise HTTPException(400, "Feed jobs can't be deleted: reject the job instead.")
    if not repository.delete_job(source, id):
        raise HTTPException(404, "No such job")
    log.info("Deleted by %s from %s: %s", admin_email, source, id)
    return {"deleted": True}
