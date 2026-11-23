# Daily lead report: how it is sent

Every morning at **8:00 AM US Eastern**, the addresses saved in **Admin → Settings** get one email listing
yesterday's **new hot leads** (3 or more reports viewed) and the day's numbers. It is sent even on days with no hot
leads, so a missing email means something is wrong.

**No cron job needed (the default):** in production (`APP_ENV=production`, with `RESEND_API_KEY` and
`ALERT_FROM_EMAIL` set) the API checks every 10 minutes and sends the report itself from 8 AM New York time. A free
Render service asleep at 8 AM sends it when it next wakes, and catches up on missed days (up to a week back); to get
it on time, keep an uptime pinger hitting `/api/health` every 5 minutes.
The deploy log shows `Daily lead report: sent once a day at 8 AM New York time…` when it's on.

**Or a cron job** (sections 4 and 5), if the server may sleep or runs on several instances. It runs one command:

```bash
cd server && python -m app.cli daily-report
```

Both can run at once: each day is sent once (`daily_report_sent_for` in `app_settings`). The rare exception is the
two checking in the same second.

Code: [server/app/leads/daily_report.py](server/app/leads/daily_report.py).

## Example email

```
Subject: MinistryHub daily leads: 1 new hot lead (Nov 16)

Lead report for Monday, November 16, 2026 (US Eastern)

1 new hot lead (3 or more reports viewed):

- Emily Rodriguez, Hope Fellowship
  emily.rodriguez@example.org
  Reports viewed: 4 | Latest search: Executive Pastor in Texas and Oklahoma
  Offer checked: $98,000 a year (Competitive)

The day in numbers:
  New sign-ups: 3
  Reports viewed: 5
  Leads active: 2
  Hot leads in total: 3

See every lead and their history: https://<your-site>/admin#leads
```

---

## 1. Set up Resend (once)

> The app sends through any SMTP server; Resend is the first provider. Other providers and the full settings are in
> [EMAIL.md](EMAIL.md).

Resend sends the email. The free plan allows 3,000 emails a month, far more than one a day needs.

1. Sign up at [resend.com](https://resend.com).
2. **Domains → Add Domain.** Use a domain MinistryHub controls, ideally a subdomain such as
   `mail.ministryhub.org`, so its email reputation is kept apart from everyday mail.
3. Add the DNS records Resend shows (SPF, DKIM and the bounce MX/TXT) wherever the domain's DNS is managed, then
   click **Verify**. This usually takes minutes, and at most a few hours.
4. **API Keys → Create API Key** with *Sending access*. Copy it (it starts with `re_`); it's shown only once.

**Testing before the domain is verified:** set `ALERT_FROM_EMAIL=onboarding@resend.dev`. Resend only delivers those
to the email address that owns the Resend account.

## 2. Environment variables

| Variable | Example | Needed by |
|---|---|---|
| `DATABASE_URL` | the Neon `-pooler` connection string | web service, cron job |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | Resend: `smtp.resend.com`, `465`, `resend`, `re_…` (keep secret). Other providers: [EMAIL.md](EMAIL.md) | web service (for the test button), cron job |
| `RESEND_API_KEY` | old setting, still works alone when `SMTP_HOST` is empty | web service, cron job |
| `ALERT_FROM_EMAIL` | `MinistryHub Leads <alerts@mail.ministryhub.org>` | web service, cron job |
| `SITE_URL` | `https://analyzer-e3u1.onrender.com` | cron job (the link in the email) |
| `APP_ENV` | `production` | cron job (with `AXIOM_TOKEN`: logs go to Axiom only) |
| `AXIOM_TOKEN` | optional | cron job (so each run's log is kept) |

Locally, put them in `server/.env` (see `server/.env.example`).

> **Tip (Render):** put `DATABASE_URL`, `RESEND_API_KEY`, `ALERT_FROM_EMAIL` and `AXIOM_TOKEN` in an
> **Environment Group** and link it to both the web service and the cron job, so they're set in one place.

## 3. Database

The report needs **migration 0010** (`leads.hot_at` and the `app_settings` table). `render.yaml` runs the migrations on
every start (see its `--up-to`).

## 4. Optional: add a cron job on Render

### Option A: Render dashboard

1. **New → Cron Job**, and connect this repository and branch.
2. Fill in:

   | Field | Value |
   |---|---|
   | Name | `daily-lead-report` |
   | Runtime | Python 3 |
   | Root Directory | *(empty: the repo root)* |
   | Build Command | `pip install -r server/requirements.txt` |
   | Command | `cd server && python -m app.cli daily-report` |
   | Schedule | `0 12,13,14 * * *` |

3. **Environment:** add the variables from step 2, or link the Environment Group. Also set `PYTHON_VERSION` =
   `3.12.8`, as on the web service.
4. Create it.

### Option B: `render.yaml` (Blueprint)

Add this under `services:` and sync the Blueprint:

```yaml
  - type: cron
    name: daily-lead-report
    runtime: python
    schedule: "0 12,13,14 * * *"   # UTC; the command sends from 8 AM New York time, once per day
    buildCommand: pip install -r server/requirements.txt
    startCommand: cd server && python -m app.cli daily-report
    envVars:
      - key: PYTHON_VERSION
        value: 3.12.8
      - key: APP_ENV
        value: production
      - key: SITE_URL
        value: https://analyzer-e3u1.onrender.com
      - key: ALERT_FROM_EMAIL
        value: MinistryHub Leads <alerts@mail.ministryhub.org>
      - key: DATABASE_URL
        sync: false
      - key: RESEND_API_KEY
        sync: false
      - key: AXIOM_TOKEN
        sync: false
```

> **Cost:** cron jobs are a paid Render service. Each run is a few seconds, so the cost is the plan's small monthly
> minimum; check Render's pricing page. Adding the block above to `render.yaml` creates that paid service on the
> next Blueprint sync, which is why it isn't in the file yet.

### Why three hours (`12,13,14`)?

Cron schedules on Render are in **UTC**. 8 AM in New York is 12:00 UTC in summer (EDT) and 13:00 UTC in winter
(EST), so running at 12:00, 13:00 and 14:00 UTC always includes **8 AM and 9 AM New York time**, all year.

- The first run from 8 AM sends every report not sent yet (yesterday's, plus any missed day up to a week back).
- Later runs send only what an earlier run failed to send. This is the automatic retry.
- A run before 8 AM, or with everything sent, logs "nothing to send".

A day is marked as sent only after Resend accepts the email, so exactly one email goes out per day, and nothing
needs changing when the clocks move.

## 5. Other ways to schedule it

**Linux server (`crontab -e`):**

```cron
0 12,13,14 * * * cd /srv/analyser/server && /srv/analyser/.venv/bin/python -m app.cli daily-report >> /var/log/daily-report.log 2>&1
```

**GitHub Actions** (`.github/workflows/daily-report.yml`). Add the variables as repository secrets:

```yaml
name: Daily lead report
on:
  schedule:
    - cron: "0 12,13,14 * * *"
  workflow_dispatch: {}          # a "Run workflow" button for testing
jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r server/requirements.txt
      - run: cd server && python -m app.cli daily-report
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          RESEND_API_KEY: ${{ secrets.RESEND_API_KEY }}
          ALERT_FROM_EMAIL: ${{ secrets.ALERT_FROM_EMAIL }}
          SITE_URL: https://analyzer-e3u1.onrender.com
          APP_ENV: production
```

GitHub sometimes starts scheduled runs late; the report then simply goes out late.

## 6. Test it

| What | How |
|---|---|
| See the email without sending | `python -m app.cli daily-report --dry-run` |
| Send yesterday's report right now | `python -m app.cli daily-report --force`. It counts as that day's report, so the 8 AM run won't repeat it. |
| Send a given day | `python -m app.cli daily-report --day 2026-11-16` |
| Check recipients and the Resend setup | **Admin → Settings → Send test report**. It doesn't count as the day's report. |
| Run the cron job once on Render | The cron job's page → **Trigger Run**. Before 8 AM New York time, or when the day is already sent, it logs "nothing to send", which is correct. |

**Did it run?**
- Render: the cron job's **Logs** and **Events** tabs; a failed run is marked failed.
- Axiom: `['analyzer'] | where app == "daily_report"`.

## 7. Troubleshooting

| Log line / symptom | Cause | Fix |
|---|---|---|
| `Not sent: no addresses in Admin → Settings` | No recipients saved | Add them in Admin → Settings and click **Save** |
| `Not sent: RESEND_API_KEY and ALERT_FROM_EMAIL must both be set` | Variables missing on the cron job | Add them (step 2) |
| `Resend refused the email (403/422) …` | Domain not verified, or the from address isn't on it | Finish step 1; check `ALERT_FROM_EMAIL` |
| `It's 7:00 in New York, before the 8 AM send` | Normal for a run before 8 AM | Nothing |
| No email, no failure | The day was already sent (`--force` earlier that morning) | Expected |
| A day was missed for more than a week | Catch-up only goes a week back | `python -m app.cli daily-report --day YYYY-MM-DD` sends that day |

When a send fails, the day is **not** marked as sent and the run exits with code 1, so the job shows as failed. The
next run (or the API's next check) tries again automatically.
