Railway deployment notes — django-helpdesk
=======================================

This document describes a minimal, safe deployment path for the `release` branch
using Railway. It assumes you already created a PostgreSQL service on Railway and
you want a separate `backend` (Django) service. If you have a separate frontend
service, create that separately and point it at your frontend build.

Quick checklist
- Create a Railway project
- Add a "backend" service using Docker and point it at `Dockerfile.railway`
- Add Railway Postgres plugin (or an existing Postgres service) and copy its `DATABASE_URL`
- Set environment variables listed below
- Deploy and inspect logs for migrations/collectstatic output

Required environment variables (set these in Railway > Settings > Variables):

- DJANGO_HELPDESK_SECRET_KEY — a secure random string
- DATABASE_URL — the Railway Postgres connection string (postgres://...)
- DJANGO_HELPDESK_ALLOWED_HOSTS — comma-separated hosts (e.g. "*")
- DEFAULT_FROM_EMAIL, SERVER_EMAIL, and optionally EMAIL_HOST/EMAIL_PORT etc

Optional / backwards-compatible env vars (not required if DATABASE_URL is present):

- POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

Persistent storage
- If you want to retain attachments (MEDIA_ROOT), create and attach a persistent
  volume to the Railway service and set `MEDIA_ROOT` to that mount path (for example
  `/data/media`). Alternatively, configure a cloud object storage (S3, GCS) and
  use a storage backend.

Railway service settings
- Build: Dockerfile
- Dockerfile path: `Dockerfile.railway` (root of repo)
- Start command: the Dockerfile runs Gunicorn by default. The container's
  `standalone/entrypoint.sh` will run migrations and collectstatic on startup.

Post-deploy checks
- Open logs: ensure `python manage.py migrate` ran successfully and `collectstatic`
  completed without fatal errors.
- Visit the app URL (Railway assigns one) and verify the home page loads.

Frontend service
- If you have a separate frontend repo or build, create a second Railway service
  named `frontend` and deploy it separately. The screenshot you provided indicated
  two services (backend & frontend) — this keeps builds and scaling independent.

Rollback and branches
- We keep production code on the `release` branch. Update `main` with frontend
  & backend merges, then merge `main` into `release` and push to trigger Railway
  deploys if you have a branch auto-deploy configured.

Troubleshooting
- If static files 404: ensure `DJANGO_HELPDESK_STATIC_URL` / `STATIC_ROOT` are
  consistent and allowed host settings permit accessing the site.
- If migrations fail: inspect the DB `DATABASE_URL` and credentials.

Security
- Do not commit secrets. Use Railway's environment variables UI to store secrets.

That's it — if you'd like, I can add a `railway.json` export to preconfigure services,
or add a small `healthz` endpoint used by Railway for healthchecks.
