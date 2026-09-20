import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Target(Base):
    """A social-media account under review, described only by information the
    account has made publicly visible. No private data (DMs, private posts,
    non-public follower lists, etc.) is collected or stored here.
    """

    __tablename__ = "targets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    platform_id: Mapped[str] = mapped_column(String(36), ForeignKey("platforms.id"), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=True)
    profile_url: Mapped[str] = mapped_column(String(500), nullable=False)
    account_id: Mapped[str] = mapped_column(String(255), nullable=True)
    profile_description: Mapped[str] = mapped_column(Text, nullable=True)
    account_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    public_followers: Mapped[int] = mapped_column(Integer, nullable=True)
    public_following: Mapped[int] = mapped_column(Integer, nullable=True)
    public_posts: Mapped[int] = mapped_column(Integer, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30), default="UNKNOWN")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    collected_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)

    platform: Mapped["Platform"] = relationship()
    cases: Mapped[list["Case"]] = relationship(back_populates="target")
