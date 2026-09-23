from pydantic import BaseModel
import uuid
from decimal import Decimal
from datetime import date, datetime


class ScenarioCreate(BaseModel):
    name: str
    description: str | None = None
    scenario_type: str  # one_time_purchase | recurring_expense | new_hire | inventory_po | etc.
    amount: Decimal
    start_date: date
    end_date: date | None = None
    frequency: str | None = None  # weekly | biweekly | monthly | quarterly | annually
    additional_params: dict = {}


class ScenarioItemResponse(BaseModel):
    week_start: date
    baseline_inflows: Decimal
    baseline_outflows: Decimal
    baseline_closing_cash: Decimal
    scenario_inflows: Decimal
    scenario_outflows: Decimal
    scenario_closing_cash: Decimal
    scenario_additional_outflow: Decimal

    model_config = {"from_attributes": True}


class ScenarioResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    description: str | None
    scenario_type: str
    amount: Decimal
    start_date: date
    end_date: date | None
    frequency: str | None

    # Baseline
    baseline_safe_to_spend: Decimal | None
    baseline_lowest_cash: Decimal | None
    baseline_lowest_cash_week: date | None

    # Projected
    projected_safe_to_spend: Decimal | None
    projected_lowest_cash: Decimal | None
    projected_lowest_cash_week: date | None

    # Verdict
    can_afford: bool | None
    reserve_impact: Decimal | None
    affected_weeks: list
    verdict_message: str | None

    status: str
    items: list[ScenarioItemResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}
