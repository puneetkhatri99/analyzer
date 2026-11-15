import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import require_editor
from app.core.db import get_conn
from app.extraction import service
from app.extraction.schemas import ExtractRequest, SaveRequest
from app.extraction.validation import validate
from app.jobs.repository import ADMIN_JOB_FIELDS, save_admin_job
from app.shared.web import url_key

router = APIRouter(prefix="/api/admin", tags=["extraction"])
log = logging.getLogger("admin")


@router.post("/extract", response_model=None)
def extract(body: ExtractRequest, admin_email: str = Depends(require_editor)) -> dict[str, Any]:
    try:
        return service.extract(str(body.url), admin_email)
    except service.ExtractionError as e:
        raise HTTPException(e.status_code, e.detail) from e


@router.post("/jobs")
def save(body: SaveRequest, admin_email: str = Depends(require_editor)) -> dict[str, Any]:
    job, _ = validate(body.job)  # the job comes back from the browser, so it is checked again
    if job.page_type != "job_posting":
        raise HTTPException(400, "Only job postings can be saved")
    url = str(body.url)
    row = {f: getattr(job, f, None) for f in ADMIN_JOB_FIELDS}
    row["remote"] = None if job.remote is None else str(job.remote).lower()
    row["church_size_source"] = (
        str(body.church_size_source) if body.church_size_source and job.church_size is not None else None
    )
    row |= {"url_key": url_key(url), "job_url": url, "added_via": f"admin_{body.method}", "added_by": admin_email}
    with get_conn() as conn:
        save_admin_job(conn, body.dataset, row)
    log.info("Saved by %s to %s: %s | %s | %s", admin_email, body.dataset, job.job_title, job.org_name, url)
    return {"saved": True, "dataset": body.dataset}
