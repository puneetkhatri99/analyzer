import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.ai_usage.service import MAX_DELETE, budget, costs_report, delete_calls, list_calls, set_limit
from app.auth.dependencies import require_admin

log = logging.getLogger("admin")

router = APIRouter(prefix="/api/admin", tags=["ai usage"], dependencies=[Depends(require_admin)])


DATE = r"^(\d{4}-\d{2}-\d{2})?$"


class Filters(BaseModel):
    purpose: str = Field(default="", max_length=40)
    run: str = Field(default="", max_length=60)  # a run's ID, or "none" for calls made outside a feed run
    date_from: str = Field(default="", pattern=DATE)
    date_to: str = Field(default="", pattern=DATE)
    q: str = Field(default="", max_length=200)


class DeleteIds(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=MAX_DELETE)


@router.get("/costs", response_model=None)
def costs() -> dict[str, Any]:
    return costs_report()


class Limit(BaseModel):
    limit_usd: float | None = Field(gt=0, le=100_000)  # dollars a month; null removes the limit


@router.patch("/costs/limit", response_model=None)
def save_limit(body: Limit, admin: str = Depends(require_admin)) -> dict[str, Any]:
    """The monthly AI spending limit: once this month's estimated spend reaches it, nothing calls OpenAI."""
    set_limit(body.limit_usd, admin)
    log.info("Monthly AI limit set to %s by %s", f"${body.limit_usd:.2f}" if body.limit_usd else "no limit", admin)
    return budget()


@router.get("/costs/calls", response_model=None)
def calls(
    purpose: str = Query("", max_length=40),
    run: str = Query("", max_length=60),
    date_from: str = Query("", pattern=DATE),
    date_to: str = Query("", pattern=DATE),
    q: str = Query("", max_length=200),
    page: int = Query(1, ge=1),
) -> dict[str, Any]:
    f = {"purpose": purpose, "run": run, "date_from": date_from, "date_to": date_to, "q": q}
    _real_dates(f)
    return list_calls(f, page)


def _real_dates(f: dict[str, Any]) -> None:
    """The pattern lets 2026-02-30 through; Postgres would then fail the whole request."""
    for key in ("date_from", "date_to"):
        try:
            if f[key]:
                date.fromisoformat(f[key])
        except ValueError:
            raise HTTPException(422, f"{key} isn't a real date") from None


@router.post("/costs/calls/delete", response_model=None)
def delete_selected(body: DeleteIds, admin: str = Depends(require_admin)) -> dict[str, int]:
    n = delete_calls(ids=body.ids)
    log.warning("AI usage: %d call(s) deleted by %s", n, admin)
    return {"deleted": n}


@router.post("/costs/calls/delete-matching", response_model=None)
def delete_matching(body: Filters, admin: str = Depends(require_admin)) -> dict[str, int]:
    _real_dates(body.model_dump())
    n = delete_calls(filters=body.model_dump())
    log.warning("AI usage: %d call(s) matching %s deleted by %s", n, body.model_dump(exclude_defaults=True), admin)
    return {"deleted": n}
