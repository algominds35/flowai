from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.models.business import Business, BusinessMember

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    import uuid
    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    return user


def get_current_active_business(
    business_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Business:
    """Get the current business context for the user."""
    import uuid
    
    if business_id:
        bid = uuid.UUID(business_id)
        member = db.query(BusinessMember).filter(
            BusinessMember.business_id == bid,
            BusinessMember.user_id == current_user.id,
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Access denied to this business")
        return member.business
    
    # Get first (primary) business
    member = (
        db.query(BusinessMember)
        .filter(BusinessMember.user_id == current_user.id)
        .order_by(BusinessMember.is_primary.desc(), BusinessMember.joined_at)
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="No business found. Please complete setup.")
    return member.business


class BusinessContext:
    """Dependency that provides business from query param or URL."""
    def __init__(self, business_id_param: str = "business_id"):
        self.business_id_param = business_id_param
    
    def __call__(
        self,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> Business:
        return get_current_active_business(None, current_user, db)
