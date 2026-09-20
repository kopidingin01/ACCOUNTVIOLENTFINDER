# API Specification

Base path for every endpoint below is `/api`. Auth is a JWT bearer token
(`Authorization: Bearer <token>`) obtained from `POST /api/auth/login`. Permission names in
the "Permission" column map to `security.ROLE_PERMISSIONS` — `*` means ADMIN-only.

This list is generated from the actual router files (`grep` over `backend/routers/*.py`),
not hand-maintained from memory, so it should stay accurate as long as it's re-checked
against the routers when they change.

## Auth (`routers/auth.py`)

| Method | Path | Permission | Notes |
|---|---|---|---|
| POST | `/auth/login` | none | Body: `{username, password}`. Returns access + refresh JWTs. |
| GET | `/auth/me` | authenticated | Returns the current user. |

## Cases (`routers/cases.py`)

| Method | Path | Permission | Notes |
|---|---|---|---|
| POST | `/cases` | `case:create` | Auto-generates `CASE-YYYY-NNNNNN`. |
| GET | `/cases` | `case:read` | Filters: `status_filter`, `platform_id`, `priority`. |
| GET | `/cases/{case_id}` | `case:read` | |
| PATCH | `/cases/{case_id}` | `case:update` | Partial update (title/status/priority/description). |

## Targets (`routers/targets.py`)

| Method | Path | Permission | Notes |
|---|---|---|---|
| POST | `/targets` | `target:create` | Public-profile fields only — see EVIDENCE_GUIDE.md. |
| GET | `/targets` | `target:read` | Filter: `platform_id`. |
| GET | `/targets/{target_id}` | `target:read` | |

## Evidence (`routers/evidence.py`)

| Method | Path | Permission | Notes |
|---|---|---|---|
| POST | `/evidence` | `evidence:create` | `multipart/form-data`: `case_id, type, source_url, description, file?`. File upload triggers SHA-256 + duplicate check; omitting `file` registers a URL-reference evidence item. |
| GET | `/evidence` | `evidence:read` | Filter: `case_id`. |
| GET | `/evidence/{evidence_id}` | `evidence:read` | |
| GET | `/evidence/{evidence_id}/file` | `evidence:read` | Streams the stored original file. |
| POST | `/evidence/{evidence_id}/verify` | `evidence:verify` | Recomputes SHA-256, checks source URL validity, appends chain-of-custody events. |
| GET | `/evidence/{evidence_id}/custody` | `evidence:read` | Full chain-of-custody history. |

## Policies (`routers/policies.py`)

| Method | Path | Permission | Notes |
|---|---|---|---|
| POST | `/policies` | `*` (admin) | Create a policy document reference for a platform. |
| POST | `/policies/rules` | `*` (admin) | Add a `PolicyRule` (category, severity, triage keywords). |
| GET | `/policies` | `assessment:read` | Filter: `platform_id`. Includes nested `rules`. |
| GET | `/policies/{policy_id}` | `assessment:read` | |

## Assessments (`routers/assessments.py`)

| Method | Path | Permission | Notes |
|---|---|---|---|
| POST | `/assessments` | `assessment:create` | Runs the triage engine for a case; returns a list (one per candidate policy match, or one INSUFFICIENT_EVIDENCE result). Always enqueues each result to the Review Queue. |
| GET | `/assessments/{assessment_id}` | `assessment:read` | |
| GET | `/assessments` | `assessment:read` | Filter: `case_id`. |

## Reports (`routers/reports.py`)

| Method | Path | Permission | Notes |
|---|---|---|---|
| POST | `/reports` | `report:create` | Body: `{case_id, assessment_id?}`. Returns **409** with `{error: "DUPLICATE_REPORT_DETECTED", existing_report_id, submission_date, current_status}` if an equivalent report already exists. |
| GET | `/reports` | `report:read` | Filters: `case_id`, `status_filter`. |
| GET | `/reports/{report_id}` | `report:read` | |
| GET | `/reports/{report_id}/status` | `report:read` | Includes the latest submission attempt, if any. |
| POST | `/reports/{report_id}/submit` | `report:update` | Body: `{method: "MANUAL"\|"API", external_reference?}`. **400** `REPORT_NOT_READY` unless `readiness_level == READY` (which itself requires a CONFIRMED, reviewer-approved assessment). |
| GET | `/reports/{report_id}/export/{fmt}` | `report:read` | `fmt` is `pdf`, `json`, or `csv`. |

## Review Queue (`routers/reviews.py`)

| Method | Path | Permission | Notes |
|---|---|---|---|
| GET | `/reviews` | `review:read` | Filter: `status_filter`. |
| POST | `/reviews/{queue_item_id}/decide` | `review:approve` | Body: `{action: APPROVE\|REQUEST_MORE_EVIDENCE\|REJECT\|RETURN_TO_OPERATOR, notes?}`. APPROVE also marks the linked assessment CONFIRMED (anything else marks it NOT_CONFIRMED). |

## Platforms (`routers/platforms.py`)

| Method | Path | Permission | Notes |
|---|---|---|---|
| POST | `/platforms` | `*` (admin) | Register a platform (name, domain, reporting URL, allowed categories, etc.). |
| GET | `/platforms` | `case:read` | |
| GET | `/platforms/{platform_id}` | `case:read` | |
| POST | `/platforms/{platform_id}/credentials` | `*` (admin) | Body: `{credential_type, value, enabled}`. Encrypts `value` at rest; the response never contains it. |
| GET | `/platforms/{platform_id}/credentials` | `*` (admin) | Metadata only (id, type, enabled) — never the value. |
| DELETE | `/platforms/{platform_id}/credentials/{credential_id}` | `*` (admin) | |

## Audit (`routers/audit.py`)

| Method | Path | Permission | Notes |
|---|---|---|---|
| GET | `/audit` | `audit:read` | Filters: `resource_type`, `action`, `limit` (max 1000). Read-only — there is deliberately no PUT/DELETE. |

## Dashboard (`routers/dashboard.py`)

| Method | Path | Permission | Notes |
|---|---|---|---|
| GET | `/dashboard/stats` | `case:read` | Aggregate counts + chart data (by platform, violation category, status, evidence validity, 30-day timeline). |

## OSINT / Account Violation Finder (`routers/osint.py`)

| Method | Path | Permission | Notes |
|---|---|---|---|
| POST | `/osint/account-finder` | `osint:run` | Body: `{account_url, create_case}`. See REPORT_WORKFLOW.md for the full behavior; never fabricates findings, reports `COULD_NOT_COLLECT` on any collection failure. |

## Errors

Standard FastAPI/Pydantic validation errors (`422`) for malformed input. Domain errors use
`HTTPException` with a structured `detail` dict where it matters for the caller to branch on
(e.g. `DUPLICATE_REPORT_DETECTED`, `REPORT_NOT_READY`) — see the Reports section above.
