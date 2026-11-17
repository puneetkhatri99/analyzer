-- Everything a signed-up visitor does (brief P10, A4): sign-ups, reports viewed, offers checked, shares, downloads
-- and call-to-action clicks, each with its time. `details` holds the event's own fields (the filters, the amount …).
CREATE TABLE IF NOT EXISTS public.lead_events (
    id          bigserial PRIMARY KEY,
    email       text NOT NULL REFERENCES public.leads (email) ON DELETE CASCADE,
    type        text NOT NULL,
    details     jsonb NOT NULL DEFAULT '{}',
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS lead_events_email_time ON public.lead_events (email, created_at DESC);
