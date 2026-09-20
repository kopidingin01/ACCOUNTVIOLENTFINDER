# Security

This document says what's actually implemented and verified, and is explicit about what
isn't — a security doc that oversells its own coverage is worse than none.

## Authentication & session

- JWT access tokens (30 min default) + refresh tokens (7 days default), HS256, signed with
  `JWT_SECRET`. **Rotate `JWT_SECRET` in production** — it's also used to derive the Fernet
  key that encrypts platform API credentials at rest (`services/crypto_service.py`), so
  losing/rotating it also invalidates stored credentials (re-add them after rotation).
- Passwords hashed with Argon2 (`passlib[argon2]`), never stored or logged in plaintext.
  Verified: `test_login_wrong_password_rejected`, `test_login_inactive_user_rejected`.
- No cookie-based session exists, so there is no CSRF attack surface in the traditional
  sense — every request needs an explicit `Authorization: Bearer` header that a browser
  never attaches automatically cross-site. This is a design choice, not an oversight; if you
  add cookie-based auth later, add CSRF tokens then.

## Authorization (RBAC)

Five roles (`ADMIN, ANALYST, REVIEWER, AUDITOR, VIEWER`) map to an explicit permission set in
`security.ROLE_PERMISSIONS`. Every mutating and most read endpoints go through
`Depends(require_permission("..."))` — there is no endpoint that skips this check and relies
on the frontend to hide a button. Verified for every role pairing that matters in
`tests/backend/test_auth_rbac.py` (viewer blocked from case creation, analyst blocked from
policy management, reviewer-only review-queue decisions, auditor-only audit log, admin
full access).

## File upload security (`services/evidence_service.py`)

- Extension allowlist (`utils/validators.ALLOWED_EVIDENCE_EXTENSIONS`) AND declared
  `Content-Type` allowlist (`ALLOWED_EVIDENCE_MIME_TYPES`) — both must pass.
- Max size enforced server-side (`MAX_UPLOAD_MB`, default 25MB).
- **Stored filename is always a server-generated UUID** with the validated extension. The
  original filename is recorded as metadata only and is never used to build a filesystem
  path — verified directly with a `../../../../etc/passwd.png`-style payload in
  `test_evidence_upload_rejects_path_traversal_in_filename`.
- SHA-256 computed at upload time; a second upload with identical bytes is flagged
  `DUPLICATE` rather than silently accepted, verified in
  `test_evidence_upload_computes_correct_sha256_and_flags_duplicates`.
- No antivirus/malware scanning hook is wired up (the spec calls for one). If you need this,
  it's a single insertion point in `evidence_service.upload_evidence_file` after the size
  check and before the file is written.

## SQL injection

All queries go through SQLAlchemy's query builder with parameter binding — there is no
string-formatted SQL anywhere in the codebase. Verified with a classic
`x' OR '1'='1` payload as a filter value in `test_sql_injection_style_query_param_is_safely_parameterized`,
which returns an empty, well-formed result rather than an error or a data dump.

## XSS

The backend is a pure JSON API — it never renders HTML from user input. The frontend is
React, which escapes all interpolated text by default; `grep -r dangerouslySetInnerHTML
frontend/src` returns nothing. A `<script>` payload in a case description round-trips as
inert text end-to-end, verified in `test_xss_payload_in_case_description_is_stored_and_returned_literally`.

## SSRF (OSINT collector, `services/osint_service.py`)

The Account Finder fetches an operator-supplied URL over HTTPS. Before doing so it:
1. Validates the URL is a well-formed `http(s)://` URL.
2. Rejects hostnames that are literally private/loopback/link-local IPs.
3. Resolves the hostname and rejects it if it resolves to a private/loopback/link-local/
   reserved/multicast address (DNS-rebinding-aware — the literal-IP check alone isn't
   enough).

This was exercised live during development: an unresolvable demo domain in this sandbox's
DNS setup resolved to a non-public address, correctly triggering the SSRF guard — and an
early version of this code let that guard's exception escape as an unhandled 500 instead of
the same graceful `COULD_NOT_COLLECT` outcome used for network failures. Fixed; see the git
history for `services/osint_service.py`. All collection failures — SSRF-blocked, invalid
URL, DNS failure, HTTP error, 401/403/429 — degrade to the same honest outcome rather than
crashing or fabricating a result.

## Rate limiting

`slowapi` enforces a global default (`RATE_LIMIT_PER_MINUTE`, default 60/minute) keyed by
client IP, applied via `app.state.limiter`. This has not been load-tested; it's a basic
throttle, not a DDoS mitigation layer (that belongs at the infrastructure/CDN level, outside
this app's scope).

## Secure headers

Set on every response by `main.py`'s `security_headers` middleware: `X-Content-Type-Options:
nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, a restrictive
`Permissions-Policy`. `nginx/nginx.conf` sets the same headers again at the edge for
defense in depth.

## Encrypted credentials at rest

`api_credentials.encrypted_value` uses Fernet (symmetric, authenticated encryption) with a
key derived from `JWT_SECRET`. `ApiCredentialOut` (the response schema) has no field for the
value at all — it's not redacted, it's structurally absent, so there's no risk of a future
code change accidentally leaking it through that schema. Verified in
`test_platform_credentials.py`.

## What is honestly NOT covered

- **Audit log immutability** is enforced by *absence of a mutation endpoint*, not a
  database-level trigger or row-level security policy. A user with direct database access
  (e.g. the Supabase service-role key, or a compromised `DATABASE_URL`) could still alter
  `audit_logs` rows. If you need tamper-evidence against that threat model, add a Postgres
  trigger that rejects `UPDATE`/`DELETE` on that table, or ship logs to an append-only
  external sink.
- **No malware/antivirus scanning** on uploaded evidence (see above).
- **No automated dependency/SCA scanning** is configured in this repo (no Dependabot config,
  no `pip-audit`/`npm audit` CI gate). `npm audit` at time of writing reports a handful of
  moderate/high transitive dev-dependency advisories in the frontend toolchain — none in
  runtime dependencies actually shipped to the browser.
- **No formal penetration test** has been run. The checks above are the specific,
  reproducible things this session verified — not a certification.
