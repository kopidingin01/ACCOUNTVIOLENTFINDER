import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.enums import ReviewAction, ReviewQueueStatus


class ReviewQueueItem(Base):
    __tablename__ = "review_queue"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), nullable=False)
    assessment_id: Mapped[str] = mapped_column(String(36), ForeignKey("violation_assessments.id"), nullable=True)
    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("reports.id"), nullable=True)
    status: Mapped[ReviewQueueStatus] = mapped_column(
        Enum(ReviewQueueStatus, name="review_queue_status_enum"), default=ReviewQueueStatus.PENDING
    )
    assigned_to: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    case: Mapped["Case"] = relationship()
    assessment: Mapped["ViolationAssessment"] = relationship()
    report: Mapped["Report"] = relationship()
    decisions: Mapped[list["ReviewDecision"]] = relationship(back_populates="queue_item", cascade="all, delete-orphan")


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    queue_item_id: Mapped[str] = mapped_column(String(36), ForeignKey("review_queue.id"), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    action: Mapped[ReviewAction] = mapped_column(Enum(ReviewAction, name="review_action_enum"), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    queue_item: Mapped["ReviewQueueItem"] = relationship(back_populates="decisions")
    reviewer: Mapped["User"] = relationship()
