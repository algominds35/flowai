from pydantic import BaseModel
import uuid
from decimal import Decimal
from datetime import date, datetime


class WeeklyReviewItemResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    item_type: str
    title: str
    description: str | None
    commitment_id: uuid.UUID | None
    receivable_id: uuid.UUID | None
    transaction_id: uuid.UUID | None
    original_amount: Decimal | None
    original_date: date | None
    action: str | None
    confirmed_amount: Decimal | None
    confirmed_date: date | None
    status: str
    actioned_at: datetime | None

    model_config = {"from_attributes": True}


class WeeklyReviewSessionResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    week_start: date
    week_end: date
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    items: list[WeeklyReviewItemResponse] = []

    model_config = {"from_attributes": True}


class WeeklyReviewActionRequest(BaseModel):
    action: str  # confirm | change_amount | change_date | match | ignore | mark_uncertain
    confirmed_amount: Decimal | None = None
    confirmed_date: date | None = None
    match_transaction_id: uuid.UUID | None = None
