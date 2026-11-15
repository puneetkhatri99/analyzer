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
    return rows


def register(commands: argparse._SubParsersAction) -> None:
    parser = commands.add_parser("import-bizdev", help="load a BizDev Excel lead sheet")
    parser.add_argument("kind", choices=BIZDEV_TABLES)
    parser.add_argument("xlsx")
    parser.set_defaults(handler=_run)


def _run(args: argparse.Namespace) -> int:
    table = BIZDEV_TABLES[args.kind]
    script_log("import_bizdev")
    rows = read_rows(args.xlsx)
    log.info("Read %d distinct jobs (merged by job URL) from every tab of %s", len(rows), args.xlsx)
    fields = ["url_key", *HEADERS, "sheets"]
    updates = ", ".join(f"{f} = EXCLUDED.{f}" for f in fields if f != "url_key")
    sql = (
        f"INSERT INTO public.{table} ({', '.join(fields)}) VALUES ({', '.join(['%s'] * len(fields))}) "
        f"ON CONFLICT (url_key) DO UPDATE SET {updates}"
    )
    with connect() as conn:
        with conn.transaction(), conn.cursor() as cur:
            cur.executemany(sql, [[r[f] for f in fields] for r in rows.values()])
        total = conn.execute(f"SELECT count(*) FROM public.{table}").fetchone()[0]
    log.info("%s: upserted %d jobs from %s; table now has %d rows", table, len(rows), args.xlsx, total)
    return 0
