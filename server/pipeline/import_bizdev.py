"""Load the BizDev Excel lead sheets into church_jobs / nonprofit_jobs.

Usage (from the server/ directory, settings read from server/.env):
  python -m pipeline.import_bizdev churches "../data/API BizDev_ Churches.xlsx"
  python -m pipeline.import_bizdev nonprofits "../data/API BizDev_ Nonprofits (Actual).xlsx"

Every tab is read (the main sheet and the weekly tabs) and rows are merged by job URL.
Re-running updates the Excel columns and leaves the fetched columns alone.
"""
import argparse
import logging
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit

import openpyxl

from app.db import get_conn
from app.logs import script_log

log = logging.getLogger("import_bizdev")
TABLES = {"churches": "church_jobs", "nonprofits": "nonprofit_jobs"}
SCHEMA = Path(__file__).resolve().parent.parent / "database" / "sources.sql"

# column in the table -> start of the Excel header (the two files differ: "Church/ ..." vs "Nonprofit/ ...")
HEADERS = {
    "contact_first_name": "first name", "contact_last_name": "last name", "contact_title": "contact's job title",
    "contact_email": "email", "org_name": "church/ organization name|nonprofit/organization name",
    "city": "city", "state": "state", "job_title": "job title", "job_url": "job post url",
    "org_website": "church website url|nonprofit website url", "date_posted": "job date posted", "note": "note",
}


def url_key(u: str) -> str:
    p = urlsplit(u.strip().lower())
    return p.netloc.removeprefix("www.") + p.path.rstrip("/")


def to_date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            d = datetime.strptime(str(v).strip(), fmt).date()
            return d if d.year >= 2000 else None  # typos like 10/22/0202
        except ValueError:
            pass
    return None


def clean(v):
    s = str(v).strip() if v is not None else ""
    return s or None


def read_rows(path: str) -> dict[str, dict]:
    wb = openpyxl.load_workbook(path, read_only=True)
    rows: dict[str, dict] = {}
    for ws in wb.worksheets:
        it = ws.iter_rows(values_only=True)
        header = [str(h or "").strip().lower() for h in next(it, [])]
        col = {}
        for field, names in HEADERS.items():
            col[field] = next((i for i, h in enumerate(header) if any(h.startswith(n) for n in names.split("|"))), None)
        if col["job_url"] is None:
            continue
        for r in it:
            get = lambda f: r[col[f]] if col[f] is not None and col[f] < len(r) else None
            u = clean(get("job_url"))
            if not u:
                continue
            rec = {f: clean(get(f)) for f in HEADERS if f != "date_posted"}
            rec["date_posted"] = to_date(get("date_posted")) if get("date_posted") else None
            k = url_key(u)
            if k in rows:  # same job on several tabs: keep the first values, fill gaps, record the tab
                old = rows[k]
                for f, v in rec.items():
                    old[f] = old[f] or v
                old["sheets"].append(ws.title)
            else:
                rows[k] = {**rec, "url_key": k, "sheets": [ws.title]}
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=TABLES)
    ap.add_argument("xlsx")
    args = ap.parse_args()
    table = TABLES[args.kind]
    script_log("import_bizdev")  # counts only: the sheets' contact names and emails are never logged

    rows = read_rows(args.xlsx)
    log.info("Read %d distinct jobs (merged by job URL) from every tab of %s", len(rows), args.xlsx)
    fields = ["url_key", *HEADERS, "sheets"]
    updates = ", ".join(f"{f} = EXCLUDED.{f}" for f in fields if f != "url_key")
    sql = (f"INSERT INTO public.{table} ({', '.join(fields)}) VALUES ({', '.join(['%s'] * len(fields))}) "
           f"ON CONFLICT (url_key) DO UPDATE SET {updates}")

    with get_conn() as conn:
        conn.execute(SCHEMA.read_text(encoding="utf-8"))
        with conn.cursor() as cur:
            cur.executemany(sql, [[r[f] for f in fields] for r in rows.values()])
        total = conn.execute(f"SELECT count(*) FROM public.{table}").fetchone()[0]
    log.info("%s: upserted %d jobs from %s; table now has %d rows", table, len(rows), args.xlsx, total)


if __name__ == "__main__":
    main()
