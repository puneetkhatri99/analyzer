"""import-bizdev: load a BizDev Excel lead sheet into church_jobs / nonprofit_jobs.

  python -m app.cli import-bizdev churches "../data/API BizDev_ Churches.xlsx"
  python -m app.cli import-bizdev nonprofits "../data/API BizDev_ Nonprofits (Actual).xlsx"

Every tab is read (the main sheet and the weekly tabs) and rows are merged by job URL.
Re-running updates the Excel columns and leaves the columns filled by check-jobs alone.
Only counts are logged: the sheets' contact names and emails never are.
"""

import argparse
import logging
from typing import Any

import openpyxl

from app.core.db import connect
from app.core.logs import script_log
from app.jobs.repository import BIZDEV_TABLES
from app.shared.dates import to_date
from app.shared.web import url_key

log = logging.getLogger("import_bizdev")

# column in the table -> start of the Excel header (the two files differ: "Church/ ..." vs "Nonprofit/ ...")
HEADERS = {
    "contact_first_name": "first name", "contact_last_name": "last name", "contact_title": "contact's job title",
    "contact_email": "email", "org_name": "church/ organization name|nonprofit/organization name",
    "city": "city", "state": "state", "job_title": "job title", "job_url": "job post url",
    "org_website": "church website url|nonprofit website url", "date_posted": "job date posted", "note": "note",
}  # fmt: skip


def clean(value: Any) -> str | None:
    s = str(value).strip() if value is not None else ""
    return s or None


def read_rows(path: str) -> dict[str, dict[str, Any]]:
    """Every job in the workbook, keyed by url_key."""
    wb = openpyxl.load_workbook(path, read_only=True)
    rows: dict[str, dict[str, Any]] = {}
    for ws in wb.worksheets:
        it = ws.iter_rows(values_only=True)
        header = [str(h or "").strip().lower() for h in next(it, [])]
        col = {
            field: next((i for i, h in enumerate(header) if any(h.startswith(n) for n in names.split("|"))), None)
            for field, names in HEADERS.items()
        }
        if col["job_url"] is None:
            continue
        for r in it:
            cells = {field: r[i] if i is not None and i < len(r) else None for field, i in col.items()}
            url = clean(cells["job_url"])
            if not url:
                continue
            rec = {f: clean(cells[f]) for f in HEADERS if f != "date_posted"}
            rec["date_posted"] = to_date(cells["date_posted"]) if cells["date_posted"] else None
            key = url_key(url)
            if key in rows:  # same job on several tabs: keep the first values, fill gaps, record the tab
                old = rows[key]
                for f, v in rec.items():
                    old[f] = old[f] or v
                old["sheets"].append(ws.title)
            else:
                rows[key] = {**rec, "url_key": key, "sheets": [ws.title]}
    wb.close()
    return rows


def register(commands: argparse._SubParsersAction) -> None:
    parser = commands.add_parser("import-bizdev", help="load a BizDev Excel lead sheet")
    parser.add_argument("kind", choices=BIZDEV_TABLES)
    parser.add_argument("xlsx")
    parser.set_defaults(handler=_run)


def import_file(kind: str, path: str) -> tuple[int, int]:
    """Merge one workbook into its table; returns (jobs new to the table, jobs already there that were updated)."""
    table = BIZDEV_TABLES[kind]
    rows = read_rows(path)
    fields = ["url_key", *HEADERS, "sheets"]
    # A job already saved (by an earlier import, the collector or an admin) keeps values the sheet leaves blank,
    # and keeps the tabs it was seen on.
    updates = ", ".join(f"{f} = coalesce(EXCLUDED.{f}, t.{f})" for f in HEADERS)
    sql = (
        f"INSERT INTO public.{table} AS t ({', '.join(fields)}) VALUES ({', '.join(['%s'] * len(fields))}) "
        f"ON CONFLICT (url_key) DO UPDATE SET {updates}, "
        "sheets = ARRAY(SELECT DISTINCT unnest(t.sheets || EXCLUDED.sheets) ORDER BY 1)"
    )
    with connect() as conn:
        before = conn.execute(f"SELECT count(*) FROM public.{table}").fetchone()[0]
        with conn.transaction(), conn.cursor() as cur:
            cur.executemany(sql, [[r[f] for f in fields] for r in rows.values()])
        after = conn.execute(f"SELECT count(*) FROM public.{table}").fetchone()[0]
    return after - before, len(rows) - (after - before)


def _run(args: argparse.Namespace) -> int:
    script_log("import_bizdev")
    new, updated = import_file(args.kind, args.xlsx)
    log.info("%s: %d new jobs, %d already there (updated) from %s", BIZDEV_TABLES[args.kind], new, updated, args.xlsx)
    return 0
