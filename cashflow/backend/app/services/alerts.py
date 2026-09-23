"""
Alerts Engine
=============

Generates alerts based on the current financial state.
All alerts are rule-based — no hard-coded numbers.
Alerts are deduplicated via fingerprints.
"""

import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertType, AlertSeverity
from app.models.business import Business
from app.models.commitment import Commitment, CommitmentStatus
from app.models.receivable import Receivable, ReceivableStatus
from app.models.credit_card import CreditCard, CreditCardStatement
from app.services.safe_to_spend import calculate_safe_to_spend

ZERO = Decimal("0.00")


def generate_alerts(db: Session, business: Business) -> list[Alert]:
    """Run all alert rules and return newly created alerts."""
    today = date.today()
    new_alerts: list[Alert] = []

    s2s = calculate_safe_to_spend(db, business, as_of_date=today, horizon_weeks=13)

    # 1. Cash cliff
    if s2s.has_cash_cliff:
        new_alerts.append(_make_alert(
            db, business,
            alert_type=AlertType.CASH_CLIFF,
            severity=AlertSeverity.CRITICAL,
            title="Cash Cliff Detected",
            message=(
                f"Your projected cash will drop to ${s2s.cash_cliff_amount:,.2f} below your minimum "
                f"reserve around {s2s.cash_cliff_date.strftime('%B %d').lstrip('0').replace(' 0', ' ')}."
            ),
            related_amount=s2s.cash_cliff_amount,
            related_date=s2s.cash_cliff_date,
            fingerprint=_fp("cash_cliff", str(business.id), str(s2s.cash_cliff_date)),
        ))

    # 2. Reserve violation (current cash already below reserve)
    if s2s.current_cash < business.minimum_cash_reserve and business.minimum_cash_reserve > ZERO:
        shortage = business.minimum_cash_reserve - s2s.current_cash
        new_alerts.append(_make_alert(
            db, business,
            alert_type=AlertType.RESERVE_VIOLATION,
            severity=AlertSeverity.CRITICAL,
            title="Cash Below Minimum Reserve",
            message=(
                f"Current cash ${s2s.current_cash:,.2f} is ${shortage:,.2f} below your "
                f"minimum reserve of ${business.minimum_cash_reserve:,.2f}."
            ),
            related_amount=shortage,
            related_date=today,
            fingerprint=_fp("reserve_violation", str(business.id), str(today)),
        ))

    # 3. Future cash shortfall (any forecast week below reserve)
    for week in s2s.weeks:
        if week["below_reserve"]:
            ws = week["week_start"]
            new_alerts.append(_make_alert(
                db, business,
                alert_type=AlertType.FUTURE_CASH_SHORTFALL,
                severity=AlertSeverity.HIGH,
                title=f"Projected Cash Shortfall Week of {ws.strftime('%B %d').lstrip('0').replace(' 0', ' ')}",
                message=(
                    f"Cash is projected to be ${week['closing_cash']:,.2f} for the week of "
                    f"{ws.strftime('%B %d').lstrip('0').replace(' 0', ' ')} — ${(business.minimum_cash_reserve - week['closing_cash']):,.2f} "
                    f"below your minimum reserve."
                ),
                related_amount=week["closing_cash"],
                related_date=ws,
                fingerprint=_fp("shortfall", str(business.id), str(ws)),
            ))

    # 4. Overdue commitments
    overdue = (
        db.query(Commitment)
        .filter(
            Commitment.business_id == business.id,
            Commitment.status == CommitmentStatus.OVERDUE,
        )
        .all()
    )
    for c in overdue:
        days_overdue = (today - c.due_date).days
        new_alerts.append(_make_alert(
            db, business,
            alert_type=AlertType.OVERDUE_COMMITMENT,
            severity=AlertSeverity.HIGH if days_overdue <= 7 else AlertSeverity.CRITICAL,
            title=f"Overdue: {c.name}",
            message=f"{c.name} of ${c.remaining_amount:,.2f} was due {days_overdue} day(s) ago.",
            related_amount=c.remaining_amount,
            related_date=c.due_date,
            commitment_id=c.id,
            fingerprint=_fp("overdue_commitment", str(c.id)),
        ))

    # 5. Overdue A/R
    overdue_ar = (
        db.query(Receivable)
        .filter(
            Receivable.business_id == business.id,
            Receivable.status.in_([ReceivableStatus.OVERDUE, ReceivableStatus.EXPECTED]),
            Receivable.expected_date < today,
        )
        .all()
    )
    for r in overdue_ar:
        days_overdue = (today - r.expected_date).days
        new_alerts.append(_make_alert(
            db, business,
            alert_type=AlertType.OVERDUE_AR,
            severity=AlertSeverity.HIGH,
            title=f"Overdue Invoice: {r.name}",
            message=(
                f"Invoice from {r.customer_name or 'unknown'} for ${r.remaining_amount:,.2f} "
                f"was expected {days_overdue} day(s) ago."
            ),
            related_amount=r.remaining_amount,
            related_date=r.expected_date,
            receivable_id=r.id,
            fingerprint=_fp("overdue_ar", str(r.id), str(today.toordinal() // 3)),
        ))

    # 6. Upcoming large commitments (> 10% of current cash, due in 7 days)
    large_threshold = max(s2s.current_cash * Decimal("0.10"), Decimal("5000.00"))
    upcoming = (
        db.query(Commitment)
        .filter(
            Commitment.business_id == business.id,
            Commitment.status == CommitmentStatus.SCHEDULED,
            Commitment.due_date.between(today, today + timedelta(days=7)),
            Commitment.amount >= large_threshold,
        )
        .all()
    )
    for c in upcoming:
        new_alerts.append(_make_alert(
            db, business,
            alert_type=AlertType.UPCOMING_LARGE_COMMITMENT,
            severity=AlertSeverity.MEDIUM,
            title=f"Large Payment Due: {c.name}",
            message=f"{c.name} of ${c.amount:,.2f} is due on {c.due_date.strftime('%B %d').lstrip('0').replace(' 0', ' ')}.",
            related_amount=c.amount,
            related_date=c.due_date,
            commitment_id=c.id,
            fingerprint=_fp("large_commitment", str(c.id)),
        ))

    # 7. Credit card payments due in 5 days
    cc_statements = (
        db.query(CreditCardStatement)
        .join(CreditCard)
        .filter(
            CreditCard.business_id == business.id,
            CreditCardStatement.is_paid == False,
            CreditCardStatement.due_date.between(today, today + timedelta(days=5)),
        )
        .all()
    )
    for stmt in cc_statements:
        days_until = (stmt.due_date - today).days
        new_alerts.append(_make_alert(
            db, business,
            alert_type=AlertType.CREDIT_CARD_PAYMENT_DUE,
            severity=AlertSeverity.HIGH if days_until <= 2 else AlertSeverity.MEDIUM,
            title=f"Credit Card Payment Due: {stmt.credit_card.name}",
            message=(
                f"Statement balance of ${stmt.statement_balance:,.2f} for {stmt.credit_card.name} "
                f"is due in {days_until} day(s) on {stmt.due_date.strftime('%B %d').lstrip('0').replace(' 0', ' ')}."
            ),
            related_amount=stmt.statement_balance,
            related_date=stmt.due_date,
            credit_card_id=stmt.credit_card_id,
            fingerprint=_fp("cc_payment", str(stmt.id)),
        ))

    # 8. Unverified assumptions (low-confidence items)
    unverified = (
        db.query(Commitment)
        .filter(
            Commitment.business_id == business.id,
            Commitment.is_verified == False,
            Commitment.confidence_level.in_(["low", "uncertain"]),
            Commitment.status == CommitmentStatus.SCHEDULED,
        )
        .count()
    )
    if unverified > 0:
        new_alerts.append(_make_alert(
            db, business,
            alert_type=AlertType.UNVERIFIED_ASSUMPTIONS,
            severity=AlertSeverity.LOW,
            title=f"{unverified} Unverified Commitment(s)",
            message=f"You have {unverified} commitment(s) with uncertain amounts or dates that need review.",
            fingerprint=_fp("unverified", str(business.id), str(today)),
        ))

    db.commit()
    return new_alerts


def _fp(*parts: str) -> str:
    """Create a deduplication fingerprint."""
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _make_alert(
    db: Session,
    business: Business,
    *,
    alert_type: AlertType,
    severity: AlertSeverity,
    title: str,
    message: str,
    related_amount: Decimal | None = None,
    related_date: date | None = None,
    commitment_id=None,
    receivable_id=None,
    credit_card_id=None,
    fingerprint: str | None = None,
    metadata: dict | None = None,
) -> Alert | None:
    """Create an alert, skipping if already exists (deduplication)."""
    if fingerprint:
        existing = db.query(Alert).filter(
            Alert.business_id == business.id,
            Alert.fingerprint == fingerprint,
            Alert.is_dismissed == False,
        ).first()
        if existing:
            return existing  # Already fired

    alert = Alert(
        business_id=business.id,
        alert_type=alert_type,
        severity=severity,
        title=title,
        message=message,
        related_amount=related_amount,
        related_date=related_date,
        commitment_id=commitment_id,
        receivable_id=receivable_id,
        credit_card_id=credit_card_id,
        fingerprint=fingerprint,
        metadata_json=metadata or {},
    )
    db.add(alert)
    return alert




