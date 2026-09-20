import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.enums import ViolationCategory


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    platform_id: Mapped[str] = mapped_column(String(36), ForeignKey("platforms.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    policy_url: Mapped[str] = mapped_column(String(500), nullable=True)
    effective_date: Mapped[date] = mapped_column(Date, nullable=True)
    last_updated: Mapped[date] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    platform: Mapped["Platform"] = relationship()
    rules: Mapped[list["PolicyRule"]] = relationship(back_populates="policy", cascade="all, delete-orphan")


class PolicyRule(Base):
    __tablename__ = "policy_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    policy_id: Mapped[str] = mapped_column(String(36), ForeignKey("policies.id"), nullable=False)
    rule_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # e.g. POL-001
    category: Mapped[ViolationCategory] = mapped_column(Enum(ViolationCategory, name="violation_category_enum"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")  # LOW/MEDIUM/HIGH/CRITICAL
    keywords: Mapped[str] = mapped_column(Text, nullable=True)  # comma-separated triage keywords, NOT auto-decision

    policy: Mapped["Policy"] = relationship(back_populates="rules")
