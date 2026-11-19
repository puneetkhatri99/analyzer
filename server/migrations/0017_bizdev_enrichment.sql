-- The BizDev sheets leave pay, church size and denomination mostly empty (most job links are on SimplyHired, which
-- blocks every page read). The AI step after each sheet sync (app/ingestion/bizdev_enrich.py) fills them in and stamps
-- what it has tried, so nothing is paid for twice.
--   employer_checked_at  the employer's church size / denomination were looked up (all rows of one employer share it)
--   pay_checked_at       the job's pay was looked up by web search (found or not)
--   salary_source        NULL = the sheet or the job page, 'ai' = read by web search
ALTER TABLE public.church_jobs
    ADD COLUMN IF NOT EXISTS employer_checked_at timestamptz,
    ADD COLUMN IF NOT EXISTS pay_checked_at      timestamptz,
    ADD COLUMN IF NOT EXISTS salary_source       text;
ALTER TABLE public.nonprofit_jobs
    ADD COLUMN IF NOT EXISTS employer_checked_at timestamptz,
    ADD COLUMN IF NOT EXISTS pay_checked_at      timestamptz,
    ADD COLUMN IF NOT EXISTS salary_source       text;
