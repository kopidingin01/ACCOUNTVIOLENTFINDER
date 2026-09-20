from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.case import Case
from models.enums import CaseStatus, Priority
from models.user import User
from schemas.case import CaseCreate, CaseOut, CaseUpdate
from security import require_permission
from services import audit_service
from utils.ids import generate_case_number

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
def create_case(payload: CaseCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("case:create"))):
    case = Case(
        case_number=generate_case_number(db),
        title=payload.title,
        platform_id=payload.platform_id,
        target_id=payload.target_id,
        report_category=payload.report_category,
        priority=payload.priority,
        description=payload.description,
        status=CaseStatus.NEW,
        created_by=user.id,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    audit_service.log_action(db, user.id, "CASE_CREATED", "case", case.case_number)
    return case


@router.get("", response_model=list[CaseOut])
def list_cases(
    status_filter: CaseStatus | None = None,
    platform_id: str | None = None,
    priority: Priority | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("case:read")),
):
    query = db.query(Case)
    if status_filter:
        query = query.filter(Case.status == status_filter)
    if platform_id:
        query = query.filter(Case.platform_id == platform_id)
    if priority:
        query = query.filter(Case.priority == priority)
    return query.order_by(Case.created_at.desc()).all()


@router.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("case:read"))):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    return case


@router.patch("/{case_id}", response_model=CaseOut)
def update_case(case_id: str, payload: CaseUpdate, db: Session = Depends(get_db), user: User = Depends(require_permission("case:update"))):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(case, field, value)
    db.add(case)
    db.commit()
    db.refresh(case)
    loggable_changes = {k: (v.value if hasattr(v, "value") else v) for k, v in changes.items()}
    audit_service.log_action(db, user.id, "CASE_UPDATED", "case", case.case_number, loggable_changes)
    return case
