-- Feed postings judged out of scope (not a church, Christian school or ministry, or a medical job) leave the
-- postings table for this one. The daily feed skips any posting found here (same post_uuid or same job URL), so a
-- rejected job is never loaded or sent to the AI again. Each row keeps the posting, its snapshots and its page check
-- as JSON, so an admin's "Include again" puts it back exactly.
CREATE TABLE IF NOT EXISTS public.rejected_postings (
    post_uuid    text PRIMARY KEY,
    post_url     text,               -- lower-cased, trimmed: how a re-posted job is recognised
    job_title    text,
    company_uuid text,
    reason       text NOT NULL,
    rejected_by  text NOT NULL,      -- 'ai', 'claude-review' or an admin's email
    rejected_at  timestamptz NOT NULL DEFAULT now(),
    posting      jsonb NOT NULL,     -- the postings row
    snapshots    jsonb NOT NULL DEFAULT '[]',
    page_check   jsonb
);
CREATE INDEX IF NOT EXISTS rejected_postings_url ON public.rejected_postings (post_url);

-- Postings already marked excluded (0013) move here. No data is lost: everything is copied before the delete.
INSERT INTO public.rejected_postings
    (post_uuid, post_url, job_title, company_uuid, reason, rejected_by, posting, snapshots, page_check)
SELECT p.post_uuid, lower(trim(p.post_url)), p.job_name_raw, p.company_uuid, p.excluded_reason,
       coalesce(p.excluded_by, 'ai'), to_jsonb(p),
       coalesce((SELECT jsonb_agg(to_jsonb(s)) FROM public.posting_snapshots s WHERE s.post_uuid = p.post_uuid), '[]'),
       (SELECT to_jsonb(k) FROM public.posting_checks k WHERE k.post_uuid = p.post_uuid)
FROM public.postings p WHERE p.excluded_reason IS NOT NULL
ON CONFLICT (post_uuid) DO NOTHING;

DELETE FROM public.posting_checks WHERE post_uuid IN (SELECT post_uuid FROM public.rejected_postings);
DELETE FROM public.posting_snapshots WHERE post_uuid IN (SELECT post_uuid FROM public.rejected_postings);
DELETE FROM public.postings WHERE post_uuid IN (SELECT post_uuid FROM public.rejected_postings);

-- The flag columns from 0013 are replaced by the table; 0013 never reached production, so they hold nothing there.
ALTER TABLE public.postings DROP COLUMN IF EXISTS excluded_reason;
ALTER TABLE public.postings DROP COLUMN IF EXISTS excluded_by;
