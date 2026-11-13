# Church job collector: how it works

`server/pipeline/collect_jobs.py` finds new **US church jobs** on job sites that allow it and saves them to the
**BizDev churches** tab, marked **Auto-collected**. What it leaves out and where it can fail: [COLLECTOR_GAPS.md](COLLECTOR_GAPS.md).

## Running it

From `server/`:

```bash
python -m pipeline.collect_jobs --dry-run              # list new jobs only; reads no job pages, saves nothing
python -m pipeline.collect_jobs                        # every source: read and save every new job
python -m pipeline.collect_jobs --source sbc --source efca --limit 50
python -m pipeline.collect_jobs --days 365             # job boards: look back a year instead of 45 days (first backfill)
```

It's safe to run daily: jobs already saved are skipped. A dry run on 12 Nov 2026 found about **1,370 new jobs**.

## Logs and problem reports

Every run writes a full log to `server/logs/collect_jobs-<date>-<time>.log` (git-ignored). The screen shows the same run more briefly
(`--verbose` shows everything on screen too).

| In the log | Example |
|---|---|
| Run settings | sources, look-back window, database host (never the password), log file path |
| Every request (log file) | `GET https://jobs.sbc.net/... -> HTTP 200, 81,233 bytes, 0.6s` |
| Every listed job (log file) | title, church, place, link, then `NEW`, `already saved`, `older than 45 days` or `outside the US` |
| Each source's total | `[sbc] 444 listed: 300 new, 144 already saved, 0 older than 45 days, 0 outside the US` |
| Each church on a hiring system | `[employers] Victory Church (BambooHR): 2 open jobs`, or why it was skipped |
| Every job page read | `SAVED Pastor \| University Baptist Church \| Macomb, IL \| $36,000–41,000/year \| …`, or `not saved, job is expired or filled` |
| Summary table | per source: listed, new, saved, unverified, expired, blocked, failed, no info, not US |
| **PROBLEMS** | each problem's type, the address involved and what to do; or "none" |

**Problem types.** The run ends with exit code 1 when there are problems, so a scheduler can alert on it:

| Type | When | What to do |
|---|---|---|
| **SITE CHANGED** | An address now returns "not found" (404/410), a reply is no longer JSON or lacks a field the collector reads, a source lists 0 jobs, a source lists under 20% of last run's jobs, or most job pages have no job title | Open the address in a browser and update that source's code |
| **BLOCKED** | The site answers 401/403/429, or most job pages are blocked | Check the site still allows crawling before retrying |
| **SITE DOWN** | No answer, timeouts, server errors (5xx), or most job pages fail to load | Usually temporary; retried next run |
| **DATABASE** | Jobs couldn't be saved | Check `DATABASE_URL` and the database |

One church failing on its hiring system is only listed under "Churches skipped". It becomes a SITE CHANGED problem when
every church (3 or more) on the same hiring system fails. Last run's counts are kept in `server/logs/collect_last_counts.json`
to spot sudden drops.

## The steps

1. **Load what's known.** Every job link already in `church_jobs`, as a `url_key` (the link without `https`, `www`, the
   query string or a trailing slash).
2. **List jobs from each source** (table below).
3. **Keep only:** jobs in the US, jobs not already known, and (for job boards) jobs posted or updated in the last 45 days.
4. **Read each new job's page** with the pipeline's existing reader (`fetch_jobs.fetch_one`). It uses the page's structured
   job data first, then the visible text, to get pay, job type, remote, denomination and church size. It also tells whether
   the job is open, expired, blocked or unreadable.
5. **Save** the open ones (see "How a job is saved").

## Websites and how each is read

| Source | Website | How jobs are listed | Extra |
|---|---|---|---|
| `sbc` | jobs.sbc.net (Southern Baptist) | Its job API (`/wp-json/wp/v2/job-listings`): title, church, location, date. Jobs marked filled are skipped. | Denomination set to Southern Baptist |
| `churchstaffing` | ChurchStaffing.com | Its sitemap: every job link with a last-updated date | |
| `ministrylist` | MinistryList | Its job sitemaps: every job link with a last-updated date | Waits 10 s between requests, as its robots.txt asks |
| `efca` | jobs.efca.org (Evangelical Free) | The job cards on its job board page | Denomination set to Evangelical Free |
| `employers` | Churches' own hiring systems | Each church's public list of open jobs (below) | All open jobs, no date limit |

**Employers source.** It goes through every employer in the database (BizDev churches + the church jobs feed) whose name
looks like a church (*church, chapel, parish, cathedral, fellowship, congregation, diocese, ministry, tabernacle, bible*) and
not like a look-alike (*residence, hospital, health, senior living, university, college, school, academy*). If that church
hires through a system with a public job list, it takes all of the church's open jobs from there:

| Hiring system | Public job list used | Churches (12 Nov) |
|---|---|---:|
| BambooHR | `https://<church>.bamboohr.com/careers/list` | 52 |
| Breezy | `https://<church>.breezy.hr/json` | 11 |
| SmartRecruiters | `api.smartrecruiters.com/v1/companies/<church>/postings` | 4 |
| Workday | `…myworkdayjobs.com/wday/cxs/<church>/<site>/jobs` | 3 |
| Lever | `api.lever.co/v0/postings/<church>` | 2 |
| Greenhouse | `boards-api.greenhouse.io/v1/boards/<church>/jobs` | 1 |
| Recruitee | `https://<church>.recruitee.com/api/offers/` | 1 |
| Workable | `apply.workable.com/api/v1/widget/accounts/<church>` | 1 |

## The criteria

| Rule | How it's decided |
|---|---|
| **Church job** | Job boards: everything (they only list church jobs). Employers: the employer's name matches the church words above. |
| **In the US** | Dropped only if the country is known and isn't the US, or the state isn't a US state. A job with no location is kept, since every source is US-based. |
| **New** | Its `url_key` isn't in `church_jobs` yet. |
| **Recent** | Job boards: posted or updated within `--days` (default 45). Employers: every job currently open. |
| **Still open** | The job page loads and doesn't say it's closed. Expired, blocked and failed pages aren't saved; failed ones are tried again next run. |
| **Allowed to fetch** | Only sites whose robots.txt allows it ([JOB_SITES.md](JOB_SITES.md)). It identifies itself as `MinistryJobsAnalyser/1.0`, waits 1 s between pages of the same site (10 s on MinistryList), and reads up to 8 sites at once. |

## How a job is saved

One new row in `church_jobs` per job. The listing's values come first; the job page fills any gaps.

| Column | Comes from |
|---|---|
| `url_key`, `job_url` | The job link |
| `job_title`, `org_name`, `org_website` | Listing, else the page's structured data |
| `city`, `state` | Listing, else the page; state stored as a 2-letter code |
| `date_posted` | Listing, else the page |
| `salary_min`, `salary_max`, `salary_period` | The page (structured data, else text such as "$45,000 – $55,000 a year") |
| `hours`, `remote`, `church_size` | The page (`hours` from the listing when it has it) |
| `denomination` | The board's denomination (SBC, EFCA), else the page, else the church's name |
| `fetch_status` | `ok` (open), or `unknown` when the page needs a browser to show the job |
| `last_live_at`, `fetched_at` | Now (`last_live_at` only when `ok`) |
| `added_via` | `collector` |
| `sheets` | `{Auto-collected}` |

Contact fields stay empty. Rows are only inserted, never updated (`ON CONFLICT DO NOTHING`), so imported and
admin-added jobs are never overwritten.

**On the dashboard** the jobs appear on the **BizDev churches** tab. "Added via" shows **Auto-collected**, and you can filter
by it under **More filters → Added via**. The role (Pastor, Worship/Music…) and the yearly pay are worked out from the title and
salary when the page loads, like every other job. To mark auto-collected jobs that close, run the existing re-check:
`python -m pipeline.fetch_jobs churches --recheck`.
