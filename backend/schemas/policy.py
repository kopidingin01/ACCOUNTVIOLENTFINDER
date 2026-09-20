from datetime import date

from pydantic import BaseModel

from models.enums import ViolationCategory


class PolicyRuleOut(BaseModel):
    id: str
    policy_id: str
    rule_code: str
    category: ViolationCategory
    description: str
    severity: str
    keywords: str | None

    class Config:
        from_attributes = True


class PolicyOut(BaseModel):
    id: str
    platform_id: str
    name: str
    policy_url: str | None
    effective_date: date | None
    last_updated: date | None
    rules: list[PolicyRuleOut] = []

    class Config:
        from_attributes = True


class PolicyRuleCreate(BaseModel):
    policy_id: str
    rule_code: str
    category: ViolationCategory
    description: str
    severity: str = "MEDIUM"
    keywords: str | None = None


class PolicyCreate(BaseModel):
    platform_id: str
    name: str
    policy_url: str | None = None
    effective_date: date | None = None
    last_updated: date | None = None
