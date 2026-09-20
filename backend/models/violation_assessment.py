import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.enums import AssessmentStatus, ViolationCategory


class ViolationAssessment(Base):
    __tablename__ = "violation_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), nullable=False)
    category: Mapped[ViolationCategory] = mapped_column(Enum(ViolationCategory, name="assessment_category_enum"), nullable=False)
    policy_rule_id: Mapped[str] = mapped_column(String(36), ForeignKey("policy_rules.id"), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    reason: Mapped[str] = mapped_column(Text, nullable=True)
    missing_evidence: Mapped[list] = mapped_column(JSON, default=list)
    requires_human_review: Mapped[bool] = mapped_column(default=True)
    status: Mapped[AssessmentStatus] = mapped_column(
        Enum(AssessmentStatus, name="assessment_status_enum"), default=AssessmentStatus.PENDING_REVIEW
    )
    generated_by: Mapped[str] = mapped_column(String(20), default="RULE_ENGINE")  # RULE_ENGINE or AI_ASSISTED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    reviewed_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    case: Mapped["Case"] = relationship()
    policy_rule: Mapped["PolicyRule"] = relationship()
