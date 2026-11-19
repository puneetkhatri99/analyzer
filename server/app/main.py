"""The API, and the built dashboard (client/dist) served from the same address."""

import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.ai_usage.router import router as ai_usage_router
from app.auth.router import router as auth_router
from app.core.config import get_settings
from app.core.db import close_pool, open_pool
from app.core.logs import api_log, request_id
from app.extraction.router import router as extraction_router
from app.ingestion import bizdev_sync, daily_feed
from app.ingestion.bizdev_sync_router import router as bizdev_sync_router
from app.ingestion.feed_router import router as feed_router
from app.jobs.router import router as jobs_router
from app.leads import daily_report
from app.leads.router import admin_router as leads_admin_router
from app.leads.router import router as leads_router
from app.report.router import router as report_router

CLIENT_DIST = Path(__file__).resolve().parents[2] / "client" / "dist"
CLIENT_PAGES = ("/admin", "/admin/{section}", "/report")  # client-side routes: serve the app's page for them

log = logging.getLogger("api")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    api_log()  # on server start, not on import, so the tests don't write into the real log files
    open_pool()
    log.info("API started")
    if get_settings().app_env == "production" and "localhost" in get_settings().site_url:
        log.error("SITE_URL isn't set: links in emails (reports, alerts) point to %s", get_settings().site_url)
    # The daily lead report without a paid cron job; production only, so a local server never sends it
    send_daily = get_settings().app_env == "production" and daily_report.email_ready()
    stop_daily = daily_report.start_scheduler() if send_daily else None
    # The daily jobs feed (app/ingestion/daily_feed.py), also production only
    stop_feed = daily_feed.start_scheduler() if get_settings().app_env == "production" else None
    stop_bizdev = bizdev_sync.start_scheduler() if get_settings().app_env == "production" else None
    yield
    if stop_bizdev:
        stop_bizdev.set()
    if stop_daily:
        stop_daily.set()
    if stop_feed:
        stop_feed.set()
    close_pool()
    log.info("API stopped")


async def log_requests(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """One line per request (method, path and query, status, time, visitor IP); a crash is logged with its traceback.
    Bodies and cookies are never logged, so passwords and session tokens stay out of the log.

    Each request gets an ID: it's on every line the request logs (request_id in Axiom) and sent back in the
    X-Request-ID header, so a user's error report can be matched to its log lines. Successful health checks and
    static files (the built dashboard) aren't logged: they'd bury the API's own lines."""
    rid = uuid.uuid4().hex[:16]
    token = request_id.set(rid)
    try:
        return await _log_request(request, call_next, rid)
    finally:
        request_id.reset(token)


def _fields(request: Request, ip: str) -> tuple[str, dict[str, Any]]:
    """The path as its route pattern ("/api/admin/leads/{email}", not the address itself), so values in a path never
    reach the log. Known after routing; a path no route matched (a 404) is logged as it came."""
    route = getattr(request.scope.get("route"), "path", None) or request.url.path
    query = request.url.query or None
    fields = {"method": request.method, "path": route, "query": query, "ip": ip}
    return route + (f"?{query}" if query else ""), fields


async def _log_request(request: Request, call_next: Callable[[Request], Awaitable[Response]], rid: str) -> Response:
    start = time.perf_counter()
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "?").split(",")[0].strip()
    try:
        response = await call_next(request)
    except Exception:
        ms = round((time.perf_counter() - start) * 1000)
        path, fields = _fields(request, ip)
        log.exception(
            "%s %s -> crashed after %d ms (%s)", request.method, path, ms, ip, extra={**fields, "status": 500, "ms": ms}
        )
        raise
    ms = round((time.perf_counter() - start) * 1000)
    path, fields = _fields(request, ip)
    response.headers["X-Request-ID"] = rid
    # the admin page polls /api/admin/feed every 2 s while a feed run is going
    polling = request.method == "GET" and request.url.path == "/api/admin/feed"
    noise = request.url.path == "/api/health" or polling or not request.url.path.startswith("/api")
    if noise and response.status_code < 400:
        return response
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

    for router in (
        report_router,
        leads_router,
        leads_admin_router,
        jobs_router,
        auth_router,
        extraction_router,
        ai_usage_router,
        feed_router,
        bizdev_sync_router,
    ):
        app.include_router(router)

    # Mounted last so /api/* routes win. Skipped when the client hasn't been built (local dev uses Vite).
    if CLIENT_DIST.is_dir():
        for page in CLIENT_PAGES:
            app.get(page, include_in_schema=False)(lambda: FileResponse(CLIENT_DIST / "index.html"))
        app.mount("/", StaticFiles(directory=CLIENT_DIST, html=True), name="client")
    return app


app = create_app()
