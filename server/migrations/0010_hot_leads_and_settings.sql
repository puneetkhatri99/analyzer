-- When a lead turned hot (its 3rd report), so the daily report can list yesterday's new hot leads.
ALTER TABLE public.leads ADD COLUMN IF NOT EXISTS hot_at timestamptz;

-- Leads that are already hot: the time of their 3rd report.
UPDATE public.leads l SET hot_at = e.created_at
FROM (SELECT email, created_at, row_number() OVER (PARTITION BY email ORDER BY created_at, id) AS n
      FROM public.lead_events WHERE type = 'report') e
WHERE e.email = l.email AND e.n = 3 AND l.hot_at IS NULL;

-- Settings an admin changes in the panel (and the daily report's own bookkeeping). One row per setting.
--   hot_lead_emails         ["a@x.org", …]  who gets the daily lead report
--   daily_report_sent_for   "2026-11-16"    the last day reported, so a day is never sent twice
CREATE TABLE IF NOT EXISTS public.app_settings (
    key         text PRIMARY KEY,
    value       jsonb NOT NULL,
    updated_at  timestamptz NOT NULL DEFAULT now(),
    updated_by  text
);
