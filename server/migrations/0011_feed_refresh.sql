-- Where a snapshot's pay came from: NULL/'feed' = the feed's comp_range, 'ai' = read from the posting text by the daily
-- feed job (app/ingestion/daily_feed.py).
ALTER TABLE public.posting_snapshots ADD COLUMN IF NOT EXISTS salary_source text;

-- Settings kept by the daily feed job in app_settings (see daily_feed.py):
--   feed_url              the signed feed link an admin pastes in Admin → Settings
--   daily_feed_done_for   "2026-11-18"  the last day the job ran, so a day is never run twice
--   daily_feed_status     {at, ok, message, new, church, pay}  the last run, shown in the admin
--   daily_feed_alert_for  "2026-11-18"  the last day the admin was emailed about the link
