"""Database writes for the ingestion pipeline."""
from datetime import datetime, timedelta, timezone

ENRICH_STALE_DAYS = 90  # denomination/size rarely change; don't re-fetch every run


def get_cached_title(conn, raw_title: str) -> str | None:
    row = conn.execute(
        "SELECT canonical_role FROM title_classifications WHERE job_name_raw = %s", (raw_title,)
    ).fetchone()
    return row[0] if row else None


def save_title_classification(conn, raw_title: str, canonical_role: str, confidence: float):
    conn.execute(
        """INSERT INTO title_classifications (job_name_raw, canonical_role, confidence)
           VALUES (%s, %s, %s)
           ON CONFLICT (job_name_raw) DO UPDATE
             SET canonical_role = EXCLUDED.canonical_role, confidence = EXCLUDED.confidence""",
        (raw_title, canonical_role, confidence),
    )


def needs_enrichment(conn, company_uuid: str) -> bool:
    row = conn.execute(
        "SELECT enriched_at FROM companies WHERE company_uuid = %s", (company_uuid,)
    ).fetchone()
    if row is None or row[0] is None:
        return True
    return row[0] < datetime.now(timezone.utc) - timedelta(days=ENRICH_STALE_DAYS)


def upsert_company(conn, company_uuid, company_name, company_url, logo_url, company_categories):
    conn.execute(
        """INSERT INTO companies (company_uuid, company_name, company_url, logo_url, company_categories)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (company_uuid) DO UPDATE
             SET company_name = EXCLUDED.company_name,
                 company_url = EXCLUDED.company_url,
                 logo_url = EXCLUDED.logo_url,
                 company_categories = EXCLUDED.company_categories""",
        (company_uuid, company_name, company_url, logo_url, company_categories),
    )


def save_company_enrichment(conn, company_uuid, denomination, church_size, church_size_source, model):
    conn.execute(
        """UPDATE companies
           SET denomination = %s, church_size = %s, church_size_source = %s,
               enriched_at = now(), enrichment_model = %s
           WHERE company_uuid = %s""",
        (denomination, church_size, church_size_source, model, company_uuid),
    )


def upsert_posting(conn, p: dict):
    conn.execute(
        """INSERT INTO postings (post_uuid, company_uuid, job_name_raw, canonical_role, department,
                hours, seniority, education, remote, board_source, post_url, job_location,
                city, region, country, language, first_indexed)
           VALUES (%(post_uuid)s, %(company_uuid)s, %(job_name_raw)s, %(canonical_role)s, %(department)s,
                %(hours)s, %(seniority)s, %(education)s, %(remote)s, %(board_source)s, %(post_url)s,
                %(job_location)s, %(city)s, %(region)s, %(country)s, %(language)s, %(first_indexed)s)
           ON CONFLICT (post_uuid) DO UPDATE
             SET canonical_role = EXCLUDED.canonical_role""",
        p,
    )


def upsert_snapshot(conn, s: dict):
    conn.execute(
        """INSERT INTO posting_snapshots (post_uuid, pull_date, comp_range_raw, comp_est_raw,
                salary_min, salary_max, salary_period, last_indexed, is_active)
           VALUES (%(post_uuid)s, %(pull_date)s, %(comp_range_raw)s, %(comp_est_raw)s,
                %(salary_min)s, %(salary_max)s, %(salary_period)s, %(last_indexed)s, %(is_active)s)
           ON CONFLICT (post_uuid, pull_date) DO UPDATE
             SET comp_range_raw = EXCLUDED.comp_range_raw, comp_est_raw = EXCLUDED.comp_est_raw,
                 salary_min = EXCLUDED.salary_min, salary_max = EXCLUDED.salary_max,
                 salary_period = EXCLUDED.salary_period, last_indexed = EXCLUDED.last_indexed,
                 is_active = EXCLUDED.is_active""",
        s,
    )
