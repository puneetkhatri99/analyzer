from typing import Any

from fastapi import APIRouter, Depends

from app.ai_usage.service import costs_report
from app.auth.dependencies import require_admin

router = APIRouter(prefix="/api/admin", tags=["ai usage"])


@router.get("/costs", dependencies=[Depends(require_admin)], response_model=None)
def costs() -> dict[str, Any]:
    return costs_report()
