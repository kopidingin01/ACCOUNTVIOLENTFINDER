from sqlalchemy.orm import Session

from models.audit import AuditLog


def log_action(
    db: Session,
    user_id: str | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=metadata or {},
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
