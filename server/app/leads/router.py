"""Public: sign-up before the report (brief P2)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.db import get_conn
from app.shared.email import is_valid_email, normalize_email

router = APIRouter(prefix="/api/leads", tags=["leads"])


class Lead(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(max_length=320)
    organization: str = Field(min_length=1, max_length=300)
    role: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    attendance: str | None = Field(default=None, max_length=100)


@router.post("")
def save_lead(lead: Lead) -> dict[str, bool]:
    """A returning email updates its row instead of adding one."""
    email = normalize_email(lead.email)
    if not is_valid_email(email):
        raise HTTPException(422, "Please enter a valid email address.")
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO public.leads (email, name, organization, role, location, attendance)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name, organization = EXCLUDED.organization,
                 role = EXCLUDED.role, location = EXCLUDED.location, attendance = EXCLUDED.attendance,
                 last_seen_at = now()""",
            (email, lead.name.strip(), lead.organization.strip(), lead.role, lead.location, lead.attendance),
        )
    return {"ok": True}
