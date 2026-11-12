"""Database writes for the ingestion pipeline."""


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


def upsert_posting(conn, p: dict):
    # A posting already loaded is left as it was; its pay changes arrive as a new snapshot (upsert_snapshot).
    conn.execute(
        """INSERT INTO postings (post_uuid, company_uuid, job_name_raw, department,
                hours, seniority, education, remote, board_source, post_url, job_location,
                city, region, country, language, first_indexed)
           VALUES (%(post_uuid)s, %(company_uuid)s, %(job_name_raw)s, %(department)s,
                %(hours)s, %(seniority)s, %(education)s, %(remote)s, %(board_source)s, %(post_url)s,
                %(job_location)s, %(city)s, %(region)s, %(country)s, %(language)s, %(first_indexed)s)
           ON CONFLICT (post_uuid) DO NOTHING""",
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
