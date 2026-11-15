"""The API, and the built dashboard (client/dist) served from the same address."""

import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.ai_usage.router import router as ai_usage_router
from app.auth.router import router as auth_router
from app.core.config import get_settings
from app.core.db import close_pool, open_pool
from app.core.logs import api_log
from app.extraction.router import router as extraction_router
from app.jobs.router import router as jobs_router
from app.leads.router import router as leads_router
from app.report.router import router as report_router

CLIENT_DIST = Path(__file__).resolve().parents[2] / "client" / "dist"
CLIENT_PAGES = ("/admin", "/report")  # client-side routes: serve the app's page for them

log = logging.getLogger("api")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    api_log()  # on server start, not on import, so the tests don't write into the real log files
    open_pool()
    log.info("API started")
    yield
    close_pool()
    log.info("API stopped")


async def log_requests(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
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
        log.exception(
            "%s %s -> crashed after %d ms (%s)", request.method, path, ms, ip, extra={**fields, "status": 500, "ms": ms}
        )
        raise
    ms = round((time.perf_counter() - start) * 1000)
    level = logging.WARNING if response.status_code >= 400 else logging.INFO
    # extra= fields become their own columns in Axiom, so requests can be charted by path, status and time
    log.log(
        level,
        "%s %s -> %s in %d ms (%s)",
        request.method,
        path,
        response.status_code,
        ms,
        ip,
        extra={**fields, "status": response.status_code, "ms": ms},
    )
    return response


def create_app() -> FastAPI:
    app = FastAPI(title="MinistryHub Market Analysis Tool API", lifespan=lifespan)
    app.middleware("http")(log_requests)
    app.add_middleware(GZipMiddleware, minimum_size=1000)  # /api/jobs replies run to megabytes
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[get_settings().allowed_origin],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["health"])
    def health() -> dict[str, bool]:
        return {"ok": True}

    for router in (report_router, leads_router, jobs_router, auth_router, extraction_router, ai_usage_router):
        app.include_router(router)

    # Mounted last so /api/* routes win. Skipped when the client hasn't been built (local dev uses Vite).
    if CLIENT_DIST.is_dir():
        for page in CLIENT_PAGES:
            app.get(page, include_in_schema=False)(lambda: FileResponse(CLIENT_DIST / "index.html"))
        app.mount("/", StaticFiles(directory=CLIENT_DIST, html=True), name="client")
    return app


app = create_app()
