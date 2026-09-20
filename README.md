# Report Validator — Evidence Collection, Violation Validation & Platform Reporting System

*Also: **Account Violation Finder** — enter a public social media account URL and get back
a structured, evidence-backed dossier of *candidate* policy violations for a human reviewer
to verify.*

This is a Trust & Safety case-management system, not a takedown bot. Its guiding principle:

> **ONE VALID REPORT > MANY DUPLICATE REPORTS.**

It exists to help an operator turn publicly verifiable evidence into a complete, honest,
duplicate-checked report that a human has reviewed — ready to be filed through a platform's
own official reporting channel. It will never:

- mass-report, report-bomb, or brigade a target,
- fabricate, alter, or embellish evidence,
- bypass a CAPTCHA, login wall, or rate limit,
- automatically resubmit the same case,
- claim a "violation" without a human confirming it first.

If it cannot find adequate public evidence, it says so:
*"Tidak ditemukan bukti pelanggaran yang memadai dari sumber publik yang diperiksa."*
If it finds an indication but not enough evidence, it says that too — it never rounds up.

## What's actually implemented (read this before demoing)

This was built and **verified by actually running it** — the backend against a live SQLite
database (Postgres/Supabase isn't reachable from the sandbox this was built in — see
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)), the frontend against that backend in a real
browser via Playwright. 30 pytest tests pass; the UI was clicked through end to end
(login → dashboard → case → evidence upload/verify → assessment → review-queue approval →
report generation/export → Account Finder) with screenshots and zero console errors.

**Fully working:**
Auth (JWT) + RBAC (5 roles) · case/target/evidence/policy CRUD · SHA-256 evidence hashing +
chain of custody · evidence verification (source/integrity checks) · rule-based violation
triage engine with a hard "human review required" gate · review queue with
approve/reject/request-more-evidence/return · report generation with a weighted readiness
score · duplicate-report detection (409, points to the existing report) · PDF/JSON/CSV
export · manual-submission tracking · Account Violation Finder (public-page collection →
policy-keyword triage → Indonesian-language findings, never fabricated) · append-only audit
log · encrypted-at-rest platform API credentials · Docker Compose stack.

**Present but narrower than the original spec's ambition, on purpose:**
- **AI assist** (`services/ai_service.py`) calls a local Ollama instance if one is
  configured and reachable, and returns `UNKNOWN`/falls back to the rule engine otherwise.
  It was not exercised against a real Ollama instance in this session — no Ollama was
  running in the build sandbox.
- **Official platform API submission** (`OfficialApiPlatformAdapter`) is real code (HTTPS
  POST with the stored credential), but has no real platform to test against. The default,
  always-safe path is `ManualPlatformAdapter` — export the report and file it yourself.
- **OSINT collection** is a single authenticated-as-nobody HTTPS GET of the public page
  plus HTML meta-tag extraction (title/description/OG tags) with SSRF protection. It is
  **not** a multi-source OSINT engine — no search-API integrations
  (Google/Bing/Brave/Serper/Tavily/SearXNG) are wired up, though `services/osint_service.py`
  is where you'd add them.
- **Notifications**: the `notifications` table exists, but nothing writes to it yet, and
  there is no email/webhook dispatcher. This is the most honest gap to call out.
- **Migrations**: `database/migrations/0001_init.sql` is a generated, reviewable DDL
  snapshot. The app itself uses `Base.metadata.create_all()` at startup for dev
  convenience; there's no Alembic version chain for incremental production migrations yet.
- **Credential management UI**: the backend has full encrypted-credential endpoints
  (admin-only); the frontend Settings page doesn't yet expose a form for them — use the API
  directly (see [docs/SECURITY.md](docs/SECURITY.md)).

None of this is faked in the demo — where a feature isn't wired up, the system says so
(`UNKNOWN`, `COULD_NOT_COLLECT`, falls back to manual mode) rather than pretending.

## Quick start (local, no Docker)

```bash
# Backend
cd backend
python3 -m venv ../.venv && source ../.venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # then edit DATABASE_URL to point at your Postgres/Supabase
python seed.py               # optional: 5 demo users, 10 cases, ~20 evidence, 5 policies, 5 reports
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                  # http://localhost:5173, proxies /api to :8000
```

Demo logins after seeding (all fictional, password `ChangeMe123!`): `admin`, `analyst1`,
`reviewer1`, `auditor1`, `viewer1`.

## Quick start (Docker Compose)

```bash
cp .env.example .env   # fill in DATABASE_URL (Supabase or your own Postgres) and JWT_SECRET
docker compose up --build
# nginx on :8080 -> / to the frontend, /api/* to the backend
```

Add `--profile ai` to also start a local Ollama container for the optional AI-assist layer.

## Tests

```bash
python -m pytest             # 30 backend tests (SQLite, per-test isolated DB)
cd frontend && npm run build # type-checks + builds the frontend
```

## Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — components, data flow, the PlatformAdapter pattern
- [API_SPEC.md](docs/API_SPEC.md) — every endpoint, its permission requirement, and payloads
- [DATABASE_SPEC.md](docs/DATABASE_SPEC.md) — schema and relationships
- [SECURITY.md](docs/SECURITY.md) — auth, RBAC, upload validation, SSRF/SQLi/XSS posture, what's *not* covered
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) — Docker Compose, Supabase setup, environment variables
- [REPORT_WORKFLOW.md](docs/REPORT_WORKFLOW.md) — the case → report → submission state machine
- [POLICY_ENGINE.md](docs/POLICY_ENGINE.md) — why keyword ≠ violation, and how triage works
- [EVIDENCE_GUIDE.md](docs/EVIDENCE_GUIDE.md) — evidence types, hashing, chain of custody
- [panduan-pengguna.html](docs/panduan-pengguna.html) — Indonesian-language interactive operator guide (open in a browser); covers every menu, role-based access, and directly addresses whether this system can force a platform takedown (it can't, by design — see that page's "Soal Takedown" section)

## Project layout

```
backend/    FastAPI + SQLAlchemy + Pydantic (models/ schemas/ routers/ services/ utils/)
frontend/   React + TypeScript + Vite + Tailwind
database/   Reference SQL DDL
nginx/      Reverse proxy config for the Docker Compose stack
docs/       This documentation set
tests/      pytest suite (tests/backend) + a manual Playwright smoke script
```
