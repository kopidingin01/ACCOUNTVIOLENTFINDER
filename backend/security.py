from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
from models.user import Role, User

settings = get_settings()

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.ADMIN: {"*"},
    Role.ANALYST: {
        "case:create", "case:read", "case:update",
        "target:create", "target:read",
        "evidence:create", "evidence:read", "evidence:verify",
        "assessment:create", "assessment:read",
        "report:create", "report:read", "report:update",
        "review:read",
        "audit:read:own",
        "osint:run",
    },
    Role.REVIEWER: {
        "case:read", "target:read", "evidence:read",
        "assessment:read", "report:read",
        "review:read", "review:approve", "review:reject", "review:return",
        "audit:read:own",
    },
    Role.AUDITOR: {
        "case:read", "target:read", "evidence:read",
        "assessment:read", "report:read", "review:read",
        "audit:read",
    },
    Role.VIEWER: {
        "case:read", "target:read", "evidence:read",
        "assessment:read", "report:read", "review:read",
    },
}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "role": role, "type": "access", "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": subject, "type": "refresh", "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    user = db.query(User).filter(User.username == payload.get("sub")).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require_permission(permission: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        perms = ROLE_PERMISSIONS.get(user.role, set())
        if "*" in perms or permission in perms:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{user.role.value}' lacks permission '{permission}'",
        )
    return dependency
