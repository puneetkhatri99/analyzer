-- One-time: the AI cost log belongs to the previous OpenAI key; the new key starts from zero.
-- Deletes data, so render.yaml's --up-to waits at 17: run `python -m app.cli migrate` by hand, then raise it.
DELETE FROM public.ai_usage;
