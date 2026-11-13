# Phase 1 — Database schema

**Status:** Done
**Code:** `server/database/schema.sql`

## Goal

A Postgres schema that holds church job postings and supports salary analytics
by role, location, denomination and church size, including how postings change
across monthly data pulls.

## Design

Raw feed data is cheap to re-pull every month. LLM enrichment is not. So
enrichment is cached once per company or per raw title, never per snapshot.

| Table | One row per | Holds |
|---|---|---|
| `companies` | church / organization | name, URL, denomination, church size, when it was enriched |
| `title_classifications` | distinct raw job title | unused: the AI title classifier was removed; roles come from `app/roles.py` |
| `postings` | posting (`post_uuid`) | fields that don't change between pulls: title, role, location, hours, URL |
| `posting_snapshots` | posting per pull date | salary and active status at that pull (the time series) |

Denomination and church size live on `companies`, not `postings`, because
they belong to the church, not the job.

## Apply it

```bash
psql "$DATABASE_URL" -f server/database/schema.sql
```

The schema file ends with example analytics queries (salary by role over time,
pay by location, how long postings stay live).
