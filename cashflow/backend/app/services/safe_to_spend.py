"""
Safe-to-Spend Engine
====================

Safe to Spend = Current Cash - Minimum Reserve - Sum of all unpaid commitments
               due within the forecast horizon (8 weeks by default) + 0

More precisely:

  Safe to Spend = Current Cash Position
                - Minimum Cash Reserve
                - Total Scheduled Outflows (commitments due ≤ horizon)
                + 0   (we do NOT add receivables — those are upside, not guaranteed)

We use the LOWEST PROJECTED CASH as the binding constraint:
  Lowest Cash = min(weekly closing cash across all forecast weeks)

  Safe to Spend = Lowest Cash - Minimum Reserve

If Lowest Cash < Minimum Reserve → Safe to Spend = 0 (or negative, shown as warning).

The engine produces a full explanation of each component.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import NamedTuple

from sqlalchemy.orm import Session

from app.models.cash_account import CashAccount
from app.models.commitment import Commitment, CommitmentStatus
from app.models.receivable import Receivable, ReceivableStatus
from app.models.business import Business


ZERO = Decimal("0.00")


class SafeToSpendComponent(NamedTuple):
    label: str
    amount: Decimal
    description: str
    items: list[dict]  # individual line items


class SafeToSpendResult(NamedTuple):
    safe_to_spend: Decimal           # The headline number
    current_cash: Decimal            # Sum of bank balances
    minimum_reserve: Decimal         # Business's configured reserve
    total_scheduled_outflows: Decimal # All future commitments in horizon
    total_expected_inflows: Decimal  # Expected receivables (for context only)
    lowest_projected_cash: Decimal   # Min cash across all weeks
    lowest_cash_week: date | None    # Which week hits lowest
    has_cash_cliff: bool             # Cash ever drops below reserve?
    cash_cliff_date: date | None     # First date cash drops below reserve
    cash_cliff_amount: Decimal | None # How far below reserve
    components: list[SafeToSpendComponent]
    weeks: list[dict]                # Weekly breakdown
    as_of_date: date


def calculate_safe_to_spend(
    db: Session,
    business: Business,
    as_of_date: date | None = None,
    horizon_weeks: int = 8,
) -> SafeToSpendResult:
    """Calculate Safe-to-Spend for a business.
    
    This is the canonical calculation — every dashboard number must
    come from this function to ensure mathematical consistency.
    """
    if as_of_date is None:
        as_of_date = date.today()

    horizon_end = as_of_date + timedelta(weeks=horizon_weeks)

    # ── Step 1: Current cash position ─────────────────────────────────────────
    accounts = (
        db.query(CashAccount)
        .filter(
            CashAccount.business_id == business.id,
            CashAccount.is_active == True,
            CashAccount.include_in_cash_position == True,
        )
        .all()
    )

    current_cash = sum((a.current_balance for a in accounts), ZERO)
    account_items = [
        {
            "account_name": a.name,
            "balance": str(a.current_balance),
            "as_of": str(a.balance_as_of) if a.balance_as_of else None,
        }
        for a in accounts
    ]

    # ── Step 2: Minimum cash reserve ──────────────────────────────────────────
    minimum_reserve = business.minimum_cash_reserve or ZERO

    # ── Step 3: All scheduled outflows in horizon ──────────────────────────────
    pending_commitments = (
        db.query(Commitment)
        .filter(
            Commitment.business_id == business.id,
            Commitment.status.in_([CommitmentStatus.SCHEDULED, CommitmentStatus.OVERDUE, CommitmentStatus.PARTIALLY_PAID]),
            Commitment.due_date <= horizon_end,
        )
        .order_by(Commitment.due_date)
        .all()
    )

    commitment_items = []
    for c in pending_commitments:
        remaining = c.amount - c.amount_paid
        if remaining > ZERO:
            commitment_items.append({
                "id": str(c.id),
                "name": c.name,
                "category": c.category.value,
                "amount": str(remaining),
                "due_date": str(c.due_date),
                "confidence": c.confidence_level,
                "is_overdue": c.due_date < as_of_date,
            })

    total_scheduled_outflows = sum(
        Decimal(item["amount"]) for item in commitment_items
    )

    # ── Step 4: Expected inflows in horizon ───────────────────────────────────
    pending_receivables = (
        db.query(Receivable)
        .filter(
            Receivable.business_id == business.id,
            Receivable.status.in_([ReceivableStatus.EXPECTED, ReceivableStatus.OVERDUE, ReceivableStatus.PARTIALLY_RECEIVED]),
            Receivable.expected_date <= horizon_end,
        )
        .order_by(Receivable.expected_date)
        .all()
    )

    receivable_items = []
    for r in pending_receivables:
        remaining = r.amount - r.amount_received
        if remaining > ZERO:
            receivable_items.append({
                "id": str(r.id),
                "name": r.name,
                "customer": r.customer_name,
                "amount": str(remaining),
                "expected_date": str(r.expected_date),
                "confidence": r.confidence_level,
                "is_overdue": r.expected_date < as_of_date,
            })

    total_expected_inflows = sum(
        Decimal(item["amount"]) for item in receivable_items
    )

    # ── Step 5: Build weekly forecast ─────────────────────────────────────────
    weeks = _build_weekly_forecast(
        as_of_date=as_of_date,
        horizon_weeks=horizon_weeks,
        current_cash=current_cash,
        commitments=pending_commitments,
        receivables=pending_receivables,
        minimum_reserve=minimum_reserve,
    )

    # ── Step 6: Find lowest projected cash ────────────────────────────────────
    lowest_projected_cash = current_cash
    lowest_cash_week: date | None = None

    for week in weeks:
        closing = week["closing_cash"]
        if closing < lowest_projected_cash:
            lowest_projected_cash = closing
            lowest_cash_week = week["week_start"]

    # ── Step 7: Cash cliff detection ──────────────────────────────────────────
    has_cash_cliff = False
    cash_cliff_date: date | None = None
    cash_cliff_amount: Decimal | None = None

    for week in weeks:
        closing = week["closing_cash"]
        if closing < minimum_reserve:
            has_cash_cliff = True
            # First week that drops below reserve
            if cash_cliff_date is None or week["week_start"] < cash_cliff_date:
                cash_cliff_date = week["week_start"]
                cash_cliff_amount = minimum_reserve - closing
            break

    # ── Step 8: Safe to Spend ─────────────────────────────────────────────────
    # Core formula: lowest projected cash minus reserve
    safe_to_spend = max(ZERO, lowest_projected_cash - minimum_reserve)

    # ── Step 9: Build explanation components ──────────────────────────────────
    components = [
        SafeToSpendComponent(
            label="Current Cash",
            amount=current_cash,
            description=f"Total balance across {len(accounts)} account(s)",
            items=account_items,
        ),
        SafeToSpendComponent(
            label="Minimum Cash Reserve",
            amount=-minimum_reserve,
            description="Required buffer you've set aside",
            items=[],
        ),
        SafeToSpendComponent(
            label="Scheduled Outflows",
            amount=-total_scheduled_outflows,
            description=f"{len(commitment_items)} commitment(s) due in the next {horizon_weeks} weeks",
            items=commitment_items,
        ),
        SafeToSpendComponent(
            label="Expected Inflows (for context)",
            amount=total_expected_inflows,
            description=f"{len(receivable_items)} receivable(s) — not counted in Safe to Spend",
            items=receivable_items,
        ),
        SafeToSpendComponent(
            label="Lowest Projected Cash",
            amount=lowest_projected_cash,
            description=f"Minimum cash point in the {horizon_weeks}-week window",
            items=[],
        ),
        SafeToSpendComponent(
            label="Safe to Spend",
            amount=safe_to_spend,
            description="Lowest Projected Cash minus your Minimum Reserve",
            items=[],
        ),
    ]

    return SafeToSpendResult(
        safe_to_spend=safe_to_spend,
        current_cash=current_cash,
        minimum_reserve=minimum_reserve,
        total_scheduled_outflows=total_scheduled_outflows,
        total_expected_inflows=total_expected_inflows,
        lowest_projected_cash=lowest_projected_cash,
        lowest_cash_week=lowest_cash_week,
        has_cash_cliff=has_cash_cliff,
        cash_cliff_date=cash_cliff_date,
        cash_cliff_amount=cash_cliff_amount,
        components=list(components),
        weeks=weeks,
        as_of_date=as_of_date,
    )


def _build_weekly_forecast(
    as_of_date: date,
    horizon_weeks: int,
    current_cash: Decimal,
    commitments: list[Commitment],
    receivables: list[Receivable],
    minimum_reserve: Decimal,
) -> list[dict]:
    """Build week-by-week forecast starting from as_of_date."""
    # Find start of current week (Monday)
    week_start = as_of_date - timedelta(days=as_of_date.weekday())
    weeks = []
    running_cash = current_cash

    for week_num in range(horizon_weeks):
        week_end = week_start + timedelta(days=6)

        # Outflows in this week
        week_outflows = []
        week_outflow_total = ZERO
        for c in commitments:
            remaining = c.amount - c.amount_paid
            if remaining > ZERO and week_start <= c.due_date <= week_end:
                week_outflow_total += remaining
                week_outflows.append({
                    "id": str(c.id),
                    "name": c.name,
                    "amount": str(remaining),
                    "date": str(c.due_date),
                    "category": c.category.value,
                    "confidence": c.confidence_level,
                })

        # Inflows in this week
        week_inflows = []
        week_inflow_total = ZERO
        for r in receivables:
            remaining = r.amount - r.amount_received
            if remaining > ZERO and week_start <= r.expected_date <= week_end:
                week_inflow_total += remaining
                week_inflows.append({
                    "id": str(r.id),
                    "name": r.name,
                    "amount": str(remaining),
                    "date": str(r.expected_date),
                    "confidence": r.confidence_level,
                })

        closing_cash = running_cash + week_inflow_total - week_outflow_total

        weeks.append({
            "week_number": week_num + 1,
            "week_start": week_start,
            "week_end": week_end,
            "opening_cash": running_cash,
            "expected_inflows": week_inflow_total,
            "expected_outflows": week_outflow_total,
            "closing_cash": closing_cash,
            "reserve_threshold": minimum_reserve,
            "below_reserve": closing_cash < minimum_reserve,
            "inflow_items": week_inflows,
            "outflow_items": week_outflows,
        })

        running_cash = closing_cash
        week_start = week_start + timedelta(weeks=1)

    return weeks
