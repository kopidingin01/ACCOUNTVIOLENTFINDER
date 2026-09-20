from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.case import Case
from models.evidence import Evidence
from models.report import Report


def _next_sequence(db: Session, column, prefix_filter: str) -> int:
    """Returns MAX(existing numeric suffix) + 1 for rows matching the given
    prefix. Using a row COUNT here would collide whenever the existing
    numbers have gaps (e.g. demo/seed data, or a deleted row) — this reads
    the actual highest sequence number instead.
    """
    existing = db.query(column).filter(column.like(f"{prefix_filter}%")).all()
    max_seq = 0
    for (value,) in existing:
        suffix = value[len(prefix_filter):]
        if suffix.isdigit():
            max_seq = max(max_seq, int(suffix))
    return max_seq + 1


def generate_case_number(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    prefix = f"CASE-{year}-"
    seq = _next_sequence(db, Case.case_number, prefix)
    return f"{prefix}{seq:06d}"


def generate_evidence_number(db: Session) -> str:
    prefix = "EV-"
    seq = _next_sequence(db, Evidence.evidence_number, prefix)
    return f"{prefix}{seq:06d}"


def generate_report_number(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    prefix = f"REP-{year}-"
    seq = _next_sequence(db, Report.report_number, prefix)
    return f"{prefix}{seq:06d}"
