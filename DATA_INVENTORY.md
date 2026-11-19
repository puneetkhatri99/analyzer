# Data inventory

What data the Ministry Jobs Analyser holds, as of **19 November 2026**. Every count is from the **local** database
(`ministry_jobs`). Production (Neon) hasn't been synced with it yet; see [DAILY_FEED.md](DAILY_FEED.md) for how.

In short: **about 4,300 US ministry jobs** from three sources (JSON, BizDev churches, BizDev nonprofits), 881 of them with pay. Alongside them are 10 leads and
their activity, the AI cost log, and the admin and settings tables.

## At a glance

| Table | Rows | What it holds | Where it comes from |
|---|---:|---|---|
| `postings` | 1,770 | JSON jobs (title, location, link, hours, dates, pay) | Daily JSON download + AI review |
| `companies` | 653 | JSON employers, with type, denomination and church size | Daily JSON download + AI review / lookup |
| `rejected_postings` | 427 | JSON jobs judged out of scope, with the reason and a full copy | AI review and admins |
| `church_jobs` | 659 | BizDev church job leads, with contact details | Excel sheets, "Add a job", the collector |
| `nonprofit_jobs` | 1,894 | BizDev nonprofit job leads, with contact details | Excel sheets |
| `leads` | 10 | People who signed up on the public site | Public lead form |
| `lead_events` | 92 | What those leads did (reports viewed, offers checked…) | Public site |
| `ai_usage` | 50 | Each OpenAI call: purpose, tokens, cost | Daily JSON run and "Add a job" |
| `admin_users` | 1 | Admin accounts (1 admin) | `create-admin` command |
| `admin_sessions` | 0 | Signed-in admin sessions | Sign-in |
| `app_settings` | 4 | JSON link, last JSON run, lead-email recipients | Admin → Settings |
| `schema_migrations` | 17 | Which database migrations have run | `migrate` |

## 1. JSON jobs

"JSON jobs" are the jobs from a signed JSON link (a file of job postings) downloaded once a day.
In the admin they are the **JSON** source (`?source=json`); some older docs and code call this the "feed". Each new posting is saved, then checked by the AI review.
The review decides three things: is the employer a church, Christian school or ministry; what type of employer it is;
and what pay the posting states.

**Postings (`postings`): 1,770 jobs, all reviewed**
- First seen between **10 Apr 2020 and 17 Nov 2026**; 288 were first seen more than a year ago.
- **Hours:** 1,072 full-time, 315 part-time, 23 hourly, 21 internships, 282 not stated.
- 79 remote. Locations cover 54 states and regions.
- The job description text (`post_html`) is **not stored**: it exists only in that day's JSON file.

**Pay (on `postings`): 706 jobs with pay (40%)**

| Pay came from | Jobs |
|---|---:|
| Stated in the JSON | 684 |
| Read from the posting text (one-off review) | 22 |

- 489 of these are yearly pay and 217 hourly.
- Monthly, bi-weekly and weekly pay is converted to yearly; day rates and project fees are left out.
- Figures that aren't a believable wage are dropped (e.g. "$6 a year").
- Jobs were downloaded on two days: 5 Nov (1,497 jobs) and 18 Nov (273 new jobs).

**Employers (`companies`): 653**

| Employer type | Employers | With church size | With denomination |
|---|---:|---:|---:|
| Church | 320 | 99 | 254 |
| Other (not Christian, or for-profit) | 172 | 1 | 5 |
| Christian nonprofit / ministry | 84 | 2 | 24 |
| Christian school | 70 | 0 | 34 |
| Not set (go-betweens: search firms, residency networks) | 7 | 0 | 0 |

- Church size is weekly attendance, found by an AI web search. Each size keeps its source page (`church_size_url`).
- A size is used only if the number appears in the quoted source and is no more than 8 years old.
- 318 of the 320 churches have been looked up; 2 are waiting.

## 2. Rejected jobs (`rejected_postings`): 427

JSON jobs that aren't at a church, Christian school or ministry, and all medical jobs. They come from 199 employers.
Each row keeps the whole posting and its pay. The daily JSON run skips these jobs if they come back, by ID or by URL.
An admin can include a job again from **Admin → Rejected jobs**.

| Rejected by | Jobs |
|---|---:|
| One-off review (Claude, Nov 2026) | 424 |
| Daily AI review | 3 |

Most common reasons:

| Reason | Jobs |
|---|---:|
| Ladgov: for-profit contractor staffing military chapels | 24 |
| Deseret Book: for-profit retailer | 16 |
| Not a specific job opening (general application, talent pool) | 15 |
| Allied Universal: security company, the church is only the site | 14 |
| Learning Care Group: for-profit child care at church sites | 10 |
| Domino's: "Church Rd" is an address | 10 |

## 3. BizDev sheets

These are lead lists imported from Excel. They hold **contact names and emails**. The job lists and the public report never
carry them; only a signed-in editor or admin sees one job's contact, in its detail dialog. The source spreadsheets sit in the git-ignored `data/` folder.

| | Churches (`church_jobs`) | Nonprofits (`nonprofit_jobs`) |
|---|---:|---:|
| Jobs | 659 | 1,894 |
| Organizations | 565 | 1,500 |
| With pay | 124 (19%) | 53 (3%) |
| With denomination | 332 | 13 |
| With church size | 192 | 0 |
| With a contact email | 658 | 1,894 |
| Job page blocked when read | 184 | 1,641 |
| Date posted | 2 Sep – 31 Oct 2026 | 30 Sep 2025 – 30 Oct 2026 |
| States | 49 | 57 |
| How rows arrived | 658 Excel, 1 "Add a job" | 1,894 Excel |

- Pay, job type, denomination and size come from reading each job's page (`check-jobs churches|nonprofits`).
- `fetch_status` records how that read went.
- The collector (`collect-jobs`) can add church jobs here as "Auto-collected", but it hasn't saved any locally yet.
- These sheets have **not** been checked against the scope rule the JSON jobs use, so some nonprofit jobs are secular.

## 4. What the public report uses

The report blends all three sources into **4,301 US jobs**: 1,770 JSON, 659 church and 1,872 nonprofit jobs.
Medical (Healthcare) roles are removed, and so are JSON jobs not yet reviewed (none today). **881 have pay** (706 JSON,
124 church, 51 nonprofit).

**Jobs by role**

| Role | Jobs |
|---|---:|
| Other | 1,014 |
| Director/Coordinator | 703 |
| Pastor/Minister (other) | 529 |
| Worship/Music | 374 |
| Teacher/Faculty | 319 |
| Youth/Student Ministry | 309 |
| Children's Ministry | 232 |
| Administrative/Operations | 208 |
| Senior/Lead Pastor | 158 |
| Communications/Media | 87 |
| Associate Pastor | 72 |
| Missions | 60 |
| Chaplain | 60 |
| Finance | 57 |
| Facilities | 55 |
| Discipleship/Teaching | 36 |
| Executive Pastor | 28 |

**States:** 50 states and DC; 101 jobs have no state. The top ten are Texas 489, California 314, Florida 302, Michigan 191, North Carolina 179,
Pennsylvania 174, Ohio 148, Washington 143, Tennessee 141 and Virginia 136.

**Denominations:** 1,366 jobs have one.

| Denomination | Jobs |
|---|---:|
| Non-denominational | 351 |
| Baptist | 332 |
| Catholic | 171 |
| Christian and Missionary Alliance | 141 |
| Southern Baptist | 90 |
| Presbyterian | 56 |
| Assemblies of God | 20 |
| Salvation Army | 19 |
| United Methodist | 18 |
| Evangelical Covenant | 18 |

**Church size:** 568 jobs have one.

| Weekly attendance | Jobs |
|---|---:|
| Under 250 | 62 |
| 250 to 999 | 85 |
| 1,000 to 4,999 | 156 |
| 5,000 or more | 265 |

## 5. Leads, AI costs and admin data

- **Leads (`leads`):** 10 sign-ups between 12 and 18 Nov 2026, 6 of them "hot" (3 or more reports viewed). Each holds
  name, email, organization, role, location and church size as entered on the form. Team addresses
  (`IGNORED_LEAD_DOMAINS`) aren't stored.
- **Lead activity (`lead_events`):** 92 events.

  | Event | Count |
  |---|---:|
  | Report viewed | 49 |
  | Signed up | 17 |
  | Offer checked | 13 |
  | Clicked | 4 |
  | Call to action clicked | 4 |
  | Report downloaded | 4 |
  | Report emailed | 1 |

- **AI costs (`ai_usage`):** 50 calls, all church lookups from the 18 Nov JSON run, costing about **$1.22**. Earlier test
  calls weren't logged. Migration 0018, held back, clears this table when you run it by hand.
- **Admin (`admin_users`, `admin_sessions`):** 1 admin account. Passwords are stored only as scrypt hashes, sessions
  only as SHA-256 hashes.
- **Settings (`app_settings`):** the JSON link, the last JSON run's status, the "already ran today" marker and the
  daily lead-email recipients.

## 6. Gaps

- **Production isn't synced.** Neon still has the old data, and none of the review results.
  `push-data` copies them (DAILY_FEED.md).
- **Church size is thin for small churches:** only 62 jobs are under 250 attendance, against 265 at 5,000 or more.
- **Pay coverage is low outside the JSON jobs:** 19% of BizDev church jobs and 3% of nonprofit jobs.
- **Jobs aren't tracked as open or closed.** Every job ever loaded counts, including 288 JSON jobs first seen over a
  year ago.
- **BizDev sheets aren't scope-reviewed.** Secular nonprofit jobs are still in the report.
- **No job description text is kept,** so postings can't be re-reviewed after they leave the JSON file.
- **"Other" is the largest role group** (1,014 jobs): titles the role rules don't recognise.
