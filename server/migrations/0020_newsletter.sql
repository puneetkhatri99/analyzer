-- The newsletter: a visitor who ticks "Send me the MinistryHub newsletter" on the sign-up form is sent to Mailchimp
-- once a week (app/leads/crm_sync.py), with what they did on the site.
--   newsletter_at        when they ticked it (NULL = never asked for it; nobody is sent without it)
--   synced_mailchimp_at  when they were last sent to Mailchimp (NULL = not yet)
ALTER TABLE public.leads
    ADD COLUMN IF NOT EXISTS newsletter_at       timestamptz,
    ADD COLUMN IF NOT EXISTS synced_mailchimp_at timestamptz;
