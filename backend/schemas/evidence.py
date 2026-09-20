from datetime import datetime

from pydantic import BaseModel

from models.enums import EvidenceType, EvidenceVerificationStatus


class EvidenceMetaCreate(BaseModel):
    """Metadata for a URL/text-based evidence item that has no uploaded file
    (e.g. PUBLIC_URL, PUBLIC_POST captured by reference)."""

    case_id: str
    content_id: str | None = None
    type: EvidenceType
    source_url: str
    description: str | None = None


class EvidenceOut(BaseModel):
    id: str
    evidence_number: str
    case_id: str
    content_id: str | None
    type: EvidenceType
    source_url: str
    description: str | None
    original_filename: str | None
    mime_type: str | None
    file_size: int | None
    sha256: str | None
    collected_at: datetime
    collected_by: str
    verification_status: EvidenceVerificationStatus
    verification_notes: str | None

    class Config:
        from_attributes = True


class EvidenceVerifyRequest(BaseModel):
    notes: str | None = None


class ChainOfCustodyOut(BaseModel):
    id: str
    evidence_id: str
    action: str
    performed_by: str
    timestamp: datetime
    previous_hash: str | None
    new_hash: str | None
    notes: str | None

    class Config:
        from_attributes = True
