"""Violation assessment engine.

This module intentionally does NOT decide, on its own, that an account or
piece of content violates a platform policy. It:

  1. Collects verified evidence and observed context for a case.
  2. Uses policy keywords only to *triage* candidate rules worth a closer
     look (keyword != violation, see policy_service.triage_by_keyword).
  3. Requires a minimum evidentiary bar (evidence + source + policy
     reference + context) before it will even propose a PENDING_REVIEW
     assessment; otherwise it returns INSUFFICIENT_EVIDENCE.
  4. Always marks requires_human_review = True. Confidence is a heuristic
     signal for triage/prioritization, never a final determination, and a
     human reviewer must CONFIRM or mark NOT_CONFIRMED before a report can
     be submitted (see routers/reviews.py + report_service.readiness).
"""

from sqlalchemy.orm import Session

from models.content import Content
from models.enums import AssessmentStatus, EvidenceVerificationStatus, ViolationCategory
from models.evidence import Evidence
from models.review import ReviewQueueItem
from models.violation_assessment import ViolationAssessment
from services import audit_service, policy_service


def _enqueue_for_review(db, case, assessment: ViolationAssessment) -> None:
    """Every assessment this engine produces requires human review before a
    report can be submitted (spec section 39), so it is placed on the
    Review Queue immediately rather than relying on a separate manual step.
    """
    item = ReviewQueueItem(case_id=case.id, assessment_id=assessment.id)
    db.add(item)
    db.commit()


def run_assessment(db: Session, case, user_id: str) -> list[ViolationAssessment]:
    verified_evidence = (
        db.query(Evidence)
        .filter(Evidence.case_id == case.id, Evidence.verification_status == EvidenceVerificationStatus.VERIFIED)
        .all()
    )
    contents = db.query(Content).filter(Content.case_id == case.id).all()
    rules = policy_service.get_rules_for_platform(db, case.platform_id)

    results: list[ViolationAssessment] = []

    if not verified_evidence:
        assessment = ViolationAssessment(
            case_id=case.id,
            category=ViolationCategory.OTHER,
            confidence=0.0,
            evidence_ids=[],
            reason="No verified evidence is available for this case yet.",
            missing_evidence=["At least one VERIFIED evidence item"],
            requires_human_review=True,
            status=AssessmentStatus.INSUFFICIENT_EVIDENCE,
            generated_by="RULE_ENGINE",
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        _enqueue_for_review(db, case, assessment)
        results.append(assessment)
        audit_service.log_action(db, user_id, "AI_ANALYSIS_RUN", "case", case.case_number, {"result": "insufficient_evidence"})
        return results

    corpus_by_rule: dict[str, list[str]] = {}
    combined_text = " \n ".join(
        [e.description or "" for e in verified_evidence] + [c.excerpt or "" for c in contents]
    )

    hits = policy_service.triage_by_keyword(combined_text, rules)

    if not hits:
        assessment = ViolationAssessment(
            case_id=case.id,
            category=ViolationCategory.OTHER,
            confidence=0.1,
            evidence_ids=[e.evidence_number for e in verified_evidence],
            reason=(
                "Verified evidence is present but keyword triage found no candidate policy match. "
                "A human reviewer should still inspect the evidence directly, since this engine "
                "does not interpret media, tone, or conversational context."
            ),
            missing_evidence=["Explicit policy rule match", "Reviewer context notes"],
            requires_human_review=True,
            status=AssessmentStatus.INSUFFICIENT_EVIDENCE,
            generated_by="RULE_ENGINE",
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        _enqueue_for_review(db, case, assessment)
        results.append(assessment)
        audit_service.log_action(db, user_id, "AI_ANALYSIS_RUN", "case", case.case_number, {"result": "no_triage_match"})
        return results

    has_context = any((c.excerpt for c in contents)) or any((e.description for e in verified_evidence))

    for rule, matched_keywords in hits:
        missing = []
        if not has_context:
            missing.append("Context (surrounding conversation/media/timestamp)")
        confidence = min(0.35 + 0.15 * len(matched_keywords) + (0.15 if has_context else 0), 0.85)
        status = AssessmentStatus.PENDING_REVIEW if not missing else AssessmentStatus.INSUFFICIENT_EVIDENCE

        assessment = ViolationAssessment(
            case_id=case.id,
            category=rule.category,
            policy_rule_id=rule.id,
            confidence=round(confidence, 2),
            evidence_ids=[e.evidence_number for e in verified_evidence],
            reason=(
                f"Evidence text/description matched triage keyword(s) {matched_keywords} associated with "
                f"policy rule {rule.rule_code}. This is a triage signal, not a violation determination; "
                "human review is required to confirm context, intent, and target before any report is generated."
            ),
            missing_evidence=missing,
            requires_human_review=True,
            status=status,
            generated_by="RULE_ENGINE",
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        _enqueue_for_review(db, case, assessment)
        results.append(assessment)

    audit_service.log_action(
        db, user_id, "AI_ANALYSIS_RUN", "case", case.case_number,
        {"result": "candidates_found", "count": len(results)},
    )
    return results


def confirm_assessment(db: Session, assessment: ViolationAssessment, reviewer_id: str, confirmed: bool, notes: str | None = None) -> ViolationAssessment:
    assessment.status = AssessmentStatus.CONFIRMED if confirmed else AssessmentStatus.NOT_CONFIRMED
    assessment.reviewed_by = reviewer_id
    from datetime import datetime, timezone
    assessment.reviewed_at = datetime.now(timezone.utc)
    if notes:
        assessment.reason = f"{assessment.reason}\n\nReviewer note: {notes}"
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    audit_service.log_action(db, reviewer_id, "ASSESSMENT_REVIEWED", "assessment", assessment.id, {"confirmed": confirmed})
    return assessment
