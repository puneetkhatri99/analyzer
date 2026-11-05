-- Ministry job salary analyser schema
-- Design: raw feed data is cheap to re-pull monthly, but LLM enrichment
-- (denomination, church size, title->role classification) is not.
-- So enrichment is cached per company / per raw title, not per snapshot.

-- ---------------------------------------------------------------
-- Companies (churches/orgs). One row per company_uuid from the feed.
-- Denomination and church size live here, not on postings, because
-- they're a property of the church, not the job posting, and don't
-- need to be re-extracted every monthly pull.
-- ---------------------------------------------------------------
CREATE TABLE companies (
    company_uuid        text PRIMARY KEY,
    company_name        text NOT NULL,
    company_url         text,
    logo_url             text,
    company_categories  jsonb,

    -- enrichment (filled by an LLM pass, cached until re-run)
    denomination         text,            -- null = unknown, not "none"
    church_size          integer,         -- avg weekly attendance, if found
    church_size_source   text,            -- 'stated' | 'inferred' | null
    enriched_at           timestamptz,
    enrichment_model     text             -- model/version used, for reproducibility
);

-- ---------------------------------------------------------------
-- Title -> canonical role cache. Many postings share an identical raw
-- title ("Youth Pastor" appears hundreds of times); classify each
-- distinct raw title once, not once per posting.
-- ---------------------------------------------------------------
CREATE TABLE title_classifications (
    job_name_raw      text PRIMARY KEY,
    canonical_role    text NOT NULL,       -- from a fixed taxonomy, e.g. 'Senior Pastor'
    confidence        real,
    classified_at     timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------
-- Postings. One row per post_uuid: the stuff that doesn't change
-- between monthly pulls of the same posting.
-- ---------------------------------------------------------------
CREATE TABLE postings (
    post_uuid        text PRIMARY KEY,
    company_uuid     text REFERENCES companies(company_uuid),

    job_name_raw     text NOT NULL,
    canonical_role   text,                -- denormalized copy of title_classifications.canonical_role
                                           -- for fast GROUP BY without a join
    department       text,
    hours            text,
    seniority        text,
    education        text,
    remote           text,

    board_source     text,
    post_url         text,
    job_location     text,
    city             text,
    region           text,
    country          text,
    language         text,

    first_indexed    timestamptz,         -- when the posting first appeared (from feed)
    created_at       timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------
-- Snapshots. One row per posting per monthly pull. This is the time
-- series: salary changes, whether it's still live, etc.
-- ---------------------------------------------------------------
CREATE TABLE posting_snapshots (
    id               bigserial PRIMARY KEY,
    post_uuid        text NOT NULL REFERENCES postings(post_uuid),
    pull_date        date NOT NULL,

    comp_range_raw   text,
    comp_est_raw     numeric,
    salary_min       numeric,
    salary_max       numeric,
    salary_period    text,                -- 'year' | 'hour'
    salary_currency  text DEFAULT 'USD',

    last_indexed     timestamptz,         -- from feed; lets us tell "still active" vs "dropped off"
    is_active        boolean NOT NULL DEFAULT true,

    UNIQUE (post_uuid, pull_date)
);

CREATE INDEX idx_postings_role     ON postings (canonical_role);
CREATE INDEX idx_postings_region   ON postings (region);
CREATE INDEX idx_postings_company  ON postings (company_uuid);
CREATE INDEX idx_snapshots_post    ON posting_snapshots (post_uuid);
CREATE INDEX idx_snapshots_date    ON posting_snapshots (pull_date);
CREATE INDEX idx_companies_denom   ON companies (denomination);

-- ---------------------------------------------------------------
-- Example analytics queries this schema answers directly:
-- ---------------------------------------------------------------

-- Median/avg salary by role over the last 6 months
-- SELECT p.canonical_role, date_trunc('month', s.pull_date) AS month,
--        avg((s.salary_min + s.salary_max) / 2.0) AS avg_salary
-- FROM posting_snapshots s JOIN postings p USING (post_uuid)
-- WHERE s.salary_min IS NOT NULL AND s.pull_date >= now() - interval '6 months'
-- GROUP BY 1, 2 ORDER BY 1, 2;

-- Pay by location
-- SELECT p.region, avg((s.salary_min + s.salary_max) / 2.0) AS avg_salary, count(*)
-- FROM posting_snapshots s JOIN postings p USING (post_uuid)
-- WHERE s.salary_min IS NOT NULL
-- GROUP BY p.region ORDER BY avg_salary DESC;

-- How long a posting stays live
-- SELECT post_uuid, min(pull_date) AS first_seen, max(pull_date) AS last_seen
-- FROM posting_snapshots WHERE is_active GROUP BY post_uuid;
