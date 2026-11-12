# Church job collector: what's left out, compromises and failure points

How the collector works: [COLLECTOR_HOW_IT_WORKS.md](COLLECTOR_HOW_IT_WORKS.md). Site-by-site test results: [JOB_SITES.md](JOB_SITES.md).

## Websites left out

| Website | Church jobs in DB | Why |
|---|---:|---|
| SimplyHired | 180 | Blocks bots (403) |
| ChurchJobs.net | 10 | Blocks bots (403), although its robots.txt allows crawling |
| ALSBOM | 9 | Blocks bots (403), and asks for 10 minutes between requests |
| ZipRecruiter, Indeed | — | Block bots, and robots.txt forbids crawling |
| Paycom, Paycor, UKG Ready, UKG Pro, Paychex, Zoho Recruit, NEOGOV, SuccessFactors, PeopleAdmin, CivicPlus, Vincere | — | robots.txt forbids crawling |
| The Gospel Coalition | 35 | Allowed, but 1 request per 10 minutes: hours for a few dozen jobs |
| iCIMS, Paylocity, HRM Direct, ADP, Oracle, CareerPlug, ApplyToJob, Loxo, Trakstar, Rippling, BrassRing and other hiring systems | — | A job page can be read, but there's no public list of a church's open jobs, so new jobs can't be found |
| Ashby | — | No church in the database uses it |
| Idealist, Classical Christian, Society for Classical Learning, CSI, ACSI, CCCU | — | Nonprofit and school jobs, not church jobs |
| Seminary boards (Truett, Westminster, Western), Hope Intl. University, JustChurchJobs, Youth Cartel | 1–7 each | Few jobs, mostly academic; not worth a collector yet |

"—" means these sites appear in the church jobs feed rather than the BizDev churches sheet.

## Compromises

1. **Jobs with no location are kept.** All sources are US-based, so a job with no stated place is assumed to be in the US.
2. **Churches are recognised by name.** Employers are matched on words like *church* or *ministry*. A church whose name
   has none of them (e.g. "Saddleback", "Hillsong") is missed. A non-church that has one can slip in; hospitals, schools
   and senior housing are filtered out.
3. **Every job of a church employer is kept**, including non-ministry roles (coffee shop manager, marketing, facilities).
   They're church jobs, but they land in the "Other" role and can pull the overall median.
4. **Only churches already in the database** are watched on hiring systems. New churches there are never discovered.
5. **No pay for some systems.** Workday and BambooHR job pages only show the job in a browser, so pay and church size stay
   empty and the status shows "Not verified".
6. **Job boards look back 45 days.** Older jobs that are still open are missed on the first run unless you run with `--days 365`.
7. **"Updated" stands in for "posted"** on ChurchStaffing and MinistryList: their sitemaps only give a last-updated date.
8. **Denomination is assumed** from the board: every SBC job is "Southern Baptist", every EFCA job "Evangelical Free".
9. **No AI church-size lookup.** Church size is saved only when the page states it (ChurchStaffing usually does). The admin
   panel's paid lookup isn't used.
10. **The same job on two sites is saved twice** (e.g. SBC and ChurchStaffing), because their links differ. It's also not
    checked against the church jobs feed tab.
11. **Titles are kept as written**, including campus codes such as "Groups Pastor (SLK)".
12. **Closed jobs aren't caught by the collector itself.** The weekly `fetch_jobs churches --recheck` marks them.

## Points of failure

| What can break | What happens | What to do |
|---|---|---|
| A site changes its layout or API (EFCA job cards, SBC API fields, `/job/` links in sitemaps, Workday API path) | Reported as **SITE CHANGED** with the address: "not found", a missing field, 0 jobs listed, a drop to under 20% of last run, or job pages without job details | Open the address; fix that source's code |
| A site changes in a way the checks can't see (e.g. a field still exists but holds something else) | Odd values get saved without a warning | Look at a few new Auto-collected jobs on the dashboard now and then |
| A site adds a bot wall or changes robots.txt | Reported as **BLOCKED**; pages aren't saved | Re-check the site ([JOB_SITES.md](JOB_SITES.md)); remove it if it now forbids crawling |
| A site is slow or down (MinistryList timed out once in testing) | Reported as **SITE DOWN**; that source stops for this run, the others carry on | Nothing; it's retried next run |
| One church's hiring system fails | Listed under "Churches skipped" with the reason; **SITE CHANGED** only when every church (3+) on that system fails | Nothing, unless it keeps happening |
| A location the parser doesn't understand ("2 Locations" on Workday) | Saved with an odd city and no state | Fix in `split_place` if it's common |
| A non-church employer matches the name rule | Its jobs are saved as church jobs | Add a word to `NOT_CHURCH_RE` |
| The database is unreachable | The run fails at the start; nothing is saved | Check `DATABASE_URL` |
| `DATABASE_URL` points at production (Neon) | Jobs go straight to the live site | Intended for scheduled runs; use `--dry-run` to try things |
| Nobody runs it | No new jobs: there's no schedule yet | Add a daily GitHub Actions or Render cron job |
| A run fails without anyone noticing | The log and PROBLEMS list say what failed, and the exit code is 1, but nothing sends an alert yet | When scheduling it, alert on a failed run (GitHub Actions emails on failure by default) |
| First run takes a while | About 1,400 pages: roughly 15–20 minutes (MinistryList's 10 s gap is the slowest) | Use `--limit` or `--source` to split it |

**Not yet tested:** saving to the database. Reading was tested on every source, and the code's unit tests pass. Start
with a small run, e.g. `python -m pipeline.collect_jobs --source efca --limit 5`, and check those jobs on the dashboard.
