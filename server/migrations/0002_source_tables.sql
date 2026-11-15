-- The two BizDev Excel lead sheets (import-bizdev), and open/closed checks of the feed's job pages (check-jobs json).

-- Its own table, so the feed tables stay exactly as ingest-feed writes them.
CREATE TABLE IF NOT EXISTS public.posting_checks (
    post_uuid     text PRIMARY KEY REFERENCES public.postings (post_uuid),
    check_status  text,          -- ok | expired | unknown (page can't be read) | blocked | error
    checked_at    timestamptz,   -- latest check
    last_live_at  timestamptz,   -- latest check that found the job open
    expired_at    timestamptz    -- first check that found it closed
);

-- Both sheets share one layout. Columns after "sheets" are filled later by check-jobs.
CREATE TABLE IF NOT EXISTS public.church_jobs (
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
    salary_min         numeric,
    salary_max         numeric,
    salary_period      text,                  -- 'year' | 'hour'
    hours              text,
    remote             text,
    denomination       text,
    church_size        integer,
    fetch_status       text,                  -- null = not read yet; ok | expired | unknown | blocked | error
    fetched_at         timestamptz,
    imported_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.nonprofit_jobs (LIKE public.church_jobs INCLUDING ALL);
