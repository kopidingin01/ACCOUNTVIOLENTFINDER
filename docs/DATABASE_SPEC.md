# Database Specification

Target: PostgreSQL 13+ (this deployment uses Supabase's managed Postgres, but nothing here
is Supabase-specific). Source of truth is `backend/models/*.py`; `database/migrations/0001_init.sql`
is a generated, reviewable DDL snapshot of exactly what those models produce.

## Entity relationship (high level)

```
users ---< cases >--- platforms ---< policies ---< policy_rules
  |          |
  |          >--- targets
  |          |
  |          >--- contents
  |          |
  |          >--- evidence ---< evidence_hashes
  |                  |
  |                  >--- chain_of_custody
  |
  |--- violation_assessments (case_id, policy_rule_id)
  |          |
  |          >--- review_queue ---< review_decisions
  |
  |--- reports (case_id, assessment_id, platform_id)
  |          |
  |          >--- report_submissions
  |
  |--- audit_logs
  |--- notifications
  |
platforms --- api_credentials (encrypted at rest)
```

## Tables

| Table | Purpose | Key fields |
|---|---|---|
| `users` | Operators/reviewers/auditors. | `role` (enum: ADMIN/ANALYST/REVIEWER/AUDITOR/VIEWER), Argon2 `password_hash`. |
| `platforms` | A social platform's reporting configuration. | `domain` (used to auto-match Account Finder URLs), `has_official_api`, `reporting_url`, `allowed_categories` (JSON), `required_fields` (JSON). |
| `api_credentials` | Encrypted credential for a platform's official API. | `encrypted_value` (Fernet, key derived from `JWT_SECRET`), `enabled`. Never exposed via any API response. |
| `policies` / `policy_rules` | A platform's policy document and its individual rules. | `rule_code` (e.g. `POL-001`), `category` (enum), `keywords` (comma-separated, triage-only). |
| `targets` | A reviewed account, described only by its public profile. | `profile_url`, `source_url`, `collected_at`, `collected_by`. No private-account fields exist in this table by design. |
| `cases` | The unit of work. | `case_number` (`CASE-YYYY-NNNNNN`), `status` (11-value enum matching the spec's workflow), `priority`. |
| `contents` | A specific observed post/comment/media item tied to a case + target. | `content_url`, `excerpt`, `observed_at`. |
| `evidence` | A piece of evidence (file or URL reference). | `evidence_number` (`EV-NNNNNN`), `sha256`, `stored_filename` (server-generated UUID, never the original name), `verification_status`. |
| `evidence_hashes` | Historical hash record per evidence item, staged (`ORIGINAL`/`WORKING`/`ANNOTATED`). | The `ORIGINAL` row is written once at upload and never overwritten. |
| `chain_of_custody` | Append-only event log per evidence item. | `action`, `performed_by`, `previous_hash`, `new_hash`. |
| `violation_assessments` | One triage result (category + confidence + reasoning) per candidate policy match. | `status` (PENDING_REVIEW/CONFIRMED/NOT_CONFIRMED/INSUFFICIENT_EVIDENCE), `requires_human_review` (always `true` from this engine). |
| `review_queue` / `review_decisions` | The human-review gate. | Every assessment is auto-enqueued; a `review_decisions` row records who decided what and why. |
| `reports` | A generated report. | `report_hash` (for duplicate detection), `readiness_score`/`readiness_level`, `body` (JSON — the full structured report content). |
| `report_submissions` | One row per submission attempt (manual or API). | `method`, `platform_response` (JSON), `external_reference`. |
| `audit_logs` | Append-only action log. | No update/delete endpoint exists anywhere in the API — immutability is enforced by *absence of a mutation path*, not a database trigger (see SECURITY.md's honesty note on this). |
| `notifications` | Schema exists for in-app/email/webhook notifications. | **Nothing currently writes to this table** — see README's scope disclosure. |

## Why UUID-as-`VARCHAR(36)` primary keys instead of native `UUID`

SQLAlchemy's `String(36)` with a Python-side `uuid4()` default was chosen so the exact same
model code runs unmodified against SQLite in tests (`tests/backend/conftest.py`) and Postgres
in production, without a dialect-specific column type. If you're hand-writing a migration
against a fresh Postgres from `0001_init.sql`, note the DDL correctly reflects this as
`VARCHAR(36)`, not `UUID` — that's not a bug, it's this same tradeoff surfacing in the DDL.

## Indexes

Unique: `users.username`, `users.email`, `cases.case_number`, `evidence.evidence_number`,
`reports.report_number`, `policy_rules.rule_code`. Non-unique: `evidence.sha256` (duplicate
lookup), `reports.report_hash` (duplicate lookup), `audit_logs.timestamp` (recency queries).
