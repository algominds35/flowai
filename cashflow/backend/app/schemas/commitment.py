from pydantic import BaseModel
import uuid
from decimal import Decimal
from datetime import date, datetime
from app.models.commitment import CommitmentCategory, CommitmentStatus, RecurringFrequency


class CommitmentCreate(BaseModel):
    name: str
    description: str | None = None
    category: CommitmentCategory = CommitmentCategory.MANUAL
    vendor_name: str | None = None
    amount: Decimal
    due_date: date
    currency: str = "USD"
    confidence_level: str = "high"
    is_recurring: bool = False
    recurring_frequency: RecurringFrequency | None = None
    recurring_day_of_month: int | None = None
    recurring_end_date: date | None = None
    notes: str | None = None
    tags: list[str] = []
    credit_card_id: uuid.UUID | None = None


class CommitmentUpdate(BaseModel):
    name: str | None = None
    amount: Decimal | None = None
    due_date: date | None = None
    status: CommitmentStatus | None = None
    confidence_level: str | None = None
    is_verified: bool | None = None
    notes: str | None = None
    paid_date: date | None = None
    amount_paid: Decimal | None = None


class CommitmentResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    description: str | None
    category: CommitmentCategory
    vendor_name: str | None
    amount: Decimal
    amount_paid: Decimal
    remaining_amount: Decimal
    currency: str
    due_date: date
    paid_date: date | None
    status: CommitmentStatus
    is_verified: bool
    confidence_level: str
    is_recurring: bool
    recurring_frequency: RecurringFrequency | None
    recurring_end_date: date | None
    credit_card_id: uuid.UUID | None
    purchase_order_id: uuid.UUID | None
    matched_transaction_id: uuid.UUID | None
    notes: str | None
    tags: list
    created_at: datetime

    model_config = {"from_attributes": True}
