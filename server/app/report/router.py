"""Public: the report (summary figures only; brief P5-P7)."""

from typing import Any, Literal

from fastapi import APIRouter, Query

from app.report import service

router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("/options", response_model=None)
def report_options() -> dict[str, Any]:
    return service.report_options()


@router.get("", response_model=None)
def get_report(
    role: list[str] = Query(default=[]),
    state: list[str] = Query(default=[]),
    size: list[str] = Query(default=[]),
    denomination: list[str] = Query(default=[]),
    type: Literal["full-time", "part-time"] = "full-time",  # noqa: A002 - the public query parameter's name
) -> dict[str, Any]:
    return service.build_report(
        {"role": role, "state": state, "size": size, "denomination": denomination, "type": type}
    )
