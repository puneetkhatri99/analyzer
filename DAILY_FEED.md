# Daily jobs feed

Once a day the API downloads the church jobs feed, adds the postings that aren't in the database yet, and uses AI to fill in
what the feed leaves out. Postings already in the database are left alone.

| Step | What | Cost |
|---|---|---|
| Review | Up to `ENRICH_MAX_PER_RUN` (50) postings not judged yet: AI reads each one and decides whether the employer is a church, Christian school or ministry (`SCOPE_RULES` in `extraction/prompts.py`), records the employer type, and reads the pay when the feed has none (`salary_source = 'ai'`). | about a tenth of a cent each |
| Church | Up to `ENRICH_MAX_PER_RUN` (50) employers judged to be churches, never looked up: denomination from the name, then a web search for weekly attendance. Saved on `companies`, with the source page in `church_size_url`. | about 2.5 cents each |

## Rejected jobs
A posting judged out of scope (by the AI, by an admin, or in the one-off review of November 2026) moves to
`rejected_postings`, with the reason and a full copy of the posting. It is in no view or figure, and the daily feed skips
any posting with the same `post_uuid` or the same job URL, so it is never loaded or sent to the AI again. Admin →
**Rejected jobs** lists them; **Include again** puts one back exactly as it was, and the AI never re-judges it. Editors
can reject a feed job from its detail dialog in the Jobs tab.

## Setup
1. Run migrations: `python -m app.cli migrate --up-to 17` (Render does this on deploy).
2. `OPENAI_API_KEY` in `server/.env` and in Render's environment. `APP_ENV=production` turns the daily timer on.
3. Admin → Settings → **Jobs feed**: paste the signed link, **Save link**, then **Run now** (the first run loads everything).
4. Optional: `FEED_HOUR_UTC` (default 6) is when the day's run starts; `FEED_URL` is only a fallback if no link is saved.

## Moving the reviewed data to production (once, before the deploy that brings the review)
The public report shows a feed job only once it has been reviewed, and a database that hasn't reviewed its jobs would
take the daily run weeks (50 a day). So copy the local, reviewed database to Neon first:
1. Back up Neon (Neon console → Branches → create a branch from now). Migrations 0014 to 0016 move and drop data; 0017 adds columns.
2. Bring Neon to the same migration: `DATABASE_URL="<Neon direct URL>" python -m app.cli migrate --up-to 17`.
3. `NEON_URL="<Neon direct URL>" python -m app.cli push-data`: copies the BizDev tables and the feed (postings,
   with their pay, companies with their church data, the rejected jobs) in one transaction; the log ends with how many postings
   still await review.
4. Deploy.

## When the link expires
The link has an expiry time in its `Expires=` value. 7 days before, and every day after it expires or is refused, the
addresses on Admin → Settings → Daily lead report are emailed. Paste the new link in Admin → Settings. The page shows the
expiry date and the last run's result.

## What a run costs
Every run has an ID like `feed-20261118-151610`, and every AI call it makes is stored in `ai_usage` with it. Admin → AI costs →
**Daily feed runs** lists one total per run; the Jobs feed card shows the running total while it works and the final cost after.

## By hand
```
python -m app.cli daily-feed --dry-run   # download and count the new postings; change nothing
python -m app.cli daily-feed --force     # run now
```

## One-time: clear the old AI cost log
`migrations/0018_clear_ai_usage.sql` deletes every row of `ai_usage` (it belonged to the old OpenAI key). It waits until you run
`python -m app.cli migrate` by hand, then raise `--up-to` in `render.yaml` to 18.

## Limits
- The timer runs inside the web service, so it only fires while the service is awake after `FEED_HOUR_UTC`.
- Existing postings are never refreshed or closed by this job: their pay stays as first loaded.
- A posting whose AI review fails stays unjudged and is tried again next run.
