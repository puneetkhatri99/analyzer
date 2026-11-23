-- The role the AI picks after reading a feed posting's whole text (daily review and the one-off classify-roles run).
-- Used only when the title alone lands in a catch-all group (app/jobs/roles.py pick_role). NULL = not asked yet.
-- The BizDev tables keep no description, so they have no such column.
ALTER TABLE public.postings ADD COLUMN IF NOT EXISTS ai_role text;
