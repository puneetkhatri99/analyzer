"""A BizDev job's contact person: editors and admins only, never in the job lists."""

from app.core.db import get_conn

ROW = "test-contact.invalid/job/1"
EMAIL = "test-contact-admin@example.invalid"


def test_contact_is_for_editors_and_never_in_the_job_list(make_user, sign_in):
    with get_conn() as conn:
        conn.execute("DELETE FROM public.church_jobs WHERE url_key = %s", (ROW,))
        conn.execute(
            """INSERT INTO public.church_jobs (url_key, job_url, job_title, org_name, contact_first_name,
                   contact_last_name, contact_title, contact_email) VALUES (%s, %s, 'Organist', 'Test Church',
                   'Pat', 'Lee', 'Lead Pastor', 'pat@test-contact.invalid')""",
            (ROW, "https://" + ROW),
        )
    try:
        make_user(EMAIL, "a-strong-pass-1", role="viewer")
        viewer, _ = sign_in(EMAIL, "a-strong-pass-1")
        assert viewer.get("/api/admin/jobs/contact", params={"source": "churches", "id": ROW}).status_code == 403
        listed = viewer.get("/api/jobs", params={"source": "churches", "search": "Organist"}).text
        assert "pat@test-contact.invalid" not in listed and "Lead Pastor" not in listed

        make_user(EMAIL, "a-strong-pass-1", role="editor")
        editor, _ = sign_in(EMAIL, "a-strong-pass-1")
        got = editor.get("/api/admin/jobs/contact", params={"source": "churches", "id": ROW})
        assert got.json() == {"first_name": "Pat", "last_name": "Lee", "title": "Lead Pastor",
                              "email": "pat@test-contact.invalid"}  # fmt: skip
        assert editor.get("/api/admin/jobs/contact", params={"source": "churches", "id": "nope"}).status_code == 404
        assert editor.get("/api/admin/jobs/contact", params={"source": "json", "id": ROW}).status_code == 422
    finally:
        with get_conn() as conn:
            conn.execute("DELETE FROM public.church_jobs WHERE url_key = %s", (ROW,))
