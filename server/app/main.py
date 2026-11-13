import re
from pathlib import Path
from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel, Field

from app import admin, jobs, report
from app.config import ALLOWED_ORIGIN
from app.db import get_conn

app = FastAPI(title="MinistryHub Market Analysis Tool API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def job_filters(
    role: Optional[str] = None,
    denomination: Optional[str] = None,
    region: Optional[str] = None,
    country: Optional[str] = None,
    hours: Optional[str] = None,
    status: Optional[Literal["open", "expired", "unverified"]] = None,
    origin: Optional[Literal["feed", "excel", "admin"]] = None,
    remote: Optional[str] = None,
    search: Optional[str] = None,
    has_pay: bool = False,
    min_salary: float = 0,
    min_church_size: float = 0,
) -> dict:
    return {
        "role": role, "denomination": denomination, "region": region, "country": country,
        "hours": hours, "status": status, "origin": origin, "remote": remote, "search": search, "has_pay": has_pay,
        "min_salary": min_salary, "min_church_size": min_church_size,
    }


@app.get("/api/health")
def health():
    return {"ok": True}


# json = the church jobs JSON feed; churches / nonprofits = the BizDev Excel imports.
Source = Literal["json", "churches", "nonprofits"]


# ---------- public: the report (summary figures only; brief P5-P7) ----------

@app.get("/api/report/options")
def report_options():
    return report.report_options()


@app.get("/api/report")
def get_report(
    role: list[str] = Query(default=[]),
    state: list[str] = Query(default=[]),
    size: list[str] = Query(default=[]),
    denomination: list[str] = Query(default=[]),
    type: Literal["full-time", "part-time"] = "full-time",
):
    return report.build_report({"role": role, "state": state, "size": size, "denomination": denomination, "type": type})


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Lead(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(max_length=320)
    organization: str = Field(min_length=1, max_length=300)
    role: Optional[str] = Field(default=None, max_length=200)
    location: Optional[str] = Field(default=None, max_length=200)
    attendance: Optional[str] = Field(default=None, max_length=100)


@app.post("/api/leads")
def save_lead(lead: Lead):
    """Sign-up before the report (brief P2). A returning email updates the row instead of adding one."""
    email = lead.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(422, "Please enter a valid email address.")
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO public.leads (email, name, organization, role, location, attendance)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name, organization = EXCLUDED.organization,
                 role = EXCLUDED.role, location = EXCLUDED.location, attendance = EXCLUDED.attendance,
                 last_seen_at = now()""",
            (email, lead.name.strip(), lead.organization.strip(), lead.role, lead.location, lead.attendance),
        )
    return {"ok": True}


# ---------- admin only: per-source view, postings and links (brief A1, A2) ----------

@app.get("/api/sources", dependencies=[Depends(admin.require_viewer)])
def sources():
    return jobs.source_counts()


@app.get("/api/filter-options", dependencies=[Depends(admin.require_viewer)])
def filter_options(source: Source = "json"):
    return jobs.build_filter_options(jobs.load_jobs(source))


@app.get("/api/jobs", dependencies=[Depends(admin.require_viewer)])
def list_jobs(source: Source = "json", filters: dict = Depends(job_filters)):
    rows = jobs.apply_filters(jobs.load_jobs(source), filters)
    return {"total": len(rows), "rows": rows}


@app.get("/api/summary", dependencies=[Depends(admin.require_viewer)])
def summary(source: Source = "json", filters: dict = Depends(job_filters)):
    all_jobs = jobs.load_jobs(source)
    return jobs.build_summary(
        jobs.apply_filters(all_jobs, filters),
        jobs.apply_filters(all_jobs, filters, skip=("role",)),
        jobs.apply_filters(all_jobs, filters, skip=("region",)),
    )


# The built dashboard (client/dist), served from the same address as the API.
# Mounted last so /api/* routes win. Skipped when the client hasn't been built (local dev uses Vite).
app.include_router(admin.router)

CLIENT_DIST = Path(__file__).resolve().parents[2] / "client" / "dist"
if CLIENT_DIST.is_dir():
    # The admin and report pages are client-side routes; serve the app's page for them.
    for page in ("/admin", "/report"):
        app.get(page, include_in_schema=False)(lambda: FileResponse(CLIENT_DIST / "index.html"))
    app.mount("/", StaticFiles(directory=CLIENT_DIST, html=True), name="client")
