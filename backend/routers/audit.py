from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.audit import AuditLog
from models.user import User
from schemas.audit import AuditLogOut
from security import require_permission

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
def list_audit_logs(
    resource_type: str | None = None,
    action: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("audit:read")),
):
    query = db.query(AuditLog)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if action:
        query = query.filter(AuditLog.action == action)
    return query.order_by(AuditLog.timestamp.desc()).limit(min(limit, 1000)).all()
