# Phase 2 — Data ingestion & enrichment

**Status:** Done. Enrichment is partial (see coverage below).
**Code:** `server/pipeline/`
**Input:** `server/data/raw/church_jobs_feed_02.10.26.json` (1,840 postings)

## Goal

Load the church jobs JSON feed into Postgres and fill in the facts the feed
doesn't have: canonical role, denomination and church size.

## How it works

`pipeline/ingest.py` walks the feed once. For each posting it:

1. Upserts the company (`repository.upsert_company`).
2. If the company hasn't been enriched in 90 days, fetches the church's homepage
   (`fetch_company.py`) and asks Claude for denomination and church size
   (`enrich.extract_church_info`). Only explicitly stated facts are kept.
3. Classifies the raw job title into the fixed role taxonomy in
   `app/roles.py`, cached per distinct title (`enrich.classify_title`).
4. Upserts the posting, then a snapshot for this pull date with salary parsed
   from `comp_range` (`enrich.parse_salary`).

Every write is an idempotent upsert, so re-running the same feed is safe and
fills in whatever was skipped before.

| File | Responsibility |
|---|---|
| `ingest.py` | CLI entry point; orchestrates one pass over the feed |
| `repository.py` | all database writes |
| `enrich.py` | Claude calls (title → role, text → denomination/size) and salary parsing |
| `fetch_company.py` | fetches a church homepage as plain text |

## Run it

From `server/`, with `DATABASE_URL` in `server/.env`:

```bash
python -m pipeline.ingest data/raw/church_jobs_feed_02.10.26.json
python -m pipeline.ingest data/raw/church_jobs_feed_02.10.26.json --limit 500   # first 500 only
```

Against Neon, use the direct connection string (host without `-pooler`). The
pooled endpoint shares sessions between clients, and a session setting such as
the one `pg_dump` output sets can leak to other connections.

Without `ANTHROPIC_API_KEY`, postings, location and salary still load. Role,
denomination and church size stay null until a later run with the key set.

## Current coverage

The LLM step has not run yet (no API key was set). Denomination, church size
and some extra salaries were instead filled once by visiting each posting's
own `post_url` and recording only what the page stated. That was a one-off
pass written straight to the database; it is **not** part of this pipeline,
so re-running the pipeline will not repeat it.

| Field | Coverage |
|---|---|
| Location (city/region) | 1,745 / 1,840 postings (95%) |
| Salary | 737 / 1,840 postings (40%) |
| Denomination | 105 / 562 companies (19%) |
| Church size | 10 / 562 companies (2%) |

Until the LLM classifies titles, the API groups roles with a keyword fallback
(`bucket_role` in `app/roles.py`). Its labels differ slightly from the
canonical taxonomy in the same file.

## Known issues

**Most job boards can't be read by a plain page fetch.** Workday, ADP
WorkforceNow, BambooHR, Paycom, Paycor, Oracle Cloud HCM, iCIMS and similar
platforms render job content with JavaScript. A static fetch gets an empty
shell, which is the main reason denomination and size coverage is low. Fixing
this needs a headless browser for those domains.

**Some `company_uuid`s are staffing agencies, not churches.** Slingshot Group,
Christian Career, Lead222, Ladgov Corporation, Pathways/Reliant residency
programs, Military Spouse Corporate Career Network and AGORA Search Group post
for many unrelated churches under one shared ID. Different postings under the
same ID showed conflicting denominations and attendance figures, so these are
deliberately left null. Enriching them properly needs a separate key for the
actual employing church.

**A few non-church postings slipped into the feed** through keyword collisions,
for example a JPMorgan Chase branch on "Church" street, a trucking company named
"Covenant", and hospitals. They carry no denomination or size, but they add
noise to company-level stats.

**The one-off enrichment pass ran in 12 independent batches.** All followed the
same rules (only explicitly stated facts, skip staffing agencies, never
overwrite an existing value), but ambiguous cases were judged per batch.
Spot-check if exact consistency matters.
