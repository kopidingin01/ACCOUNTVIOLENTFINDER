from datetime import datetime

from pydantic import BaseModel

from models.enums import CaseStatus, Priority


class CaseCreate(BaseModel):
    title: str
    platform_id: str
    target_id: str | None = None
    report_category: str | None = None
    priority: Priority = Priority.MEDIUM
    description: str | None = None


class CaseUpdate(BaseModel):
    title: str | None = None
    status: CaseStatus | None = None
    priority: Priority | None = None
    description: str | None = None


class CaseOut(BaseModel):
    id: str
    case_number: str
    title: str
    platform_id: str
    target_id: str | None
    report_category: str | None
    priority: Priority
    description: str | None
    status: CaseStatus
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
