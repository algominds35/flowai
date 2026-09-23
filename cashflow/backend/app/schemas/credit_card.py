from pydantic import BaseModel
import uuid
from decimal import Decimal
from datetime import date, datetime


class CreditCardCreate(BaseModel):
    name: str
    last_four: str | None = None
    card_network: str | None = None
    issuing_bank: str | None = None
    statement_closing_day: int | None = None
    payment_due_days: int = 21
    credit_limit: Decimal | None = None
    current_balance: Decimal = Decimal("0.00")
    payment_cash_account_id: uuid.UUID | None = None


class CreditCardUpdate(BaseModel):
    name: str | None = None
    current_balance: Decimal | None = None
    statement_closing_day: int | None = None
    payment_due_days: int | None = None
    payment_cash_account_id: uuid.UUID | None = None
    is_active: bool | None = None


class CreditCardResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    last_four: str | None
    card_network: str | None
    issuing_bank: str | None
    statement_closing_day: int | None
    payment_due_days: int
    current_balance: Decimal
    credit_limit: Decimal | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CreditCardTransactionResponse(BaseModel):
    id: uuid.UUID
    credit_card_id: uuid.UUID
    transaction_date: date
    description: str
    amount: Decimal
    merchant_name: str | None
    is_pending: bool

    model_config = {"from_attributes": True}


class CreditCardStatementResponse(BaseModel):
    id: uuid.UUID
    credit_card_id: uuid.UUID
    period_start: date
    period_end: date
    due_date: date
    statement_balance: Decimal
    is_paid: bool
    paid_date: date | None

    model_config = {"from_attributes": True}
