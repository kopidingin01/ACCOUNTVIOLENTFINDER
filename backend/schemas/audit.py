from datetime import datetime

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: str
    user_id: str | None
    action: str
    resource_type: str | None
    resource_id: str | None
    metadata_json: dict | None
    timestamp: datetime

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_cases: int
    open_cases: int
    under_review: int
    validated_cases: int
    reports_ready: int
    reports_submitted: int
    platform_responses: int
    action_taken: int
    rejected_reports: int
    by_platform: dict[str, int]
    by_violation_category: dict[str, int]
    by_status: dict[str, int]
    by_evidence_validity: dict[str, int]
    timeline: list[dict]
