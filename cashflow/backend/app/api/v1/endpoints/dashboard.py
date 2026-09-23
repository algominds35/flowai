"""Dashboard / Home endpoint — the primary Safe-to-Spend view."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date

from app.db.session import get_db
from app.core.deps import get_current_user, get_current_active_business
from app.models.user import User
from app.models.business import Business
from app.schemas.safe_to_spend import SafeToSpendResponse
from app.services.safe_to_spend import calculate_safe_to_spend

router = APIRouter()


@router.get("/safe-to-spend", response_model=SafeToSpendResponse)
def get_safe_to_spend(
    horizon_weeks: int = Query(default=8, ge=4, le=26),
    as_of_date: date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Calculate and return Safe-to-Spend with full explanation.
    
    This is the primary number shown on the Home screen.
    Every component is calculated from the financial domain model.
    """
    business = get_current_active_business(None, current_user, db)
    result = calculate_safe_to_spend(
        db=db,
        business=business,
        as_of_date=as_of_date,
        horizon_weeks=horizon_weeks,
    )
    
    from app.schemas.safe_to_spend import ComponentItem, WeekForecast
    
    return SafeToSpendResponse(
        safe_to_spend=result.safe_to_spend,
        current_cash=result.current_cash,
        minimum_reserve=result.minimum_reserve,
        total_scheduled_outflows=result.total_scheduled_outflows,
        total_expected_inflows=result.total_expected_inflows,
        lowest_projected_cash=result.lowest_projected_cash,
        lowest_cash_week=result.lowest_cash_week,
        has_cash_cliff=result.has_cash_cliff,
        cash_cliff_date=result.cash_cliff_date,
        cash_cliff_amount=result.cash_cliff_amount,
        components=[
            ComponentItem(
                label=c.label,
                amount=c.amount,
                description=c.description,
                items=c.items,
            )
            for c in result.components
        ],
        weeks=[
            WeekForecast(
                week_number=w["week_number"],
                week_start=w["week_start"],
                week_end=w["week_end"],
                opening_cash=w["opening_cash"],
                expected_inflows=w["expected_inflows"],
                expected_outflows=w["expected_outflows"],
                closing_cash=w["closing_cash"],
                reserve_threshold=w["reserve_threshold"],
                below_reserve=w["below_reserve"],
                inflow_items=w["inflow_items"],
                outflow_items=w["outflow_items"],
            )
            for w in result.weeks
        ],
        as_of_date=result.as_of_date,
        horizon_weeks=horizon_weeks,
    )
