-- Visitors who signed up to see a report (brief P2). One row per email; a returning visitor updates it.
-- The search they started with is kept for the MinistryHub team (role, location, attendance band).
CREATE TABLE IF NOT EXISTS public.leads (
    email          text PRIMARY KEY,          -- stored lowercase
    name           text NOT NULL,
    organization   text NOT NULL,
    role           text,
    location       text,
    attendance     text,
    created_at     timestamptz NOT NULL DEFAULT now(),
    last_seen_at   timestamptz NOT NULL DEFAULT now()
);
