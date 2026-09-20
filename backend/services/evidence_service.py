import os
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from config import get_settings
from models.enums import EvidenceType, EvidenceVerificationStatus
from models.evidence import ChainOfCustodyEvent, Evidence, EvidenceHash
from services import audit_service, hash_service
from utils.ids import generate_evidence_number
from utils.validators import (
    ALLOWED_EVIDENCE_MIME_TYPES,
    is_https,
    is_valid_http_url,
    sanitize_filename_extension,
)

settings = get_settings()


def _record_custody(db: Session, evidence: Evidence, action: str, user_id: str, previous_hash=None, new_hash=None, notes=None):
    event = ChainOfCustodyEvent(
        evidence_id=evidence.id,
        action=action,
        performed_by=user_id,
        previous_hash=previous_hash,
        new_hash=new_hash,
        notes=notes,
    )
    db.add(event)
    db.commit()


def create_reference_evidence(
    db: Session,
    case_id: str,
    evidence_type: EvidenceType,
    source_url: str,
    description: str | None,
    user_id: str,
    content_id: str | None = None,
) -> Evidence:
    """Register evidence that is a reference to a public URL rather than an
    uploaded file (e.g. a public post captured by link + timestamp)."""
    if not is_valid_http_url(source_url):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Source URL is not a valid http(s) URL")

    evidence = Evidence(
        evidence_number=generate_evidence_number(db),
        case_id=case_id,
        content_id=content_id,
        type=evidence_type,
        source_url=source_url,
        description=description,
        collected_by=user_id,
        verification_status=EvidenceVerificationStatus.PENDING,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    _record_custody(db, evidence, "CREATED", user_id, notes=f"Reference evidence registered from {source_url}")
    audit_service.log_action(db, user_id, "EVIDENCE_CREATED", "evidence", evidence.evidence_number)
    return evidence


async def upload_evidence_file(
    db: Session,
    case_id: str,
    evidence_type: EvidenceType,
    source_url: str,
    description: str | None,
    file: UploadFile,
    user_id: str,
) -> Evidence:
    if not is_valid_http_url(source_url):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Source URL is not a valid http(s) URL")

    ext = sanitize_filename_extension(file.filename or "")
    if ext is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File extension is not on the evidence allowlist")

    contents = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"File exceeds {settings.max_upload_mb}MB limit")

    declared_mime = file.content_type or "application/octet-stream"
    if declared_mime not in ALLOWED_EVIDENCE_MIME_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"MIME type '{declared_mime}' is not allowed")

    os.makedirs(settings.storage_path, exist_ok=True)
    stored_filename = f"{uuid.uuid4().hex}{ext}"
    stored_path = os.path.join(settings.storage_path, stored_filename)
    # Path is fully server-generated (UUID + allowlisted extension); the
    # original filename is never used to build a filesystem path.
    with open(stored_path, "wb") as f:
        f.write(contents)

    digest = hash_service.sha256_bytes(contents)

    duplicate = db.query(Evidence).filter(Evidence.sha256 == digest).first()

    evidence = Evidence(
        evidence_number=generate_evidence_number(db),
        case_id=case_id,
        type=evidence_type,
        source_url=source_url,
        description=description,
        stored_filename=stored_filename,
        original_filename=file.filename,
        mime_type=declared_mime,
        file_size=len(contents),
        sha256=digest,
        collected_by=user_id,
        verification_status=EvidenceVerificationStatus.DUPLICATE if duplicate else EvidenceVerificationStatus.PENDING,
        verification_notes=f"Duplicate of {duplicate.evidence_number}" if duplicate else None,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    db.add(EvidenceHash(evidence_id=evidence.id, stage="ORIGINAL", sha256=digest))
    db.commit()

    _record_custody(db, evidence, "UPLOADED", user_id, new_hash=digest, notes=f"Original file: {file.filename}")
    _record_custody(db, evidence, "HASHED", user_id, new_hash=digest, notes="SHA-256 computed at upload time")

    audit_service.log_action(db, user_id, "EVIDENCE_UPLOADED", "evidence", evidence.evidence_number, {"sha256": digest})
    return evidence


def verify_evidence(db: Session, evidence: Evidence, user_id: str, notes: str | None) -> Evidence:
    """Re-validates source accessibility characteristics and integrity, then
    marks evidence VERIFIED. Does not re-fetch third-party content (no
    automated re-scraping); validates what is already recorded.
    """
    problems = []

    if not is_valid_http_url(evidence.source_url):
        problems.append("Source URL is not a valid http(s) URL")
    elif not is_https(evidence.source_url):
        problems.append("Source URL is not HTTPS (recommended but not blocking)")

    if evidence.stored_filename:
        stored_path = os.path.join(settings.storage_path, evidence.stored_filename)
        if not os.path.exists(stored_path):
            problems.append("Stored file is missing from evidence storage")
        else:
            recomputed = hash_service.sha256_file(stored_path)
            if recomputed != evidence.sha256:
                problems.append("Recomputed SHA-256 does not match recorded hash (possible corruption/tampering)")

    blocking = [p for p in problems if "recommended but not blocking" not in p]

    if blocking:
        evidence.verification_status = EvidenceVerificationStatus.FAILED
        evidence.verification_notes = "; ".join(problems)
    else:
        evidence.verification_status = EvidenceVerificationStatus.VERIFIED
        evidence.verification_notes = notes or ("; ".join(problems) if problems else "Verified: source and integrity checks passed")

    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    _record_custody(db, evidence, "VERIFIED" if not blocking else "REVIEWED", user_id, new_hash=evidence.sha256, notes=evidence.verification_notes)
    audit_service.log_action(db, user_id, "EVIDENCE_VERIFIED", "evidence", evidence.evidence_number, {"status": evidence.verification_status.value})
    return evidence
