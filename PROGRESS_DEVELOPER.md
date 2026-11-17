# Progress: MinistryHub Market Analysis Tool

**Status as of 16 November 2026** · branch `backend-restructure` · plan: [NEW_PLAN.md](NEW_PLAN.md) · brief: *Market Analysis Tool – Developer Brief*

> **Summary.** The public product (Chunks 3–5) is mostly built. The data foundation (Chunks 1–2) has barely started,
> and it is the client's stated "big risk". Overall about **45%** of the effort is done; the remaining work is weighted
> towards the large data-cleanup chunks.
>
> ⚠️ This session's work is **not committed**, and neither is a set of earlier edits (`report/service.py`,
> `MarketGlance`, the deleted `InsightCard`). Live Render still runs an older commit; see [UNDEPLOYED_CHANGES.md](UNDEPLOYED_CHANGES.md).

**Legend:** ✅ done · 🟡 partial · ⬜ not started · ⏳ blocked on the client

---

## Overview by chunk

| # | Chunk | Status | Done | Brief refs |
|---|---|---|---|---|
| 0 | Security & housekeeping | ✅ | ~95% | A6 |
| 1 | Data model: history, status, openings | 🟡 | ~15% | D2, D3, D4 |
| 2 | Data cleanup | 🟡 | ~10% | D1, D5, D6, R2, R6 |
| 3 | Pay engine | ✅ | ~85% | R1, D4 |
| 4 | Public API lockdown | ✅ | ~90% | P4–P7 |
| 5 | Public redesign | ✅ | ~85% | P1–P3, P7, P9, R3, R5 |
| 6 | Leads, tracking, integrations | 🟡 | ~20% | P10, A3, A4, R4, R5 |
| 7 | Branded export | 🟡 | ~60% | P8 |
| 8 | Admin | 🟡 | ~40% | A1–A5 |
| 9 | More data & live refresh | 🟡 | ~20% | R3, D2 |
| 10 | Lead-gen R&D | ⬜ ⏳ | 0% | — |

---

## Done

### Chunk 0: Security
- ✅ No credentials on the admin sign-in page ([LoginPage.jsx](client/src/features/admin/auth/LoginPage.jsx)).
- ✅ One account per admin: `admin_users` table, a users page, and `create_admin` on the command line ([auth/](server/app/auth/)).
- ✅ SSRF guard on link fetching (`get_public` in [shared/web.py](server/app/shared/web.py)).
- ✅ Gzip responses, and `--proxy-headers` so the sign-in lockout sees the real visitor IP ([main.py](server/app/main.py), [render.yaml](render.yaml)).
- ✅ Renamed to "MinistryHub Market Analysis Tool".
- 🟡 **Left:** set `AXIOM_TOKEN` in the Render dashboard (`sync: false`). Rotating it isn't needed: the token was never committed.

### Chunk 3: Pay engine ([report/service.py](server/app/report/service.py))
- ✅ Full-time pay is yearly; part-time is an hourly rate, never mixed (`_pay`).
- ✅ Auto-widen state → region → national, with a plain-words note; seven regions in [shared/geo.py](server/app/shared/geo.py).
- ✅ P25–P75 range plus median, and a confidence label (`CONFIDENCE`: 30 / 10 / 5).
- ✅ A row needs `MIN_PAID = 5` paid jobs; roles are ordered by importance (`ROLE_ORDER`).
- ✅ Healthcare is hidden (`HIDDEN_ROLES`); unit tests in [test_report.py](server/tests/report/test_report.py).
- ⬜ **Left:** D4 time windows. Pay should use jobs seen in the last 12 months (widening to 24); "open now" figures should use open jobs only. Today every job counts.

### Chunk 4: Public API
- ✅ The single public endpoint is `GET /api/report` (multi-select `role/state/size/denomination`, plus `type`), with `/api/report/options` for the choices.
- ✅ `/api/jobs`, `/api/sources`, `/api/summary` and `/api/filter-options` need a signed-in viewer ([jobs/router.py](server/app/jobs/router.py)).
- ✅ No counts, employers, sources or URLs in public replies; `openings_label` rounds ("2,000+").

### Chunk 5: Public site ([features/landing](client/src/features/landing/), [features/report](client/src/features/report/))
- ✅ Landing page with headline stats (`MarketGlance`), the lead form, branding, and the book-a-call band.
- ✅ Report: pay card, market stats, breakdowns, multi-select refine panel, widened-search note.
- ✅ Check my offer (`OfferCheck`, `offerVerdict` in [pay.js](client/src/features/report/lib/pay.js)).
- ✅ "MinistryHub insight" removed, as the client asked.
- ✅ Privacy Policy and Terms link to ministryhub.org/privacy-policy/ and /terms-and-conditions/ (footer and sign-up consent line).
- ⏳ **Left:** real `SERVICES_URL` and `HOW_URL`; they point to the homepage for now ([links.js](client/src/features/site/links.js)).

### This session
| Change | Where |
|---|---|
| **Share menu**: copy link, `mailto:` email, download PDF | [ShareMenu.jsx](client/src/features/report/components/ShareMenu.jsx), [share.js](client/src/features/report/lib/share.js) |
| **Shared links require sign-up**: `/report` redirects to `/?next=<report>`, and the form then asks only for name, email and organization before opening that report. `next` only accepts `/report…` (no open redirect). | [ReportPage.jsx](client/src/features/report/ReportPage.jsx), [useLeadForm.js](client/src/features/landing/useLeadForm.js), [LeadForm.jsx](client/src/features/landing/LeadForm.jsx) |
| **Fix: Share menu didn't open**: `Button` now uses `forwardRef` (React 18 + Radix `asChild`) | [button.jsx](client/src/components/ui/button.jsx) |
| **Fix: Reset filters** goes back to the search the report opened with, and is disabled until a filter changes | [useReport.js](client/src/features/report/hooks/useReport.js), [RefinePanel.jsx](client/src/features/report/components/refine/RefinePanel.jsx) |
| **Logs**: with `APP_ENV=production` and `AXIOM_TOKEN` both set, logs go to Axiom only (`writes_files()`) | [logs.py](server/app/core/logs.py), [config.py](server/app/core/config.py), [test_logs.py](server/tests/core/test_logs.py) |

---

## Not done

### 🔴 Quick fixes (about a day, do first)
1. **Nonprofits are in the public numbers.** The client said "don't turn it on live yet". `blended_jobs()` loops over `("json", "churches", "nonprofits")`.
2. **The sign-up form promises an email that never goes out.** [LeadForm.jsx](client/src/features/landing/LeadForm.jsx) says "We'll email you a copy". Reword it until Chunk 6 sends the email.
3. **"Active openings" counts expired jobs and duplicates.** `openings_label(len(jobs))`. Fix with the D4 time windows.
4. **Lead history is lost.**
   - `ON CONFLICT … DO UPDATE` in [leads/router.py](server/app/leads/router.py) overwrites role and location.
   - Returning visitors skip `postLead` entirely, so their searches aren't recorded.
   - Both get fixed by the event log in Chunk 6.
5. **Lint:** E501 at `server/app/report/service.py:124`.

### Chunk 1: Data model
- ⬜ `employers` table: kind, denomination, church size, source URL, confidence, `checked_at`, `reviewed_by`.
- ⬜ `openings`: link reposts (same employer, title and state within 90 days); every stat counts openings, not postings.
- ⬜ Relevance columns: `relevance`, `relevance_reason`, `relevance_by`, `relevance_at`.
- 🟡 `last_live_at` and `expired_at` exist for the BizDev tables ([0003_expiry_tracking.sql](server/migrations/0003_expiry_tracking.sql)); a consistent `first_seen` / `last_seen` across all sources is still needed.
- ⬜ Never delete closed jobs. `delete_job` in [jobs/repository.py](server/app/jobs/repository.py) still deletes rows outright.

### Chunk 2: Data cleanup
- ⬜ **D1 relevance (AI):** judge the whole posting and the employer. The brief's examples are the test set (Churchwell Elementary, Churchville Chili, Deseret "Church News", Houston Methodist).
- ⬜ **R6 roles:** [roles.py](server/app/jobs/roles.py) is still the old list, matched on the title only.
  - Missing: Campus Pastor, Executive Director, Head of School, Discipleship & Groups.
  - "Teaching Pastor" maps to Discipleship instead of Senior/Lead.
  - Target: "Other" under 10%. ⏳ Q2.
- 🟡 **D5 lists:**
  - States: ✅ (`state_name`).
  - Denominations: `denomination_in()` runs only on new collector or extraction rows. `load_jobs` passes raw values, so duplicates still reach the public filter. ⏳ Q5.
  - Placeholder employers: ⬜ ("Z. Do Not Use").
- ⬜ **D6 / R2:** look up each employer once and apply it to all its postings. Today only the single-job lookup in admin Add Job exists (`lookup_church`).

### Chunk 6: Leads and integrations
- ⬜ `user_events` table: search, filter change, offer amount, export, share, email, CTA click.
- ⬜ Hot-lead email (export, 3+ reports, or a book-a-call click). ⏳ Q10.
- ⬜ Server-sent report email. Needs an email provider; today's email option is `mailto:` only.
- ⬜ Loxo daily and Mailchimp weekly sync, with retries. ⏳ Q11.
- ⬜ Optional: Instantly per-contact codes that skip the sign-up form (Q14).
- ℹ️ The sign-up gate runs only in the browser; `/api/report` is open. Acceptable while replies hold only summary figures.

### Chunk 7: Branded export
- 🟡 Print-to-PDF works ([PrintReport.jsx](client/src/features/report/components/PrintReport.jsx)).
- ⬜ A server-generated PDF, needed so the email and the download are the same file.
- ⬜ Log every export as an event.

### Chunk 8: Admin
- ✅ A1 source tabs, A2 jobs list (source, link, status), A5 costs page, A6 accounts.
- ⬜ A2: relevance decision with its reason, plus overrides for relevance, role, denomination and size.
- ⬜ A3/A4: a page of visitors who signed up, with an activity timeline and CSV export. The current Users page lists admin accounts only.
- ⬜ A5: monthly AI budget (stop AI calls and email an admin), and one provider-swappable AI function.
- ⬜ Newsletter and social export (Q4).

### Chunk 9: Data refresh
- 🟡 The collector exists ([ingestion/collector](server/app/ingestion/collector/)).
- ⬜ A scheduled run: no cron job in `render.yaml` and no GitHub Actions workflow.
- ⬜ The first full DB run with `--days 365`.
- ⬜ The client's site list. ⏳ Q13.
- ⚠️ `collect_last_counts.json` lives in `server/logs/`. On Render's temporary disk it's wiped between runs, so the "sudden drop" warning never fires. Move it to the database before scheduling.

### Chunk 10: Lead-gen R&D
- ⬜ Not started. ⏳ Q13.

---

## Blocked on the client

| Q | Need | Blocks |
|---|---|---|
| Q2 | MinistryHub job board role list | R6 roles |
| Q5 | OK on the denomination merge rules | D5 |
| Q10 | Jordan's email address | Hot-lead alert |
| Q11 | Loxo and Mailchimp keys, list ID | Sync |
| Q12 | ~~Privacy Policy and Terms of Use URLs~~ Done: using the existing ministryhub.org pages | Sign-up consent line |
| Q13 | List of job sites | Chunks 9–10 |
| Q15 | Access to Loxo searches and the MinistryHub job board | More data |

---

## Suggested order

1. 🔴 Quick fixes (above).
2. **Chunks 1 + 2:** data model, then relevance, dedupe, roles and denominations. Review the output by hand before the public tool goes live.
3. **D4 time windows** in the pay engine.
4. **Chunk 6 + A3/A4:** event log, visitors page in admin, hot-lead alert.
5. **Chunk 7:** server PDF, then the report email.
6. **Chunk 9:** scheduled refresh, then more sources.

## Running the checks

```bash
cd client && npm test && npm run build        # 9 tests
cd server && python -m pytest && python -m ruff check app tests
```
