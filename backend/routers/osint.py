from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.osint import AccountFinderRequest, AccountFinderResult
from security import require_permission
from services import account_finder_service

router = APIRouter(prefix="/api/osint", tags=["osint"])


@router.post("/account-finder", response_model=AccountFinderResult)
def run_account_finder(payload: AccountFinderRequest, db: Session = Depends(get_db), user: User = Depends(require_permission("osint:run"))):
    return account_finder_service.analyze_account(db, payload.account_url, payload.create_case, user.id)
