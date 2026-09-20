from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.target import Target
from models.user import User
from schemas.target import TargetCreate, TargetOut
from security import require_permission
from services import audit_service

router = APIRouter(prefix="/api/targets", tags=["targets"])


@router.post("", response_model=TargetOut, status_code=status.HTTP_201_CREATED)
def create_target(payload: TargetCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("target:create"))):
    target = Target(**payload.model_dump(), collected_by=user.id)
    db.add(target)
    db.commit()
    db.refresh(target)
    audit_service.log_action(db, user.id, "TARGET_COLLECTED", "target", target.id, {"profile_url": target.profile_url})
    return target


@router.get("", response_model=list[TargetOut])
def list_targets(platform_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission("target:read"))):
    query = db.query(Target)
    if platform_id:
        query = query.filter(Target.platform_id == platform_id)
    return query.order_by(Target.collected_at.desc()).all()


@router.get("/{target_id}", response_model=TargetOut)
def get_target(target_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("target:read"))):
    target = db.get(Target, target_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Target not found")
    return target
