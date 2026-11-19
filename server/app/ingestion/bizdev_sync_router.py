"""Admin → Settings: the links the weekly BizDev sync downloads, and a button to run it now."""

import logging
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.dependencies import require_admin
from app.core.settings_store import get_setting, set_setting
from app.ingestion import bizdev_sync as sync
from app.jobs.repository import BizdevSource

log = logging.getLogger("admin")

router = APIRouter(prefix="/api/admin/bizdev-sync", tags=["bizdev-sync"], dependencies=[Depends(require_admin)])


class SheetLink(BaseModel):
    kind: Literal["churches", "nonprofits"]
    url: str = Field(max_length=4000)  # empty removes the link


def _state() -> dict[str, Any]:
    return {
        "links": {kind: sync.safe_link(get_setting(key)) for kind, key in sync.URL_KEYS.items()},
        "status": get_setting(sync.STATUS_KEY),
        "enrich": get_setting(sync.ENRICH_KEY),
        "running": sync.is_running(),
    }


@router.get("", response_model=None)
def get_sync() -> dict[str, Any]:
    return _state()


@router.post("", response_model=None)
def save_link(body: SheetLink, admin: str = Depends(require_admin)) -> dict[str, Any]:
    kind: BizdevSource = body.kind
    url = body.url.strip()
    if url:
        try:
            sync.check_link(url)
        except ValueError as e:
            raise HTTPException(422, str(e)) from e
    set_setting(sync.URL_KEYS[kind], url, by=admin)
    log.info("BizDev %s link %s by %s", kind, "saved" if url else "removed", admin)
    return _state()


@router.post("/run", response_model=None)
def run_sync(tasks: BackgroundTasks, admin: str = Depends(require_admin)) -> dict[str, Any]:
    if sync.is_running():
        raise HTTPException(409, "A sync is already in progress.")
    if not sync.has_link():
        raise HTTPException(400, "Save a link first.")
    log.info("BizDev sync started by %s", admin)
    tasks.add_task(sync.run_now)
    return {**_state(), "running": True}
