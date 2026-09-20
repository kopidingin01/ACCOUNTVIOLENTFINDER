from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from database import get_db
from models.case import Case
from models.enums import ReportStatus
from models.platform import Platform
from models.report import Report, ReportSubmission
from models.violation_assessment import ViolationAssessment
from models.user import User
from schemas.report import ReportCreate, ReportOut, ReportSubmissionOut, ReportSubmitRequest
from security import require_permission
from services import audit_service, export_service, platform_service, report_service

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_report(payload: ReportCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("report:create"))):
    case = db.get(Case, payload.case_id)
    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    assessment = db.get(ViolationAssessment, payload.assessment_id) if payload.assessment_id else None
    return report_service.generate_report(db, case, assessment, user.id)


@router.get("", response_model=list[ReportOut])
def list_reports(case_id: str | None = None, status_filter: ReportStatus | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission("report:read"))):
    query = db.query(Report)
    if case_id:
        query = query.filter(Report.case_id == case_id)
    if status_filter:
        query = query.filter(Report.status == status_filter)
    return query.order_by(Report.created_at.desc()).all()


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("report:read"))):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    return report


@router.get("/{report_id}/status")
def get_report_status(report_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("report:read"))):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    latest = (
        db.query(ReportSubmission)
        .filter(ReportSubmission.report_id == report.id)
        .order_by(ReportSubmission.submitted_at.desc())
        .first()
    )
    return {
        "report_id": report.report_number,
        "status": report.status.value,
        "readiness_level": report.readiness_level.value,
        "readiness_score": report.readiness_score,
        "missing_items": report.missing_items,
        "latest_submission": {
            "method": latest.method,
            "submitted_at": latest.submitted_at.isoformat(),
            "status": latest.status,
            "external_reference": latest.external_reference,
        }
        if latest
        else None,
    }


@router.post("/{report_id}/submit", response_model=ReportSubmissionOut)
def submit_report(report_id: str, payload: ReportSubmitRequest, db: Session = Depends(get_db), user: User = Depends(require_permission("report:update"))):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")

    # READY is the only level whose checklist already verifies human review
    # was completed (see report_service.compute_readiness). Blocking on
    # anything less than READY — not just INSUFFICIENT — closes a gap where
    # a report with no linked assessment could otherwise skip the human
    # review gate required before a report reaches SUBMITTED (spec section 19).
    if report.readiness_level.value != "READY":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            {
                "error": "REPORT_NOT_READY",
                "readiness_level": report.readiness_level.value,
                "missing": report.missing_items,
            },
        )

    platform = db.get(Platform, report.platform_id)
    adapter = platform_service.get_adapter(db, platform)

    if payload.method == "API":
        result = adapter.submit_report(report)
    else:
        result = platform_service.ManualPlatformAdapter(platform).submit_report(report)

    submission = ReportSubmission(
        report_id=report.id,
        method=payload.method,
        submitted_by=user.id,
        external_reference=payload.external_reference,
        platform_response=result,
        status=result.get("status", "SUBMITTED"),
    )
    db.add(submission)

    report.status = ReportStatus.SUBMITTED
    db.add(report)
    db.commit()
    db.refresh(submission)

    audit_service.log_action(db, user.id, "REPORT_SUBMITTED", "report", report.report_number, {"method": payload.method})
    return submission


@router.get("/{report_id}/export/{fmt}")
def export_report(report_id: str, fmt: str, db: Session = Depends(get_db), user: User = Depends(require_permission("report:read"))):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")

    if fmt == "pdf":
        content = export_service.to_pdf(report)
        media_type = "application/pdf"
    elif fmt == "json":
        content = export_service.to_json(report)
        media_type = "application/json"
    elif fmt == "csv":
        content = export_service.to_csv(report)
        media_type = "text/csv"
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unsupported export format")

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{report.report_number}.{fmt}"'},
    )
