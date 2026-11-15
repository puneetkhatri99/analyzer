"""Public sign-up: validation, and a returning email updates its row."""

from app.core.db import get_conn


def test_leads(client):
    c = client
    email = "test-lead@example.invalid"
    body = {"name": "Test Person", "email": email.upper(), "organization": "Test Church", "role": "Worship/Music"}
    try:
        assert c.post("/api/leads", json={**body, "email": "not-an-email"}).status_code == 422
        assert c.post("/api/leads", json={**body, "name": ""}).status_code == 422
        assert c.post("/api/leads", json=body).status_code == 200
        assert c.post("/api/leads", json={**body, "organization": "Renamed Church"}).status_code == 200
        with get_conn() as conn:
            rows = conn.execute("SELECT organization FROM public.leads WHERE email = %s", (email,)).fetchall()
        assert rows == [("Renamed Church",)]
    finally:
        with get_conn() as conn:
            conn.execute("DELETE FROM public.leads WHERE email = %s", (email,))
