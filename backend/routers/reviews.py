from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.enums import ReviewAction, ReviewQueueStatus
from models.review import ReviewDecision, ReviewQueueItem
from models.violation_assessment import ViolationAssessment
from models.user import User
from schemas.review import ReviewDecisionRequest, ReviewQueueOut
from security import require_permission
from services import audit_service, violation_service

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

_ACTION_TO_QUEUE_STATUS = {
    ReviewAction.APPROVE: ReviewQueueStatus.APPROVED,
    ReviewAction.REQUEST_MORE_EVIDENCE: ReviewQueueStatus.NEEDS_MORE_EVIDENCE,
    ReviewAction.REJECT: ReviewQueueStatus.REJECTED,
    ReviewAction.RETURN_TO_OPERATOR: ReviewQueueStatus.RETURNED,
}


@router.get("", response_model=list[ReviewQueueOut])
def list_review_queue(status_filter: ReviewQueueStatus | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission("review:read"))):
    query = db.query(ReviewQueueItem)
    if status_filter:
        query = query.filter(ReviewQueueItem.status == status_filter)
    return query.order_by(ReviewQueueItem.created_at.desc()).all()


@router.post("/{queue_item_id}/decide", response_model=ReviewQueueOut)
def decide(queue_item_id: str, payload: ReviewDecisionRequest, db: Session = Depends(get_db), user: User = Depends(require_permission("review:approve"))):
    item = db.get(ReviewQueueItem, queue_item_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review queue item not found")

    decision = ReviewDecision(queue_item_id=item.id, reviewer_id=user.id, action=payload.action, notes=payload.notes)
    db.add(decision)

    item.status = _ACTION_TO_QUEUE_STATUS[payload.action]
    db.add(item)
    db.commit()
    db.refresh(item)

    if item.assessment_id:
        assessment = db.get(ViolationAssessment, item.assessment_id)
        if assessment:
            violation_service.confirm_assessment(db, assessment, user.id, confirmed=(payload.action == ReviewAction.APPROVE), notes=payload.notes)

    audit_service.log_action(db, user.id, "REPORT_REVIEW_DECISION", "review_queue", item.id, {"action": payload.action.value})
    return item
