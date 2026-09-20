# Deployment

## Environment variables

See `.env.example` for the full list with defaults. The ones that matter most:

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | Yes | `postgresql+psycopg2://user:pass@host:port/db`. See the Supabase section below. |
| `JWT_SECRET` | Yes | Long random value. Also derives the encryption key for stored platform credentials — see SECURITY.md. |
| `STORAGE_PATH` | Yes | Where uploaded evidence files land. Mounted as a volume in Docker Compose so it survives container restarts. |
| `CORS_ORIGINS` | Yes | Comma-separated list of frontend origins allowed to call the API. |
| `OLLAMA_URL`, `OLLAMA_MODEL` | No | Optional AI-assist backend. The app works fully without it. |
| `PLATFORM_API_KEY`, `SEARCH_API_KEY` | No | Reserved for future direct-env-var credential use; the actual, encrypted-at-rest credential mechanism is the `api_credentials` table via `POST /api/platforms/{id}/credentials` (see API_SPEC.md). |

`.env` is git-ignored. Never commit real secrets — `.env.example` only ever holds
placeholders.

## Using Supabase Postgres

1. Supabase Dashboard → Project Settings → Database → **Connection string** → tab **URI**.
2. For a long-running backend process (not serverless), prefer the **Session pooler** or
   **Transaction pooler** string (port `6543`) over the direct `db.<ref>.supabase.co:5432`
   connection — the pooler is more forgiving of connection churn and, on some networks, is
   the only one that resolves over IPv4 (the direct connection can be IPv6-only).
3. Paste the string into `.env` as `DATABASE_URL`, with your actual database password
   substituted for the placeholder. Add `?sslmode=require` if it isn't already present.
4. On first backend startup, `Base.metadata.create_all()` creates every table if it doesn't
   exist yet (dev-mode convenience — see the migrations note below for production).

**A note on verifying this**: this project was built in a sandboxed environment whose
outbound network only permits HTTPS traffic through a policy-enforcing proxy — it cannot
open a raw TCP connection to a Postgres port (5432/6543) at all, to Supabase or anywhere
else. That's a sandbox limitation, not a code issue: the connection string format, the
SQLAlchemy engine configuration, and every query the app runs were all verified against a
real (SQLite) database in this session; only the literal "can this container reach
Supabase's IP" check couldn't be performed here. Verify it yourself with:

```bash
psql "$DATABASE_URL" -c "select 1;"
```

before assuming the deployment is correctly networked.

## Running with Docker Compose

```bash
cp .env.example .env   # fill in DATABASE_URL and JWT_SECRET at minimum
docker compose up --build
```

This starts `backend` (:8000, also exposed directly), `frontend` (static build served by its
own nginx), and `nginx` (the single public entry point, :8080 → `/` to the frontend and
`/api/*` to the backend). There is **no Postgres container** in this compose file — it's
designed around the managed Supabase instance in `.env`. If you want a fully local stack
instead, add your own `postgres:16` service and point `DATABASE_URL` at it; nothing in the
backend is Supabase-specific.

Add the optional AI-assist container:

```bash
docker compose --profile ai up --build
# then, one time: docker compose exec ollama ollama pull llama3
```

`docker compose config` was used in this session to validate the compose file, both
Dockerfiles' build contexts, and the nginx volume mount all resolve correctly (no Docker
daemon was available in the sandbox to actually build/run the images — do that yourself
before relying on this in production).

## Running without Docker

See the Quick Start in the root `README.md`. In short: a Python venv for the backend
(`uvicorn main:app --reload`), `npm run dev` for the frontend (Vite dev server proxies
`/api` to `localhost:8000` per `frontend/vite.config.ts`).

## Migrations

`database/migrations/0001_init.sql` is a full, reviewable DDL snapshot generated from the
current SQLAlchemy models (enum types + tables, in dependency order). For a fresh production
database, running this file is equivalent to what `Base.metadata.create_all()` does at app
startup, but explicit and auditable. **There is no Alembic version chain yet** — if the
schema changes after initial deployment, you currently need to hand-write the `ALTER
TABLE`/`CREATE TYPE` statements (or add Alembic and generate an autogenerate diff against
`0001_init.sql`'s state). This is a known gap, not an oversight.

## What a production operator still needs to add

These are called out here rather than silently assumed:

- **Scheduled jobs**: nothing in this codebase periodically enforces the retention windows
  in `.env` (`EVIDENCE_RETENTION_DAYS` etc.) or dispatches notifications — the `notifications`
  table exists but nothing writes to it. Add a cron job / Celery beat schedule for both.
- **Backups**: rely on Supabase's own backup features, or `pg_dump` on your own Postgres.
- **TLS termination**: `nginx/nginx.conf` in this repo terminates plain HTTP on :8080; put a
  real TLS-terminating load balancer or Certbot-managed nginx in front of it for anything
  internet-facing.
- **Secrets management**: `.env` is fine for a single-host deployment; for anything larger,
  move `JWT_SECRET`/`DATABASE_URL` into your platform's secret manager and inject them as
  environment variables at container start instead.
