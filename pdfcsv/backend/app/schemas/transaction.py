from pydantic import BaseModel
from typing import Optional
from datetime import date


class TransactionUpdate(BaseModel):
    transaction_date: Optional[date] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    balance: Optional[float] = None
    category: Optional[str] = None
    notes: Optional[str] = None
    is_verified: Optional[bool] = None


class TransactionBulkUpdate(BaseModel):
    transaction_ids: list[int]
    category: Optional[str] = None
    is_verified: Optional[bool] = None
