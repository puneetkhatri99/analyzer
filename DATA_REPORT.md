# Ministry Jobs Analyser — Data Report

As of 6 November 2026, local database `ministry_jobs`. Every figure below was queried from that database;
none are estimates unless marked.

## 1. Summary

| | Church jobs feed (JSON) | BizDev churches (Excel) | BizDev nonprofits (Excel) |
|---|---|---|---|
| Postings | **1,840** | **658** | **1,894** |
| Postings with pay | 737 (40%) | 124 (19%) | 53 (3%) |
| Median annual pay | **$47,840** | **$61,750** | **$50,500** |
| Middle half (p25–p75) | $38,480–$61,500 | $50,000–$75,000 | $41,600–$71,500 |
| Employers | 534 | 564 | 1,500 |
| States | 56 (full names) | 49 (abbreviations) | 57 (abbreviations) |
| Date posted | Apr 2020 – Nov 3, 2026 | Oct 4 – Oct 31, 2026 | Sep 30, 2025 – Oct 30, 2026 |
| Where pay came from | Stated in the feed | Read from each job page | Read from each job page |
| Database table | `json_jobs` (view) | `church_jobs` | `nonprofit_jobs` |

**Key points**

- The three sources barely overlap. No job URL appears in more than one source. Only 10 church and 25
  nonprofit organization names match the feed.
- The two JSON files supplied are byte-for-byte identical. They also hold the same 1,840 records already
  loaded into the database, so they added nothing new.
- The Excel files are sales lead lists, not job feeds, and contain no pay. Pay was filled in by visiting
  each job URL. That worked for 69% of church pages and only 6% of nonprofit pages, because SimplyHired,
  ZipRecruiter and ACSI block automated visits.
- Excel-sourced pay is higher than the feed's ($61,750 vs. $47,840 median for church jobs), probably
  because the Excel jobs are mostly full-time ministry roles from church job boards.

## 2. Source files

| File | What it is | Rows | Notes |
|---|---|---|---|
| `Jobs_Data_Church_Feed_Created_02.10.26_Expires_02.10.26.json` | Job-postings feed, 37 fields per posting | 1,840 | Same content as `server/data/raw/church_jobs_feed_02.10.26.json`; the file sizes differ only in whitespace |
| `... (1) (1).json` | Duplicate download | 1,840 | Same SHA-256 hash as the file above; safe to delete |
| `API BizDev_ Churches.xlsx` | Contact leads at churches that are hiring | 667 rows on Sheet 1, plus 4 weekly tabs (Weeks 96–99) | Sheet 1 is exactly the 4 weekly tabs combined; 658 unique jobs after cleaning URLs |
| `API BizDev_ Nonprofits (Actual).xlsx` | Contact leads at nonprofits that are hiring | 1,028 rows on Sheet 1, plus 52 weekly tabs (Weeks 35–51) | The weekly tabs hold 1,961 job URLs; Sheet 1 holds only 1,028 of them; 1,894 unique jobs after cleaning URLs |

### Fields

| Information | JSON feed | Excel files |
|---|---|---|
| Job title, job URL, organization, website, city, state, date posted | Yes | Yes |
| Pay (`comp_range`, `comp_est`) | Yes, on 790 rows | **No** |
| Job type, remote, seniority, education, department, tags | Yes | No |
| Full job description (`post_html`), company description, social links | Yes | No |
| Named contact: first/last name, title, email | No (a generic `emails` field on 402 rows) | **Yes** |

### Overlap between sources

URLs were compared after removing the scheme, `www`, query strings and trailing slashes.

| Comparison | Matches |
|---|---|
| Excel job URLs found in the JSON feed | 0 (churches) / 0 (nonprofits) |
| Same job title and organization as in the feed | 2 / 3 |
| Job URLs in both Excel files | 0 |
| Contact emails in both Excel files | 1 (Hope Center Ministries, a different job in each file) |
| Same person and organization in both Excel files | 0 |
| Nonprofit contacts listed for more than one job | 90 |

## 3. Database layout

| Table | Contents |
|---|---|
| `postings`, `companies`, `posting_snapshots`, `title_classifications` | The normalized JSON feed. The dashboard reads these. `title_classifications` is empty because the AI title classifier has never run. |
| `json_jobs` | A view that flattens the feed tables into one row per job, with the same columns as the two tables below. |
| `church_jobs`, `nonprofit_jobs` | One row per unique job URL from each Excel file, across every tab. |

Columns in `church_jobs` / `nonprofit_jobs`:

- **From Excel:** `job_url`, `job_title`, `org_name`, `org_website`, `city`, `state`, `date_posted`,
  `contact_first_name`, `contact_last_name`, `contact_title`, `contact_email`, `note`, and `sheets`
  (every tab the job appeared in).
- **From the job page:** `salary_min`, `salary_max`, `salary_period`, `hours`, `remote`,
  `denomination`, `church_size`, `fetch_status`, `fetched_at`.
- **Reserved, empty:** `canonical_role`, for a later AI role-classification pass.

Contact names and emails are stored in the database but **never returned by the API**.

## 4. How the missing data was fetched

Script: `server/pipeline/fetch_jobs.py`.

1. **Download.** Each `job_url` was fetched once with a plain HTTP request that identifies itself as
   `MinistryJobsAnalyser`. Requests were spaced at least 1 second apart per site, with up to 8 sites in
   parallel.
2. **Structured data first.** If the page carries schema.org `JobPosting` data (most job boards do), the
   script took `baseSalary`, `employmentType` and `jobLocationType` from it. Monthly and weekly pay was
   converted to annual.
3. **Visible text as fallback:**
   - Pay ranges such as "$45,000 – $55,000 per year", "$18–22/hr" or "$50k–$60k". Amounts that cannot be a
     wage were discarded: yearly pay must be between $12,000 and $500,000, hourly pay between $7 and $250.
   - Job type: Full-time, Part-time, Intern or Contract.
   - Church size from "Church/Company Size 1001 to 1500". The lower bound is stored.
   - Denomination, from the organization name or a labeled "Denomination" field only. Matching the whole
     page picked up navigation text and gave wrong labels.
4. **Status recorded per row:**
   - `ok`: the page loaded.
   - `expired`: a 404 or 410, or wording such as "position filled".
   - `blocked`: a 403 or 429, or a bot check such as "Just a moment...".
   - `error`: a timeout or a server error.
5. **Two passes.**
   - First pass: a site was skipped after 10 blocks in a row.
   - Second pass (`--retry --no-skip`): every remaining URL was tried individually.
   - Bot checks were not bypassed.

Parsing is covered by `server/tests/test_fetch_jobs.py`, and I spot-checked 14 extracted salaries against
their job titles.

## 5. Fetch results

### Overall

| Status | Churches | Nonprofits |
|---|---|---|
| Page read (`ok`) | **454** (69%) | **111** (6%) |
| Blocked | 184 | 1,641 |
| Expired | 10 | 141 |
| Error | 10 | 1 |
| **Total** | 658 | 1,894 |

| Field filled from the page | Churches | Nonprofits |
|---|---|---|
| Pay | **124** (108 yearly, 16 hourly) | **53** (28 yearly, 25 hourly) |
| Job type | 438 | 66 |
| Church size | 192 | 0 |
| Denomination | 331 | 13 |
| Remote | 0 | 2 |

### By site: churches

| Site | Jobs | Read | Expired | Blocked | Error | With pay |
|---|---|---|---|---|---|---|
| churchstaffing.com | 203 | 195 | 8 | 0 | 0 | **97** |
| simplyhired.com | 180 | 14 | 0 | 166 | 0 | 8 |
| jobs.sbc.net | 146 | 145 | 1 | 0 | 0 | 6 |
| thegospelcoalition.org | 35 | 35 | 0 | 0 | 0 | 4 |
| ministrylist.com | 27 | 26 | 1 | 0 | 0 | 4 |
| jobs.efca.org | 23 | 23 | 0 | 0 | 0 | 3 |
| caskeycenter.org | 10 | 0 | 0 | 0 | 10 | 0 |
| churchjobs.net | 10 | 0 | 0 | 10 | 0 | 0 |
| alsbom.org | 9 | 1 | 0 | 8 | 0 | 0 |
| Other sites (5) | 15 | 15 | 0 | 0 | 0 | 2 |

### By site: nonprofits

| Site | Jobs | Read | Expired | Blocked | Error | With pay |
|---|---|---|---|---|---|---|
| simplyhired.com | 1,585 | 80 | 0 | 1,504 | 1 | **43** |
| idealist.org | 86 | 6 | 80 | 0 | 0 | 6 |
| careers.acsi.org | 70 | 3 | 0 | 67 | 0 | 3 |
| ziprecruiter.com | 69 | 0 | 0 | 69 | 0 | 0 |
| csionline.org | 38 | 0 | 38 | 0 | 0 | 0 |
| classicalchristian.org | 25 | 20 | 5 | 0 | 0 | 0 |
| societyforclassicallearning.org | 19 | 1 | 18 | 0 | 0 | 0 |
| Other sites (2) | 2 | 1 | 0 | 1 | 0 | 1 |

**Takeaways**

- **churchstaffing.com** supplied most church pay (97 of 124), plus church size and denomination.
- **jobs.sbc.net, thegospelcoalition.org, ministrylist.com and efca** load fine, but most of their
  postings don't state pay.
- **SimplyHired** answers about 1 request in 20, so another retry would add roughly 80 pages at most.
  Some of its figures may be SimplyHired's own estimates rather than the employer's; the page data doesn't
  say which.
- **Many nonprofit links have expired:** 80 of 86 on idealist.org and all 38 on csionline.org.

## 6. Pay benchmarks

Annual pay is the midpoint of the stated range, with hourly pay × 2,080 hours. A group needs at least
5 postings with pay to be benchmarked (shown as "—" below that).

### By role

Roles are assigned from the job title by keyword rules (`server/app/roles.py`).

| Role | Feed: postings / paid / median | Churches: postings / paid / median | Nonprofits: postings / paid / median |
|---|---|---|---|
| Senior/Lead Pastor | 71 / 10 / $68,750 | 71 / 15 / **$87,500** | — |
| Executive Pastor | 7 / 2 / — | 19 / 4 / — | — |
| Associate Pastor | 25 / 4 / — | 40 / 6 / $71,250 | — |
| Pastor/Minister (other) | 398 / 193 / $51,348 | 115 / 18 / $60,000 | 12 / 0 / — |
| Worship/Music | 204 / 43 / $46,800 | 143 / 24 / $56,915 | 6 / 0 / — |
| Youth/Student Ministry | 174 / 80 / $52,500 | 85 / 18 / $56,625 | 24 / 1 / — |
| Children's Ministry | 112 / 48 / $46,800 | 64 / 14 / $55,000 | 50 / 2 / — |
| Director/Coordinator | 153 / 63 / $62,220 | 45 / 10 / $65,000 | 500 / 13 / $55,000 |
| Administrative/Operations | 59 / 19 / $54,250 | 11 / 3 / — | 149 / 4 / — |
| Teacher/Faculty | 47 / 22 / $37,638 | — | 266 / 6 / $41,890 |
| Chaplain | 26 / 16 / $70,876 | 3 / 0 / — | 54 / 2 / — |
| Missions | 26 / 8 / $96,652 | 9 / 1 / — | 24 / 0 / — |
| Facilities | 23 / 8 / $43,281 | 4 / 1 / — | 38 / 3 / — |
| Healthcare | 9 / 6 / $93,414 | — | 22 / 2 / — |
| Other | 479 / 206 / $40,560 | 17 / 3 / — | 625 / 18 / $42,640 |

### By state (top 10 by postings)

| Feed | Postings / paid / median | Churches | Postings / paid / median | Nonprofits | Postings / paid / median |
|---|---|---|---|---|---|
| Texas | 219 / 45 / $39,552 | TX | 73 / 9 / $58,000 | TX | 189 / 4 / — |
| California | 115 / 81 / $52,000 | CA | 48 / 13 / $69,750 | FL | 157 / 6 / $39,000 |
| Florida | 105 / 24 / $47,214 | FL | 41 / 7 / $95,000 | CA | 153 / 5 / $48,204 |
| Michigan | 84 / 30 / $45,840 | NC | 31 / 5 / $67,000 | MI | 90 / 3 / — |
| New York | 81 / 54 / $49,116 | IL | 29 / 11 / $60,000 | PA | 85 / 3 / — |
| North Carolina | 73 / 14 / $48,594 | AL | 28 / 0 / — | NC | 77 / 1 / — |
| Georgia | 67 / 18 / $52,500 | OH | 28 / 7 / $52,000 | VA | 68 / 3 / — |
| Ohio | 62 / 23 / $42,500 | PA | 28 / 6 / $67,500 | WA | 67 / 6 / $44,429 |
| Tennessee | 59 / 16 / $45,280 | TN | 24 / 1 / — | TN | 66 / 1 / — |
| Virginia | 59 / 23 / $52,500 | GA | 24 / 3 / — | CO | 64 / 1 / — |

### By denomination (top by postings)

| Feed | Postings / paid / median | Churches | Postings / paid / median |
|---|---|---|---|
| Christian and Missionary Alliance | 127 / 18 / $62,250 | Baptist | 160 / 20 / $66,500 |
| Baptist | 125 / 19 / $62,500 | Non-denominational | 100 / 51 / $65,000 |
| Catholic | 100 / 41 / $55,000 | Southern Baptist | 15 / 7 / $67,500 |
| Southern Baptist | 30 / 1 / — | Presbyterian | 14 / 2 / — |
| Presbyterian | 26 / 14 / $52,000 | Evangelical Free | 12 / 3 / — |
| Non-denominational | 19 / 9 / $35,360 | Assemblies of God | 9 / 4 / — |
| Roman Catholic | 17 / 3 / — | Methodist | 6 / 0 / — |
| Evangelical (The Salvation Army) | 11 / 10 / $41,600 | United Methodist | 5 / 4 / — |
| Salvation Army | 10 / 8 / $44,200 | | |

Nonprofits: only 13 postings have a denomination (Catholic 8, Lutheran 3, Baptist 1, Nazarene 1).

### Job type

| Type | Feed | Churches | Nonprofits |
|---|---|---|---|
| Full-Time | 1,053 | 360 | 51 |
| Part-Time | 393 | 77 | 14 |
| Other (Hourly, Temp, Student, Intern, Contract…) | 121 | 1 | 1 |
| Not stated | 273 | 220 | 1,828 |

## 7. Data-quality issues

| # | Issue | Effect | Suggested fix |
|---|---|---|---|
| 1 | **Pay outliers in the JSON feed.** 17 postings work out under $15,000 a year: hourly rates labeled "per year" (e.g. "24–30 per year"), $6 "per year", weekly amounts. 15 are over $250,000: hospital physician roles up to $700,000, and "$850–1,000 per hour" for adjunct teaching. Range: $1 – $1,924,000. | Medians barely move, but the histogram and minimum/maximum are distorted. | Apply the same sanity limits used for the Excel pages to the feed, or flag these rows for review. |
| 2 | **Feed roles are weak.** 479 postings are "Other" and 398 "Pastor/Minister (other)"; roles come from keyword rules only. | Pay by role leaves out about half the feed. | Extend the keyword rules in `server/app/roles.py`. |
| 3 | **Role bug, fixed in this round.** The pattern `rector` matched inside "Director", so 82 feed postings were counted as pastors. | Fixed in `server/app/roles.py`, with a test. The live site still has the old numbers until it is redeployed. | Deploy. |
| 4 | **Duplicate denomination names in the feed:** Catholic / Roman Catholic, Southern Baptist / Southern Baptist Convention, Salvation Army / Evangelical (The Salvation Army), Lutheran / Lutheran Church-Missouri Synod. | Each denomination's count is split across names. | Map each name to one standard name. |
| 5 | **State format differs:** the feed uses full names ("Texas"), the Excel files use abbreviations ("TX"). | Sources can't be compared state by state directly. | Convert both to one format on load. |
| 6 | **Remote is rarely stated.** Feed: 232 of 1,840. Excel: 2 of 2,552. | The Remote filter covers few postings. | Label the filter "stated remote / stated on-site". |
| 7 | **Church size is sparse in the feed** (54 of 1,840). The Excel church pages added 192. | The church-size breakdown is thin. | Extract church size from the feed's `post_html`, as was done for the Excel pages. |
| 8 | **Country filter does nothing:** every feed posting is in the United States. | — | Hide it. |
| 9 | **Excel gaps:** 17 church and 1 nonprofit rows have no date posted (one nonprofit date is the typo `10/22/0202`), and 2 nonprofit rows have no state. Each sheet also has about 50 blank rows, which were skipped. | Minor. | Fix at the source spreadsheet. |
| 10 | **Excel pay may include SimplyHired estimates** (51 rows across both files). | Some pay figures may not be the employer's own. | Treat as approximate, or exclude SimplyHired pay from benchmarks. |
| 11 | **Excel files hold personal contact data** (names and emails for about 2,450 contacts). | Privacy risk if published. | `data/` is git-ignored and the API never returns contact fields. Keep it that way if the tables are copied to Neon. |

## 8. How to reproduce

From `server/`:

```bash
python -m pipeline.import_bizdev churches "../data/API BizDev_ Churches.xlsx"
python -m pipeline.import_bizdev nonprofits "../data/API BizDev_ Nonprofits (Actual).xlsx"
python -m pipeline.fetch_jobs churches
python -m pipeline.fetch_jobs nonprofits
python -m pipeline.fetch_jobs nonprofits --retry --no-skip   # re-try blocked and errored rows, never skip a site
```

The dashboard shows each source on its own tab at `http://127.0.0.1:8000/?source=json|churches|nonprofits`.

## 9. Status and next steps

**Status.** Everything in this report is in the **local** database only. Neon and the live site
(analyzer-e3u1.onrender.com) still show the JSON feed alone, with the old role rules, and none of the new
code is committed.

**Next steps, in order of value:**

1. Deploy: create the two tables in Neon, copy the rows, and push the code.
2. Clean the feed's pay outliers (issue 1) and merge duplicate denomination names (issue 4).
3. Run AI role classification on the feed (issue 2).
4. For blocked nonprofit jobs, look for the posting on the employer's own website (the Excel files include
   it), or get pay data directly from whoever compiles the BizDev sheets.
