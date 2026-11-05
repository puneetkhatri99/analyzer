from typing import Optional

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import jobs
from app.config import ALLOWED_ORIGIN

app = FastAPI(title="Ministry Jobs Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def job_filters(
    role: Optional[str] = None,
    denomination: Optional[str] = None,
    region: Optional[str] = None,
    country: Optional[str] = None,
    hours: Optional[str] = None,
    remote: Optional[str] = None,
    search: Optional[str] = None,
    has_pay: bool = False,
    min_salary: float = 0,
    min_church_size: float = 0,
) -> dict:
    return {
        "role": role, "denomination": denomination, "region": region, "country": country,
        "hours": hours, "remote": remote, "search": search, "has_pay": has_pay,
        "min_salary": min_salary, "min_church_size": min_church_size,
    }


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/filter-options")
def filter_options():
    return jobs.build_filter_options(jobs.load_jobs())


@app.get("/api/jobs")
def list_jobs(filters: dict = Depends(job_filters)):
    rows = jobs.apply_filters(jobs.load_jobs(), filters)
    return {"total": len(rows), "rows": rows}


@app.get("/api/summary")
def summary(filters: dict = Depends(job_filters)):
    all_jobs = jobs.load_jobs()
    return jobs.build_summary(
        jobs.apply_filters(all_jobs, filters),
        jobs.apply_filters(all_jobs, filters, skip=("role",)),
        jobs.apply_filters(all_jobs, filters, skip=("region",)),
    )
