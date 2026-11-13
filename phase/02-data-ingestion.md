# Phase 2 — Data ingestion & enrichment

**Status:** Done. Enrichment is partial (see coverage below).
**Code:** `server/pipeline/`
**Input:** `server/data/raw/church_jobs_feed_02.10.26.json` (1,840 postings)

## Goal

Load the church jobs JSON feed into Postgres. Denomination and church size come from a one-off enrichment pass
(below); roles come from keyword rules on the title.

## How it works

`pipeline/ingest.py` walks the feed once. For each posting it:

1. Upserts the company (`repository.upsert_company`).
2. Inserts the posting if it's new.
3. Upserts a snapshot for this pull date, with salary parsed from `comp_range`
   (`enrich.parse_salary`).

The job's role isn't stored: the API works it out from the title with keyword rules (`app/roles.py`).

Every write is an idempotent upsert, so re-running the same feed is safe and
fills in whatever was skipped before.

| File | Responsibility |
|---|---|
| `ingest.py` | CLI entry point; orchestrates one pass over the feed |
| `repository.py` | all database writes |
| `enrich.py` | salary parsing |

## Run it

From `server/`, with `DATABASE_URL` in `server/.env`:

```bash
python -m pipeline.ingest data/raw/church_jobs_feed_02.10.26.json
python -m pipeline.ingest data/raw/church_jobs_feed_02.10.26.json --limit 500   # first 500 only
```

Against Neon, use the direct connection string (host without `-pooler`). The
pooled endpoint shares sessions between clients, and a session setting such as
the one `pg_dump` output sets can leak to other connections.

Denomination and church size in `companies` come from earlier runs; the AI step that filled them was removed
(no Anthropic key). Jobs from the BizDev sources get them from their job pages instead (`pipeline.fetch_jobs`).

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

The API groups roles with keyword rules (`bucket_role` in `app/roles.py`).

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
