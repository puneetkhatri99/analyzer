-- How each BizDev-table job arrived: 'excel' (the import), 'admin_page' / 'admin_web_search' (added in the admin
-- panel) or 'collector'. added_by: the admin's email, for audit.
ALTER TABLE public.church_jobs    ADD COLUMN IF NOT EXISTS added_via text NOT NULL DEFAULT 'excel';
ALTER TABLE public.church_jobs    ADD COLUMN IF NOT EXISTS added_by  text;
ALTER TABLE public.nonprofit_jobs ADD COLUMN IF NOT EXISTS added_via text NOT NULL DEFAULT 'excel';
ALTER TABLE public.nonprofit_jobs ADD COLUMN IF NOT EXISTS added_by  text;

-- Where a church size came from when it isn't in the posting (a page found by the admin panel's web lookup).
ALTER TABLE public.church_jobs    ADD COLUMN IF NOT EXISTS church_size_source text;
ALTER TABLE public.nonprofit_jobs ADD COLUMN IF NOT EXISTS church_size_source text;
