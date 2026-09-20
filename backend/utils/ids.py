from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.case import Case
from models.evidence import Evidence
from models.report import Report


def _next_sequence(db: Session, model, column, prefix_filter: str) -> int:
    count = db.query(func.count(column)).filter(column.like(f"{prefix_filter}%")).scalar() or 0
    return count + 1


def generate_case_number(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    prefix = f"CASE-{year}-"
    seq = _next_sequence(db, Case, Case.case_number, prefix)
    return f"{prefix}{seq:06d}"


def generate_evidence_number(db: Session) -> str:
    prefix = "EV-"
    seq = _next_sequence(db, Evidence, Evidence.evidence_number, prefix)
    return f"{prefix}{seq:06d}"


def generate_report_number(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    prefix = f"REP-{year}-"
    seq = _next_sequence(db, Report, Report.report_number, prefix)
    return f"{prefix}{seq:06d}"
