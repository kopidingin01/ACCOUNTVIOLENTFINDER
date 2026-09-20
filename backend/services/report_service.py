from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.case import Case
from models.enums import AssessmentStatus, EvidenceVerificationStatus, ReadinessLevel, ReportStatus
from models.evidence import Evidence
from models.content import Content
from models.platform import Platform
from models.policy import Policy, PolicyRule
from models.report import Report
from models.target import Target
from models.violation_assessment import ViolationAssessment
from services import audit_service, duplicate_service, policy_service
from utils.ids import generate_report_number

DISCLAIMER = (
    "This report contains factual observations and supporting evidence submitted for "
    "platform review. Final enforcement decisions remain with the platform."
)

QUALITY_CHECKLIST_LABELS = {
    "target": "Target identified",
    "content": "Content identified",
    "evidence": "Evidence attached",
    "source_verified": "Source verified",
    "timestamp": "Timestamp available",
    "policy": "Policy identified",
    "context": "Context provided",
    "integrity": "Evidence integrity verified",
    "human_review": "Human review completed",
    "duplicate_check": "Duplicate check passed",
}

# Only these items carry weight toward the readiness score (spec section 13);
# the rest (target/content/integrity/duplicate_check) are pass/fail gates
# shown on the checklist but don't move the percentage on their own.
READINESS_WEIGHTS = {
    "evidence": 25.0,
    "source_verified": 20.0,
    "policy": 20.0,
    "context": 15.0,
    "timestamp": 10.0,
    "human_review": 10.0,
}


def _quality_checklist(case: Case, assessment: ViolationAssessment | None, evidence: list[Evidence], contents: list[Content]) -> dict[str, bool]:
    verified = [e for e in evidence if e.verification_status == EvidenceVerificationStatus.VERIFIED]
    has_context = any(c.excerpt for c in contents) or any(e.description for e in evidence)
    has_timestamp = any(c.observed_at for c in contents) or bool(evidence)
    return {
        "target": bool(case.target_id),
        "content": bool(contents),
        "evidence": bool(evidence),
        "source_verified": bool(verified),
        "timestamp": has_timestamp,
        "policy": bool(assessment and assessment.policy_rule_id),
        "context": has_context,
        "integrity": bool(verified) and all(e.sha256 or not e.stored_filename for e in verified),
        "human_review": bool(assessment and assessment.status == AssessmentStatus.CONFIRMED and assessment.reviewed_by),
        "duplicate_check": True,  # set False by caller if a live duplicate exists
    }


def compute_readiness(checklist: dict[str, bool]) -> tuple[float, ReadinessLevel, list[str]]:
    score = sum(weight for key, weight in READINESS_WEIGHTS.items() if checklist.get(key))
    missing = [QUALITY_CHECKLIST_LABELS[k] for k, v in checklist.items() if not v]

    if score >= 90 and checklist.get("human_review") and checklist.get("duplicate_check"):
        level = ReadinessLevel.READY
    elif score >= 50:
        level = ReadinessLevel.NEEDS_REVIEW
    else:
        level = ReadinessLevel.INSUFFICIENT
    return round(score, 1), level, missing


def preview_readiness(db: Session, case: Case) -> dict:
    """Live report-quality checklist for a case, computable at any time
    (before a Report row is created) so an operator can see exactly what
    to fix next — without triggering duplicate-hash checks or persisting
    anything. Backs GET /api/cases/{id}/readiness.
    """
    assessment = (
        db.query(ViolationAssessment)
        .filter(ViolationAssessment.case_id == case.id)
        .order_by(ViolationAssessment.created_at.desc())
        .first()
    )
    evidence = db.query(Evidence).filter(Evidence.case_id == case.id).all()
    contents = db.query(Content).filter(Content.case_id == case.id).all()

    checklist = _quality_checklist(case, assessment, evidence, contents)
    score, level, missing = compute_readiness(checklist)

    items = [
        {
            "key": key,
            "label": QUALITY_CHECKLIST_LABELS[key],
            "weight": READINESS_WEIGHTS.get(key, 0.0),
            "met": met,
        }
        for key, met in checklist.items()
    ]

    return {
        "score": score,
        "level": level.value,
        "missing_items": missing,
        "items": items,
        "assessment_status": assessment.status.value if assessment else None,
    }


def _policy_citation(db: Session, assessment: ViolationAssessment | None) -> dict:
    """Full, quotable citation for the report — a reviewer on the platform
    side should be able to jump straight from this to the exact clause in
    their own guidelines without guessing which rule is meant."""
    if not assessment or not assessment.policy_rule_id:
        return {
            "policy_name": None,
            "policy_url": None,
            "rule_code": None,
            "rule_description": None,
            "severity": None,
            "citation": "No specific policy rule has been matched for this case yet.",
        }

    rule = db.get(PolicyRule, assessment.policy_rule_id)
    policy = db.get(Policy, rule.policy_id) if rule else None

    citation = "No specific policy rule has been matched for this case yet."
    if rule and policy:
        citation = f"{policy.name} — {rule.rule_code}: {rule.description}"

    return {
        "policy_name": policy.name if policy else None,
        "policy_url": policy.policy_url if policy else None,
        "rule_code": rule.rule_code if rule else None,
        "rule_description": rule.description if rule else None,
        "severity": rule.severity if rule else None,
        "citation": citation,
    }


def build_report_body(db: Session, case: Case, target: Target, platform: Platform, assessment: ViolationAssessment | None, evidence: list[Evidence], contents: list[Content], reviewer_id: str | None) -> dict:
    policy_citation = _policy_citation(db, assessment)
    target_line = f"@{target.username}" if target else "the identified account"

    observation = (
        f"On review of the case referenced above, the attached evidence documents content associated with "
        f"{target_line} on {platform.name}. The evidence and its collection details are set out below for "
        f"the platform's own verification and assessment against the cited policy."
    )

    return {
        "case_number": case.case_number,
        "platform": platform.name,
        "target": {
            "username": target.username if target else None,
            "profile_url": target.profile_url if target else None,
            "account_id": target.account_id if target else None,
        },
        "case_summary": case.description,
        "content_urls": sorted({c.content_url for c in contents}) or sorted({e.source_url for e in evidence}),
        "date_time_observed": [c.observed_at.isoformat() for c in contents if c.observed_at],
        "violation_category": assessment.category.value if assessment else None,
        "relevant_policy": {
            "rule_id": assessment.policy_rule_id if assessment else None,
            "reason": assessment.reason if assessment else None,
            **policy_citation,
        },
        "description": observation,
        "evidence": [
            {
                "evidence_id": e.evidence_number,
                "type": e.type.value,
                "source_url": e.source_url,
                "sha256": e.sha256,
                "verification_status": e.verification_status.value,
            }
            for e in evidence
        ],
        "why_may_violate": assessment.reason if assessment else "Not yet assessed.",
        "context": [c.excerpt for c in contents if c.excerpt],
        "request_for_review": (
            "We request that the platform review the attached evidence against the cited policy and take "
            "whatever action, if any, its own guidelines and moderation process determine to be warranted."
        ),
        "reviewer": reviewer_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": DISCLAIMER,
    }


def generate_report(db: Session, case: Case, assessment: ViolationAssessment | None, user_id: str, allow_duplicate: bool = False) -> Report:
    target = db.get(Target, case.target_id) if case.target_id else None
    platform = db.get(Platform, case.platform_id)
    evidence = db.query(Evidence).filter(Evidence.case_id == case.id).order_by(Evidence.evidence_number).all()
    contents = db.query(Content).filter(Content.case_id == case.id).all()

    report_hash = duplicate_service.compute_report_hash(db, case, assessment)
    existing = duplicate_service.find_existing_report(db, report_hash)
    if existing and not allow_duplicate:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "error": "DUPLICATE_REPORT_DETECTED",
                "existing_report_id": existing.report_number,
                "submission_date": existing.created_at.isoformat(),
                "current_status": existing.status.value,
            },
        )

    checklist = _quality_checklist(case, assessment, evidence, contents)
    score, level, missing = compute_readiness(checklist)

    body = build_report_body(db, case, target, platform, assessment, evidence, contents, user_id)

    report = Report(
        report_number=generate_report_number(db),
        case_id=case.id,
        assessment_id=assessment.id if assessment else None,
        platform_id=case.platform_id,
        body=body,
        report_hash=report_hash,
        readiness_score=score,
        readiness_level=level,
        missing_items=missing,
        status=ReportStatus.READY if level == ReadinessLevel.READY else ReportStatus.DRAFT,
        created_by=user_id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    audit_service.log_action(db, user_id, "REPORT_CREATED", "report", report.report_number, {"readiness": level.value, "score": score})
    return report
