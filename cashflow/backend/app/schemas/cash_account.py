from pydantic import BaseModel
import uuid
from decimal import Decimal
from datetime import date, datetime


class CashAccountCreate(BaseModel):
    name: str
    account_type: str = "checking"
    institution_name: str | None = None
    last_four: str | None = None
    current_balance: Decimal = Decimal("0.00")
    balance_as_of: date | None = None
    include_in_cash_position: bool = True


class CashAccountUpdate(BaseModel):
    name: str | None = None
    current_balance: Decimal | None = None
    balance_as_of: date | None = None
    is_active: bool | None = None
    include_in_cash_position: bool | None = None


class CashAccountResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    account_type: str
    institution_name: str | None
    last_four: str | None
    current_balance: Decimal
    balance_as_of: date | None
    is_active: bool
    include_in_cash_position: bool
    created_at: datetime

    model_config = {"from_attributes": True}
