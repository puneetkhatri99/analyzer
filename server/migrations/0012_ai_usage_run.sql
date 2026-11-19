-- Which run an AI call belonged to (a daily feed run, e.g. 'feed-20261118-151610'), so a run's cost can be added up.
-- NULL for a call made from the admin's Add a job page.
ALTER TABLE public.ai_usage ADD COLUMN IF NOT EXISTS run_id text;
CREATE INDEX IF NOT EXISTS idx_ai_usage_run ON public.ai_usage (run_id) WHERE run_id IS NOT NULL;
