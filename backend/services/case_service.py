import os

from sqlalchemy.orm import Session

from config import get_settings
from models.case import Case
from models.content import Content
from models.evidence import Evidence
from models.report import Report
from models.review import ReviewQueueItem
from models.violation_assessment import ViolationAssessment
from services import audit_service

settings = get_settings()


def delete_case_cascade(db: Session, case: Case, user_id: str) -> None:
    """Permanently remove a case and everything filed under it.

    Deliberately not the default way to retire a case — status transitions
    to REJECTED/CLOSED preserve the record for the audit trail, which is
    the whole point of a Trust & Safety evidence system. This exists for
    operators who need true removal (e.g. a case opened by mistake or
    containing data that must not persist) and is restricted to admins.
    An audit entry is written before anything is removed, so the fact that
    a case existed and was deleted survives even though its detail rows
    don't.

    Deletion order respects the foreign keys between these tables (each
    level references the ones above it): review queue items -> reports ->
    assessments -> evidence -> content -> the case itself. Objects are
    fetched and passed to db.delete() rather than bulk-deleted so that each
    model's own ORM-level cascade (e.g. Evidence -> its hashes and custody
    events) still runs.
    """
    audit_service.log_action(
        db,
        user_id,
        "CASE_DELETED",
        "case",
        case.case_number,
        {"title": case.title, "platform_id": case.platform_id, "status": case.status.value},
    )

    for item in db.query(ReviewQueueItem).filter(ReviewQueueItem.case_id == case.id).all():
        db.delete(item)
    for report in db.query(Report).filter(Report.case_id == case.id).all():
        db.delete(report)
    for assessment in db.query(ViolationAssessment).filter(ViolationAssessment.case_id == case.id).all():
        db.delete(assessment)
    for evidence in db.query(Evidence).filter(Evidence.case_id == case.id).all():
        if evidence.stored_filename:
            try:
                os.remove(os.path.join(settings.storage_path, evidence.stored_filename))
            except OSError:
                pass
        db.delete(evidence)
    for content in db.query(Content).filter(Content.case_id == case.id).all():
        db.delete(content)

    db.delete(case)
    db.commit()
