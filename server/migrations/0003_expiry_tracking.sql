-- Expiry history for the BizDev rows: fetch_status / fetched_at hold the latest check.
--   last_live_at  latest check that found the job open
--   expired_at    first check that found it closed (it closed between last_live_at and expired_at)
ALTER TABLE public.church_jobs    ADD COLUMN IF NOT EXISTS last_live_at timestamptz;
ALTER TABLE public.church_jobs    ADD COLUMN IF NOT EXISTS expired_at   timestamptz;
ALTER TABLE public.nonprofit_jobs ADD COLUMN IF NOT EXISTS last_live_at timestamptz;
ALTER TABLE public.nonprofit_jobs ADD COLUMN IF NOT EXISTS expired_at   timestamptz;

-- backfill from checks made before these columns existed
UPDATE public.church_jobs    SET last_live_at = fetched_at WHERE fetch_status = 'ok' AND last_live_at IS NULL;
UPDATE public.church_jobs    SET expired_at   = fetched_at WHERE fetch_status = 'expired' AND expired_at IS NULL;
UPDATE public.nonprofit_jobs SET last_live_at = fetched_at WHERE fetch_status = 'ok' AND last_live_at IS NULL;
UPDATE public.nonprofit_jobs SET expired_at   = fetched_at WHERE fetch_status = 'expired' AND expired_at IS NULL;
