"""Duplicate-report prevention (spec section 18/35).

Principle: ONE VALID REPORT is worth more than many duplicate submissions.
Before a new report is created for a case, we hash the tuple that defines
"the same underlying case" (target + platform + policy rule + the sorted
set of evidence content URLs) and look for an existing, still-relevant
report with that same hash.
"""

from sqlalchemy.orm import Session

from models.enums import ReportStatus
from models.evidence import Evidence
from models.report import Report
from services import hash_service


def compute_report_hash(db: Session, case, assessment) -> str:
    evidence = db.query(Evidence).filter(Evidence.case_id == case.id).order_by(Evidence.evidence_number).all()
    urls = sorted({e.source_url for e in evidence})
    policy_rule_id = assessment.policy_rule_id if assessment else "NONE"
    key = f"{case.target_id}|{case.platform_id}|{policy_rule_id}|{'|'.join(urls)}"
    return hash_service.sha256_text(key)


def find_existing_report(db: Session, report_hash: str) -> Report | None:
    return (
        db.query(Report)
        .filter(Report.report_hash == report_hash)
        .filter(Report.status != ReportStatus.REJECTED)
        .order_by(Report.created_at.desc())
        .first()
    )
