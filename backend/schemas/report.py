from datetime import datetime

from pydantic import BaseModel

from models.enums import ReadinessLevel, ReportStatus


class ReportCreate(BaseModel):
    case_id: str
    assessment_id: str | None = None


class ReportOut(BaseModel):
    id: str
    report_number: str
    case_id: str
    assessment_id: str | None
    platform_id: str
    body: dict
    report_hash: str
    readiness_score: float
    readiness_level: ReadinessLevel
    missing_items: list[str]
    status: ReportStatus
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportSubmitRequest(BaseModel):
    method: str = "MANUAL"  # MANUAL or API
    external_reference: str | None = None


class ReportSubmissionOut(BaseModel):
    id: str
    report_id: str
    method: str
    submitted_by: str
    submitted_at: datetime
    external_reference: str | None
    status: str

    class Config:
        from_attributes = True
