import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal, Optional

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import admin, jobs
from app.config import ALLOWED_ORIGIN
from app.logs import api_log

log = logging.getLogger("api")


@asynccontextmanager
async def lifespan(_):
    api_log()  # on server start, not on import, so the tests don't write into the real log files
    log.info("API started")
    yield
    log.info("API stopped")


app = FastAPI(title="Ministry Jobs Analytics API", lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """One line per request (method, path and query, status, time, visitor IP); a crash is logged with its traceback.
    Bodies and cookies are never logged, so passwords and session tokens stay out of the log."""
    start = time.perf_counter()
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "?").split(",")[0].strip()
    path = request.url.path + (f"?{request.url.query}" if request.url.query else "")
    fields = {"method": request.method, "path": request.url.path, "query": request.url.query or None, "ip": ip}
    try:
        response = await call_next(request)
    except Exception:
        ms = round((time.perf_counter() - start) * 1000)
        log.exception("%s %s -> crashed after %d ms (%s)", request.method, path, ms, ip, extra={**fields, "status": 500, "ms": ms})
        raise
    ms = round((time.perf_counter() - start) * 1000)
    level = logging.WARNING if response.status_code >= 400 else logging.INFO
    # extra= fields become their own columns in Axiom, so requests can be charted by path, status and time
    log.log(level, "%s %s -> %s in %d ms (%s)", request.method, path, response.status_code, ms, ip,
            extra={**fields, "status": response.status_code, "ms": ms})
    return response

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
    origin: Optional[Literal["feed", "excel", "admin", "collector"]] = None,
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
app.include_router(admin.router)

CLIENT_DIST = Path(__file__).resolve().parents[2] / "client" / "dist"
if CLIENT_DIST.is_dir():
    # The admin page is a client-side route; serve the app's page for it.
    app.get("/admin", include_in_schema=False)(lambda: FileResponse(CLIENT_DIST / "index.html"))
    app.mount("/", StaticFiles(directory=CLIENT_DIST, html=True), name="client")
