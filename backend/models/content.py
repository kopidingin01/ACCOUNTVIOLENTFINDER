import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Content(Base):
    """A single piece of publicly observed content (post, comment, media, etc.)
    associated with a target account, referenced by evidence records.
    """

    __tablename__ = "contents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), ForeignKey("targets.id"), nullable=False)
    content_url: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=True)  # post, comment, media, bio, link
    excerpt: Mapped[str] = mapped_column(Text, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    case: Mapped["Case"] = relationship()
    target: Mapped["Target"] = relationship()
