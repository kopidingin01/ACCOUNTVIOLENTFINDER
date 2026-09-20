# Architecture

## System diagram

```
Internet
   |
   v
+--------+        +-----------+        +---------------------+
| Nginx  | -----> | Frontend  |        |                      |
| :8080  |        | (static,  |        |                      |
|        |        |  React)   |        |                      |
|        | -/api->+-----------+        |                      |
|        | ------------------------->  |  FastAPI backend     |
+--------+                             |  (:8000)             |
                                       |                      |
                                       +----------+-----------+
                                                  |
                                +-----------------+------------------+
                                |                                    |
                                v                                    v
                     PostgreSQL (Supabase)               Ollama (optional, --profile ai)
                     via SQLAlchemy                       services/ai_service.py
```

The backend has no code path that is Supabase-specific — it talks to `DATABASE_URL` over
plain `psycopg2`/SQLAlchemy. Supabase is simply the Postgres provider this deployment is
configured to use; swap the connection string and it runs against any Postgres 13+.

## Backend layers

```
routers/     HTTP layer only: auth, validation via Pydantic schemas, permission checks
             via `Depends(require_permission(...))`, then delegate to services/.
services/    All business logic. No FastAPI imports here — services take a `Session` and
             plain arguments so they're unit-testable and reusable from scripts (seed.py).
models/      SQLAlchemy ORM models — the schema's source of truth (see DATABASE_SPEC.md).
schemas/     Pydantic request/response contracts. Never expose a model field the schema
             doesn't declare (e.g. ApiCredentialOut has no value/encrypted_value field).
utils/       Pure helpers: ID generation (CASE-YYYY-NNNNNN etc.), URL/filename validators.
```

### Why the request flow always goes router → service → model, never router → model

Keeping business rules out of routers means the same rule (e.g. "duplicate-report
detection", "readiness scoring") is enforced identically whether it's called from the API,
a future CLI, or a test. It also makes the false-positive-protection guarantees in
POLICY_ENGINE.md testable in isolation from HTTP.

## The core workflow, as code

```
INPUT TARGET                  -> routers/targets.py, services/account_finder_service.py
COLLECT PUBLIC EVIDENCE       -> services/osint_service.py (public GET, SSRF-guarded)
EVIDENCE VALIDATION           -> services/evidence_service.py (source + integrity checks)
CONTENT ANALYSIS              -> services/policy_service.py (keyword triage, not verdict)
POLICY MATCHING               -> models/policy.py (PolicyRule per platform)
VIOLATION ASSESSMENT          -> services/violation_service.py (always requires_human_review)
HUMAN REVIEW                  -> models/review.py + routers/reviews.py (mandatory gate)
GENERATE REPORT               -> services/report_service.py (readiness score, body)
OFFICIAL PLATFORM CHANNEL     -> services/platform_service.py (PlatformAdapter)
REPORT STATUS TRACKING        -> models/report.py (ReportSubmission rows)
CASE CLOSED / FOLLOW-UP       -> routers/cases.py (status transitions)
```

## The PlatformAdapter abstraction

```python
class PlatformAdapter(ABC):
    def validate_payload(self, report: Report) -> list[str]: ...
    def submit_report(self, report: Report) -> dict: ...
    def get_status(self, external_reference: str) -> dict: ...
```

Two implementations:

- **`ManualPlatformAdapter`** (the default, and the only one used unless an admin has
  explicitly configured a credential): validates required fields and returns
  `AWAITING_HUMAN_SUBMISSION` with the platform's own reporting URL. It never touches the
  network. This is what "submit" means for every platform out of the box.
- **`OfficialApiPlatformAdapter`**: only selected when `Platform.has_official_api=True` AND
  an enabled `ApiCredential` row exists for it. Does exactly one HTTPS POST with the
  decrypted credential as a bearer token. No retries, no rate-limit workaround, no CAPTCHA
  handling — if the platform's real API needs something more specific than a bearer-token
  POST, this adapter needs a platform-specific subclass, which is intentionally left as a
  narrow, reviewable extension point rather than guessed at generically.

`services/platform_service.get_adapter(db, platform)` is the only place that decides which
adapter to use, so adding a real platform integration means: register the platform, add its
credential via `POST /api/platforms/{id}/credentials`, and (if its API needs anything beyond
"POST the report body with a bearer token") subclass `OfficialApiPlatformAdapter`.

## Frontend

Plain React Router SPA, no server components. `src/hooks/useAuth.tsx` holds the JWT in
`localStorage` and exposes `hasRole(...)` for role-gated UI (mirroring, not replacing, the
backend's own permission checks — the backend is the actual authority). `src/api/client.ts`
is a thin fetch wrapper; file exports go through `downloadFile()` (fetch + Blob) since a
plain `<a href>` can't carry the `Authorization` header FastAPI's OAuth2 bearer scheme needs.

## Deliberate non-goals

- No server-side rendering — this is an internal operator tool, not a public-facing site.
- No multi-tenancy — one deployment serves one organization's case queue.
- No automated periodic jobs (retention cleanup, notification dispatch) are scheduled from
  inside the app; see README.md's "what's actually implemented" section and DEPLOYMENT.md
  for what a production operator would still need to add (e.g. a cron/Celery beat job).
