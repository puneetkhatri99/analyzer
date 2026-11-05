# Project phases

The roadmap for the ministry jobs salary analyser. Each phase has its own file
with its goal, design decisions, where the code lives, and how to run it.

| # | Phase | Status | Code |
|---|---|---|---|
| 1 | [Database schema](01-database-schema.md) | Done | `server/database/` |
| 2 | [Data ingestion & enrichment](02-data-ingestion.md) | Done, enrichment partial | `server/pipeline/` |
| 3 | [API](03-api.md) | Done | `server/app/` |
| 4 | [Dashboard](04-dashboard.md) | Done | `client/` |
| 5 | [Lead gate](05-lead-gate.md) | Not started | — |

Data flows one way through the phases:

```
JSON feed ──► pipeline (phase 2) ──► Postgres (phase 1) ──► API (phase 3) ──► dashboard (phase 4)
```
