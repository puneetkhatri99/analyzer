# Undeployed Changes

Status as of 10 November 2026. Everything below was built and tested locally. None of it is committed,
pushed to GitHub, loaded into Neon, or live on Render.

- **Live site:** https://analyzer-e3u1.onrender.com. It runs commit `08ca2a9` and shows only the JSON job
  feed.
- **Local:** 11 modified files (+213 / −56 lines), 7 new files or folders, and 3 new tables plus 1 view in
  the local database.

## 1. Summary

| Area | What changed | User-visible? |
|---|---|---|
| Data sources | Two Excel lead files (churches, nonprofits) imported as separate tables alongside the JSON feed | Yes: three source tabs |
| Data enrichment | Each Excel job URL visited to fill in pay, job type, church size and denomination | Yes: pay benchmarks for the Excel sources |
| Expiry tracking | Every job (all three sources) checked for open / expired, with first-seen-closed and last-seen-open dates | Yes: Status filter, Status column, expired counts |
| Bug fix | "Director" titles no longer counted as pastors | Yes: role numbers change on the feed |
| Privacy | Excel files git-ignored; contact names and emails never returned by the API | No |
| Docs | README commands; full data report | No |

## 2. Features

### 2.1 Three data sources, viewed separately

- **Database:**
  - `church_jobs`: 658 jobs from `API BizDev_ Churches.xlsx`.
  - `nonprofit_jobs`: 1,894 jobs from `API BizDev_ Nonprofits (Actual).xlsx`.
  - `json_jobs`: a read-only view of the existing feed tables (1,840 jobs) with the same columns.
- **Import:** every tab of each workbook (the main sheet and the weekly tabs) is read and merged by job URL.
  Re-running the import updates rows without duplicating them.
- **API:** every endpoint accepts `?source=json|churches|nonprofits` (default `json`, so existing links
  keep working). A new `/api/sources` endpoint returns postings, postings with pay, pages read, open and
  expired counts for each source.
- **Dashboard:**
  - Three source tabs above the title, each showing its counts.
  - Charts, filters, the table and the CSV export all follow the selected tab.
  - The tab is kept in the URL (`?source=churches`), and switching tabs clears the filters.
  - The church-size card and filter are hidden on the nonprofit tab.

### 2.2 Filling in missing data from job pages

The Excel files hold contacts and job URLs but no pay. `pipeline/fetch_jobs.py` visits each URL:

1. It reads the page's structured job data (schema.org `JobPosting`) first, then falls back to the page
   text.
2. It extracts:
   - pay (with sanity limits: $12k–$500k a year, $7–$250 an hour);
   - job type;
   - church size (from "Church/Company Size 1001 to 1500");
   - denomination (only from the organization name or a labeled "Denomination" field).
3. It waits 1 second between requests to the same site and does not try to get past bot checks.

| Result | Churches (658) | Nonprofits (1,894) |
|---|---|---|
| Pages read | 454 | 111 |
| Pay found | **124** | **53** |
| Median annual pay | $61,750 | $50,500 |
| Blocked or failed | 194 | 1,642 |

Most blocked pages are SimplyHired (1,765 jobs across both files), which blocks automated visits. ZipRecruiter and ACSI block them too.

### 2.3 Expired-job tracking (all three sources)

- **Fields recorded per job:**
  - check status (`ok`, `expired`, `unknown`, `blocked` or `error`);
  - last checked;
  - **last seen open** (`last_live_at`);
  - **first found closed** (`expired_at`).
- **What counts as expired:**
  - the page returns 404 or 410;
  - it says "position filled", "no longer accepting" or similar;
  - Workday's job API says the job is gone or can't be applied to.
- **What counts as unknown:** JavaScript-only job pages (HRM Direct, BambooHR, ADP, UKG, Oracle) send an
  empty shell. Those jobs are marked `unknown` and shown as **Not verified**, never as open.
- **Re-checks:** `--recheck` re-checks every job not already expired. A later check never moves
  `expired_at` and never erases pay found earlier.
- **Storage:** feed results are in a new `posting_checks` table, because the app's database user cannot
  alter the feed tables. The Excel tables got the same columns.
- **Dashboard:**
  - Each tab shows its expired count.
  - **More filters → Status** filters to Still open, Expired or Not verified.
  - The table has a Status column, e.g. "Expired 2026-11-06", with the last-seen-open date on hover.
  - The CSV export includes the status.

| Source | Open | Expired | Not verified (unknown, blocked, error, unchecked) |
|---|---|---|---|
| JSON feed (1,840) | 1,205 | 36 | 599 |
| Excel churches (658) | 454 | 10 | 194 |
| Excel nonprofits (1,894) | 111 | 141 | 1,642 |

Expired jobs still count toward the pay benchmarks; use the Status filter to leave them out.

## 3. Bug fix: role classification

The role rule matched "rector" (a church office) inside "Di**rector**". As a result, any Director title
that no earlier rule caught was counted as **Pastor/Minister (other)**.

- **Fix:** word boundaries in `server/app/roles.py`, with a test.
- **Effect on the feed:** 82 jobs move from Pastor/Minister (other) to Director/Coordinator
  (480 → 398).
- **The live site still shows the old, wrong numbers.**

## 4. Files

### Modified

| File | Change |
|---|---|
| `server/app/jobs.py` | Loads any of the three sources; adds job status and the expiry dates; status filter; per-source counts |
| `server/app/main.py` | `source` and `status` query parameters; `/api/sources` endpoint |
| `server/app/roles.py` | Director/rector fix |
| `server/requirements.txt` | Adds `openpyxl` (reads Excel) |
| `client/src/App.jsx` | Source tabs, source in the URL, status filter state |
| `client/src/api.js` | Passes `source` to every request; `fetchSources` |
| `client/src/components/FilterBar.jsx` | Status filter; church-size filter hidden for nonprofits |
| `client/src/components/JobsTable.jsx` | Status column (included in the CSV) |
| `client/src/styles.css` | Source tab and status styles |
| `README.md` | Import, fetch and recheck commands |
| `.gitignore` | Ignores `/data/` (the Excel files contain contact details) |

### New

| File | Purpose |
|---|---|
| `server/database/sources.sql` | Creates `json_jobs`, `church_jobs`, `nonprofit_jobs`, `posting_checks`; safe to re-run |
| `server/pipeline/import_bizdev.py` | Loads the Excel files |
| `server/pipeline/fetch_jobs.py` | Visits job URLs: fills in details and records open/expired |
| `client/src/components/SourceTabs.jsx` | The source tabs |
| `server/tests/` | Tests for the page parser, expiry tracking and the role fix (all pass) |
| `DATA_REPORT.md` | Full data report. It does not yet include the expiry numbers. |
| `UNDEPLOYED_CHANGES.md` | This report |

`.vscode/` is also untracked. It holds editor settings and should not be committed.

## 5. Data that exists only in the local database

| Object | Rows | Needed on Neon? |
|---|---|---|
| `json_jobs` (view) | 1,840 | Yes, created by `sources.sql` |
| `posting_checks` | 1,840 | **Yes. The feed query now reads it, so the live site breaks without it.** |
| `church_jobs` | 658 | Yes, for the churches tab |
| `nonprofit_jobs` | 1,894 | Yes, for the nonprofits tab |

`church_jobs` and `nonprofit_jobs` contain contact names and emails for about 2,450 people. The API never
returns these fields, but copying the tables to Neon puts that personal data in the hosted database.

## 6. Deploying: order matters

If the code is pushed before Neon has `posting_checks`, every dashboard request fails.

1. **Create the tables on Neon.** Run `server/database/sources.sql` with the direct (non-pooler) Neon URL.
2. **Copy the data.** Copy rows from local to Neon for `church_jobs`, `nonprofit_jobs` and
   `posting_checks`. Alternatively, run the import and fetch commands against Neon, which takes about
   1–2 hours.
3. **Check the counts on Neon:** 658, 1,894 and 1,840.
4. **Commit and push** everything except `.vscode/`. Render rebuilds automatically; `openpyxl` installs
   from `requirements.txt`.
5. **Smoke-test the live site:**
   - `/api/sources` lists three sources with counts.
   - Each tab loads.
   - The Status filter changes the count.
   - `/api/jobs?source=churches` contains no `contact_` or `email` fields.

**Rollback:** redeploy commit `08ca2a9` on Render. The new Neon tables don't affect the old code.

## 7. Not done yet

| Item | Why it matters |
|---|---|
| Weekly re-check is not scheduled | Expiry data goes stale unless `fetch_jobs ... --recheck` runs regularly (a Windows scheduled task or a Render cron job) |
| `DATA_REPORT.md` lacks the expiry numbers | The report is out of date on job status |
| Feed pay outliers not cleaned | 17 feed postings work out under $15k a year and 15 over $250k (mislabeled hourly/weekly pay, physician roles) |
| Duplicate denomination names not merged | e.g. Catholic / Roman Catholic, so each denomination's count is split |
| Roles come from keyword rules only | 479 feed jobs are "Other"; extend the rules in `server/app/roles.py` |
| No private leads view | The contact data is in the database but not shown anywhere; showing it would need a login |
| Neon password not rotated | Raised earlier and still open |

## 8. How to run locally

From `server/`:

```bash
python -m uvicorn app.main:app --reload --port 8000   # dashboard at http://127.0.0.1:8000
```

After changing anything in `client/`, run `npm run build` in `client/`. If `--reload` misses a server change,
restart the server.
