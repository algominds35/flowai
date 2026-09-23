"""
Decision Engine — "Can I Afford This?"
=======================================

Computes the before/after impact of a proposed spending decision on
the cash forecast. Shows:

- Safe to Spend before vs after
- Lowest cash before vs after
- Reserve impact
- Which weeks are affected
- Verdict: yes/no/warning
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.scenario import Scenario, ScenarioItem
from app.models.commitment import Commitment, CommitmentCategory, CommitmentStatus, RecurringFrequency
from app.services.safe_to_spend import calculate_safe_to_spend, _build_weekly_forecast

ZERO = Decimal("0.00")


def compute_scenario(
    db: Session,
    business: Business,
    scenario: Scenario,
) -> Scenario:
    """
    Run the Can-I-Afford-It calculation for a scenario.
    
    Computes baseline forecast, then adds the proposed expenditure(s)
    and recomputes to show impact.
    """
    today = date.today()
    horizon_weeks = 13

    # ── Baseline ──────────────────────────────────────────────────────────────
    baseline = calculate_safe_to_spend(
        db=db,
        business=business,
        as_of_date=today,
        horizon_weeks=horizon_weeks,
    )

    scenario.baseline_safe_to_spend = baseline.safe_to_spend
    scenario.baseline_lowest_cash = baseline.lowest_projected_cash
    scenario.baseline_lowest_cash_week = baseline.lowest_cash_week

    # ── Build scenario cash events ────────────────────────────────────────────
    scenario_events = _build_scenario_events(scenario)

    # ── Re-run forecast with scenario events added ────────────────────────────
    from app.models.cash_account import CashAccount
    from app.models.commitment import Commitment
    from app.models.receivable import Receivable, ReceivableStatus

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

    horizon_end = today + timedelta(weeks=horizon_weeks)

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

    minimum_reserve = business.minimum_cash_reserve or ZERO

    # Build baseline weeks
    baseline_weeks = _build_weekly_forecast(
        as_of_date=today,
        horizon_weeks=horizon_weeks,
        current_cash=current_cash,
        commitments=pending_commitments,
        receivables=pending_receivables,
        minimum_reserve=minimum_reserve,
    )

    # Build scenario weeks (same commitments + scenario events)
    scenario_weeks = _build_scenario_weeks(
        as_of_date=today,
        horizon_weeks=horizon_weeks,
        current_cash=current_cash,
        commitments=pending_commitments,
        receivables=pending_receivables,
        minimum_reserve=minimum_reserve,
        scenario_events=scenario_events,
    )

    # ── Compute scenario results ──────────────────────────────────────────────
    scenario_lowest = current_cash
    scenario_lowest_week = None
    affected_weeks = []

    for i, (bw, sw) in enumerate(zip(baseline_weeks, scenario_weeks)):
        if sw["closing_cash"] < scenario_lowest:
            scenario_lowest = sw["closing_cash"]
            scenario_lowest_week = sw["week_start"]

        if sw["closing_cash"] < minimum_reserve and bw["closing_cash"] >= minimum_reserve:
            # This week becomes problematic because of the scenario
            affected_weeks.append(str(sw["week_start"]))
        elif sw["closing_cash"] < minimum_reserve:
            affected_weeks.append(str(sw["week_start"]))

    scenario_s2s = max(ZERO, scenario_lowest - minimum_reserve)
    reserve_impact = baseline.lowest_projected_cash - scenario_lowest

    scenario.projected_safe_to_spend = scenario_s2s
    scenario.projected_lowest_cash = scenario_lowest
    scenario.projected_lowest_cash_week = scenario_lowest_week
    scenario.reserve_impact = reserve_impact
    scenario.affected_weeks = affected_weeks

    # Verdict
    can_afford = scenario_s2s > ZERO
    scenario.can_afford = can_afford

    if can_afford:
        if reserve_impact > Decimal("5000"):
            scenario.verdict_message = (
                f"You can afford this, but it significantly reduces your safety buffer by "
                f"${reserve_impact:,.2f}. Safe to Spend drops from "
                f"${baseline.safe_to_spend:,.2f} to ${scenario_s2s:,.2f}."
            )
        else:
            scenario.verdict_message = (
                f"Yes — you can afford this. Safe to Spend goes from "
                f"${baseline.safe_to_spend:,.2f} to ${scenario_s2s:,.2f}."
            )
    else:
        scenario.verdict_message = (
            f"Not recommended — this would push your cash below the minimum reserve. "
            f"Lowest projected cash drops to ${scenario_lowest:,.2f} "
            f"(reserve: ${minimum_reserve:,.2f}). "
            f"Consider delaying or reducing the amount."
        )

    # ── Persist weekly comparison rows ────────────────────────────────────────
    db.query(ScenarioItem).filter(ScenarioItem.scenario_id == scenario.id).delete()

    for bw, sw in zip(baseline_weeks, scenario_weeks):
        item = ScenarioItem(
            scenario_id=scenario.id,
            week_start=bw["week_start"],
            baseline_inflows=bw["expected_inflows"],
            baseline_outflows=bw["expected_outflows"],
            baseline_closing_cash=bw["closing_cash"],
            scenario_inflows=sw["expected_inflows"],
            scenario_outflows=sw["expected_outflows"],
            scenario_closing_cash=sw["closing_cash"],
            scenario_additional_outflow=sw.get("scenario_additional_outflow", ZERO),
        )
        db.add(item)

    scenario.status = "computed"
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return scenario


def _build_scenario_events(scenario: Scenario) -> list[dict]:
    """Convert scenario parameters into a list of dated cash events."""
    events = []
    amount = scenario.amount
    start_date = scenario.start_date
    end_date = scenario.end_date
    frequency = scenario.frequency
    scenario_type = scenario.scenario_type

    if scenario_type in ("one_time_purchase", "inventory_po", "marketing",
                          "vehicle_equipment", "owner_distribution"):
        # Single outflow
        events.append({"date": start_date, "amount": amount, "direction": "out"})

        # For POs, may have installments in additional_params
        installments = scenario.additional_params.get("installments", [])
        for inst in installments:
            events.append({
                "date": date.fromisoformat(inst["date"]),
                "amount": Decimal(str(inst["amount"])),
                "direction": "out",
            })

    elif scenario_type in ("recurring_expense", "new_hire"):
        # Recurring outflow
        if not frequency:
            events.append({"date": start_date, "amount": amount, "direction": "out"})
        else:
            current = start_date
            horizon_end = date.today() + timedelta(weeks=13)
            while current <= (end_date or horizon_end):
                events.append({"date": current, "amount": amount, "direction": "out"})
                current = _advance_date(current, frequency)

    return events


def _advance_date(d: date, frequency: str) -> date:
    freq_map = {
        "weekly": timedelta(days=7),
        "biweekly": timedelta(days=14),
        "monthly": None,
        "quarterly": None,
        "annually": None,
    }
    if frequency == "monthly":
        month = d.month + 1
        year = d.year
        if month > 12:
            month = 1
            year += 1
        import calendar
        day = min(d.day, calendar.monthrange(year, month)[1])
        return d.replace(year=year, month=month, day=day)
    elif frequency == "quarterly":
        month = d.month + 3
        year = d.year
        while month > 12:
            month -= 12
            year += 1
        import calendar
        day = min(d.day, calendar.monthrange(year, month)[1])
        return d.replace(year=year, month=month, day=day)
    elif frequency == "annually":
        return d.replace(year=d.year + 1)
    else:
        delta = freq_map.get(frequency, timedelta(days=30))
        return d + delta


def _build_scenario_weeks(
    as_of_date, horizon_weeks, current_cash, commitments, receivables, minimum_reserve, scenario_events
):
    """Like _build_weekly_forecast but with additional scenario outflows."""
    from app.services.safe_to_spend import _build_weekly_forecast as _bwf
    # Build base weeks
    weeks = _bwf(
        as_of_date=as_of_date,
        horizon_weeks=horizon_weeks,
        current_cash=current_cash,
        commitments=commitments,
        receivables=receivables,
        minimum_reserve=minimum_reserve,
    )

    # Apply scenario events on top
    from datetime import timedelta
    week_start = as_of_date - timedelta(days=as_of_date.weekday())
    running_cash = current_cash

    for i, week in enumerate(weeks):
        ws = week["week_start"]
        we = week["week_end"]

        additional_out = ZERO
        for event in scenario_events:
            if ws <= event["date"] <= we:
                if event["direction"] == "out":
                    additional_out += event["amount"]

        new_outflows = week["expected_outflows"] + additional_out
        new_closing = week["opening_cash"] + week["expected_inflows"] - new_outflows

        weeks[i] = {
            **week,
            "expected_outflows": new_outflows,
            "closing_cash": new_closing,
            "below_reserve": new_closing < minimum_reserve,
            "scenario_additional_outflow": additional_out,
        }

        # Propagate cash forward
        if i + 1 < len(weeks):
            weeks[i + 1] = {**weeks[i + 1], "opening_cash": new_closing}

    return weeks
