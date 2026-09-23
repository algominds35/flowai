from pydantic import BaseModel
import uuid
from decimal import Decimal
from datetime import date, datetime
from app.models.receivable import ReceivableStatus


class ReceivableCreate(BaseModel):
    name: str
    description: str | None = None
    receivable_type: str = "invoice"
    customer_name: str | None = None
    invoice_number: str | None = None
    amount: Decimal
    expected_date: date
    invoice_date: date | None = None
    currency: str = "USD"
    confidence_level: str = "high"
    notes: str | None = None


class ReceivableUpdate(BaseModel):
    name: str | None = None
    amount: Decimal | None = None
    expected_date: date | None = None
    status: ReceivableStatus | None = None
    confidence_level: str | None = None
    is_verified: bool | None = None
    notes: str | None = None


class ReceivableResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    description: str | None
    receivable_type: str
    customer_name: str | None
    invoice_number: str | None
    amount: Decimal
    amount_received: Decimal
    remaining_amount: Decimal
    currency: str
    invoice_date: date | None
    expected_date: date
    received_date: date | None
    status: ReceivableStatus
    confidence_level: str
    is_verified: bool
    external_source: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReceivablePaymentCreate(BaseModel):
    amount: Decimal
    received_date: date
    notes: str | None = None
