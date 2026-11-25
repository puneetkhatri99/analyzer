"""bizdev-sync: once a week, download the two BizDev workbooks (churches, nonprofits) from the links saved in
Admin → Settings and add the jobs that aren't in church_jobs / nonprofit_jobs yet. Jobs already there are matched by
job URL; a value the sheet leaves blank never erases one already saved (see import_file in bizdev.py).

  python -m app.cli bizdev-sync             # download once a week (first check of a new week, after FEED_HOUR_UTC),
                                            # then fill in the gaps with AI once a day (bizdev_enrich.py)
  python -m app.cli bizdev-sync --force     # both, now

A link can be a Google Sheets share link (it is turned into an .xlsx download) or any https link that serves an .xlsx
file. A private Google Sheet works too once it is shared, as Viewer, with the server's own Google account (a key file
on EC2, see DEPLOY_EC2.md; read-only, see google_account). Only counts are logged and shown: the sheets' contact names
and emails never are.
"""

import argparse
import logging
import os
import re
import tempfile
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import google.auth
import requests
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request

from app.ai_usage.service import current_run
from app.core.config import get_settings
from app.core.logs import script_log
from app.core.settings_store import get_setting, set_setting
from app.ingestion import bizdev_enrich, daily_feed
from app.ingestion.bizdev import import_file
from app.shared.tables import BIZDEV_TABLES
from app.shared.web import UnsafeURLError, get_public

log = logging.getLogger("bizdev_sync")

URL_KEYS = {kind: f"bizdev_url_{kind}" for kind in BIZDEV_TABLES}
STATUS_KEY = "bizdev_sync_status"
DONE_KEY = "bizdev_sync_done_for"  # the ISO week ("2026-W47") that was synced
ENRICH_KEY = "bizdev_enrich_status"
ENRICH_DONE_KEY = "bizdev_enrich_done_for"  # the day the AI step last ran
TRIED_KEY = "bizdev_sync_tried_on"  # the last day a run was tried, so a failure is retried tomorrow, not every 15 min
CHECK_EVERY = 15 * 60
MAX_BYTES = 50 * 1024 * 1024
GOOGLE_SHEET = re.compile(r"^https://docs\.google\.com/spreadsheets/d/([\w-]+)")
# The server's own Google account asks for a read-only token: it can download a sheet, never change one.
DRIVE_READ_ONLY = "https://www.googleapis.com/auth/drive.readonly"
DRIVE_FILES = "https://www.googleapis.com/drive/v3/files"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_running = threading.Lock()


class SyncError(Exception):
    """A message an admin can act on."""


def download_url(link: str) -> str:
    """The address that serves the workbook: a Google Sheets share link becomes its .xlsx export."""
    m = GOOGLE_SHEET.match(link.strip())
    return f"https://docs.google.com/spreadsheets/d/{m[1]}/export?format=xlsx" if m else link.strip()


def check_link(link: str) -> None:
    """Raise ValueError unless `link` is an https address."""
    parts = urlsplit(link.strip())
    if parts.scheme != "https" or not parts.hostname:
        raise ValueError("The link must start with https://")


def safe_link(link: str | None) -> str | None:
    """What the admin page shows: no query string, which may hold the share key."""
    if not link:
        return None
    p = urlsplit(link)
    return f"{p.scheme}://{p.netloc}{p.path}"


def google_account() -> tuple[str, str] | None:
    """(email, read-only token) of the server's own Google account, or None when it has none. On EC2 the account is
    the key file GOOGLE_APPLICATION_CREDENTIALS names; on Cloud Run it is the service's built-in one."""
    try:
        creds, _ = google.auth.default(scopes=[DRIVE_READ_ONLY])
        creds.refresh(Request())
    except GoogleAuthError as e:
        if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):  # a key file was meant to be used: say why it wasn't
            log.warning("Google key file not usable (%s): only sheets shared with anyone can be read", e)
        return None
    return getattr(creds, "service_account_email", None) or "the app's Google account", creds.token


def drive_download(file_id: str, email: str, token: str) -> requests.Response | None:
    """A sheet shared with the server's account, through Google Drive: a Google Sheet is exported as .xlsx, an
    uploaded .xlsx is downloaded as it is. None when Drive refuses it (then the link itself is tried).
    shortcut: Drive exports stop at 10 MB (the sheets are about 1 MB); download the file directly if they outgrow it."""
    auth = {"Authorization": f"Bearer {token}"}
    url = f"{DRIVE_FILES}/{file_id}"
    try:
        r = requests.get(url, params={"fields": "mimeType", "supportsAllDrives": "true"}, headers=auth, timeout=30)
        if r.ok and r.json().get("mimeType") == "application/vnd.google-apps.spreadsheet":
            r = requests.get(f"{url}/export", params={"mimeType": XLSX}, headers=auth, timeout=(10, 120))
        elif r.ok:
            r = requests.get(url, params={"alt": "media", "supportsAllDrives": "true"}, headers=auth, timeout=(10, 120))
    except (requests.RequestException, ValueError) as e:
        log.warning("Google Drive unreachable as %s (%s): trying the link itself", email, e.__class__.__name__)
        return None
    if not r.ok:
        log.warning("Google Drive refused the sheet as %s (%d %s): trying the link itself", email, r.status_code,
                    r.text[:300])  # fmt: skip
        return None
    log.info("Sheet read through Google Drive as %s", email)
    return r


def fetch(link: str, dest: Path) -> None:
    """Save the workbook at `link` to `dest`, or raise SyncError. A Google Sheet is first read as the server's own
    Google account (a private sheet shared with it), then through the link (a sheet shared with anyone)."""
    sheet = GOOGLE_SHEET.match(link.strip())
    account = google_account() if sheet else None
    r = drive_download(sheet[1], *account) if sheet and account else None
    if r is None:
        try:
            r = get_public(download_url(link), timeout=(10, 120))
        except UnsafeURLError as e:
            raise SyncError(str(e)) from e
        except requests.RequestException as e:
            raise SyncError(f"Couldn't reach the link ({e.__class__.__name__})") from e
    share = f" To keep it private, share it as Viewer with the app's Google account {account[0]}." if account else ""
    if r.status_code in (401, 403, 404):
        refused = "The link was refused: it is wrong, expired, or not shared with 'anyone with the link'."
        raise SyncError(refused + share)
    if not r.ok:
        raise SyncError(f"The link answered {r.status_code}")
    if len(r.content) > MAX_BYTES:
        raise SyncError("The file is too big")
    if not r.content.startswith(b"PK"):  # an .xlsx is a zip file; a sign-in page is HTML
        raise SyncError(f"The link didn't give an Excel file (is it a sign-in page?).{share}")
    dest.write_bytes(r.content)


def run() -> dict[str, Any]:
    """Sync every kind that has a link. Returns the status that is saved for the admin page."""
    results: dict[str, Any] = {}
    with tempfile.TemporaryDirectory() as tmp:
        for kind, key in URL_KEYS.items():
            link = get_setting(key)
            if not link:
                continue
            try:
                path = Path(tmp) / f"{kind}.xlsx"
                fetch(link, path)
                new, updated = import_file(kind, str(path))
                results[kind] = {"ok": True, "new": new, "updated": updated}
                log.info("%s: %d new jobs, %d already there", BIZDEV_TABLES[kind], new, updated)
            except SyncError as e:
                results[kind] = {"ok": False, "message": str(e)}
                log.error("%s: %s", BIZDEV_TABLES[kind], e)
            except Exception as e:  # a workbook that can't be read must not stop the other one
                results[kind] = {"ok": False, "message": f"The file couldn't be read ({e.__class__.__name__})"}
                log.exception("%s: import failed", BIZDEV_TABLES[kind])
    ok = all(r["ok"] for r in results.values())
    return {"at": datetime.now(UTC).isoformat(), "ok": ok, "kinds": results}


def run_and_record(*, force: bool = False) -> int:
    """0 = fine or nothing due, 1 = a sheet failed. Without force, once per ISO week (retried daily after a failure)."""
    if not has_link():
        return 0
    now = datetime.now(UTC)
    week = f"{now.isocalendar().year}-W{now.isocalendar().week:02d}"
    if not force and (get_setting(DONE_KEY) == week or get_setting(TRIED_KEY) == now.date().isoformat()):
        return 0
    if not _running.acquire(blocking=False):
        return 0
    try:
        status = run()
        set_setting(STATUS_KEY, status, by="bizdev-sync")
        set_setting(TRIED_KEY, now.date().isoformat(), by="bizdev-sync")
        if status["ok"]:
            set_setting(DONE_KEY, week, by="bizdev-sync")
        else:
            bad = "; ".join(f"{k}: {r['message']}" for k, r in status["kinds"].items() if not r["ok"])
            daily_feed.alert_admin(
                "MinistryHub BizDev sheet sync failed",
                f"The weekly BizDev sheet download failed ({bad}).\nCheck the links in Admin → Settings: "
                f"{daily_feed.admin_link()}",
            )
        return 0 if status["ok"] else 1
    finally:
        _running.release()


def enrich_and_record(*, force: bool = False) -> int:
    """The AI step: church size, denomination and pay for what the sheets leave empty. Once a day, capped per run."""
    today = datetime.now(UTC).date().isoformat()
    if not force and get_setting(ENRICH_DONE_KEY) == today:
        return 0
    if not _running.acquire(blocking=False):
        return 0
    try:
        run_id = f"bizdev-{datetime.now(UTC):%Y%m%d-%H%M%S}"
        token = current_run.set(run_id)  # every AI call made below is stored with this ID
        try:
            result: dict[str, Any] = {"ok": True, **bizdev_enrich.run()}
        except Exception as e:  # recorded as today's run: the timer must not redo (and re-pay) it every 15 minutes
            log.exception("BizDev enrichment failed")
            result = {"ok": False, "message": f"The AI step stopped on an error ({e.__class__.__name__})."}
        finally:
            current_run.reset(token)
        result["cost_usd"], result["calls"] = daily_feed.run_cost(run_id)
        result.update(at=datetime.now(UTC).isoformat(), run_id=run_id)
        log.log(logging.INFO if result["ok"] else logging.ERROR, "BizDev enrichment: %s", result)
        set_setting(ENRICH_KEY, result, by="bizdev-sync")
        set_setting(ENRICH_DONE_KEY, today, by="bizdev-sync")
        return 0 if result["ok"] else 1
    finally:
        _running.release()


def is_running() -> bool:
    return _running.locked()


def has_link() -> bool:
    return any(get_setting(key) for key in URL_KEYS.values())


def run_if_due() -> int:
    """The timer's check. Nothing happens, and nothing is paid for, until an admin has saved a sheet link."""
    if not has_link() or datetime.now(UTC).hour < get_settings().feed_hour_utc:
        return 0
    return run_and_record() | enrich_and_record()


def run_now() -> int:
    """Run now: download, then the AI step."""
    return run_and_record(force=True) | enrich_and_record(force=True)


def register(commands: argparse._SubParsersAction) -> None:
    parser = commands.add_parser("bizdev-sync", help="download the two BizDev workbooks and add the new jobs")
    parser.add_argument("--force", action="store_true", help="run now, even if this week was already synced")
    parser.set_defaults(handler=_run)


def _run(args: argparse.Namespace) -> int:
    script_log("bizdev_sync")
    return run_now() if args.force else run_if_due()


def start_scheduler() -> threading.Event:
    """Check every CHECK_EVERY seconds, inside the API process, whether this week's sync is due. Set the returned
    event to stop. shortcut: one timer per server process, like daily_feed's; move to a cron job before scaling out."""
    stop = threading.Event()

    def loop() -> None:
        while True:  # check at once: a free Render service may sleep through Monday and catch up when it wakes
            try:
                run_if_due()
            except Exception:
                log.exception("BizDev sync check failed")
            if stop.wait(CHECK_EVERY):
                return

    threading.Thread(target=loop, name="bizdev-sync", daemon=True).start()
    log.info("BizDev sync: runs once a week, each week from Monday %02d:00 UTC", get_settings().feed_hour_utc)
    return stop
