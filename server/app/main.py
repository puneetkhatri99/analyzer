from pathlib import Path
from typing import Literal, Optional

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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
    status: Optional[Literal["open", "expired", "unverified"]] = None,
    remote: Optional[str] = None,
    search: Optional[str] = None,
    has_pay: bool = False,
    min_salary: float = 0,
    min_church_size: float = 0,
) -> dict:
    return {
        "role": role, "denomination": denomination, "region": region, "country": country,
        "hours": hours, "status": status, "remote": remote, "search": search, "has_pay": has_pay,
        "min_salary": min_salary, "min_church_size": min_church_size,
    }


@app.get("/api/health")
def health():
    return {"ok": True}


# json = the church jobs JSON feed; churches / nonprofits = the BizDev Excel imports.
Source = Literal["json", "churches", "nonprofits"]


@app.get("/api/sources")
def sources():
    return jobs.source_counts()


@app.get("/api/filter-options")
def filter_options(source: Source = "json"):
    return jobs.build_filter_options(jobs.load_jobs(source))


@app.get("/api/jobs")
def list_jobs(source: Source = "json", filters: dict = Depends(job_filters)):
    rows = jobs.apply_filters(jobs.load_jobs(source), filters)
    return {"total": len(rows), "rows": rows}


@app.get("/api/summary")
def summary(source: Source = "json", filters: dict = Depends(job_filters)):
    all_jobs = jobs.load_jobs(source)
    return jobs.build_summary(
        jobs.apply_filters(all_jobs, filters),
        jobs.apply_filters(all_jobs, filters, skip=("role",)),
        jobs.apply_filters(all_jobs, filters, skip=("region",)),
    )


# The built dashboard (client/dist), served from the same address as the API.
# Mounted last so /api/* routes win. Skipped when the client hasn't been built (local dev uses Vite).
CLIENT_DIST = Path(__file__).resolve().parents[2] / "client" / "dist"
if CLIENT_DIST.is_dir():
    app.mount("/", StaticFiles(directory=CLIENT_DIST, html=True), name="client")
