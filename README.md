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

**Optional: the BizDev Excel sources** (from `server/`; the spreadsheets live in the git-ignored `data/` folder because they hold contact details)

```bash
python -m pipeline.import_bizdev churches "../data/API BizDev_ Churches.xlsx"
python -m pipeline.import_bizdev nonprofits "../data/API BizDev_ Nonprofits (Actual).xlsx"
python -m pipeline.fetch_jobs churches     # reads each job page for pay, job type, church size
python -m pipeline.fetch_jobs nonprofits   # add --retry to re-try blocked/failed pages
```

**Collecting new church jobs automatically** (from `server/`). Finds new US church jobs on the sites that allow it and adds
them to the BizDev churches tab as "Auto-collected". [COLLECTOR_HOW_IT_WORKS.md](COLLECTOR_HOW_IT_WORKS.md) explains how; [COLLECTOR_GAPS.md](COLLECTOR_GAPS.md) lists what it leaves out. Safe to run daily:

```bash
python -m pipeline.collect_jobs --dry-run          # see what's new, save nothing
python -m pipeline.collect_jobs                    # read and save every new job
python -m pipeline.collect_jobs --source sbc --limit 50
# every run logs to server/logs/ and ends with a PROBLEMS list (site changed / blocked / site down)
```

**Tracking expired jobs** (from `server/`). Each check records whether a job's page is still open:

```bash
python -m pipeline.fetch_jobs json                 # first check of the JSON feed's job URLs
python -m pipeline.fetch_jobs churches --recheck   # re-check every job not yet expired; run weekly
python -m pipeline.fetch_jobs nonprofits --recheck
python -m pipeline.fetch_jobs json --recheck
```

A job's status is `ok` (open), `expired` (404 / "position filled" / Workday says it's closed), `unknown`
(a JavaScript-only page such as Paycom, ADP or HRM Direct, so open or closed can't be told), `blocked` or
`error`. `last_live_at` is the latest check that found it open; `expired_at` is the first that found it
closed, so the job closed between the two. Feed results live in `posting_checks`; the BizDev tables carry
the same columns. The dashboard's **More filters → Status** and the table's Status column show them.

The dashboard shows each source on its own tab (`?source=json|churches|nonprofits`). The import creates
`json_jobs` (a view of the feed), `church_jobs` and `nonprofit_jobs`. Contact names and emails stay in
the database; the API never returns them.

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

## Logs

Everything logs to files in `server/logs/` (git-ignored), and to the screen. Set up in [server/app/logs.py](server/app/logs.py).

| Log file | What's in it |
|---|---|
| `api.log` (new file each midnight, 30 days kept) | Every request: method, path, status, time, IP. Every error with its traceback. Admin actions: sign-ins and failed sign-ins, URLs extracted and what was found, AI calls and their cost, church size lookups, jobs saved and by whom |
| `<script>-<date>-<time>.log`, one per run | Every pipeline script (`collect_jobs`, `fetch_jobs`, `ingest`, `import_bizdev`, `push_data`, `create_admin`): settings, every page fetched (status, size, time), every row's outcome, the summary, and a crash's traceback |

The screen shows the main lines; the files hold every detail. Passwords, session tokens, the database password and
the spreadsheets' contact names and emails are never logged. On Render the disk is wiped on each deploy, so `api.log`
only lasts until the next deploy there.

**Axiom.** When `AXIOM_TOKEN` is set (in `server/.env` locally, in Render's environment settings in production), every
log line is also sent to the Axiom dataset `AXIOM_DATASET` (default `analyzer`) at [axiom.co](https://axiom.co), where it's
kept, searchable and chartable. A background thread sends batches every 2 seconds, so requests never wait on Axiom; if
Axiom is unreachable the lines are skipped and the files still have them. Fields: `_time`, `level`, `logger`, `message`,
`app` (`api` or the script), `run`, `env` (`local`/`render`), `exception`, and per request `method`, `path`, `status`,
`ms`, `ip`. The collector also sends one `event = "source_summary"` row per source per run, and `event = "problem"` rows.

## Admin panel

`/admin` is a signed-in page where an admin pastes any job posting URL. The server reads the page
(structured job data first, then the visible text; Workday through its job API; blocked or JavaScript-only
pages through OpenAI web search), an OpenAI model extracts the job, and the admin reviews it and saves it
to the churches or nonprofits dataset. Pages that aren't a single job posting are reported as such.

Admin accounts live in the database (`admin_users`, scrypt-hashed passwords); sessions live in
`admin_sessions`, so signing out ends a session immediately and no signing secret is needed. Create an admin,
or reset a password, from `server/` (set `DATABASE_URL` to the Neon URL to do it in production):

```bash
python -m pipeline.create_admin admin@example.com   # asks for the password
```

Set in `server/.env` locally and in Render's environment settings in production:

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Enables extraction |
| `OPENAI_MODEL` | Optional; default `gpt-5.4-mini` |

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
