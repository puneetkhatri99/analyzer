-- The church jobs JSON feed, normalized (loaded by `python -m app.cli ingest-feed`).
-- Denomination and church size live on companies: they are facts about the church, not the posting.

CREATE TABLE IF NOT EXISTS public.companies (
    company_uuid        text PRIMARY KEY,
    company_name        text NOT NULL,
    company_url         text,
    logo_url            text,
    company_categories  jsonb,
    denomination        text,           -- null = unknown, not "none"
    church_size         integer,        -- average weekly attendance, if found
    church_size_source  text,           -- 'stated' | 'inferred' | null
    enriched_at         timestamptz,
    enrichment_model    text
);

-- One row per post_uuid: what doesn't change between pulls of the same posting.
CREATE TABLE IF NOT EXISTS public.postings (
    post_uuid      text PRIMARY KEY,
    company_uuid   text REFERENCES public.companies (company_uuid),
    job_name_raw   text NOT NULL,
    department     text,
    hours          text,
    seniority      text,
    education      text,
    remote         text,
    board_source   text,
    post_url       text,
    job_location   text,
    city           text,
    region         text,
    country        text,
    language       text,
    first_indexed  timestamptz,         -- when the posting first appeared (from the feed)
    created_at     timestamptz NOT NULL DEFAULT now()
);

-- One row per posting per pull: the pay time series.
CREATE TABLE IF NOT EXISTS public.posting_snapshots (
    id               bigserial PRIMARY KEY,
    post_uuid        text NOT NULL REFERENCES public.postings (post_uuid),
    pull_date        date NOT NULL,
    comp_range_raw   text,
    comp_est_raw     numeric,
    salary_min       numeric,
    salary_max       numeric,
    salary_period    text,              -- 'year' | 'hour'
    salary_currency  text DEFAULT 'USD',
    last_indexed     timestamptz,
    is_active        boolean NOT NULL DEFAULT true,
    UNIQUE (post_uuid, pull_date)
);

-- Only when missing: Postgres checks table ownership before IF NOT EXISTS, and on databases set up before migrations
-- these tables may belong to another role.
DO $$
BEGIN
    IF to_regclass('public.idx_postings_region') IS NULL THEN
        CREATE INDEX idx_postings_region ON public.postings (region);
    END IF;
    IF to_regclass('public.idx_postings_company') IS NULL THEN
        CREATE INDEX idx_postings_company ON public.postings (company_uuid);
    END IF;
    IF to_regclass('public.idx_snapshots_post') IS NULL THEN
        CREATE INDEX idx_snapshots_post ON public.posting_snapshots (post_uuid);
    END IF;
    IF to_regclass('public.idx_snapshots_date') IS NULL THEN
        CREATE INDEX idx_snapshots_date ON public.posting_snapshots (pull_date);
    END IF;
    IF to_regclass('public.idx_companies_denom') IS NULL THEN
        CREATE INDEX idx_companies_denom ON public.companies (denomination);
    END IF;
END $$;
