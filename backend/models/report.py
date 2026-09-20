import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.enums import ReadinessLevel, ReportStatus


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_number: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)  # REP-2026-000001
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), nullable=False)
    assessment_id: Mapped[str] = mapped_column(String(36), ForeignKey("violation_assessments.id"), nullable=True)
    platform_id: Mapped[str] = mapped_column(String(36), ForeignKey("platforms.id"), nullable=False)
    body: Mapped[dict] = mapped_column(JSON, nullable=False)  # structured report content (see report_service)
    report_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)  # for duplicate detection
    readiness_score: Mapped[float] = mapped_column(Float, default=0.0)
    readiness_level: Mapped[ReadinessLevel] = mapped_column(
        Enum(ReadinessLevel, name="readiness_level_enum"), default=ReadinessLevel.INSUFFICIENT
    )
    missing_items: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus, name="report_status_enum"), default=ReportStatus.DRAFT)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    case: Mapped["Case"] = relationship()
    assessment: Mapped["ViolationAssessment"] = relationship()
    platform: Mapped["Platform"] = relationship()
    submissions: Mapped[list["ReportSubmission"]] = relationship(back_populates="report", cascade="all, delete-orphan")


class ReportSubmission(Base):
    """Record of an attempt to send a report through an official channel
    (API where available, or logged manual submission via the platform's
    own reporting page).
    """

    __tablename__ = "report_submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("reports.id"), nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False)  # API or MANUAL
    submitted_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    external_reference: Mapped[str] = mapped_column(String(255), nullable=True)  # platform's own ticket/report id
    platform_response: Mapped[dict] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="SUBMITTED")

    report: Mapped["Report"] = relationship(back_populates="submissions")
