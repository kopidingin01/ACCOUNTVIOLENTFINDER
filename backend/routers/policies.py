from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.policy import Policy, PolicyRule
from models.user import User
from schemas.policy import PolicyCreate, PolicyOut, PolicyRuleCreate, PolicyRuleOut
from security import require_permission

router = APIRouter(prefix="/api/policies", tags=["policies"])


@router.post("", response_model=PolicyOut, status_code=status.HTTP_201_CREATED)
def create_policy(payload: PolicyCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("*"))):
    policy = Policy(**payload.model_dump())
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.post("/rules", response_model=PolicyRuleOut, status_code=status.HTTP_201_CREATED)
def create_policy_rule(payload: PolicyRuleCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("*"))):
    rule = PolicyRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("", response_model=list[PolicyOut])
def list_policies(platform_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission("assessment:read"))):
    query = db.query(Policy)
    if platform_id:
        query = query.filter(Policy.platform_id == platform_id)
    return query.all()


@router.get("/{policy_id}", response_model=PolicyOut)
def get_policy(policy_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("assessment:read"))):
    policy = db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Policy not found")
    return policy
