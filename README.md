# Ministry Jobs Analyser

Salary analytics for church and ministry job postings: what roles pay, by
location, denomination and church size.

## Project structure

```
analyser/
├── client/                 React dashboard (Vite, Chart.js, Tabulator)
│   └── src/
│       ├── App.jsx         filter state, data fetching, layout
│       ├── api.js          calls to the API
│       └── components/     FilterBar, StatTiles, Charts, JobsTable
├── server/
│   ├── app/                FastAPI API: routes, queries, settings
│   ├── pipeline/           loads the JSON feed into Postgres and enriches it
│   ├── database/           schema.sql
│   └── data/raw/           the source JSON feed
├── phase/                  one document per project phase, with status
└── render.yaml             deploys the API and the dashboard on Render
```

Start with [phase/README.md](phase/README.md) for the roadmap and what each
phase does.

## Run it locally

You need Python 3.11+, Node 20+, and a Postgres database.

**1. Database and data** (from `server/`)

```bash
cp .env.example .env                      # then set DATABASE_URL
pip install -r requirements.txt
psql "$DATABASE_URL" -f database/schema.sql
python -m pipeline.ingest data/raw/church_jobs_feed_02.10.26.json
```

**2. API** (from `server/`)

```bash
python -m uvicorn app.main:app --reload   # http://127.0.0.1:8000/docs
```

**3. Dashboard** (from `client/`)

```bash
cp .env.example .env
npm install
npm run dev                               # http://localhost:5173
```

## Deploy

Everything runs on Render from one blueprint, `render.yaml`; the data lives on Neon.

| Part | Host | Settings |
|---|---|---|
| Database | Neon Postgres (loaded with the full local data) | the API uses the pooled (`-pooler`) connection string; run restores and the pipeline against the direct one (same host without `-pooler`) |
| API | Render web service `ministry-jobs-api` | `DATABASE_URL` = the Neon pooled connection string |
| Dashboard | Render static site `ministry-jobs-dashboard` | `VITE_API_BASE` = the API's URL, e.g. `https://ministry-jobs-api.onrender.com` |

In Render: New → Blueprint → pick this repo. Every `git push` redeploys both.
