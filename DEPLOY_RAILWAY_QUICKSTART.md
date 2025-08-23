Railway quickstart — minimal steps to deploy the `release` branch

1) Choose deployment mode

- Option A (recommended): Use the repository Dockerfile. Select the `release` branch and point Railway to the repo root. Set Dockerfile path to `Dockerfile.railway`.
- Option B (Railpack): Use automatic Python build. The repo contains a `Procfile` so Railpack will run Gunicorn.

2) Service settings

- Port: 8000 (Railway will inject $PORT; both Dockerfile and Procfile bind to it)
- Healthcheck path: `/healthz`

3) Environment variables (paste these into Railway for the backend service)

Replace secret values with your real secrets; paste without quotes.

DATABASE_PUBLIC_URL=<your-public-postgres-url>
DATABASE_URL=<your-internal-or-public-db-url>
DJANGO_HELPDESK_SECRET_KEY=<your-secret-key>
DJANGO_ALLOWED_HOSTS=*
DEBUG=False
MEDIA_ROOT=/data/media
STATIC_ROOT=/data/static

Optional (if using an external SMTP provider):
EMAIL_HOST=<smtp-host>
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<username>
EMAIL_HOST_PASSWORD=<password>

4) Volumes

- If you need persistent uploads, attach a persistent volume and set `MEDIA_ROOT` to that mount (example `/data/media`).

5) Trigger deploy

- Start the deploy; watch logs. The container entrypoint will wait for the DB, run migrations and collectstatic, then start Gunicorn.

6) If Railpack reports "No start command was found"

- Ensure `Procfile` exists at the repo root (present). If you use Dockerfile, ensure Railway is configured to build from `Dockerfile.railway`.

7) If something fails, paste the Railway build or deploy logs here and I will parse and fix the issue.
