from datetime import datetime

from pydantic import BaseModel

from models.enums import AssessmentStatus, ViolationCategory


class AssessmentCreate(BaseModel):
    case_id: str


class AssessmentOut(BaseModel):
    id: str
    case_id: str
    category: ViolationCategory
    policy_rule_id: str | None
    confidence: float
    evidence_ids: list[str]
    reason: str | None
    missing_evidence: list[str]
    requires_human_review: bool
    status: AssessmentStatus
    generated_by: str
    created_at: datetime
    reviewed_by: str | None
    reviewed_at: datetime | None

    class Config:
        from_attributes = True
