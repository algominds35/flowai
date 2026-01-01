from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from ..core.database import Base


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    OCR_COMPLETE = "ocr_complete"
    EXTRACTION_COMPLETE = "extraction_complete"
    READY = "ready"
    ERROR = "error"
    SYNCED = "synced"


class DocumentType(str, enum.Enum):
    BANK_STATEMENT = "bank_statement"
    CREDIT_CARD = "credit_card"
    UNKNOWN = "unknown"


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # File info
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)  # S3/R2 path
    file_size = Column(Integer, nullable=False)  # bytes
    mime_type = Column(String, default="application/pdf")
    page_count = Column(Integer, default=1)
    
    # Processing
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED)
    document_type = Column(Enum(DocumentType), default=DocumentType.UNKNOWN)
    error_message = Column(Text, nullable=True)
    
    # OCR results
    ocr_text = Column(Text, nullable=True)
    ocr_confidence = Column(Integer, nullable=True)  # 0-100
    
    # QuickBooks sync
    synced_to_quickbooks = Column(Boolean, default=False)
    quickbooks_sync_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="documents")
    transactions = relationship("Transaction", back_populates="document", cascade="all, delete-orphan")
