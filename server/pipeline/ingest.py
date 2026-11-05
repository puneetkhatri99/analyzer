"""Load a church-jobs JSON feed into Postgres, enriching each posting with
canonical role, denomination, and church size along the way.

Usage (from the server/ directory, settings read from server/.env):
  python -m pipeline.ingest data/raw/church_jobs_feed_02.10.26.json [--pull-date 2026-11-04] [--limit 500]

Without ANTHROPIC_API_KEY, postings, location and salary still load; role,
denomination and church size stay null until a later run with the key set.
"""
import argparse
import json
import sys
from datetime import date

from bs4 import BeautifulSoup

from app.config import ANTHROPIC_API_KEY
from app.db import get_conn
from pipeline import repository as db
from pipeline.enrich import MODEL, classify_title, extract_church_info, parse_salary
from pipeline.fetch_company import fetch_company_text

HAS_LLM = bool(ANTHROPIC_API_KEY)


def html_to_text(html: str, limit: int = 3000) -> str:
    if not html:
        return ""
    return " ".join(BeautifulSoup(html, "html.parser").get_text(separator=" ").split())[:limit]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_file")
    ap.add_argument("--pull-date", default=date.today().isoformat())
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    with open(args.json_file, encoding="utf-8") as f:
        jobs = json.load(f)
    if args.limit:
        jobs = jobs[:args.limit]

    conn = get_conn()
    n_companies_enriched = 0
    n_titles_classified = 0

    for i, job in enumerate(jobs):
        company_uuid = job.get("company_uuid")
        post_uuid = job.get("post_uuid")
        if not post_uuid:
            continue

        # --- company + enrichment (once per company, cached) ---
        if company_uuid:
            db.upsert_company(
                conn, company_uuid, job.get("company_name"), job.get("company_url"),
                job.get("logo_url"), json.dumps(job.get("company_categories")),
            )
            if HAS_LLM and db.needs_enrichment(conn, company_uuid):
                website_text = fetch_company_text(job.get("company_url"))
                info = extract_church_info(
                    job.get("company_name") or "",
                    html_to_text(job.get("post_html")),
                    website_text,
                )
                db.save_company_enrichment(
                    conn, company_uuid,
                    info.get("denomination"), info.get("church_size"),
                    info.get("church_size_source"), MODEL,
                )
                n_companies_enriched += 1

        # --- title classification (once per distinct raw title, cached) ---
        # Left null when no API key is set yet; a later re-run (same JSON,
        # idempotent upserts) fills it in once ANTHROPIC_API_KEY is provided.
        raw_title = job.get("job_name") or ""
        canonical_role = db.get_cached_title(conn, raw_title)
        if canonical_role is None and HAS_LLM:
            canonical_role, confidence = classify_title(raw_title)
            db.save_title_classification(conn, raw_title, canonical_role, confidence)
            n_titles_classified += 1

        db.upsert_posting(conn, {
            "post_uuid": post_uuid,
            "company_uuid": company_uuid,
            "job_name_raw": raw_title,
            "canonical_role": canonical_role,
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

        if (i + 1) % 100 == 0:
            print(f"{i + 1}/{len(jobs)} postings processed", file=sys.stderr)

    print(f"Done. {len(jobs)} postings, {n_companies_enriched} companies enriched, "
          f"{n_titles_classified} new titles classified.")


if __name__ == "__main__":
    main()
