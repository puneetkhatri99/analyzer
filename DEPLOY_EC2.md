# Deploying on one EC2 server

One machine runs everything:

```
internet -> nginx (host, ports 80/443, rate limits, HTTPS)
              -> app container  (FastAPI: the API and the built dashboard, 127.0.0.1:8080)
                   -> db container  (Postgres 18, no public port, data in a Docker volume)
```

Files: [Dockerfile](Dockerfile) (builds dashboard + API), [docker-compose.yml](docker-compose.yml) (app + db),
[deploy/nginx.conf](deploy/nginx.conf) (proxy + rate limits), [deploy/env.example](deploy/env.example) (settings).
Email settings: [EMAIL.md](EMAIL.md).

> These files have not been run on a real EC2 server yet. Do the first deploy with the test steps in section 9.

## 1. The server

- Ubuntu 24.04, `t3.small` or bigger (the image build needs about 2 GB of memory), 20 GB disk or more.
- Security group: 22 (SSH, your IP only), 80, 443. **Never open 8080 or 5432.**
- Give it an Elastic IP and point your domain's A record at it.

## 2. Install

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2 nginx certbot python3-certbot-nginx git
sudo usermod -aG docker $USER      # then log out and back in
```

## 3. Get the code and the settings

```bash
git clone https://github.com/puneetkhatri99/analyzer.git && cd analyzer
git checkout backend-restructure
cp deploy/env.example .env && chmod 600 .env
mkdir -p logs secrets              # log files, and the optional Google key (both owned by you = uid 1000)
nano .env                          # fill in POSTGRES_PASSWORD (openssl rand -hex 24), domain, keys, SMTP
```

## 4. Start the database and load your data

```bash
docker compose up -d db
```

Copy your backup to the server (from your PC: `scp ministry_jobs_*.dump ubuntu@<server>:~/`), then restore it:

```bash
docker compose exec -T db pg_restore -U ministry_app -d ministry_jobs --no-owner < ~/ministry_jobs_YYYYMMDD_HHMMSS.dump
docker compose exec db psql -U ministry_app -d ministry_jobs -c "select count(*) from public.postings"
```

Starting with an empty database instead? Skip the restore; the app creates the tables when it starts (step 5), then
create the first admin (step 7).

## 5. Start the app

```bash
docker compose up -d --build
docker compose ps                  # both "healthy"
curl http://127.0.0.1:8080/api/health
docker compose logs -f app
```

On start the app applies any migrations that are not applied yet (`MIGRATE_UP_TO` in `.env` holds newer ones back; the
old Dockerfile pinned this at 17 because some later ones are destructive. Empty applies all. On a restored database
that already has them, nothing happens).

## 6. nginx and HTTPS

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/analyzer
sudo sed -i 's/yourdomain.org/YOUR.DOMAIN/' /etc/nginx/sites-available/analyzer
sudo ln -s /etc/nginx/sites-available/analyzer /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d YOUR.DOMAIN      # adds HTTPS and renews it automatically
```

Rate limits in [deploy/nginx.conf](deploy/nginx.conf), per visitor address (over the limit gets HTTP 429):

| Where | Limit |
|---|---|
| `/api/admin/login` | 5 a minute (burst 5) |
| `/api/leads`, `/api/leads/events` (public sign-up, tracking) | 20 a minute (burst 10) |
| every other `/api/` path | 10 a second (burst 40) |
| dashboard pages and files | 10 a second (burst 100) |
| open connections | 30 per address |

Change the numbers in the file and run `sudo nginx -t && sudo systemctl reload nginx`. nginx sets `X-Forwarded-For` to
the real visitor address itself, so the app's sign-in lockout and its logs see the right address and a visitor cannot
fake one. That is also why the app's port is bound to 127.0.0.1 only: if it were public, anyone could send their own
`X-Forwarded-For`.

Everyone behind one office or school network shares one address, so keep the sign-up limit generous.

## 7. First admin

```bash
docker compose exec app python -m app.cli create-admin you@yourdomain.org   # asks for the password
```

Then open `https://YOUR.DOMAIN/admin`.

## 8. Daily work

| Task | Command |
|---|---|
| Update to new code | `git pull && docker compose up -d --build` |
| Logs | `docker compose logs -f app` (also `./logs/api.log`) |
| Restart | `docker compose restart app` |
| Database shell | `docker compose exec db psql -U ministry_app -d ministry_jobs` |
| Stop everything | `docker compose down` (the data volume stays; `down -v` would delete it) |

**Backups.** The data lives only in the Docker volume on this one disk, so back it up. Daily dump, 14 days kept
(`crontab -e`):

```
0 3 * * * mkdir -p ~/backups && cd ~/analyzer && docker compose exec -T db pg_dump -U ministry_app -Fc --no-owner ministry_jobs > ~/backups/db_$(date +\%F).dump && find ~/backups -name 'db_*.dump' -mtime +14 -delete
```

Copy the dumps off the machine as well (for example `aws s3 cp` to a bucket), and take EBS snapshots of the disk.
Test a restore once.

**Only one app container.** The daily feed, the daily lead report and the BizDev sync run as timers inside the app
process. Two copies would run the jobs twice and spend AI money twice. Do not scale `app` above 1.

**Private Google Sheets (optional).** A BizDev sheet that only invited people can open can be read by a Google robot
account of the app's own. The app asks Google for read-only access and is shared as Viewer, so it can never change the
sheet. Skip this if the sheets are shared as "anyone with the link".

1. In [Google Cloud Console](https://console.cloud.google.com), create or pick a project. Then go to **APIs & Services →
   Library → Google Drive API → Enable**.
2. Go to **IAM & Admin → Service accounts → Create service account**, for example `sheet-reader`. **Grant it no roles.**
   Then open it and choose **Keys → Add key → Create new key → JSON**. This downloads the key file. It is a password:
   never email it or commit it. Because the account has no roles, the key opens only what you share with it.
3. Share each sheet with the account's email (`sheet-reader@<project>.iam.gserviceaccount.com`) as **Viewer**, with
   "Notify people" unticked.
4. Put the key on the server:

   ```bash
   # from your computer
   scp -i your-ec2-key.pem sheet-reader-key.json ubuntu@YOUR.SERVER:~/analyzer/google-key.json
   # on the server
   cd ~/analyzer && mkdir -p secrets && mv google-key.json secrets/ && chmod 600 secrets/google-key.json
   echo 'GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/google-key.json' >> .env
   docker compose up -d
   # check: prints sheet-reader@<project>.iam.gserviceaccount.com
   docker compose exec app python -c "import google.auth; print(google.auth.default()[0].service_account_email)"
   ```

5. In Admin → Settings → **Excel sheets**, paste each sheet's link, press **Save link**, then **Check the sheets now**.
   `docker compose logs app | grep "Google Drive"` shows `Sheet read through Google Drive as sheet-reader@…`. If
   Google refuses, that line says why, and the app falls back to the plain link.

If step 2 says key creation is disabled, your Google organisation blocks keys. Its admin can allow them for this project.
If sharing in step 3 is blocked ("outside your organisation"), the Google Workspace admin has to allow it.

## 9. First-deploy checklist

1. `docker compose ps` shows `db` and `app` healthy.
2. `curl https://YOUR.DOMAIN/api/health` returns `{"ok":true}`.
3. The landing page and `/report` load; `/admin` asks for sign-in.
4. Sign in, then Admin → Settings → Send test report arrives in your inbox.
5. Rate limit works: `for i in $(seq 1 15); do curl -s -o /dev/null -w "%{http_code} " -X POST https://YOUR.DOMAIN/api/admin/login -H 'Content-Type: application/json' -d '{"email":"x@x.io","password":"x"}'; done` shows `401` first, then `429`.
6. `ss -tlnp | grep -E '5432|8080'` shows 8080 only on 127.0.0.1 and nothing on 5432.

## 10. Troubleshooting

| Problem | Likely cause |
|---|---|
| `app` keeps restarting | `docker compose logs app`: a wrong `.env` value, or the database not restored/migrated |
| `POSTGRES_PASSWORD` error on `up` | Not set in `.env` |
| 502 Bad Gateway | The app is not running or not healthy yet (it waits for the database) |
| Everyone gets 429 | Limits too tight for your traffic; raise them in `deploy/nginx.conf` |
| Permission denied writing `logs/` | `sudo chown -R 1000:1000 logs` |
| Changing `POSTGRES_PASSWORD` later has no effect | Postgres only reads it the first time; change it with `ALTER USER` inside the database |
| Emails fail | [EMAIL.md](EMAIL.md) troubleshooting; EC2 blocks outbound port 25, use 465 or 587 |
