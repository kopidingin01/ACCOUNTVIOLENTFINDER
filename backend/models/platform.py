import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Platform(Base):
    __tablename__ = "platforms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    reporting_url: Mapped[str] = mapped_column(String(500), nullable=True)
    api_endpoint: Mapped[str] = mapped_column(String(500), nullable=True)
    has_official_api: Mapped[bool] = mapped_column(Boolean, default=False)
    allowed_categories: Mapped[list] = mapped_column(JSON, default=list)
    required_fields: Mapped[list] = mapped_column(JSON, default=list)
    attachment_rules: Mapped[dict] = mapped_column(JSON, default=dict)
    rate_limit_notes: Mapped[str] = mapped_column(Text, nullable=True)
    terms_url: Mapped[str] = mapped_column(String(500), nullable=True)
    privacy_requirements: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    credentials: Mapped[list["ApiCredential"]] = relationship(back_populates="platform")


class ApiCredential(Base):
    """Encrypted-at-rest credential config for an official platform API/search provider.

    The actual secret value is stored via a symmetric-encryption helper (see
    services/crypto_service.py) and is never returned by any API response or
    written to logs.
    """

    __tablename__ = "api_credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    platform_id: Mapped[str] = mapped_column(String(36), ForeignKey("platforms.id"), nullable=False)
    credential_type: Mapped[str] = mapped_column(String(50), nullable=False)  # api_key, oauth2, webhook_secret
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    platform: Mapped["Platform"] = relationship(back_populates="credentials")
