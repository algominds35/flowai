from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from ..core.database import Base


class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    PRO = "pro"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Subscription
    subscription_tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.FREE)
    stripe_customer_id = Column(String, nullable=True, unique=True)
    stripe_subscription_id = Column(String, nullable=True)
    
    # QuickBooks connection
    quickbooks_realm_id = Column(String, nullable=True)
    quickbooks_access_token = Column(String, nullable=True)
    quickbooks_refresh_token = Column(String, nullable=True)
    quickbooks_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Usage tracking
    pages_processed_this_month = Column(Integer, default=0)
    pages_processed_total = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
