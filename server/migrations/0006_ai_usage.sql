-- One row per OpenAI call, for the AI costs page. cost_usd is an estimate from token counts and list prices
-- (app/ai_usage/service.py PRICES); OpenAI's billing page is the source of truth.
CREATE TABLE IF NOT EXISTS public.ai_usage (
    id             bigserial PRIMARY KEY,
    created_at     timestamptz NOT NULL DEFAULT now(),
    admin_email    text,
    purpose        text NOT NULL,          -- extract | church_lookup
    url            text,
    model          text NOT NULL,
    input_tokens   integer NOT NULL,
    cached_tokens  integer NOT NULL DEFAULT 0,
    output_tokens  integer NOT NULL,
    web_searches   integer NOT NULL DEFAULT 0,
    cost_usd       numeric(12, 6)          -- null when the model's price isn't known
);
CREATE INDEX IF NOT EXISTS idx_ai_usage_created ON public.ai_usage (created_at);
