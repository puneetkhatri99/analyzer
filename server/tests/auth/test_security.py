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
