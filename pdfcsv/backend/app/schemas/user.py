from pydantic import BaseModel, EmailStr, computed_field
from typing import Optional
from datetime import datetime
from ..models.user import SubscriptionTier


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    subscription_tier: SubscriptionTier
    pages_processed_this_month: int
    pages_processed_total: int
    quickbooks_realm_id: Optional[str] = None
    quickbooks_access_token: Optional[str] = None
    created_at: datetime
    
    @computed_field
    @property
    def quickbooks_connected(self) -> bool:
        """Check if QuickBooks is connected"""
        return bool(self.quickbooks_realm_id and self.quickbooks_access_token)
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
