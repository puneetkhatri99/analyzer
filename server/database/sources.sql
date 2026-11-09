-- Three source tables, one per dataset, so each can be browsed on its own:
--   json_jobs       the church jobs JSON feed (a view over the normalized tables the dashboard uses)
--   church_jobs     API BizDev_ Churches.xlsx
--   nonprofit_jobs  API BizDev_ Nonprofits (Actual).xlsx
-- Safe to re-run.

-- Expiry tracking for the feed (filled by `pipeline.fetch_jobs json`). Its own table, so the feed
-- tables stay exactly as pipeline.ingest writes them.
CREATE TABLE IF NOT EXISTS posting_checks (
    post_uuid     text PRIMARY KEY REFERENCES postings(post_uuid),
    check_status  text,          -- ok | expired | unknown (page can't be read) | blocked | error
    checked_at    timestamptz,   -- latest check
    last_live_at  timestamptz,   -- latest check that found the job open
    expired_at    timestamptz    -- first check that found it closed
);

CREATE OR REPLACE VIEW json_jobs AS
SELECT p.post_uuid, p.job_name_raw AS job_title, p.canonical_role,
       c.company_name AS org_name, c.company_url AS org_website, c.denomination, c.church_size,
       p.city, p.region AS state, p.country, p.hours, p.remote, p.seniority, p.department,
       s.salary_min, s.salary_max, s.salary_period, s.comp_range_raw,
       p.board_source, p.post_url AS job_url, p.first_indexed AS date_posted, s.pull_date,
       k.check_status, k.checked_at, k.last_live_at, k.expired_at
FROM postings p
LEFT JOIN companies c USING (company_uuid)
LEFT JOIN posting_checks k USING (post_uuid)
LEFT JOIN LATERAL (
    SELECT * FROM posting_snapshots ps WHERE ps.post_uuid = p.post_uuid
    ORDER BY ps.pull_date DESC LIMIT 1
) s ON true;

-- The two Excel files share one layout. Columns after "sheets" are empty on import and
-- are meant to be filled later by fetching job_url.
CREATE TABLE IF NOT EXISTS church_jobs (
    url_key            text PRIMARY KEY,      -- job_url without scheme, www, query or trailing slash
    job_url            text NOT NULL,
    job_title          text,
    org_name           text,
    org_website        text,
    city               text,
    state              text,
    date_posted        date,
    contact_first_name text,
    contact_last_name  text,
    contact_title      text,
    contact_email      text,
    note               text,
    sheets             text[],                -- every tab the row appeared in

    canonical_role     text,
    salary_min         numeric,
    salary_max         numeric,
    salary_period      text,                  -- 'year' | 'hour'
    hours              text,
    remote             text,
    denomination       text,
    church_size        integer,
    fetch_status       text,                  -- null = not fetched yet; 'ok' | 'expired' | 'blocked' | 'error'
    fetched_at         timestamptz,
    imported_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS nonprofit_jobs (LIKE church_jobs INCLUDING ALL);

-- Expiry tracking: fetch_status/fetched_at hold the latest check; these keep its history.
--   last_live_at  latest check that found the job open
--   expired_at    first check that found it closed (it closed between last_live_at and expired_at)
ALTER TABLE church_jobs    ADD COLUMN IF NOT EXISTS last_live_at timestamptz;
ALTER TABLE church_jobs    ADD COLUMN IF NOT EXISTS expired_at   timestamptz;
ALTER TABLE nonprofit_jobs ADD COLUMN IF NOT EXISTS last_live_at timestamptz;
ALTER TABLE nonprofit_jobs ADD COLUMN IF NOT EXISTS expired_at   timestamptz;
-- backfill from checks made before these columns existed
UPDATE church_jobs    SET last_live_at = fetched_at WHERE fetch_status = 'ok' AND last_live_at IS NULL;
UPDATE church_jobs    SET expired_at   = fetched_at WHERE fetch_status = 'expired' AND expired_at IS NULL;
UPDATE nonprofit_jobs SET last_live_at = fetched_at WHERE fetch_status = 'ok' AND last_live_at IS NULL;
UPDATE nonprofit_jobs SET expired_at   = fetched_at WHERE fetch_status = 'expired' AND expired_at IS NULL;
