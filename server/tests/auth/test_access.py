"""Roles: admins create viewer/editor users with a one-time password; each role only reaches what it may."""

from app.core.db import get_conn

ADMIN, VIEWER, EDITOR = (
    "test-rbac-admin@example.invalid",
    "test-rbac-viewer@example.invalid",
    "test-rbac-editor@example.invalid",
)
PASSWORD, TEMP, NEW = "admin-pass-123", "temp-pass-123", "my-own-pass-456"
JOB_KEY = "example.org/jobs/test-rbac-delete"


def test_roles(make_user, sign_in):
    make_user(ADMIN, PASSWORD)
    try:
        _flow(sign_in)
    finally:
        with get_conn() as conn:
            conn.execute("DELETE FROM public.admin_users WHERE email = ANY(%s)", ([VIEWER, EDITOR],))
            conn.execute("DELETE FROM public.church_jobs WHERE url_key = %s", (JOB_KEY,))


def _flow(sign_in):
    a, _ = sign_in(ADMIN, PASSWORD)
    assert a.post("/api/admin/users", json={"email": VIEWER, "role": "viewer", "password": TEMP}).status_code == 200
    assert (
        a.post("/api/admin/users", json={"email": EDITOR.upper(), "role": "editor", "password": TEMP}).status_code
        == 200
    )
    assert a.post("/api/admin/users", json={"email": VIEWER, "role": "viewer", "password": TEMP}).status_code == 409
    assert (
        a.post("/api/admin/users", json={"email": "x@example.invalid", "role": "admin", "password": TEMP}).status_code
        == 422
    )
    assert (
        a.post(
            "/api/admin/users", json={"email": "x@example.invalid", "role": "viewer", "password": "short"}
        ).status_code
        == 422
    )
    assert (
        a.patch(f"/api/admin/users/{ADMIN}", json={"role": "viewer"}).status_code == 403
    )  # admins aren't managed here
    users = {u["email"]: u for u in a.get("/api/admin/users").json()}
    assert (
        users[EDITOR]["role"] == "editor"
        and users[EDITOR]["must_change_password"]
        and users[EDITOR]["created_by"] == ADMIN
    )

    # A new user must change the one-time password before anything else.
    v, me = sign_in(VIEWER, TEMP)
    assert me == {"email": VIEWER, "role": "viewer", "must_change_password": True}
    assert v.get("/api/jobs").status_code == 403
    assert v.post("/api/admin/password", json={"current_password": TEMP, "new_password": TEMP}).status_code == 422
    assert (
        v.post("/api/admin/password", json={"current_password": "wrong-pass", "new_password": NEW}).status_code == 401
    )
    assert v.post("/api/admin/password", json={"current_password": TEMP, "new_password": NEW}).status_code == 200
    assert v.get("/api/admin/me").json()["must_change_password"] is False

    # Viewer: reads only.
    assert v.get("/api/jobs?source=churches").status_code == 200
    for method, path in [
        ("post", "/api/admin/extract"),
        ("post", "/api/admin/jobs"),
        ("delete", f"/api/admin/jobs?source=churches&id={JOB_KEY}"),
        ("get", "/api/admin/users"),
        ("post", "/api/admin/users"),
        ("get", "/api/admin/costs"),
        ("get", "/api/admin/leads"),
        ("get", "/api/admin/settings"),
        ("post", "/api/admin/settings/test-email"),
    ]:
        assert getattr(v, method)(path, **({"json": {}} if method == "post" else {})).status_code == 403, path

    # Editor: reads, adds and deletes jobs; can't manage users or see costs.
    e, _ = sign_in(EDITOR, TEMP)
    assert e.post("/api/admin/password", json={"current_password": TEMP, "new_password": NEW}).status_code == 200
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO public.church_jobs (url_key, job_url, job_title) VALUES (%s, %s, 'Test job')",
            (JOB_KEY, "https://" + JOB_KEY),
        )
    assert e.delete(f"/api/admin/jobs?source=churches&id={JOB_KEY}").status_code == 200
    assert e.delete(f"/api/admin/jobs?source=churches&id={JOB_KEY}").status_code == 404
    assert (
        e.post("/api/admin/users", json={"email": "x@example.invalid", "role": "viewer", "password": TEMP}).status_code
        == 403
    )
    assert e.get("/api/admin/costs").status_code == 403
    assert e.get("/api/admin/leads").status_code == 403
    assert e.delete("/api/admin/leads/x@example.invalid").status_code == 403

    # Admin resets a password: the user is signed out and must change it again; then promotes and removes users.
    assert a.patch(f"/api/admin/users/{VIEWER}", json={"password": "another-temp-1"}).status_code == 200
    assert v.get("/api/jobs").status_code == 401
    _, me = sign_in(VIEWER, "another-temp-1")
    assert me["must_change_password"] is True
    assert a.patch(f"/api/admin/users/{VIEWER}", json={"role": "editor"}).status_code == 200
    assert a.delete(f"/api/admin/users/{VIEWER}").status_code == 200
    assert a.delete(f"/api/admin/users/{VIEWER}").status_code == 404
