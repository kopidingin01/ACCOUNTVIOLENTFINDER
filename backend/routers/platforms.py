from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.platform import Platform
from models.user import User
from schemas.platform import PlatformCreate, PlatformOut
from security import require_permission

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
