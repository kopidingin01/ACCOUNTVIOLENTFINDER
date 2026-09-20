from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.case import Case
from models.violation_assessment import ViolationAssessment
from models.user import User
from schemas.assessment import AssessmentCreate, AssessmentOut
from security import require_permission
from services import violation_service

router = APIRouter(prefix="/api/assessments", tags=["assessments"])


@router.post("", response_model=list[AssessmentOut], status_code=status.HTTP_201_CREATED)
def create_assessment(payload: AssessmentCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("assessment:create"))):
    case = db.get(Case, payload.case_id)
    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    return violation_service.run_assessment(db, case, user.id)


@router.get("/{assessment_id}", response_model=AssessmentOut)
def get_assessment(assessment_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("assessment:read"))):
    assessment = db.get(ViolationAssessment, assessment_id)
    if not assessment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assessment not found")
    return assessment


@router.get("", response_model=list[AssessmentOut])
def list_assessments(case_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission("assessment:read"))):
    query = db.query(ViolationAssessment)
    if case_id:
        query = query.filter(ViolationAssessment.case_id == case_id)
    return query.order_by(ViolationAssessment.created_at.desc()).all()
