"""Logging for every pipeline script and the API: to files in server/logs/ (git-ignored), the screen, and Axiom.
In production (APP_ENV=production) with an Axiom token, the files are skipped: Render wipes its disk on every deploy,
so Axiom is the only log that lasts there.

  Scripts:  script_log("fetch_jobs")  -> server/logs/fetch_jobs-<date>-<time>.log, one file per run
  API:      api_log()                 -> server/logs/api.log, a new file each midnight, 30 days kept
  Axiom:    when AXIOM_TOKEN is set, every line also goes to the AXIOM_DATASET dataset (https://axiom.co), as fields:
            _time, level, logger, message, app, run, env, exception, plus any extra= fields (e.g. status, ms).

Never log passwords, session tokens, the database password, or the spreadsheets' contact names and emails.
On Render the disk is wiped on every deploy, so api.log only lasts until the next deploy there; Axiom keeps everything.
"""

import atexit
import contextvars
import logging
import os
import queue
import sys
import threading
import time
from datetime import UTC, datetime
from logging.handlers import TimedRotatingFileHandler

from app.core.config import SERVER_DIR, Settings, get_settings

LOG_DIR = SERVER_DIR / "logs"
FILE_FORMAT = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
SCREEN_FORMAT = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%H:%M:%S")
QUIET = (
    "urllib3",
    "httpx",
    "httpcore",
    "openai",
    "charset_normalizer",
    "psycopg",
    "multipart",
    "asyncio",
)  # library chatter
# The current API request's ID (set by main.log_requests); RequestIdFilter copies it onto every line that request logs.
request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
_STANDARD = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime", "taskName"}  # LogRecord's own attributes


class RequestIdFilter(logging.Filter):
    """Adds request_id to lines logged while handling an API request, so Axiom can show one request end to end."""

    def filter(self, record):
        if rid := request_id.get():
            record.request_id = rid
        return True


class AxiomShipper(logging.Handler):
    """Sends log lines to Axiom from a background thread, in batches every 2 seconds.

    Logging only puts the line in a queue, so a request never waits on Axiom. If Axiom can't be reached the
    batch is dropped (the log files still have it) and a note goes to stderr; the app carries on."""

    def __init__(self, token, dataset, app, run=None, interval=2.0):
        super().__init__(logging.DEBUG)
        from axiom_py import Client  # imported only when shipping is on

        self.client, self.dataset, self.interval = Client(token), dataset, interval
        self.fields = {"app": app, "run": run, "env": "render" if os.environ.get("RENDER") else "local"}
        self.queue = queue.SimpleQueue()
        self.thread = threading.Thread(target=self._run, name="axiom-shipper", daemon=True)
        self.thread.start()
        atexit.register(self.close)  # registered after the client's own hook, so it runs first: the last lines get sent

    def emit(self, record):
        try:
            event = {
                "_time": datetime.fromtimestamp(record.created, UTC).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                **self.fields,
            }
            if record.exc_info:
                event["exception"] = logging.Formatter().formatException(record.exc_info)
            event.update({k: v for k, v in record.__dict__.items() if k not in _STANDARD})  # extra= fields
            self.queue.put(event)
        except Exception:
            self.handleError(record)

    def _run(self):
        done = False
        while not done:
            batch, deadline = [], time.monotonic() + self.interval
            while len(batch) < 1000 and (left := deadline - time.monotonic()) > 0:
                try:
                    item = self.queue.get(timeout=left)
                except queue.Empty:
                    break
                if item is None:  # close() was called
                    done = True
                    break
                batch.append(item)
            if batch:
                self._send(batch)

    def _send(self, batch):
        try:
            self.client.ingest_events(self.dataset, batch)
        except Exception as e:  # never log from here: it would queue more lines about the failure
            sys.stderr.write(
                f"Axiom: {len(batch)} log lines not sent ({e.__class__.__name__}); the log files still have them\n"
            )

    def close(self):
        if self.thread.is_alive():
            self.queue.put(None)
            self.thread.join(timeout=10)
        super().close()


def writes_files(settings: Settings) -> bool:
    """False only in production with Axiom on: there Axiom keeps the logs and local files would be wiped anyway."""
    return not (settings.axiom_token and settings.app_env == "production")


def _configure(handlers: list[logging.Handler], app: str, level: str, run: str | None = None) -> None:
    """`level` is the default; LOG_LEVEL overrides it (e.g. DEBUG to look into a problem in production)."""
    settings = get_settings()
    if settings.axiom_token:
        handlers.append(AxiomShipper(settings.axiom_token, settings.axiom_dataset, app, run))
    for h in handlers:
        h.addFilter(RequestIdFilter())
    root = logging.getLogger()
    root.setLevel((settings.log_level or level).upper())
    root.handlers[:] = handlers
    for name in QUIET:
        logging.getLogger(name).setLevel(logging.WARNING)


def script_log(name: str, verbose: bool = False) -> str:
    """Send everything this run logs to its own file (all detail), Axiom (all detail) and the screen (INFO and up,
    or all with verbose). Crashes are logged with their full traceback. Returns where to find the log: the file's
    path, or the Axiom dataset and run when files are off."""
    LOG_DIR.mkdir(exist_ok=True)  # also holds collect_last_counts.json, so it's made even when no log file is
    settings = get_settings()
    run = f"{name}-{datetime.now():%Y%m%d-%H%M%S}"
    handlers: list[logging.Handler] = []
    if writes_files(settings):
        file = logging.FileHandler(LOG_DIR / f"{run}.log", encoding="utf-8")
        file.setLevel(logging.DEBUG)
        file.setFormatter(FILE_FORMAT)
        handlers.append(file)
        where = str(LOG_DIR / f"{run}.log")
    else:
        where = f"Axiom dataset {settings.axiom_dataset}, run={run}"
    screen = logging.StreamHandler(sys.stdout)
    screen.setLevel(logging.DEBUG if verbose else logging.INFO)
    screen.setFormatter(SCREEN_FORMAT)
    _configure([*handlers, screen], app=name, level="DEBUG", run=run)
    log = logging.getLogger(name)
    sys.excepthook = lambda *exc: log.critical("Crashed: %s", exc[1], exc_info=exc)
    also = f" | also sent to Axiom ({settings.axiom_dataset})" if settings.axiom_token and handlers else ""
    log.info("Started: %s | log: %s%s", " ".join(sys.argv), where, also)
    return where


def api_log() -> None:
    """The API's log: server/logs/api.log (rotated at midnight, 30 days kept), Axiom, and the screen."""
    handlers: list[logging.Handler] = []
    if writes_files(get_settings()):
        LOG_DIR.mkdir(exist_ok=True)
        file = TimedRotatingFileHandler(LOG_DIR / "api.log", when="midnight", backupCount=30, encoding="utf-8")
        file.setFormatter(FILE_FORMAT)
        handlers.append(file)
    screen = logging.StreamHandler(sys.stdout)
    screen.setFormatter(SCREEN_FORMAT)
    _configure([*handlers, screen], app="api", level="INFO")
    logging.getLogger("uvicorn.access").disabled = True  # main.log_requests already logs every request
