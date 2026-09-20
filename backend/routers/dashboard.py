from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.case import Case
from models.enums import CaseStatus, EvidenceVerificationStatus
from models.evidence import Evidence
from models.platform import Platform
from models.report import Report, ReportSubmission
from models.user import User
from models.violation_assessment import ViolationAssessment
from schemas.audit import DashboardStats
from security import require_permission

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

_OPEN_STATUSES = {CaseStatus.NEW, CaseStatus.COLLECTING_EVIDENCE}
_VALIDATED_STATUSES = {CaseStatus.EVIDENCE_VALIDATED, CaseStatus.VIOLATION_CONFIRMED}


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db), user: User = Depends(require_permission("case:read"))):
    cases = db.query(Case).all()
    reports = db.query(Report).all()
    submissions = db.query(ReportSubmission).all()
    evidence = db.query(Evidence).all()

    by_platform_counts = Counter()
    for c in cases:
        platform = db.get(Platform, c.platform_id)
        by_platform_counts[platform.name if platform else "Unknown"] += 1

    by_category = Counter(a.category.value for a in db.query(ViolationAssessment).all())
    by_status = Counter(c.status.value for c in cases)
    by_validity = Counter(e.verification_status.value for e in evidence)

    since = datetime.now(timezone.utc) - timedelta(days=30)
    timeline_counter: Counter = Counter()
    for c in cases:
        created = c.created_at
        if created and created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created and created >= since:
            timeline_counter[created.date().isoformat()] += 1
    timeline = [{"date": d, "count": n} for d, n in sorted(timeline_counter.items())]

    return DashboardStats(
        total_cases=len(cases),
        open_cases=sum(1 for c in cases if c.status in _OPEN_STATUSES),
        under_review=sum(1 for c in cases if c.status == CaseStatus.UNDER_REVIEW),
        validated_cases=sum(1 for c in cases if c.status in _VALIDATED_STATUSES),
        reports_ready=sum(1 for r in reports if r.status.value == "READY"),
        reports_submitted=sum(1 for r in reports if r.status.value in ("SUBMITTED", "ACKNOWLEDGED", "ACTIONED")),
        platform_responses=sum(1 for s in submissions if s.platform_response),
        action_taken=sum(1 for r in reports if r.status.value == "ACTIONED"),
        rejected_reports=sum(1 for r in reports if r.status.value == "REJECTED"),
        by_platform=dict(by_platform_counts),
        by_violation_category=dict(by_category),
        by_status=dict(by_status),
        by_evidence_validity=dict(by_validity),
        timeline=timeline,
    )
