import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.logs import RequestIdFilter
from app.main import log_requests


def test_request_id_reaches_route_logs_and_noise_is_skipped(caplog: pytest.LogCaptureFixture) -> None:
    app = FastAPI()  # the real app mounts the dashboard at "/", which would catch a route added after it
    app.middleware("http")(log_requests)

    @app.get("/api/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/api/_probe")
    def probe() -> dict[str, bool]:  # a sync route runs in a worker thread: the ID must still follow it
        logging.getLogger("probe").info("inside the route")
        return {"ok": True}

    caplog.handler.addFilter(RequestIdFilter())
    caplog.set_level(logging.INFO)
    client = TestClient(app)

    rid = client.get("/api/_probe").headers["X-Request-ID"]
    lines = [r for r in caplog.records if getattr(r, "request_id", None) == rid]
    assert {r.name for r in lines} == {"probe", "api"}  # the route's own line and the request line

    caplog.clear()
    assert client.get("/api/health").headers["X-Request-ID"]
    assert not [r for r in caplog.records if r.name == "api"]  # health checks aren't logged

    assert client.get("/api/nope").status_code == 404
    assert [r for r in caplog.records if r.name == "api" and r.levelno == logging.WARNING]  # errors still are


def test_values_in_the_path_stay_out_of_the_log(caplog: pytest.LogCaptureFixture) -> None:
    app = FastAPI()
    app.middleware("http")(log_requests)

    @app.get("/api/admin/leads/{email}")
    def lead(email: str) -> dict[str, str]:
        return {"email": email}

    caplog.set_level(logging.INFO)
    TestClient(app).get("/api/admin/leads/jane.doe@church.org?x=1")
    line = next(r for r in caplog.records if r.name == "api")
    assert "jane.doe" not in line.getMessage() and "jane.doe" not in str(line.__dict__)
    assert line.path == "/api/admin/leads/{email}" and "/api/admin/leads/{email}?x=1" in line.getMessage()
