# MinistryHub Market Analysis Tool: implementation plan

The internal prototype ("Ministry Jobs Analyser") becomes a public, branded MinistryHub resource. It must answer
"what does this role pay?" quickly and then lead the visitor to a conversation with MinistryHub.

The client brief is large, so the work is split into **10 chunks**. Each chunk can ship and be tested on its own.
Chunks 0–4 have to come first: they fix the data and lock down what the public can see. Chunks 5–8 build the public
product. Chunks 9–10 grow the data and are research work.

Reference IDs (P1, D3, A5, R1 …) match the client brief: **P** = public site, **D** = data quality, **A** = admin,
**R** = recommendations.

---

## Open questions (need answers before the chunk that uses them)

| # | Question | Needed for | Status |
|---|---|---|---|
| Q1 | Church size basis: average weekend attendance (AWA), total active followers, formal membership, or online/multi-site reach? **Proposal: AWA.** Job posts and church sites state it most often, and it's the figure comparable tools use. | Chunk 2 | Asked client |
| Q2 | Full list of roles. Can the client share the MinistryHub job board categories? | Chunk 2 | Asked client |
| Q3 | Landing page: show headline stats by default, or show part of the report after the search? | Chunk 5 | Asked client |
| Q4 | What data should the admin export for newsletters and social posts? | Chunk 8 | Asked client |
| Q5 | Denomination merges. "Baptist" vs "Southern Baptist", "Methodist" vs "United Methodist" are different groups. **Proposal:** merge only exact synonyms (SBC = Southern Baptist = Southern Baptist Convention; Catholic = Roman Catholic; the two Salvation Army entries). Keep the generic families separate and let an admin edit the mapping. | Chunk 2 | Needs client OK |
| Q6 | "MinistryHub insight": who writes the two sentences per role, and how often? **Proposal:** admin-edited text per role, hidden when empty. | Chunk 5 | Needs clarification |
| Q7 | "Share with your board": a share link to a read-only report, or just the emailed PDF? | Chunk 6 | Needs clarification |
| Q8 | Sign-up flow: form before the report (as in the design), or "Your report is ready" and then the form? | Chunk 5 | Client to choose |
| Q9 | Regions: which region gets the states the brief doesn't name (Mountain states, Alaska, Hawaii, Plains)? **Proposal:** the six regions from the brief, plus a "Mountain West" region, with every state assigned (table in Chunk 3). | Chunk 3 | Needs client OK |
| Q10 | Hot-lead email: Jordan's address, and the exact trigger (export, 3+ reports, booked-call click). | Chunk 6 | Needs address |
| Q11 | Loxo and Mailchimp: API keys, Mailchimp audience/list ID, Loxo fields to fill. | Chunk 6 | Needs keys |
| Q12 | Privacy notice and Terms of Use page URLs for the sign-up consent line. | Chunk 5 | Needs URLs |
| Q13 | List of job sites to scrape (all MinistryHire sites plus others). | Chunk 9 | Asked client |
| Q14 | Instantly per-contact codes so cold-email visitors skip sign-up. The client is unsure yet. | Chunk 6 (optional) | Later |
| Q15 | Access to Loxo searches and the MinistryHub job board as data sources. | Chunk 9 | Needs access |

Answers already given to the client (kept here for the record):
- **AI provider:** we're using our own OpenAI account, not MinistryHub's. OpenAI can't cap monthly spend, so we build
  the cap into the app. We can support switching between OpenAI and Claude, but we recommend staying on one, because
  switching changes quality and cost.
- **Data refresh:** the data is stale right now. The pipeline gets a schedule once the plan is confirmed. First-seen and
  last-seen dates start recording in Chunk 1.
- **Mobile:** the public site works on mobile, and the redesign keeps it that way.
- **Scraping many sites:** send us the site list (Q13) and we'll use AI to read differently formatted sites (Chunk 9).
- **Contact info for leads:** needs R&D (Chunk 10).

---

## Chunk 0: Security and housekeeping (do first, small)

- [ ] **A6:** remove the reference email and password from the admin sign-in page (`client/src/Admin.jsx`). Change that
      admin's password.
- [ ] **A6:** one sign-in per admin. Accounts already live in `admin_users` (`pipeline.create_admin`). Create one per
      person and remove the shared account.
- [ ] Fix the security and data-loss findings from the audit:
  - Stop link fetching from following redirects to private addresses (SSRF) (`server/app/admin.py`).
  - `push_data` must not wipe jobs that exist only in production.
  - Login lockout must use the real visitor IP behind Render's proxy (`--forwarded-allow-ips`).
  - Compress API replies (GZipMiddleware).
- [ ] Rotate the Axiom token and set `AXIOM_TOKEN` in Render. Merge the `job-collector-and-logging` branch.
- [ ] Rename to **"MinistryHub Market Analysis Tool"** in the header and browser tab.

**Done when:** no credentials appear anywhere on the site, every admin has their own sign-in, and the branch is merged
and live.

---

## Chunk 1: Data model for history, status and decisions (D2, D3, D4, A2)

Today a job is a posting row plus pay snapshots. The tool also needs history, open/closed status, links between reposts,
and a recorded relevance decision.

New or changed tables (`server/database/`):
- **`jobs`**: one row per posting from any source (feed, church sheet, nonprofit sheet, collector, admin-added).
  This is the single blended dataset (P5).
  - Fields: title, description text, employer_id, city, state, country, pay min/max/period, job type
    (full-time / part-time / unknown), role, source, original URL.
  - `status`: open, closed or not verified.
  - `first_seen` and `last_seen` (**D2**, recorded on every run from now on), `closed_at`.
  - `opening_id` links reposts (D3).
  - `relevance`: include or exclude, with `relevance_reason`, `relevance_by` (ai or admin) and `relevance_at` (D1).
- **`employers`**: name, website, kind (church, Christian school, Christian nonprofit or ministry, other),
  denomination, church size (Q1 basis), size source and confidence, `checked_at`, `reviewed_by` (D6).
- **`openings`**: one row per real job opening.
  - Postings with the same employer, title and location that reappear within 90 days are linked to one opening, even
    if the URL changed.
  - Every stat counts openings, not postings (**D3**).
- **Archive (D4):** never delete closed jobs. Keep the core fields (title, employer, place, pay, job type, role, dates)
  for good. Raw page HTML can be dropped after 90 days. Old links don't need to stay live.

Tasks:
- [ ] Migration that copies existing postings and sheet rows into `jobs` and `employers`, keeping `source` and URLs.
- [ ] Update `fetch_jobs --recheck` and the collector to set `status` and `last_seen`, and to set `closed_at` when a
      job disappears from its feed or its page shows it as expired.
- [ ] Repost and duplicate linker: run after every collection.
  - Exact match on normalized employer, title and state first.
  - AI is used only for near-misses, such as a reworded title.
  - Fixes the duplicate "Campus Pastor, Central Christian Church, Arizona".

**Done when:** every job has a status and first/last-seen dates, duplicates collapse into one opening, and nothing
is ever deleted.

---

## Chunk 2: Clean the data (D1, D5, D6, R2, R6)

**Rule: review the data once by hand before the public tool answers anything.**

- [ ] **D1 Relevance (AI):** judge the whole posting and the employer, not keywords.
  - Keep a job only if the employer is a church, a Christian school, or a Christian nonprofit or ministry.
  - Remove all medical jobs and the whole "Healthcare" category.
  - Keep food service and teaching jobs only when the employer is a confirmed church or Christian school.
  - Excluded jobs stay in admin with the reason, and an admin can reverse any call.
  - Test set: the brief's examples must be excluded:
    - Robert Churchwell Elementary
    - Churchville Chili school district
    - Deseret "Church News"
    - Houston Methodist
    - Church's Chicken
    - Church Street addresses
- [ ] **R6 Roles:** a new list of roles.
  - Senior/Lead/Teaching Pastor
  - Executive Pastor
  - Associate Pastor
  - Campus Pastor
  - Worship
  - Youth and Student
  - Children's and Family
  - Discipleship and Groups
  - Communications
  - Operations and Administration
  - Executive Director
  - Head of School
  - Other

  Adjust once the MinistryHub job board categories arrive (Q2). AI classifies using the title **and** the full
  description. Keyword rules (`server/app/roles.py`) stay as a free first pass. Target: "Other" well under 10%.
- [ ] **D5 Lists:**
  - States: only the 50 states plus DC. "Cook", "N/A" and "Varies" become "unknown", or are fixed from the city.
  - Denominations: merge using an admin-editable mapping table (Q5).
  - Employers: remove placeholders such as "Z. Do Not Use".
- [ ] **D6 / R2 Church size and denomination:** look up each **employer** once and apply the result to all its jobs.
  - Method: web search (Tavily) plus AI reading of the church's own site.
  - Save the source URL and a confidence level for each value.
  - Admin spot-check screen: approve or correct, with a random sample each week.
  - Denomination can often be inferred from the church name or site. Size is harder, so leave it empty rather than
    guess.
  - Targets: denomination known for 80% or more of employers. Size known for as many as can be found; current
    coverage is 3%.
- [ ] **Cost guard:** every AI call goes through the existing `ai_usage` logging. Measure cost on a 100-job sample
      first, then estimate the full run and the monthly cost (answers the client's model and cost question).

**Done when:** none of the brief's bad examples remain public, "Other" plus "Pastor/Minister (other)" falls from 48%
to under 10%, the lists are clean, and coverage numbers are reported to the client.

---

## Chunk 3: Pay engine: always give an answer (R1, D4 rules)

All maths runs on the server (`server/app/jobs.py`). The public never receives postings.

- [ ] **Job type:** default to full-time. Show part-time and hourly pay separately as an hourly rate. Stop converting
      hourly pay at 2,080 hours (`HOURS_PER_YEAR`) and mixing it into salary medians.
- [ ] **Time windows (D4):**
  - "Open now" figures use open jobs only.
  - Pay benchmarks use jobs seen in the last 12 months, widening to 24 if needed.
  - Trends use everything.
- [ ] **Auto-widen:** state → region → national.
  - Label it in plain words, for example "Based on Midwest data".
  - Region table (Q9): North East, South East, Midwest, Pacific Northwest, West Coast, Southwest, plus a proposed
    Mountain West, so every state has a region.
- [ ] **Answer format:**
  - Pay range from the 25th to the 75th percentile, plus the median.
  - A confidence label: **Strong**, **Moderate** or **Limited**. Proposed thresholds, to tune after Chunk 2: 30 or more
    paid openings, 10–29, 5–9. Below 5, widen the area.
  - "Too few to benchmark" only when even national data is too thin.
- [ ] **Minimum sample** for any chart row (proposal: 5 paid openings), so tiny groups like Missions or Healthcare
      never headline.
- [ ] **Order roles by importance**, not by pay.
- [ ] **Filters apply to every chart.** The issue: with Worship + Ohio selected, "Pay by role" still shows other roles.
      Either apply all filters or say the chart's scope in its title, for example "Worship pay by state".
- [ ] **No counts in replies:** the API returns ranges, percentages and confidence labels only.
- [ ] Unit tests for the percentiles, widening and confidence labels. There are no pay maths tests yet, which was an
      audit finding.

**Done when:** Worship + Ohio (and every role × state combination) returns a labelled range with a confidence level,
and no API reply contains a raw count.

---

## Chunk 4: Lock down the public API (P4, P5, P6, P7)

- [ ] **P5:** the public API reads only the blended dataset. Remove the `source` parameter and the `/api/sources`
      endpoint from the public side.
- [ ] **P6:** remove public `/api/jobs` (the postings list) entirely. No employer names, job site names, "added via"
      or original links in any public reply. All of this moves under `/api/admin/*`, signed-in only.
- [ ] **P7:** filter options come back without counts (no "Executive Pastor (7)").
- [ ] **P4:** multi-select parameters for state, church size, denomination, role and job type.
- [ ] One public endpoint: `GET /api/report?role=&states=&sizes=&denoms=&type=` → stats, charts and the widening label.
- [ ] Add a test that fails if any public reply contains a URL, employer name or count field.

**Done when:** a visitor using browser dev tools can't see sources, employers, links or counts.

---

## Chunk 5: Public site redesign (P1, P2, P3, P7, P9, R3, R5)

Build from the client's Sample Design. Use the branding and the "Montserrat" font.

| Element | Value |
|---|---|
| Primary teal / dark teal | #028082 / #005F60 |
| Accent yellow | #FFC200 |
| Soft backgrounds | Cream #FFF6DB, Mint #D1EAE4 |
| Text and footer | Black #000000 |
| Logo | MINISTRYHUB wordmark, black with yellow "H"; white on dark |
| Tagline | Power Your Mission With The Right Team. |
| Book a call | https://bookme.ministryhub.org/search-strategy-consultation |

- [ ] **P1 Landing page:**
  - Welcome section, then role and location pickers.
  - Headline stats (Q3), for example:
    - Average salary across all US ministry roles
    - Average size of churches that are hiring
    - Most in-demand roles
  - **R3 "Live market data" message:** "Drawn from 2,000+ active ministry jobs nationwide, refreshed [weekly]". This is
    what churches are offering right now, not last year's survey.
- [ ] **P2 Sign-up:**
  - Fields: name, email and organization, required before any report is shown. Flow per Q8.
  - Consent line linking to the Privacy Policy and Terms of Use (Q12).
- [ ] **P3 Report page:**
  - Kept light: pay for the role, pay by state, by church size and by denomination.
  - All filters (multi-select) change on the report page.
  - "Typical time open" appears once there is enough history (from Chunk 1).
  - What to show and what to hide: agree with the client on the design before building.
- [ ] **P7 Wording:** percentages and general statements only. No "4 Executive Pastor roles", no "19% list a salary".
- [ ] **R5 Marketing in the report:**
  - Calls to action that use the search terms, for example "Hiring a Worship Pastor in Ohio? Let's talk through your
    search." Links go to the consultation page.
  - **"Check my offer":** the visitor enters a salary and sees where it lands against the market. The entered amount is
    saved to their activity.
  - **"MinistryHub insight":** two sentences per role, edited by an admin (Q6).
  - Links to MinistryHub search services.
- [ ] Remove `SourceTabs`, `JobsTable`, `JobDetail` and the origin filter from the public app. Move them to admin.
- [ ] Mobile check on phone width.

**Done when:** a visitor goes landing → sign-up → report → book a call on desktop and phone, with MinistryHub branding
throughout.

---

## Chunk 6: Leads, tracking and integrations (P10, A3, A4, R4, R5)

- [ ] **Users:** `site_users` table (name, email, organization, first sign-up date, last seen). A returning visitor is
      matched by email (A4), so their history continues months later.
- [ ] **Activity (P10):** `user_events` table with time, user, type and details. Event types:
  - search
  - filter change
  - check-my-offer amount
  - export
  - email report
  - call-to-action click
  - share
- [ ] **Hot lead alert:** email Jordan (Q10) when a visitor exports, runs 3 or more reports, or clicks "book a call".
      Mark the user as a warm lead in admin.
- [ ] **Email the report:** send the branded PDF (Chunk 7) to the sign-up address. This also confirms the email is real.
- [ ] **Share with your board (Q7):** proposal: a read-only share link with a random token that opens the same report
      and has its own expiry.
- [ ] **Loxo and Mailchimp sync (R4):**
  - Each new sign-up is added to Mailchimp (newsletter list) and Loxo (contact).
  - Failed syncs are retried and logged; sign-up still succeeds.
  - Needs API keys (Q11).
- [ ] **Optional, later (Q14):** Instantly per-contact code in the link skips the sign-up form and is pre-matched to
      the contact.
- [ ] **Data storage answer for the client:** sign-ups and activity live in our Postgres (Neon), and copies are sent to
      Loxo and Mailchimp.

**Done when:** a test sign-up appears in admin with its full activity, in Mailchimp and in Loxo, and triggers an alert
email when it meets the hot-lead rule.

---

## Chunk 7: Branded export (P8)

- [ ] Replace "Export 1,840 postings" (raw data) with a **branded PDF report**. It contains:
  - MinistryHub logo and colors
  - The visitor's search terms
  - Pay range and confidence label
  - The charts
  - "Check my offer" result, if used
  - The MinistryHub insight
  - A "book a call" link
- [ ] Generate it on the server, so the email (Chunk 6) and the download are the same file.
- [ ] Log every export as an event.

**Done when:** the download matches the client's export design and contains no raw postings, sources or links.

---

## Chunk 8: Admin side (A1–A5)

- [ ] **A1 Source view:** keep the ability to switch between the JSON feed, church sheet and nonprofit sheet. Admin only.
- [ ] **A2 Full jobs list:**
  - Every job shows its source, original link, status (open, closed, not verified) and relevance decision with reason.
  - Filter by status and excluded.
  - An admin can override relevance, role, denomination and size.
- [ ] **A3 Users:** list with name, email, organization, sign-up date, last activity and warm-lead flag. Export to CSV.
- [ ] **A4 Activity:** per-user timeline of searches, filters, exports and call-to-action clicks. Export to CSV.
- [ ] **A5 AI costs:**
  - Keep the costs page.
  - Add a **monthly budget**: AI calls stop and an admin is emailed when it's reached.
  - Put all AI calls behind one small function, so the provider can be changed in config (OpenAI now; Claude possible).
    Stay on one provider.
- [ ] **Data export for newsletter and social posts (Q4):** export of headline stats per role and region, once the
      client says what they need.
- [ ] Review screens for Chunk 2: relevance, duplicates and employer size/denomination spot checks.

**Done when:** an admin can review and correct any automated decision, and see and export every user's activity.

---

## Chunk 9: More data and a live refresh (R3, D2, scale)

- [ ] **Schedule:** run the collector and recheck daily (GitHub Actions or a Render cron job). Alert by email on failure.
      Show the "refreshed" date publicly.
- [ ] **Test the collector writing to the database**, then do the first full run with `--days 365`.
- [ ] **Find more churches:**
  - Tavily searches limited to hiring systems with free job feeds (Breezy, BambooHR, Workday, Lever, Greenhouse …).
  - Plus church job boards.
  - New employers are added to the collector's daily list.
- [ ] **Client site list (Q13):** for each site, check robots.txt and how it can be read.
  - Use the site's feed or sitemap when there is one.
  - Otherwise use **AI extraction** of the job list and job fields, so we don't build one scraper per site. Pages are
    only sent to AI when they changed.
  - Sites that block bots are skipped.
- [ ] **New sources (Q15):** Loxo searches and the MinistryHub job board.
- [ ] Every new source flows into the same cleanup: relevance, role, dedupe and employer lookup.
- [ ] **Monitoring:** Axiom logs and the "site changed" alerts already in the collector.

**Done when:** data refreshes daily without manual work, and the public dataset passes 2,000 active, relevant openings.

---

## Chunk 10: R&D: lead generation (client's extra ask)

- [ ] Export all collected jobs (100+ sites, duplicates removed) to a spreadsheet for MinistryHub's lead generation.
- [ ] **Contact info:**
  - Step 1 (easy): when the posting names a contact (first name, last name, email), AI extracts it.
  - Step 2 (R&D): when it doesn't, find the best contact, such as the executive pastor or HR, from the church's staff
    page, or use a contact-data vendor.
  - Measure the hit rate on 50 churches before deciding whether this can be automated or stays partly manual.
- [ ] Check the legal and ethical limits of collecting contact emails, and use only published business contacts.

**Done when:** the client has a sample spreadsheet with a measured contact hit rate and a go/no-go recommendation.

---

## Issues from the prototype: where each is fixed

| Issue | Chunk |
|---|---|
| Admin email and password on the sign-in page | 0 |
| Worship + Ohio returns no answer | 3 |
| Non-ministry jobs, "Healthcare" category | 2 |
| Duplicate postings | 1 |
| Tiny samples lead the pay-by-role chart (Missions, Healthcare) | 3 |
| 48% in "Other" / "Pastor/Minister (other)" | 2 |
| Church size known for 3%; 5,000+ row has no median | 2 |
| Hourly pay converted at 2,080 hours and mixed in | 3 |
| Role and state filters don't apply to their own charts | 3 |
| "Cook", "N/A", "Varies"; duplicate denominations; "Z. Do Not Use" | 2 |
| Export downloads raw postings | 7 |
| Source, job site and link shown on every posting | 4, 5 |
| No MinistryHub branding, wrong name | 0, 5 |

## Suggested order and rough size

| Chunk | Depends on | Size |
|---|---|---|
| 0 Security | — | Small (1 day) |
| 1 Data model | 0 | Medium |
| 2 Data cleanup | 1, Q1, Q2, Q5 | Large (AI runs + human review) |
| 3 Pay engine | 1, 2 | Medium |
| 4 Public API lockdown | 3 | Small |
| 5 Public redesign | 4, Q3, Q8, Q12 | Large |
| 6 Leads and integrations | 5, Q10, Q11 | Medium |
| 7 Branded export | 5 | Medium |
| 8 Admin | 1, 6 | Medium |
| 9 More data and refresh | 1, 2 (can start alongside 5) | Large, ongoing |
| 10 Lead-gen R&D | 9 | R&D |

Chunks 0–4 can go to the client as **Milestone 1: trustworthy data**. Chunks 5–8 are **Milestone 2: the public
product**. Chunks 9–10 are **Milestone 3: growth**.
