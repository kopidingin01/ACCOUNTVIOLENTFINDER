import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.enums import CaseStatus, Priority


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_number: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)  # CASE-2026-000001
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    platform_id: Mapped[str] = mapped_column(String(36), ForeignKey("platforms.id"), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), ForeignKey("targets.id"), nullable=True)
    report_category: Mapped[str] = mapped_column(String(50), nullable=True)
    priority: Mapped[Priority] = mapped_column(Enum(Priority, name="priority_enum"), default=Priority.MEDIUM)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[CaseStatus] = mapped_column(Enum(CaseStatus, name="case_status_enum"), default=CaseStatus.NEW)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    platform: Mapped["Platform"] = relationship()
    target: Mapped["Target"] = relationship(back_populates="cases")
    creator: Mapped["User"] = relationship()
