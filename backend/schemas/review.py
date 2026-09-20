from datetime import datetime

from pydantic import BaseModel

from models.enums import ReviewAction, ReviewQueueStatus


class ReviewQueueOut(BaseModel):
    id: str
    case_id: str
    assessment_id: str | None
    report_id: str | None
    status: ReviewQueueStatus
    assigned_to: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewDecisionRequest(BaseModel):
    action: ReviewAction
    notes: str | None = None
