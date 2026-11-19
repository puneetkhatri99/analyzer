from app.auth.security import LoginLimiter, hash_password, verify_password


def test_password_hashing():
    h = hash_password("admin@123")
    assert h.startswith("scrypt$") and "admin@123" not in h and h != hash_password("admin@123")  # salted
    assert verify_password("admin@123", h) and not verify_password("admin@124", h)


def test_login_limiter_blocks_after_max_failures_per_ip():
    limiter = LoginLimiter(max_failures=2, window=60)
    limiter.fail("1.1.1.1")
    assert not limiter.blocked("1.1.1.1")
    limiter.fail("1.1.1.1")
    assert limiter.blocked("1.1.1.1") and not limiter.blocked("2.2.2.2")
    limiter.succeed("1.1.1.1")
    assert not limiter.blocked("1.1.1.1")
    assert not LoginLimiter(max_failures=1, window=0).blocked("x")  # old failures expire


def test_faked_ips_dont_get_around_the_lockout(make_user):
    """Production trusts X-Forwarded-For from anyone (render.yaml), so each guess can claim a new IP."""
    from fastapi.testclient import TestClient
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

    from app.auth.security import login_limiter
    from app.main import app

    email = "test-lockout@example.invalid"
    make_user(email, "the-right-pass-1")
    client = TestClient(ProxyHeadersMiddleware(app, trusted_hosts="*"))
    for i in range(login_limiter.max_failures):
        r = client.post(
            "/api/admin/login", json={"email": email, "password": "wrong"}, headers={"X-Forwarded-For": f"10.0.0.{i}"}
        )
        assert r.status_code == 401
    r = client.post(
        "/api/admin/login",
        json={"email": email, "password": "the-right-pass-1"},
        headers={"X-Forwarded-For": "10.0.0.99"},
    )
    assert r.status_code == 429  # blocked by account, though this "IP" never failed
