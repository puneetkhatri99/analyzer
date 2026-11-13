"""Load a church-jobs JSON feed into Postgres: companies, postings, and a pay snapshot per pull date.

Usage (from the server/ directory, settings read from server/.env):
  python -m pipeline.ingest data/raw/church_jobs_feed_02.10.26.json [--pull-date 2026-11-04] [--limit 500]

The dashboard works out each job's role from its title (app/roles.py) when it loads.
"""
import argparse
import json
import logging
from datetime import date

from app.db import get_conn
from app.logs import script_log
from pipeline import repository as db
from pipeline.enrich import parse_salary

log = logging.getLogger("ingest")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_file")
    ap.add_argument("--pull-date", default=date.today().isoformat())
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    script_log("ingest")

    with open(args.json_file, encoding="utf-8") as f:
        jobs = json.load(f)
    if args.limit is not None:  # --limit 0 means none, not all
        jobs = jobs[:args.limit]
    log.info("Loading %d postings from %s (pull date %s)", len(jobs), args.json_file, args.pull_date)

    conn = get_conn()

    for i, job in enumerate(jobs):
        company_uuid = job.get("company_uuid")
        post_uuid = job.get("post_uuid")
        if not post_uuid:
            log.warning("Posting %d skipped: it has no post_uuid (%s)", i + 1, job.get("job_name") or "untitled")
            continue

        if company_uuid:
            db.upsert_company(
                conn, company_uuid, job.get("company_name"), job.get("company_url"),
                job.get("logo_url"), json.dumps(job.get("company_categories")),
            )

        raw_title = job.get("job_name") or ""
        db.upsert_posting(conn, {
            "post_uuid": post_uuid,
            "company_uuid": company_uuid,
            "job_name_raw": raw_title,
            "department": job.get("department"),
            "hours": job.get("hours"),
            "seniority": job.get("seniority"),
            "education": job.get("education"),
            "remote": job.get("remote"),
            "board_source": job.get("board_source"),
            "post_url": job.get("post_url"),
            "job_location": job.get("job_location"),
            "city": job.get("city"),
            "region": job.get("region"),
            "country": job.get("country"),
            "language": job.get("language"),
            "first_indexed": job.get("first_indexed"),
        })

        salary = parse_salary(job.get("comp_range"))
        db.upsert_snapshot(conn, {
            "post_uuid": post_uuid,
            "pull_date": args.pull_date,
            "comp_range_raw": job.get("comp_range"),
            "comp_est_raw": job.get("comp_est"),
            "salary_min": salary["salary_min"],
            "salary_max": salary["salary_max"],
            "salary_period": salary["salary_period"],
            "last_indexed": job.get("last_indexed"),
            "is_active": True,
        })
        log.debug("Posting %s: %s | %s | pay %s", post_uuid, raw_title, job.get("company_name") or "-",
                  job.get("comp_range") or "-")

        if (i + 1) % 100 == 0:
            log.info("%d/%d postings processed", i + 1, len(jobs))

    log.info("Done. %d postings loaded.", len(jobs))


if __name__ == "__main__":
    main()
