from pydantic import BaseModel
from decimal import Decimal
from datetime import date


class ComponentItem(BaseModel):
    label: str
    amount: Decimal
    description: str
    items: list[dict] = []


class WeekForecast(BaseModel):
    week_number: int
    week_start: date
    week_end: date
    opening_cash: Decimal
    expected_inflows: Decimal
    expected_outflows: Decimal
    closing_cash: Decimal
    reserve_threshold: Decimal
    below_reserve: bool
    inflow_items: list[dict] = []
    outflow_items: list[dict] = []


class SafeToSpendResponse(BaseModel):
    safe_to_spend: Decimal
    current_cash: Decimal
    minimum_reserve: Decimal
    total_scheduled_outflows: Decimal
    total_expected_inflows: Decimal
    lowest_projected_cash: Decimal
    lowest_cash_week: date | None
    has_cash_cliff: bool
    cash_cliff_date: date | None
    cash_cliff_amount: Decimal | None
    components: list[ComponentItem]
    weeks: list[WeekForecast]
    as_of_date: date
    horizon_weeks: int = 8
