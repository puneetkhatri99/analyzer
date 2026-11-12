# Job sites in the database: which can be fetched

Checked on 12 November 2026 against every job site in the local database: **94 sites, 4,393 postings**.

## Summary

| Verdict | Sites | Jobs in DB |
|---|---:|---:|
| ✅ Yes, through a public jobs API | 9 | 698 |
| ✅ Yes, plain page fetch | 49 | 1,268 |
| 🟡 Yes, but needs a real browser | 11 | 94 |
| ⛔ No, robots.txt forbids it | 13 | 341 |
| 🚫 No, the site blocks bots | 6 | 1,856 |
| ❓ Unclear | 6 | 136 |

**Source** is where the jobs came from: the church jobs **Feed**, the BizDev **Churches** sheet, or the BizDev **Nonprofits** sheet.
Feed sites are employers' hiring systems (Workday, Breezy…). Each church has its own page on them, so you can only
watch employers you already know; you can't search the whole platform. Spreadsheet sites are job boards you can search.

## How this was checked

Each site was tested two ways on up to 3 real job links from the database, preferring jobs still open and different employers:

- **Check A, plain request:** the same user agent and job-page parser your pipeline uses. It reads robots.txt (rules for all crawlers or for this bot,
  wildcards, longest match wins), waits each site's crawl delay, and passes if the page returns 200 with the job title or structured job data in the
  HTML and no bot wall. Public jobs APIs were called where the platform has one.
- **Check B, real browser:** headless Chrome loads the same links and passes if the job title appears on the rendered page with no bot wall.
- **By hand:** every robots.txt "forbids" was traced to the exact rule. Every case where A and B disagreed was reviewed: "captcha" text
  from an apply form isn't a block, and iCIMS public vs internal sites differ.

`A 2/3` means 2 of the 3 sampled job pages passed check A.

## ✅ Yes, through a public jobs API (best option)

Structured data per employer, no page scraping needed.

| Site | Jobs in DB | Source | How to fetch / why not | Evidence |
|---|---:|---|---|---|
| Workday | 338 | Feed | Workday job API (already used by your pipeline). | A 3/3 · B 3/3 · robots: ok |
| Breezy | 174 | Feed | Breezy `/json` feed per employer. | A 3/3 · B 3/3 · robots: ok |
| BambooHR | 105 | Feed | BambooHR `/careers/list` per employer. | A 0/3 · B 2/3 · robots: ok |
| SmartRecruiters | 38 | Feed | SmartRecruiters public postings API. | A 3/3 · B 3/3 · robots: ok |
| Lever | 21 | Feed | Lever public postings API. | A 3/3 · B 3/3 · robots: ok, delay 1s |
| Recruitee | 13 | Feed | Recruitee `/api/offers/`. | A 3/3 · B 3/3 · robots: ok |
| Greenhouse | 4 | Feed | Greenhouse job board API. | A 3/3 · B 3/3 · robots: ok |
| Workable | 3 | Feed | Workable public jobs API. | A 0/3 · B 3/3 · robots: ok |
| Ashby | 2 | Feed | Ashby job board API. | A 1/2 · B 2/2 · robots: ok |

## ✅ Yes, plain page fetch

robots.txt allows it and a normal request gets the job.

| Site | Jobs in DB | Source | How to fetch / why not | Evidence |
|---|---:|---|---|---|
| churchstaffing.com | 203 | Churches | Search pages allowed; its `/api/` and filtered searches are not. | A 3/3 · B 3/3 · robots: ok |
| HRM Direct (ClearCompany) | 164 | Feed | Readable, but your pipeline can't tell open from closed (shown as Not verified). | A 3/3 · B 3/3 · robots: ok |
| jobs.sbc.net | 146 | Churches | Also has a WordPress job API and an RSS feed (checked by hand; the automated API test misread the reply because it starts with an invisible byte-order mark). | A 3/3 · B 3/3 · robots: ok |
| Paylocity | 109 | Feed | — | A 3/3 · B 3/3 · robots: ok |
| idealist.org | 86 | Nonprofits | Has a job sitemap. | A 3/3 · B 3/3 · robots: ok |
| iCIMS | 59 | Feed | Public `careers-…` sites allow crawling and publish a sitemap; `internal-…` staff sites forbid it, so skip those. | A 3/3 · B 0/3 · robots: forbids |
| Recruiterflow | 55 | Feed | — | A 3/3 · B 3/3 · robots: ok |
| ApplyToJob (JazzHR) | 52 | Feed | 25 of its rows have no job link. | A 2/3 · B 2/3 · robots: ok |
| CareerPlug | 45 | Feed | — | A 3/3 · B 3/3 · robots: ok |
| Loxo | 35 | Feed | — | A 3/3 · B 3/3 · robots: ok |
| thegospelcoalition.org | 35 | Churches | Allowed, but only 1 request every 10 minutes. | A 1/1 · B skipped (crawl delay) · robots: ok, delay 600s |
| Trakstar Hire | 28 | Feed | — | A 3/3 · B 3/3 · robots: ok |
| ministrylist.com | 27 | Churches | 1 request every 10 s. Has a full job sitemap. | A 3/3 · B 3/3 · robots: ok, delay 10s |
| classicalchristian.org | 25 | Nonprofits | — | A 3/3 · B 0/3 · robots: ok |
| jobs.efca.org | 23 | Churches | — | A 3/3 · B 3/3 · robots: ok |
| Rippling | 22 | Feed | — | A 2/3 · B 2/3 · robots: ok |
| BrassRing | 22 | Feed | — | A 3/3 · B 3/3 · robots: ok |
| societyforclassicallearning.org | 19 | Nonprofits | 1 live job read fine; the others are expired. | A 1/3 · B 1/3 · robots: ok |
| Betterteam | 17 | Feed | — | A 3/3 · B 3/3 · robots: ok |
| iSolvedHire | 14 | Feed | — | A 3/3 · B 3/3 · robots: ok |
| Gusto | 11 | Feed | Plain fetch works; a headless browser gets blocked. | A 3/3 · B 0/3 · robots: ok, delay 1s |
| USAJobs | 7 | Feed | — | A 3/3 · B 3/3 · robots: ok |
| ministryconnections.truettseminary.baylor.edu | 7 | Churches | Plain fetch works; a headless browser gets blocked. | A 3/3 · B 0/3 · robots: ok |
| GetHired | 5 | Feed | — | A 3/3 · B 3/3 · robots: ok |
| Efficient Apply | 5 | Feed | — | A 3/3 · B 3/3 · robots: ok |
| CSOD (Cornerstone) | 5 | Feed | — | A 3/3 · B 3/3 · robots: ok |
| jobs.wts.edu | 4 | Churches | Plain fetch works; a headless browser gets blocked. | A 3/3 · B 0/3 · robots: ok |
| Jobvite | 3 | Feed | — | A 3/3 · B 3/3 · robots: ok |
| JobScore | 3 | Feed | — | A 3/3 · B 3/3 · robots: ok |
| ApplicantStack | 3 | Feed | — | A 3/3 · B 3/3 · robots: ok, delay 5s |
| EdJoin | 3 | Feed | — | A 3/3 · B 3/3 · robots: ok |
| AppliTrack | 3 | Feed | — | A 3/3 · B 1/3 · robots: ok |
| WizeHire | 2 | Feed | — | A 2/2 · B 2/2 · robots: ok |
| JobAdder | 2 | Feed | — | A 2/2 · B 2/2 · robots: ok |
| Pinpoint | 2 | Feed | — | A 2/2 · B 2/2 · robots: ok |
| ApplicantPro | 2 | Feed | — | A 2/2 · B 2/2 · robots: ok |
| Manatal | 2 | Feed | — | A 2/2 · B 2/2 · robots: ok |
| youthcartel.jobboardly.com | 2 | Churches | — | A 2/2 · B 2/2 · robots: ok |
| Insperity Talent Connect | 1 | Feed | — | A 1/1 · B 1/1 · robots: ok |
| HireClick | 1 | Feed | — | A 1/1 · B 1/1 · robots: ok, delay 10s |
| SilkRoad | 1 | Feed | — | A 1/1 · B 1/1 · robots: ok |
| WorkBright | 1 | Feed | — | A 1/1 · B 1/1 · robots: ok |
| SnapHire | 1 | Feed | — | A 1/1 · B 1/1 · robots: ok |
| HR Partner | 1 | Feed | — | A 1/1 · B 1/1 · robots: ok |
| Tracker RMS | 1 | Feed | — | A 1/1 · B 1/1 · robots: ok |
| TriNet Hire | 1 | Feed | — | A 1/1 · B 1/1 · robots: ok |
| justchurchjobs.com | 1 | Churches | — | A 1/1 · B 1/1 · robots: ok |
| hiu.edu | 1 | Churches | — | A 1/1 · B 1/1 · robots: ok |
| apps.westernseminary.edu | 1 | Churches | — | A 1/1 · B 1/1 · robots: ok |

## 🟡 Yes, but needs a real browser

robots.txt allows it, but the job only appears after JavaScript runs (or plain requests are refused). Slower and heavier to scrape.

| Site | Jobs in DB | Source | How to fetch / why not | Evidence |
|---|---:|---|---|---|
| Oracle | 44 | Feed | — | A 0/3 · B 3/3 · robots: ok |
| ADP Career Site | 12 | Feed | — | A 0/3 · B 3/3 · robots: ok |
| caskeycenter.org | 10 | Churches | Refuses plain Python connections; a real browser loads it. | A 0/3 · B 3/3 · robots: ok |
| HiringThing | 7 | Feed | — | A 1/3 · B 3/3 · robots: ok |
| Dayforce | 6 | Feed | — | A 0/3 · B 3/3 · robots: ok |
| PageUp | 6 | Feed | — | A 1/3 · B 3/3 · robots: ok |
| Taleo | 5 | Feed | — | A 0/3 · B 3/3 · robots: ok |
| Fountain | 1 | Feed | — | A 0/1 · B 1/1 · robots: ok |
| SchoolSpring | 1 | Feed | — | A 0/1 · B 1/1 · robots: ok |
| Interfolio | 1 | Feed | — | A 0/1 · B 1/1 · robots: ok |
| Gem | 1 | Feed | — | A 0/1 · B 1/1 · robots: ok |

## ⛔ No: robots.txt forbids crawling

The pages often load fine, but the site's rules say not to crawl them. Get these jobs another way: the admin's "add a job from a URL", or a partner feed.

| Site | Jobs in DB | Source | How to fetch / why not | Evidence |
|---|---:|---|---|---|
| Paycom | 111 | Feed | Pages load, but robots.txt disallows the whole site. | A 3/3 · B 3/3 · robots: forbids |
| ziprecruiter.com | 69 | Nonprofits | robots.txt disallows everything, and the site returns 403. | A 0/3 · B 0/3 · robots: forbids |
| UKG Ready | 44 | Feed | — | A 0/3 · B 3/3 · robots: forbids |
| Paycor | 43 | Feed | — | A 3/3 · B 1/3 · robots: forbids |
| UKG Pro | 37 | Feed | — | A 0/3 · B 3/3 · robots: forbids |
| Zoho Recruit | 15 | Feed | — | A 3/3 · B 3/3 · robots: forbids |
| Paychex | 10 | Feed | — | A 3/3 · B 3/3 · robots: forbids |
| NEOGOV (governmentjobs.com) | 4 | Feed | — | A 0/3 · B 3/3 · robots: forbids |
| SuccessFactors | 3 | Feed | robots.txt disallows the `company=` job links. | A 3/3 · B 3/3 · robots: forbids |
| PeopleAdmin | 2 | Feed | — | A 2/2 · B 2/2 · robots: forbids |
| CivicPlus | 1 | Feed | — | A 1/1 · B 1/1 · robots: forbids |
| Vincere | 1 | Feed | — | A 0/1 · B 1/1 · robots: forbids |
| indeed.com | 1 | Nonprofits | robots.txt disallows `/viewjob`, and the site returns 403. | A 0/1 · B 0/1 · robots: forbids |

## 🚫 No: the site blocks bots

Both a plain request and a real browser were refused (403 or a bot-check page).

| Site | Jobs in DB | Source | How to fetch / why not | Evidence |
|---|---:|---|---|---|
| simplyhired.com | 1,765 | Churches | 403 for both checks (bot wall). Biggest gap: 1,765 of your postings. | A 0/3 · B 0/3 · robots: ok |
| careers.acsi.org | 70 | Nonprofits | 403 (bot wall) for both checks. | A 0/3 · B 0/3 · robots: ok |
| churchjobs.net | 10 | Churches | robots.txt allows it, but the site answers 403 (bot wall) to both checks. | A 0/3 · B 0/3 · robots: ok |
| alsbom.org | 9 | Churches | 403 (bot wall), and asks for 10 minutes between requests. | A 0/3 · B skipped (crawl delay) · robots: ok, delay 600s |
| Avature | 1 | Feed | 403 for both checks. | A 0/1 · B 0/1 · robots: ok |
| careers.cccu.org | 1 | Nonprofits | Bot wall for both checks. | A 0/1 · B 0/1 · robots: ok |

## ❓ Unclear

| Site | Jobs in DB | Source | How to fetch / why not | Evidence |
|---|---:|---|---|---|
| ADP Workforce Now | 88 | Feed | Page loads, but the job never appears, even in a real browser (it loads inside nested frames). | A 0/3 · B 0/3 · robots: ok |
| csionline.org | 38 | Nonprofits | Site is up and allows crawling (1 request / 10 s), but all 38 jobs in your DB are expired (404), so no live job could be tested. | A 0/3 · B 0/3 · robots: ok, delay 10s |
| Infor CloudSuite HCM | 4 | Feed | Page loads, but the job text was not found in either check. | A 0/3 · B 0/3 · robots: ok |
| Homebase | 3 | Feed | Page loads, but the job text was not found in either check. | A 0/3 · B 0/3 · robots: ok |
| Dover | 2 | Feed | Page loads, but the job text was not found in either check. | A 0/2 · B 0/2 · robots: ok |
| Eploy | 1 | Feed | Page loads, but the job text was not found in either check. | A 0/1 · B 0/1 · robots: ok |

## Caveats

- This is a technical check, not legal advice. robots.txt shows what a site allows crawlers to do; read each site's terms of use before scraping it.
- Results can change: bot walls and robots.txt rules get updated. Re-check before building a scraper for a site.
- 1 to 3 jobs per site were sampled, and for hiring systems the result covers those employers only. A few employers may set different rules,
  as iCIMS's internal sites do.
