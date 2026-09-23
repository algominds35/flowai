"""
Forecast Engine
===============

Computes rolling 8-week and 13-week cash forecasts and persists them
as ForecastSnapshot + ForecastWeek + ForecastItem records.

The forecast is always based on the current financial state:
- Current cash accounts (bank balances)
- Pending/overdue commitments (outflows)
- Expected receivables (inflows)
- Recurring commitments projected forward

Reconciliation flow:
- After a week closes, actual transactions are matched against forecast items
- Variance is computed and stored
- Original forecast is PRESERVED (never overwritten by actuals)
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Sequence

from sqlalchemy.orm import Session


import uuid as _uuid_mod


def _to_date(value) -> date:
    """Ensure a value is a Python date object (not a string)."""
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    return value


def _to_uuid(value):
    """Ensure a value is a UUID object (not a string)."""
    if value is None:
        return None
    if isinstance(value, _uuid_mod.UUID):
        return value
    return _uuid_mod.UUID(str(value))

from app.models.business import Business
from app.models.commitment import Commitment, CommitmentStatus, RecurringFrequency
from app.models.receivable import Receivable, ReceivableStatus
from app.models.forecast import ForecastSnapshot, ForecastWeek, ForecastItem
from app.services.safe_to_spend import calculate_safe_to_spend, ZERO


def compute_and_save_forecast(
    db: Session,
    business: Business,
    horizon_weeks: int = 13,
    as_of_date: date | None = None,
) -> ForecastSnapshot:
    """Compute the rolling forecast and persist it."""
    if as_of_date is None:
        as_of_date = date.today()

    # Mark all previous snapshots for this business as not current
    db.query(ForecastSnapshot).filter(
        ForecastSnapshot.business_id == business.id,
        ForecastSnapshot.is_current == True,
    ).update({"is_current": False})

    # Run the Safe-to-Spend calculation (which also builds the weekly forecast)
    s2s = calculate_safe_to_spend(
        db=db,
        business=business,
        as_of_date=as_of_date,
        horizon_weeks=horizon_weeks,
    )

    # Create the snapshot
    snapshot = ForecastSnapshot(
        business_id=business.id,
        as_of_date=as_of_date,
        horizon_weeks=horizon_weeks,
        opening_cash=s2s.current_cash,
        safe_to_spend=s2s.safe_to_spend,
        minimum_cash_reserve=s2s.minimum_reserve,
        lowest_projected_cash=s2s.lowest_projected_cash,
        lowest_cash_week=s2s.lowest_cash_week,
        has_cash_cliff=s2s.has_cash_cliff,
        cash_cliff_date=s2s.cash_cliff_date,
        cash_cliff_amount=s2s.cash_cliff_amount,
        is_current=True,
    )
    db.add(snapshot)
    db.flush()  # get snapshot.id

    # Create week records
    for week_data in s2s.weeks:
        week = ForecastWeek(
            snapshot_id=snapshot.id,
            week_number=week_data["week_number"],
            week_start=week_data["week_start"],
            week_end=week_data["week_end"],
            opening_cash=week_data["opening_cash"],
            expected_inflows=week_data["expected_inflows"],
            expected_outflows=week_data["expected_outflows"],
            closing_cash=week_data["closing_cash"],
            reserve_threshold=week_data["reserve_threshold"],
            below_reserve=week_data["below_reserve"],
        )
        db.add(week)
        db.flush()

        # Create forecast items (inflows)
        for item in week_data["inflow_items"]:
            fi = ForecastItem(
                week_id=week.id,
                item_type="inflow",
                amount=Decimal(item["amount"]),
                label=item["name"],
                expected_date=_to_date(item["date"]),
                confidence=item["confidence"],
                receivable_id=_to_uuid(item.get("id")),
            )
            db.add(fi)

        # Create forecast items (outflows)
        for item in week_data["outflow_items"]:
            fi = ForecastItem(
                week_id=week.id,
                item_type="outflow",
                amount=Decimal(item["amount"]),
                label=item["name"],
                expected_date=_to_date(item["date"]),
                confidence=item["confidence"],
                commitment_id=_to_uuid(item.get("id")),
            )
            db.add(fi)

    db.commit()
    db.refresh(snapshot)
    return snapshot


def get_current_forecast(db: Session, business: Business) -> ForecastSnapshot | None:
    """Get the most recent current forecast snapshot."""
    return (
        db.query(ForecastSnapshot)
        .filter(
            ForecastSnapshot.business_id == business.id,
            ForecastSnapshot.is_current == True,
        )
        .order_by(ForecastSnapshot.computed_at.desc())
        .first()
    )


def reconcile_forecast_week(
    db: Session,
    week: ForecastWeek,
    actual_inflows: Decimal,
    actual_outflows: Decimal,
    actual_closing_cash: Decimal,
) -> ForecastWeek:
    """Fill in actual values for a closed week and compute variance.
    
    Original forecast values are PRESERVED — variance is additive.
    """
    week.actual_inflows = actual_inflows
    week.actual_outflows = actual_outflows
    week.actual_closing_cash = actual_closing_cash

    week.inflow_variance = actual_inflows - week.expected_inflows
    week.outflow_variance = actual_outflows - week.expected_outflows
    week.cash_variance = actual_closing_cash - week.closing_cash

    db.add(week)
    db.commit()
    db.refresh(week)
    return week


def project_recurring_commitments(
    commitments: Sequence[Commitment],
    from_date: date,
    to_date: date,
) -> list[dict]:
    """
    Given a list of recurring commitments, project future occurrences
    between from_date and to_date.
    
    Returns virtual commitment records (not persisted — used for forecasting only).
    """
    projected = []
    freq_map = {
        RecurringFrequency.WEEKLY: 7,
        RecurringFrequency.BIWEEKLY: 14,
        RecurringFrequency.MONTHLY: 30,  # approximate
        RecurringFrequency.QUARTERLY: 91,
        RecurringFrequency.ANNUALLY: 365,
    }

    for c in commitments:
        if not c.is_recurring or c.recurring_frequency is None:
            continue

        # Only project from tomorrow onwards (today's is already in DB)
        next_date = c.due_date
        if c.recurring_frequency == RecurringFrequency.SEMIMONTHLY:
            # 1st and 15th
            while next_date <= to_date:
                if next_date >= from_date:
                    projected.append({
                        "name": c.name,
                        "category": c.category.value,
                        "amount": str(c.amount),
                        "due_date": str(next_date),
                        "confidence": c.confidence_level,
                        "is_projected": True,
                        "source_commitment_id": str(c.id),
                    })
                # Advance to next semi-monthly date
                if next_date.day < 15:
                    next_date = next_date.replace(day=15)
                else:
                    if next_date.month == 12:
                        next_date = next_date.replace(year=next_date.year + 1, month=1, day=1)
                    else:
                        next_date = next_date.replace(month=next_date.month + 1, day=1)
        elif c.recurring_frequency == RecurringFrequency.MONTHLY:
            # Same day each month
            while next_date <= to_date:
                if next_date >= from_date:
                    projected.append({
                        "name": c.name,
                        "category": c.category.value,
                        "amount": str(c.amount),
                        "due_date": str(next_date),
                        "confidence": c.confidence_level,
                        "is_projected": True,
                        "source_commitment_id": str(c.id),
                    })
                # Next month, same day
                month = next_date.month + 1
                year = next_date.year
                if month > 12:
                    month = 1
                    year += 1
                import calendar
                day = min(next_date.day, calendar.monthrange(year, month)[1])
                next_date = next_date.replace(year=year, month=month, day=day)
        else:
            delta_days = freq_map.get(c.recurring_frequency, 30)
            while next_date <= to_date:
                if next_date >= from_date:
                    projected.append({
                        "name": c.name,
                        "category": c.category.value,
                        "amount": str(c.amount),
                        "due_date": str(next_date),
                        "confidence": c.confidence_level,
                        "is_projected": True,
                        "source_commitment_id": str(c.id),
                    })
                next_date = next_date + timedelta(days=delta_days)

    return projected
