from pydantic import BaseModel
import uuid
from decimal import Decimal
from datetime import date, datetime


class ForecastWeekResponse(BaseModel):
    id: uuid.UUID
    week_number: int
    week_start: date
    week_end: date
    opening_cash: Decimal
    expected_inflows: Decimal
    expected_outflows: Decimal
    closing_cash: Decimal
    reserve_threshold: Decimal
    below_reserve: bool
    actual_inflows: Decimal | None
    actual_outflows: Decimal | None
    actual_closing_cash: Decimal | None
    inflow_variance: Decimal | None
    outflow_variance: Decimal | None
    cash_variance: Decimal | None

    model_config = {"from_attributes": True}


class ForecastSnapshotResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    computed_at: datetime
    as_of_date: date
    horizon_weeks: int
    opening_cash: Decimal
    safe_to_spend: Decimal
    minimum_cash_reserve: Decimal
    lowest_projected_cash: Decimal
    lowest_cash_week: date | None
    has_cash_cliff: bool
    cash_cliff_date: date | None
    cash_cliff_amount: Decimal | None
    weeks: list[ForecastWeekResponse] = []

    model_config = {"from_attributes": True}
