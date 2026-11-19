"""Admin → Settings: the feed link the daily job downloads, and a button to run it now."""

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.dependencies import require_admin
from app.core.settings_store import get_setting, set_setting
from app.ingestion import daily_feed as feed
from app.shared.email import email_ready

log = logging.getLogger("admin")

router = APIRouter(prefix="/api/admin/feed", tags=["feed"], dependencies=[Depends(require_admin)])


class FeedLink(BaseModel):
    url: str = Field(min_length=10, max_length=4000)


def _state() -> dict[str, Any]:
    return {
        **feed.link_state(feed.feed_url()),
        "status": get_setting(feed.STATUS_KEY),
        "running": feed.is_running(),
        "live": dict(feed.live) if feed.is_running() else None,
        "email_ready": email_ready(),
    }


@router.get("", response_model=None)
def get_feed() -> dict[str, Any]:
    return _state()


@router.post("", response_model=None)
def save_feed(body: FeedLink, admin: str = Depends(require_admin)) -> dict[str, Any]:
    url = body.url.strip()
    try:
        feed.check_feed_url(url)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    set_setting(feed.URL_KEY, url, by=admin)
    feed.forget_today()  # the timer may try again today with the new link
    log.info("Feed link changed by %s (expires %s)", admin, feed.link_state(url)["expires_at"])
    return _state()


@router.post("/run", response_model=None)
def run_feed(tasks: BackgroundTasks, admin: str = Depends(require_admin)) -> dict[str, Any]:
    if feed.is_running():
        raise HTTPException(409, "A run is already in progress.")
    if not feed.feed_url():
        raise HTTPException(400, "Save a feed link first.")
    log.info("Feed run started by %s", admin)
    tasks.add_task(feed.run_and_record, force=True)
    return {**_state(), "running": True}
