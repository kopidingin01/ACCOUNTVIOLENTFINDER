# Policy Engine — why keyword ≠ violation

## The core rule this whole module exists to enforce

> A keyword match is a reason to look closer. It is never, by itself, a reason to say a
> violation occurred.

This isn't a slogan bolted on afterward — it's structurally enforced in
`services/violation_service.run_assessment`:

1. If a case has **zero verified evidence**, the engine returns `INSUFFICIENT_EVIDENCE`
   immediately. It never even attempts keyword matching without evidence to match against.
2. `policy_service.triage_by_keyword()` only returns *candidates* — a `(PolicyRule,
   matched_keywords)` pair — never a verdict. Its own docstring says so, and its only caller
   treats the result as an input to further checks, not an output.
3. Even with a keyword hit, the engine checks for **context**: is there an `Evidence.description`
   or `Content.excerpt` at all? If not, the resulting assessment is `INSUFFICIENT_EVIDENCE`
   with `missing_evidence: ["Context (surrounding conversation/media/timestamp)"]` — a bare
   keyword hit with zero surrounding text cannot become `PENDING_REVIEW`.
4. Even a `PENDING_REVIEW` assessment (evidence + keyword + context all present) is capped at
   confidence 0.85 and its `reason` field explicitly states: *"This is a triage signal, not a
   violation determination; human review is required to confirm context, intent, and target
   before any report is generated."*
5. `requires_human_review` is `True` on every single assessment this engine produces — there
   is no code path that sets it to `False`.
6. The only way an assessment reaches `CONFIRMED` is a human reviewer calling
   `POST /api/reviews/{id}/decide` with `action: APPROVE`. See REPORT_WORKFLOW.md.

This is why the sample from the pivoted "Account Violation Finder" spec — `"bunuh"` (Indonesian
for "kill") appearing in a post does not automatically mean a threat — holds structurally:
the engine can flag the policy rule it matched and say *why* it's worth a look, but its
output status is capped below `CONFIRMED` until a person reads the actual post.

## Confidence is a triage/prioritization signal, not a probability

`confidence = min(0.35 + 0.15 * len(matched_keywords) + (0.15 if has_context else 0), 0.85)`
in `run_assessment`, and a similar cap in `account_finder_service.analyze_account`. This
formula exists to let a reviewer sort a queue by "how much triage signal is here," not to
imply "this is X% likely to be a real violation" — the codebase and UI both say so
explicitly (`Confidence: {n}% (triage signal, not a verdict)` in `CaseDetail.tsx`).

## Where AI assist fits (`services/ai_service.py`)

If a local Ollama instance is configured and reachable, `ai_service.analyze()` can produce a
`reasoning_summary`/`detected_category`/`policy_match` alongside the rule engine's output.
Its system prompt explicitly instructs the model: *"You must not invent facts. If
information is not present in the provided evidence/context, respond with 'UNKNOWN' for that
field... Your output is a triage aid for a human reviewer, not a final decision."* Every
response this function returns — whether from a real model call, an unreachable Ollama, or a
parse failure — carries `recommended_human_review: true`. It was not exercised against a
real running Ollama instance in this session (none was available in the build sandbox); the
"Ollama unreachable" fallback path was the one actually exercised, and it correctly returns
`UNKNOWN`/`0.0` confidence rather than guessing.

## False-positive protection, concretely (spec section 39)

The minimum bar before *any* assessment can even reach `PENDING_REVIEW` is:
**evidence + source (the evidence's `source_url`) + policy (a matched rule) + context
(a description/excerpt)**. Remove any one of those four and the result is
`INSUFFICIENT_EVIDENCE`, never a guess. This exact requirement is tested in
`tests/backend/test_policy_and_assessment.py`:
`test_assessment_is_insufficient_without_verified_evidence`,
`test_keyword_alone_does_not_confirm_a_violation`, and
`test_no_keyword_match_reports_insufficient_not_a_false_violation`.

## Extending the policy set

Policies and rules are plain data — `POST /api/policies` and `POST /api/policies/rules`
(admin-only). Keywords are a comma-separated string on `PolicyRule.keywords`; there's no
NLP/stemming applied, it's a case-insensitive substring match
(`policy_service.triage_by_keyword`). This is intentionally simple: a fancier matcher would
raise, not lower, the risk of the "keyword ≈ violation" conflation this whole module exists
to prevent. If you need multi-language stemming or fuzzy matching, treat it as a bigger triage
signal for the *same* gated pipeline, not a shortcut around the human-review requirement.
