# Phase 3 — API

**Status:** Done
**Code:** `server/app/`

## Goal

A read-only HTTP API that serves filtered postings and pre-computed analytics,
so the dashboard only renders and never aggregates.

## Endpoints

| Method & path | Returns |
|---|---|
| `GET /api/health` | `{"ok": true}` |
| `GET /api/filter-options` | distinct roles, denominations, regions, countries and employment types, each with a count |
| `GET /api/jobs` | `{total, rows}`: every posting matching the filters |
| `GET /api/summary` | `stats` (postings, postings with pay, 25th/50th/75th percentile pay, employers, data date), plus `by_role`, `by_state`, `by_denomination`, `by_church_size` (each with the same pay figures) and a `histogram` of annual pay |

The role breakdown ignores the `role` filter and the state breakdown ignores the
`region` filter, so the dashboard can show every role or state with the
selected one highlighted.

`/api/jobs` and `/api/summary` take the same optional query parameters:

| Param | Example | Meaning |
|---|---|---|
| `role` | `Worship/Music` | exact role |
| `denomination` | `Baptist` | exact denomination |
| `region` | `Texas` | exact state/region |
| `country` | `United States` | exact country |
| `hours` | `Full-Time` | exact employment type |
| `remote` | `true` / `false` | remote flag |
| `search` | `youth` | substring of job title or employer |
| `has_pay` | `true` | only postings that list pay |
| `min_salary` | `50000` | annualized salary floor; excludes postings without salary |
| `min_church_size` | `1000` | attendance floor; excludes churches without a known size |

Hourly pay is annualized at 2,080 hours per year.

| File | Responsibility |
|---|---|
| `main.py` | FastAPI app, CORS, routes, shared filter parameters |
| `jobs.py` | loads postings, applies filters, builds summary and filter options |
| `roles.py` | role taxonomy and keyword role bucketing |
| `db.py` | Postgres connection |
| `config.py` | reads settings from `server/.env` or the environment |

## Run it

From `server/`:

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Interactive docs are at http://127.0.0.1:8000/docs.

## Settings

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | yes | Postgres connection string |
| `ALLOWED_ORIGIN` | production | the dashboard's URL for CORS; defaults to `*` |
| `ANTHROPIC_API_KEY` | no | used by the pipeline only |

The API re-queries all postings on every request. That takes a few ms at
1,840 rows; add caching if the dataset grows by orders of magnitude.
