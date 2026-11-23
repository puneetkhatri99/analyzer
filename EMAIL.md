# Email: what the app sends, how, and how to change provider

The app sends plain-text email through **any SMTP server**. Switching provider (Resend, Gmail, SendGrid, your own
host) is a matter of changing environment variables. No code change.

## 1. What emails the app sends

| Email | Sent to | When | Code |
|---|---|---|---|
| **Daily lead report**: yesterday's new hot leads and the day's numbers | The addresses saved in Admin → Settings → Daily lead report | Once a day from 8 AM New York time (the API's own timer in production, or the `daily-report` cron command) | `server/app/leads/daily_report.py` |
| **"Email me this report"**: headline figures and a link to the full report | The visitor who ticked the box on the sign-up form | Right after sign-up (max 5 per address and a site-wide cap per 24 h) | `server/app/leads/report_email.py` |
| **Feed link alerts**: the jobs feed link expires in 7 days, has expired, was refused, or the monthly AI limit is reached | The daily-report addresses | At most one per kind of alert per day | `server/app/ingestion/daily_feed.py` |
| **Test report** (Admin → Settings → Send test report) | The daily-report addresses | When an admin clicks it | `server/app/leads/router.py` |

Every one of them calls the single function `send_email(to, subject, text)` in
`server/app/shared/email.py`. Nothing else in the app talks to a mail server.

## 2. How sending works

1. `email_ready()` is true when an SMTP host (`SMTP_HOST`) and a from address (`ALERT_FROM_EMAIL`) are set. Features
   that need email skip themselves, and say why in the log or Admin page, when it is false.
2. `send_email` opens a connection to `SMTP_HOST:SMTP_PORT` with a 10 second timeout:
   - **port 465**: SSL from the first byte;
   - **any other port (usually 587)**: plain connection upgraded with STARTTLS.
3. If `SMTP_USER` is set it logs in with `SMTP_USER` / `SMTP_PASSWORD`; then it sends the message.
4. Any failure becomes an `EmailError` with a readable reason, e.g.
   `the mail server refused the email (550): ...` or `couldn't send through smtp.example.com (TimeoutError: ...)`.
   Callers record it (report email status, log) and never crash the request. The daily report is marked sent only after
   the server accepts it, so a failed day is retried by the next check.

Messages are plain text, one message per call (all recipients in `To`).

## 3. Settings

Set as environment variables (locally in `server/.env`, in production in your host's environment settings).

| Variable | Meaning | Default |
|---|---|---|
| `SMTP_HOST` | Mail server, e.g. `smtp.resend.com` | empty = email off |
| `SMTP_PORT` | `465` = SSL, anything else (`587`) = STARTTLS | `587` |
| `SMTP_USER` | Login name. Leave empty for a server that needs none | empty |
| `SMTP_PASSWORD` | Login password or API key. Keep secret | empty |
| `ALERT_FROM_EMAIL` | From address, e.g. `MinistryHub Leads <alerts@ministryhub.org>`. Must be allowed by the provider | empty = email off |
| `SITE_URL` | Public address of the site, used for links inside emails | `http://localhost:5173` |
| `RESEND_API_KEY` | **Old setting.** Used only if `SMTP_HOST` is empty: then the app sends through Resend's SMTP (`smtp.resend.com`, 465, user `resend`) with this key | empty |

So an existing deployment that only has `RESEND_API_KEY` and `ALERT_FROM_EMAIL` keeps working without changes.

## 4. How to change provider

Change the variables, restart (or redeploy) the server, then check it with **Admin → Settings → Send test report**.
There is no code to touch.

| Provider | `SMTP_HOST` | `SMTP_PORT` | `SMTP_USER` | `SMTP_PASSWORD` | `ALERT_FROM_EMAIL` |
|---|---|---|---|---|---|
| **Resend** | `smtp.resend.com` | `465` | `resend` | your API key `re_...` | address on a domain verified at resend.com/domains |
| **Gmail / Google Workspace** | `smtp.gmail.com` | `587` | the full Gmail address | an [app password](https://myaccount.google.com/apppasswords) (needs 2-step verification) | the same Gmail address (Gmail rewrites other senders). About 500 emails a day |
| **SendGrid** | `smtp.sendgrid.net` | `587` | `apikey` | your SendGrid API key | a verified sender or domain |
| **Amazon SES** | `email-smtp.<region>.amazonaws.com` | `587` | SMTP user from the SES console | SMTP password from the SES console | a verified identity |
| **Microsoft 365** | `smtp.office365.com` | `587` | the mailbox address | its password or app password (SMTP AUTH must be enabled for the mailbox) | the mailbox address |
| **Your own host / hosting provider** | their SMTP host | `587` or `465` | as they tell you | as they tell you | an address on your domain |

Notes that apply to every provider:
- **Cloud Run, Render and most clouds block outbound port 25.** Use 587 or 465.
- **The from address must be allowed.** A provider will refuse (usually `550` or `403`) mail from a domain you have not
  verified. Verifying means adding the DNS records (SPF, DKIM) the provider shows you.
- **Providers' test senders only deliver to you.** Resend's `onboarding@resend.dev` delivers only to the Resend
  account owner's address. That is fine for a first test, but the daily report and the visitor emails need a verified
  domain. (Admin → Settings shows a notice while the from address is `@resend.dev`.)
- Sending is slow-ish and happens inside the request's background task or the timers; a slow server does not block
  the visitor.

### Switching, step by step

1. Get the host, port, user, password and an allowed from address from the new provider (table above).
2. Edit `server/.env` (local) and/or the production environment variables:
   ```
   SMTP_HOST=...
   SMTP_PORT=...
   SMTP_USER=...
   SMTP_PASSWORD=...
   ALERT_FROM_EMAIL=Name <address@yourdomain>
   ```
3. Restart the server (the settings are read at start-up).
4. Add your address in Admin → Settings → Daily lead report, click **Send test report**, and check it arrives.
5. Remove `RESEND_API_KEY` from the environment if you moved away from Resend (it is ignored once `SMTP_HOST` is set,
   but there is no reason to keep a secret you do not use).

## 5. Setting up Resend (the first provider)

1. Sign up at resend.com and create an API key (Sending access is enough for SMTP).
2. Domains → Add Domain (a subdomain such as `send.yourdomain.org` is a good choice), then add the DNS records Resend
   shows (SPF, DKIM, MX) at the DNS host, and click Verify.
3. Set `SMTP_HOST=smtp.resend.com`, `SMTP_PORT=465`, `SMTP_USER=resend`, `SMTP_PASSWORD=<the re_... key>` and
   `ALERT_FROM_EMAIL=MinistryHub Leads <alerts@send.yourdomain.org>`.

Until the domain is verified, only `onboarding@resend.dev` works as the from address, and only to the account owner.

## 6. Troubleshooting

| What you see | Cause | Fix |
|---|---|---|
| `Email sending isn't set up: SMTP_HOST and ALERT_FROM_EMAIL are needed` | One of them is empty | Set both, restart |
| `the mail server refused the email (550/403): ...` | From address or domain not allowed, or the account is in test mode | Verify the domain / use an allowed sender |
| `the mail server refused the email (535): ...` | Wrong user or password | Re-check the credentials (Gmail: use an app password) |
| `couldn't send through <host> (TimeoutError ...)` or `ConnectionRefusedError` | Wrong host or port, or the network blocks that port | Use 587 or 465; check the host name |
| `couldn't send through <host> (SSLError ...)` | Port and mode mismatch | 465 is SSL; use 587 for STARTTLS |
| Email arrives in spam | SPF/DKIM not set up for the from domain | Add the provider's DNS records |
| Report email shows `failed` in Admin → Leads | The reason after it is the server's answer | See the row above that matches |

Logs: the API logs every failed and skipped send (logger `leads`, `daily_report`, `daily_feed`), searchable by the
reason text above.

## 7. Where the code is

- `server/app/shared/email.py`: `send_email`, `email_ready`, `EmailError` (the only SMTP code).
- `server/app/core/config.py`: the `SMTP_*` and `ALERT_FROM_EMAIL` settings.
- `server/tests/shared/test_email.py`: SSL vs STARTTLS, login, the `RESEND_API_KEY` fallback, unreachable server.
- `server/tests/leads/conftest.py`: the `outbox` fixture that replaces `smtplib` so tests never send real mail.
- `DAILY_REPORT_CRON.md`: running the daily report from a cron job instead of the API's timer.
