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

One Render web service builds the dashboard and serves it from the API, so the
app and its API share one address. The data lives on Neon.

| Render field | Value |
|---|---|
| Root Directory | *(empty: the repo root)* |
| Build Command | `cd client && npm ci && npm run build && cd ../server && pip install -r requirements.txt` |
| Start Command | `cd server && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/api/health` |
| Environment | `DATABASE_URL` = the Neon pooled (`-pooler`) connection string; `PYTHON_VERSION` = `3.12.8`; `NODE_VERSION` = `20` |

`render.yaml` holds the same settings (New → Blueprint). Every `git push`
redeploys. Run database restores and the pipeline against Neon's direct
connection string (same host without `-pooler`).

In local dev, Vite (port 5173) forwards `/api` to the API on port 8000.
