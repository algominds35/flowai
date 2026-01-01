from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..core.database import Base


class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    
    # Transaction data
    transaction_date = Column(Date, nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    balance = Column(Numeric(10, 2), nullable=True)
    
    # Categorization
    category = Column(String, nullable=True)  # e.g., "Meals & Entertainment"
    category_confidence = Column(Integer, nullable=True)  # 0-100
    
    # QuickBooks mapping
    quickbooks_vendor_name = Column(String, nullable=True)
    quickbooks_account_id = Column(String, nullable=True)
    quickbooks_transaction_id = Column(String, nullable=True)
    
    # Status
    is_verified = Column(Boolean, default=False)  # User reviewed
    synced_to_quickbooks = Column(Boolean, default=False)
    
    # Metadata
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    synced_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    document = relationship("Document", back_populates="transactions")
