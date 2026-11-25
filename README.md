# Ministry Jobs Analyser

Salary analytics for church and ministry job postings: what roles pay, by
location, denomination and church size.

## Project structure

```
analyser/
├── client/                 React (Vite, Tailwind, shadcn/ui): the public site and the admin area
│   └── src/
│       ├── features/       landing, report, admin (jobs, rejected, leads, costs, settings, users, add-job)
│       ├── api/            calls to the API
│       ├── components/    shared components: ui/ (shadcn/ui), site/ (public header, footer, layout)
│       ├── hooks/          shared hooks
│       └── lib/            shared helpers: formatting, CSV, pay, report filters and share links, lead tracking
├── server/
│   ├── app/                one folder per feature (below), plus core/ and shared/
│   │   ├── main.py         the FastAPI app: middleware, routers, the built dashboard
│   │   ├── cli.py          every command: python -m app.cli <command> --help
│   │   ├── core/           settings, database pool, logging, migration runner
│   │   ├── shared/         US states and regions, quantiles, email and URL helpers
│   │   ├── auth/           sign-in, sessions, users and roles, create-admin
│   │   ├── jobs/           admin views of the postings per source, role rules, delete
│   │   ├── report/         the public report (/api/report)
│   │   ├── leads/          the public sign-up (/api/leads)
│   │   ├── extraction/     admin "add a job from any URL" with OpenAI, and saving it
│   │   ├── ai_usage/       AI call costs and the costs page
│   │   ├── job_pages/      reading job pages (pay, type, size, denomination) and check-jobs
│   │   └── ingestion/      daily-feed (+ AI review), import-bizdev, bizdev-sync, push-data, collector/ (collect-jobs)
│   ├── migrations/         numbered SQL files: the database schema, applied by `migrate`
│   └── tests/              one folder per feature
└── render.yaml             deploys the API and the dashboard on Render
```

[DAILY_FEED.md](DAILY_FEED.md) explains the daily jobs feed and its AI review; [DAILY_REPORT_CRON.md](DAILY_REPORT_CRON.md)
the daily lead email.

## Run it locally

You need Python 3.11+, Node 20+, and a Postgres database.

**1. Database and data** (from `server/`)

```bash
cp .env.example .env                      # then set DATABASE_URL
pip install -r requirements-dev.txt       # requirements.txt + pytest and ruff
python -m app.cli migrate                 # creates or updates every table
python -m app.cli daily-feed --force      # loads the jobs feed (FEED_URL, or the link saved in Admin → Settings)
```

**Optional: the BizDev Excel sources** (from `server/`; the spreadsheets live in the git-ignored `data/` folder because they hold contact details)

```bash
python -m app.cli import-bizdev churches "../data/API BizDev_ Churches.xlsx"
python -m app.cli import-bizdev nonprofits "../data/API BizDev_ Nonprofits (Actual).xlsx"
python -m app.cli check-jobs churches     # reads each job page for pay, job type, church size
python -m app.cli check-jobs nonprofits   # add --retry to re-try blocked/failed pages
```

**Weekly sheet sync.** Instead of importing by hand, paste the two sheet links in Admin → Settings → BizDev sheets (a Google
Sheets share link, "anyone with the link can view", or a direct .xlsx link). Once a week the server downloads both and
adds the jobs it doesn't have (matched by job URL; saved values are never erased). `python -m app.cli bizdev-sync --force`
runs it now. It runs on the API's own timer (production only, from `FEED_HOUR_UTC` on the first check of each week), so
a sleeping free Render service catches up when it wakes. A failed download retries the next day and emails the
daily-report addresses. Code: `server/app/ingestion/bizdev_sync.py`.

*Private sheets.* A sheet no one else can open can be shared, as a **Viewer**, with the app's own Google account. The
server asks Google for read-only access, so it can download the sheet but never change it. On EC2 that account is a key
file named by `GOOGLE_APPLICATION_CREDENTIALS` (steps: [DEPLOY_EC2.md](DEPLOY_EC2.md), "Private Google Sheets"). On
Cloud Run it is the service's built-in account and needs no key. Without either, the plain link is used, as before.

**AI fill-in for the BizDev jobs** (`bizdev_enrich.py`, `python -m app.cli bizdev-enrich [--limit N]`). The sheets hold no pay,
church size or denomination, and most job links (SimplyHired) block page reads, so once a day, after the sync, up to
`ENRICH_MAX_PER_RUN` (50) per sheet are filled in: the denomination from the employer's name (free); church size and
denomination by web search, once per employer (church sheet: every employer; nonprofit sheet: church-like names only);
and pay by web search for jobs whose page couldn't be read and that were posted in the last 180 days. Each step is stamped
(`employer_checked_at`, `pay_checked_at`), so nothing is paid for twice; pay it finds is marked `salary_source = 'ai'`.
Costs show under Admin → AI costs as `bizdev-…` runs. Without `OPENAI_API_KEY` only the free step runs.

**Monthly AI limit** (Admin → AI costs → Monthly AI limit). An admin sets the most the AI may cost in a month (US dollars,
UTC calendar month, estimated from `ai_usage`). At the limit, all four places that call OpenAI stop (the daily JSON review,
the church lookup, the BizDev pay search, and "Add a job", which answers 429) until the next month or until the limit is
raised or removed; the daily-report addresses are emailed when a run is paused. No limit is set until an admin sets one.
Calls already running can overshoot by a few cents. Code: `ensure_budget()` in `server/app/ai_usage/service.py`.

**Roles** (`server/app/jobs/roles.py`). A job's role comes from its title (the brief's role list plus the extras the
client chose). When the title only reaches a catch-all group (Other, Director/Coordinator, Pastor/Minister (other)), the
role the AI picked from the whole posting is used instead (`postings.ai_role`, asked in the daily review). The AI never
moves a job into the hidden Healthcare/Counseling group. `python -m app.cli classify-roles --estimate` prices the
one-off catch-up for feed postings reviewed before this existed; without `--estimate` it runs it.

**One opening, counted once** (`server/app/report/reposts.py`). Before any public figure, copies of one job are merged:
the same link in the same state, or the same employer, title, state and city posted within 90 days of each other
(employers and titles compared as cleaned-up word sets). `python -m app.cli check-duplicates` logs every merged group,
the role counts, the denomination names merged (`job_pages/parser.py` `DENOMINATIONS`) and jobs hidden for a
placeholder or missing employer; the daily feed run logs the same at its end.

**Church size**: a stated size, weekly attendance first, else membership (never staff counts or estimates). Churches
whose size wasn't found are looked up again after 90 days. Editors can type a size and denomination in a job's detail
dialog; it applies to every job of that employer and is logged.

**Newsletter sync** (`server/app/leads/crm_sync.py`): once a week, sign-ups who ticked "Send me the MinistryHub
newsletter" go to Mailchimp with their activity (tags and a note). Off until `MAILCHIMP_API_KEY` and
`MAILCHIMP_LIST_ID` are set. `python -m app.cli crm-sync --dry-run` shows what would be sent. Loxo waits for the
client's Loxo API docs.

**Collecting new church jobs automatically** (from `server/`). Finds new US church jobs on the sites that allow it and adds
them to the BizDev churches tab as "Auto-collected". [COLLECTOR_HOW_IT_WORKS.md](COLLECTOR_HOW_IT_WORKS.md) explains how; [COLLECTOR_GAPS.md](COLLECTOR_GAPS.md) lists what it leaves out. Safe to run daily:

```bash
python -m app.cli collect-jobs --dry-run         # see what's new, save nothing
python -m app.cli collect-jobs                   # read and save every new job
python -m app.cli collect-jobs --source sbc --limit 50
# every run logs to server/logs/ and ends with a PROBLEMS list (site changed / blocked / site down)
```

Jobs aren't tracked as open or closed: a page check on the feed's jobs that had left the feed found about a quarter
still open, and JavaScript-only job sites (ClearCompany, ADP, Paycom...) can't be read at all, so the status wasn't
reliable. Migration 0015 removed the old check results (`posting_checks` and the BizDev `last_live_at` /
`expired_at` columns).

The dashboard shows each source on its own tab (`?source=json|churches|nonprofits`): the feed tables,
`church_jobs` and `nonprofit_jobs`. Contact names and emails stay in the database. The job lists and the public report never carry them; only a signed-in editor or admin sees a job's contact, in its detail dialog (`GET /api/admin/jobs/contact`, logged).

**Database changes** go in a new numbered file in `server/migrations/` (`0009_what_it_does.sql`), never by editing
one that has run: `migrate` refuses a file whose text changed after it was applied. Each file runs in its own
transaction. `python -m app.cli migrate --dry-run` lists what would run. Render runs `migrate` before every start.

**Import rule.** Imports go one way: `core` ← `shared` ← `auth` ← `job_pages`/`ai_usage` ← `jobs` ← `report` ← `leads`/`extraction` ← `ingestion` ← `main`/`cli` (a package imports only what is to its left). On the client, shared code (`api`, `components`, `hooks`, `lib`) never imports a feature, and one feature reaches another only through its `index.js`. `lint-imports` (server) and `npm run lint` (client) fail on a break.

**Tests and lint** (from `server/`): `pytest`, `ruff check .`, `ruff format .`, `lint-imports`. Client (from `client/`): `npm test`, `npm run lint`. Tests use `DATABASE_URL`; set
`TEST_DATABASE_URL` to run them against a separate database instead (it is migrated first).

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

Everything logs to files in `server/logs/` (git-ignored), and to the screen. Set up in [server/app/core/logs.py](server/app/core/logs.py).

| Log file | What's in it |
|---|---|
| `api.log` (new file each midnight, 30 days kept) | Every request: method, path, status, time, IP. Every error with its traceback. Admin actions: sign-ins and failed sign-ins, URLs extracted and what was found, AI calls and their cost, church size lookups, jobs saved and by whom |
| `<script>-<date>-<time>.log`, one per run | Every command (`daily_feed`, `daily_report`, `collect_jobs`, `check_jobs`, `import_bizdev`, `push_data`, `create_admin`, `migrate`): settings, every page fetched (status, size, time), every row's outcome, the summary, and a crash's traceback |

The screen shows the main lines; the files hold every detail. Passwords, session tokens, the database password and
the spreadsheets' contact names and emails are never logged. On Render the disk is wiped on each deploy, so with
`APP_ENV=production` (set in `render.yaml`) and `AXIOM_TOKEN` both set, no log files are written there and Axiom holds
everything. Without the token, production still writes the files.

**Axiom.** When `AXIOM_TOKEN` is set (in `server/.env` locally, in Render's environment settings in production), every
log line is also sent to the Axiom dataset `AXIOM_DATASET` (default `analyzer`) at [axiom.co](https://axiom.co), where it's
kept, searchable and chartable. A background thread sends batches every 2 seconds, so requests never wait on Axiom; if
Axiom is unreachable the lines are skipped and the files still have them. Fields: `_time`, `level`, `logger`, `message`,
`app` (`api` or the script), `run`, `env` (`local`/`render`), `exception`, and per request `method`, `path`, `status`,
`ms`, `ip`. The collector also sends one `event = "source_summary"` row per source per run, and `event = "problem"` rows.

Every API request gets an ID, returned in the `X-Request-ID` header and set as `request_id` on every line it logs:
`['analyzer'] | where request_id == "<id>"` shows one request end to end. Successful health checks and static files
aren't logged. `LOG_LEVEL` overrides the default level (API `INFO`, scripts `DEBUG`), for example `LOG_LEVEL=DEBUG`
on Render to look into a problem without changing code.

## Admin panel

`/admin` is a signed-in page where an admin pastes any job posting URL. The server reads the page
(structured job data first, then the visible text; Workday through its job API; blocked or JavaScript-only
pages through OpenAI web search), an OpenAI model extracts the job, and the admin reviews it and saves it
to the churches or nonprofits dataset. Pages that aren't a single job posting are reported as such.

**Settings** and **AI costs** (admins only) open from the profile menu, the round button at the top right, not from the tabs.
Settings opens on a plain-words summary of what runs by itself (the daily church jobs download, the weekly Excel sheets, the
AI's spending, the daily email) and marks anything that needs a person; each area then has its own section.

Admin accounts live in the database (`admin_users`, scrypt-hashed passwords); sessions live in
`admin_sessions`, so signing out ends a session immediately and no signing secret is needed. Create an admin,
or reset a password, from `server/` (set `DATABASE_URL` to the Neon URL to do it in production):

```bash
python -m app.cli create-admin admin@example.com   # asks for the password
```

Set in `server/.env` locally and in Render's environment settings in production:

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Enables extraction |

## Deploy

One Render web service builds the dashboard and serves it from the API, so the
app and its API share one address. The data lives on Neon.

| Render field | Value |
|---|---|
| Root Directory | *(empty: the repo root)* |
| Build Command | `cd client && npm ci && npm run build && cd ../server && pip install -r requirements.txt` |
| Start Command | `cd server && python -m app.cli migrate && uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*'` |
| Health Check Path | `/api/health` |
| Environment | `DATABASE_URL` = the Neon pooled (`-pooler`) connection string; `PYTHON_VERSION` = `3.12.8`; `NODE_VERSION` = `20` |

`render.yaml` holds the same settings (New → Blueprint). Every `git push`
redeploys. Run database restores and the pipeline against Neon's direct
connection string (same host without `-pooler`).

In local dev, Vite (port 5173) forwards `/api` to the API on port 8000.
