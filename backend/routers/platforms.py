from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.platform import ApiCredential, Platform
from models.user import User
from schemas.platform import ApiCredentialCreate, ApiCredentialOut, PlatformCreate, PlatformOut
from security import require_permission
from services import audit_service
from services.crypto_service import encrypt_secret

router = APIRouter(prefix="/api/platforms", tags=["platforms"])


@router.post("", response_model=PlatformOut, status_code=status.HTTP_201_CREATED)
def create_platform(payload: PlatformCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("*"))):
    platform = Platform(**payload.model_dump())
    db.add(platform)
    db.commit()
    db.refresh(platform)
    return platform


@router.get("", response_model=list[PlatformOut])
def list_platforms(db: Session = Depends(get_db), user: User = Depends(require_permission("case:read"))):
    return db.query(Platform).order_by(Platform.name).all()


@router.get("/{platform_id}", response_model=PlatformOut)
def get_platform(platform_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("case:read"))):
    platform = db.get(Platform, platform_id)
    if not platform:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Platform not found")
    return platform


@router.post("/{platform_id}/credentials", response_model=ApiCredentialOut, status_code=status.HTTP_201_CREATED)
def create_platform_credential(
    platform_id: str,
    payload: ApiCredentialCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("*")),
):
    """Admin-only. The plaintext value is accepted once, encrypted at rest
    immediately, and never stored or returned in plaintext again — this
    response and every future GET omit it entirely (see ApiCredentialOut)."""
    platform = db.get(Platform, platform_id)
    if not platform:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Platform not found")

    credential = ApiCredential(
        platform_id=platform_id,
        credential_type=payload.credential_type,
        encrypted_value=encrypt_secret(payload.value),
        enabled=payload.enabled,
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    audit_service.log_action(db, user.id, "PLATFORM_CREDENTIAL_CREATED", "platform", platform_id, {"credential_type": payload.credential_type})
    return credential


@router.get("/{platform_id}/credentials", response_model=list[ApiCredentialOut])
def list_platform_credentials(platform_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("*"))):
    return db.query(ApiCredential).filter(ApiCredential.platform_id == platform_id).all()


@router.delete("/{platform_id}/credentials/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_platform_credential(platform_id: str, credential_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("*"))):
    credential = db.get(ApiCredential, credential_id)
    if not credential or credential.platform_id != platform_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Credential not found")
    db.delete(credential)
    db.commit()
    audit_service.log_action(db, user.id, "PLATFORM_CREDENTIAL_DELETED", "platform", platform_id, {"credential_id": credential_id})
