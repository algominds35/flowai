from pydantic import BaseModel
import uuid
from decimal import Decimal
from datetime import datetime


class BusinessCreate(BaseModel):
    name: str
    industry: str | None = None
    currency: str = "USD"
    minimum_cash_reserve: Decimal = Decimal("0.00")
    fiscal_year_start_month: int = 1


class BusinessUpdate(BaseModel):
    name: str | None = None
    industry: str | None = None
    currency: str | None = None
    minimum_cash_reserve: Decimal | None = None
    fiscal_year_start_month: int | None = None
    onboarding_step: int | None = None
    onboarding_completed: bool | None = None


class BusinessResponse(BaseModel):
    id: uuid.UUID
    name: str
    industry: str | None
    currency: str
    minimum_cash_reserve: Decimal
    fiscal_year_start_month: int
    onboarding_completed: bool
    onboarding_step: int
    created_at: datetime

    model_config = {"from_attributes": True}


class OnboardingStep(BaseModel):
    step: int
    data: dict = {}
