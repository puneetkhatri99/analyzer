"""Tests run against a real Postgres: DATABASE_URL by default, or TEST_DATABASE_URL (migrated first) when it is set.
Tests that write rows use addresses on example.invalid and remove them afterwards."""

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.auth.security import hash_password, login_limiter
from app.core.config import get_settings
from app.core.db import connect, get_conn
from app.core.migrations import migrate
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def database() -> None:
    if url := os.environ.get("TEST_DATABASE_URL"):
        get_settings().database_url = url
        with connect() as conn:
            migrate(conn)


@pytest.fixture(autouse=True)
def reset_login_limiter() -> Iterator[None]:
    login_limiter.reset()
    yield
    login_limiter.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def make_user():
    """make_user(email, password, role='admin'): an account that is removed after the test."""
    made: list[str] = []

    def make(email: str, password: str, role: str = "admin") -> str:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO public.admin_users (email, password_hash, role) VALUES (%s, %s, %s) "
                "ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash, role = EXCLUDED.role",
                (email, hash_password(password), role),
            )
        made.append(email)
        return email

    yield make
    with get_conn() as conn:
        conn.execute("DELETE FROM public.admin_users WHERE email = ANY(%s)", (made,))


@pytest.fixture
def sign_in():
    """sign_in(email, password) -> (a client holding that user's session cookie, the /login reply)."""

    def sign_in(email: str, password: str) -> tuple[TestClient, dict]:
        c = TestClient(app)
        r = c.post("/api/admin/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        return c, r.json()

    return sign_in
