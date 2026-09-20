from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.auth import UserCreate, UserOut, UserUpdate
from security import hash_password, require_permission
from services import audit_service

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db), admin: User = Depends(require_permission("*"))):
    """Admin-only. Lets an admin add teammates (analysts, reviewers,
    auditors, viewers) so a case queue can be worked by more than one
    person, each restricted to their role's permissions."""
    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Username or email already in use")
    db.refresh(user)
    audit_service.log_action(db, admin.id, "USER_CREATED", "user", user.id, {"role": payload.role.value})
    return user


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_permission("*"))):
    return db.query(User).order_by(User.username).all()


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: str, payload: UserUpdate, db: Session = Depends(get_db), admin: User = Depends(require_permission("*"))):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    changes = payload.model_dump(exclude_unset=True, exclude={"password"})
    for field, value in changes.items():
        setattr(user, field, value)
    if payload.password:
        user.password_hash = hash_password(payload.password)
        changes["password"] = "***"

    db.add(user)
    db.commit()
    db.refresh(user)
    loggable = {k: (v.value if hasattr(v, "value") else v) for k, v in changes.items()}
    audit_service.log_action(db, admin.id, "USER_UPDATED", "user", user.id, loggable)
    return user
