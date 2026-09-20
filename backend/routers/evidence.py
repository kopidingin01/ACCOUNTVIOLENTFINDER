import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
from models.enums import EvidenceType
from models.evidence import ChainOfCustodyEvent, Evidence
from models.user import User
from schemas.evidence import ChainOfCustodyOut, EvidenceMetaCreate, EvidenceOut, EvidenceVerifyRequest
from security import require_permission
from services import evidence_service

router = APIRouter(prefix="/api/evidence", tags=["evidence"])
settings = get_settings()


@router.post("", response_model=EvidenceOut, status_code=status.HTTP_201_CREATED)
async def create_evidence(
    case_id: str = Form(...),
    type: EvidenceType = Form(...),
    source_url: str = Form(...),
    description: str | None = Form(None),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("evidence:create")),
):
    if file is not None and file.filename:
        return await evidence_service.upload_evidence_file(db, case_id, type, source_url, description, file, user.id)
    return evidence_service.create_reference_evidence(db, case_id, type, source_url, description, user.id)


@router.get("", response_model=list[EvidenceOut])
def list_evidence(case_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission("evidence:read"))):
    query = db.query(Evidence)
    if case_id:
        query = query.filter(Evidence.case_id == case_id)
    return query.order_by(Evidence.evidence_number).all()


@router.get("/{evidence_id}", response_model=EvidenceOut)
def get_evidence(evidence_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("evidence:read"))):
    evidence = db.get(Evidence, evidence_id)
    if not evidence:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidence not found")
    return evidence


@router.get("/{evidence_id}/file")
def get_evidence_file(evidence_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("evidence:read"))):
    evidence = db.get(Evidence, evidence_id)
    if not evidence or not evidence.stored_filename:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No stored file for this evidence item")
    path = os.path.join(settings.storage_path, evidence.stored_filename)
    if not os.path.exists(path):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stored file missing from disk")
    return FileResponse(path, media_type=evidence.mime_type, filename=evidence.original_filename or evidence.stored_filename)


@router.post("/{evidence_id}/verify", response_model=EvidenceOut)
def verify_evidence(evidence_id: str, payload: EvidenceVerifyRequest, db: Session = Depends(get_db), user: User = Depends(require_permission("evidence:verify"))):
    evidence = db.get(Evidence, evidence_id)
    if not evidence:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidence not found")
    return evidence_service.verify_evidence(db, evidence, user.id, payload.notes)


@router.get("/{evidence_id}/custody", response_model=list[ChainOfCustodyOut])
def get_custody_chain(evidence_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("evidence:read"))):
    return (
        db.query(ChainOfCustodyEvent)
        .filter(ChainOfCustodyEvent.evidence_id == evidence_id)
        .order_by(ChainOfCustodyEvent.timestamp)
        .all()
    )
