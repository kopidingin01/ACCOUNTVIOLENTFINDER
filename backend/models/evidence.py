import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.enums import EvidenceType, EvidenceVerificationStatus


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evidence_number: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)  # EV-000001
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), nullable=False)
    content_id: Mapped[str] = mapped_column(String(36), ForeignKey("contents.id"), nullable=True)
    type: Mapped[EvidenceType] = mapped_column(Enum(EvidenceType, name="evidence_type_enum"), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=True)  # randomized on-disk name
    original_filename: Mapped[str] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=True)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    collected_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    verification_status: Mapped[EvidenceVerificationStatus] = mapped_column(
        Enum(EvidenceVerificationStatus, name="evidence_verification_status_enum"),
        default=EvidenceVerificationStatus.PENDING,
    )
    verification_notes: Mapped[str] = mapped_column(Text, nullable=True)

    case: Mapped["Case"] = relationship()
    content: Mapped["Content"] = relationship()
    collector: Mapped["User"] = relationship()
    hashes: Mapped[list["EvidenceHash"]] = relationship(back_populates="evidence", cascade="all, delete-orphan")
    custody_events: Mapped[list["ChainOfCustodyEvent"]] = relationship(back_populates="evidence", cascade="all, delete-orphan")


class EvidenceHash(Base):
    """Historical record of hash computations for an evidence item.

    The FIRST row for a given evidence_id is the immutable hash of the
    original file. Any subsequent row (e.g. for a working/annotated copy)
    references stage='WORKING' or stage='ANNOTATED' and never overwrites
    the original row.
    """

    __tablename__ = "evidence_hashes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evidence_id: Mapped[str] = mapped_column(String(36), ForeignKey("evidence.id"), nullable=False)
    stage: Mapped[str] = mapped_column(String(20), default="ORIGINAL")  # ORIGINAL, WORKING, ANNOTATED
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    evidence: Mapped["Evidence"] = relationship(back_populates="hashes")


class ChainOfCustodyEvent(Base):
    __tablename__ = "chain_of_custody"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evidence_id: Mapped[str] = mapped_column(String(36), ForeignKey("evidence.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # CREATED, UPLOADED, HASHED, REVIEWED, VERIFIED, REPORT_GENERATED, SUBMITTED
    performed_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    new_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    evidence: Mapped["Evidence"] = relationship(back_populates="custody_events")
    actor: Mapped["User"] = relationship()
