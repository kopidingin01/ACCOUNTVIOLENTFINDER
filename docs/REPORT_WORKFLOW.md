# Report Workflow

## Case status machine

```
NEW -> COLLECTING_EVIDENCE -> EVIDENCE_VALIDATED -> UNDER_REVIEW -> VIOLATION_CONFIRMED
    -> REPORT_READY -> SUBMITTED -> ACKNOWLEDGED -> ACTION_TAKEN / REJECTED -> CLOSED
```

`Case.status` is a plain field an operator/analyst sets via `PATCH /api/cases/{id}` — the
backend doesn't currently auto-advance it as evidence/assessments/reports change underneath
it (a case can be `NEW` while its report is `SUBMITTED`; the two are related but not
mechanically linked). This is worth knowing before assuming the dashboard's "Open Cases"
count is a perfect real-time reflection of report state — cross-check the Reports page too.

## Evidence verification status

`PENDING -> VERIFIED` (source + integrity checks pass) or `PENDING -> FAILED` (hash mismatch,
missing file, invalid source URL) or `PENDING -> DUPLICATE` (identical SHA-256 already on
file, set automatically at upload time, before any human verifies anything).

## Violation assessment status

`PENDING_REVIEW` (candidate match, needs a human) / `INSUFFICIENT_EVIDENCE` (either no
verified evidence at all, or a policy-keyword hit with no surrounding context) /
`CONFIRMED` / `NOT_CONFIRMED` (only reachable via a reviewer's decision — see below).

**No status in this table is ever set to `CONFIRMED` by the engine itself.** The engine
(`services/violation_service.run_assessment`) always sets `requires_human_review = True` and
the initial status to `PENDING_REVIEW` or `INSUFFICIENT_EVIDENCE`. `CONFIRMED`/`NOT_CONFIRMED`
only happen inside `services/violation_service.confirm_assessment`, which is only called from
`POST /api/reviews/{id}/decide` — i.e., a human reviewer's explicit action.

## Report readiness score

Computed in `services/report_service.compute_readiness` from a checklist, weighted exactly
as the spec asks:

| Component | Weight | Satisfied when |
|---|---|---|
| Evidence completeness | 25% | At least one evidence item is `VERIFIED`. |
| Source verification | 20% | Same signal as above (verified evidence implies its source passed validation). |
| Policy mapping | 20% | The linked assessment has a `policy_rule_id`. |
| Context | 15% | At least one `Content.excerpt` or `Evidence.description` is present. |
| Timestamp | 10% | At least one observed timestamp exists (content `observed_at`, or evidence exists at all — evidence always has `collected_at`). |
| Human verification | 10% | The linked assessment is `CONFIRMED` **and** has a `reviewed_by`. |

Levels: `READY` (score ≥ 90 **and** human review satisfied **and** no live duplicate) /
`NEEDS_REVIEW` (score ≥ 50) / `INSUFFICIENT` (below 50). `Report.missing_items` lists the
specific unmet checklist items in the section-40-style format the spec asks for
("Missing Evidence: - Source URL - Screenshot - Policy reference").

**Submission is gated on `READY`, not just "not INSUFFICIENT"** — this was a real bug found
and fixed during this session's live testing: a report with no linked assessment could
otherwise reach `SUBMITTED` without ever being reviewed, since the original check only
blocked the `INSUFFICIENT` level. See `routers/reports.py` and the git history for the fix.

## Duplicate detection

`services/duplicate_service.compute_report_hash` hashes
`target_id | platform_id | policy_rule_id | sorted(evidence source URLs)`. Creating a second
report for the same case with the same evidence set produces the same hash, and
`POST /api/reports` returns **409** pointing at the existing report instead of creating a
duplicate — verified live and in `test_duplicate_report_detected_on_second_generation`. The
UI surfaces this as "DUPLICATE REPORT DETECTED — existing report REP-... — use the existing
report" rather than silently succeeding or silently failing.

## Submission

`services/platform_service.get_adapter()` picks `ManualPlatformAdapter` unless the platform
has `has_official_api=True` **and** an enabled credential is configured — see
ARCHITECTURE.md. Manual submission means: the operator exports the report (PDF/JSON/CSV) and
files it themselves via the platform's own reporting page; the app tracks that this happened
(`ReportSubmission` row, `status: AWAITING_HUMAN_SUBMISSION`) but never automates the actual
filing, per the spec's hard "no automation of platform submission" constraint.

## The Account Violation Finder flow specifically

```
account_url
  -> _find_platform_by_url()      match by registered Platform.domain
  -> osint_service.collect_public_page()   single HTTPS GET, SSRF-guarded, no auth bypass
  -> _get_or_create_target()      register/reuse a Target from public profile fields only
  -> [optional] create a Case
  -> policy_service.triage_by_keyword() over the collected page's title/description/OG tags
  -> one TEMUAN finding per matched policy rule, status PERLU_VERIFIKASI, confidence capped
     at 0.7, explicitly labeled as a triage signal in its `reasoning` text
```

If collection fails for any reason (invalid URL, SSRF-blocked, DNS failure, HTTP error,
login-walled/rate-limited response), the result is `collection_status: COULD_NOT_COLLECT`
and the summary text is the exact Indonesian phrase the spec asks for:
*"Tidak dapat mengumpulkan konten publik dari URL ini (...). Tidak ditemukan bukti
pelanggaran yang memadai dari sumber publik yang diperiksa."* If collection succeeds but no
keyword triage hits: *"Tidak ditemukan bukti pelanggaran yang memadai dari sumber publik
yang diperiksa."* Findings are never invented to fill in a result.
