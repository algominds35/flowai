from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
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
