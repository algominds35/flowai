from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime, date
from ..models.document import DocumentStatus, DocumentType


class DocumentBase(BaseModel):
    filename: str


class DocumentCreate(DocumentBase):
    pass


class TransactionResponse(BaseModel):
    id: int
    transaction_date: str  # Will be formatted as YYYY-MM-DD
    description: str
    amount: float
    balance: Optional[float] = None
    category: Optional[str] = None
    category_confidence: Optional[int] = None
    is_verified: bool
    synced_to_quickbooks: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    
    @field_validator('transaction_date', mode='before')
    @classmethod
    def convert_date_to_string(cls, v):
        """Convert date object to string"""
        if isinstance(v, (date, datetime)):
            return v.strftime('%Y-%m-%d')
        return v
    
    class Config:
        from_attributes = True


class DocumentResponse(DocumentBase):
    id: int
    status: DocumentStatus
    document_type: DocumentType
    page_count: int
    file_size: int
    ocr_confidence: Optional[int] = None
    error_message: Optional[str] = None
    synced_to_quickbooks: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    transactions: List[TransactionResponse] = []
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
