-- The pay moves from posting_snapshots onto postings. Snapshots were one row per posting per day the feed was pulled,
-- but a loaded posting is never refreshed, so every posting has exactly one. salary_currency (always USD) and
-- is_active (always true) aren't carried over. The newest snapshot of each posting is copied before the table is
-- dropped, and a rejected posting's snapshot joins its saved row, so "Include again" still brings its pay back.
ALTER TABLE public.postings
    ADD COLUMN IF NOT EXISTS pull_date      date,           -- the day the posting was downloaded
    ADD COLUMN IF NOT EXISTS comp_range_raw text,           -- the feed's pay text
    ADD COLUMN IF NOT EXISTS comp_est_raw   numeric,
    ADD COLUMN IF NOT EXISTS salary_min     numeric,
    ADD COLUMN IF NOT EXISTS salary_max     numeric,
    ADD COLUMN IF NOT EXISTS salary_period  text,           -- 'year' | 'hour'
    ADD COLUMN IF NOT EXISTS salary_source  text,           -- NULL = the feed, 'ai' / 'claude' = read from the posting
    ADD COLUMN IF NOT EXISTS last_indexed   timestamptz;

UPDATE public.postings p
SET pull_date = s.pull_date, comp_range_raw = s.comp_range_raw, comp_est_raw = s.comp_est_raw,
    salary_min = s.salary_min, salary_max = s.salary_max, salary_period = s.salary_period,
    salary_source = s.salary_source, last_indexed = s.last_indexed
FROM (SELECT DISTINCT ON (post_uuid) * FROM public.posting_snapshots ORDER BY post_uuid, pull_date DESC) s
WHERE s.post_uuid = p.post_uuid;

UPDATE public.rejected_postings r
SET posting = r.posting || (
    SELECT s - 'id' - 'post_uuid' - 'salary_currency' - 'is_active'
    FROM jsonb_array_elements(r.snapshots) s ORDER BY s->>'pull_date' DESC LIMIT 1)
WHERE jsonb_array_length(r.snapshots) > 0;

ALTER TABLE public.rejected_postings DROP COLUMN snapshots;
DROP TABLE public.posting_snapshots;
