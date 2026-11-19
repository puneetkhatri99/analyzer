-- Which feed postings are in scope: the employer is a church, a Christian school, or a Christian nonprofit/ministry,
-- and the job isn't medical. Excluded postings stay in the table (admins see them with the reason and can reverse
-- the call) but every public figure leaves them out.
ALTER TABLE public.postings ADD COLUMN IF NOT EXISTS scope_checked_at timestamptz;  -- NULL = not judged yet
ALTER TABLE public.postings ADD COLUMN IF NOT EXISTS excluded_reason text;          -- NULL = included
ALTER TABLE public.postings ADD COLUMN IF NOT EXISTS excluded_by text;              -- 'ai', 'claude-review' or an admin's email

-- church | christian_school | christian_nonprofit | other. Only churches get an attendance lookup.
ALTER TABLE public.companies ADD COLUMN IF NOT EXISTS employer_type text;
-- the page the church_size figure came from
ALTER TABLE public.companies ADD COLUMN IF NOT EXISTS church_size_url text;
