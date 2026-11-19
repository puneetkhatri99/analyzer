-- Jobs are no longer tracked as open or closed (a page check found about a quarter of the jobs that had left the feed
-- still open, and JavaScript-only job sites can't be read at all). The check results go with the feature; the code
-- no longer reads or writes them, and the posting_checks foreign key would otherwise block rejecting a checked posting.
-- fetch_status / fetched_at stay: check-jobs still records how reading a BizDev job page went.
DROP TABLE IF EXISTS public.posting_checks;
ALTER TABLE public.church_jobs    DROP COLUMN IF EXISTS last_live_at, DROP COLUMN IF EXISTS expired_at;
ALTER TABLE public.nonprofit_jobs DROP COLUMN IF EXISTS last_live_at, DROP COLUMN IF EXISTS expired_at;
ALTER TABLE public.rejected_postings DROP COLUMN IF EXISTS page_check;
