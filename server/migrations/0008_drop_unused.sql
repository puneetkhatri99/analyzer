-- Leftovers from the removed Anthropic classifier, and a view no code reads. Fresh databases never had them.
--   title_classifications    the per-title role cache; the classifier never ran, so it is empty
--   canonical_role           never filled on postings, church_jobs or nonprofit_jobs; roles come from titles at
--                            read time (app/jobs/roles.py)
--   json_jobs                a flattened view of the feed; app/jobs/repository.py builds its own query
DO $$
DECLARE
    has_rows boolean;
BEGIN
    IF to_regclass('public.title_classifications') IS NOT NULL THEN
        -- dynamic SQL: a static reference fails to plan on databases that never had the table
        EXECUTE 'SELECT EXISTS (SELECT 1 FROM public.title_classifications)' INTO has_rows;
        IF has_rows THEN
            RAISE EXCEPTION 'title_classifications has rows; keep a copy before dropping it';
        END IF;
    END IF;
END $$;

DROP VIEW IF EXISTS public.json_jobs;
DROP TABLE IF EXISTS public.title_classifications;
ALTER TABLE public.postings       DROP COLUMN IF EXISTS canonical_role;
ALTER TABLE public.church_jobs    DROP COLUMN IF EXISTS canonical_role;
ALTER TABLE public.nonprofit_jobs DROP COLUMN IF EXISTS canonical_role;
