"""
Weekly Review Service
=====================

Surfaces uncertain, overdue, and missing items for human review.
Generates a WeeklyReviewSession with WeeklyReviewItems that need attention.
"""

from datetime import date, timedelta, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.commitment import Commitment, CommitmentStatus
from app.models.receivable import Receivable, ReceivableStatus
from app.models.transaction import Transaction
from app.models.weekly_review import WeeklyReviewSession, WeeklyReviewItem

ZERO = Decimal("0.00")


def create_weekly_review(db: Session, business: Business) -> WeeklyReviewSession:
    """Create a new weekly review session with items that need attention."""
    today = date.today()
    # Week starts Monday
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    # Check for existing open session this week
    existing = (
        db.query(WeeklyReviewSession)
        .filter(
            WeeklyReviewSession.business_id == business.id,
            WeeklyReviewSession.week_start == week_start,
            WeeklyReviewSession.status != "completed",
        )
        .first()
    )
    if existing:
        return existing

    session = WeeklyReviewSession(
        business_id=business.id,
        week_start=week_start,
        week_end=week_end,
        status="pending",
    )
    db.add(session)
    db.flush()

    items = []

    # ── 1. Uncertain/unverified commitments ───────────────────────────────────
    uncertain_commitments = (
        db.query(Commitment)
        .filter(
            Commitment.business_id == business.id,
            Commitment.is_verified == False,
            Commitment.confidence_level.in_(["low", "uncertain"]),
            Commitment.status.in_([CommitmentStatus.SCHEDULED, CommitmentStatus.OVERDUE]),
        )
        .all()
    )
    for c in uncertain_commitments:
        items.append(WeeklyReviewItem(
            session_id=session.id,
            item_type="uncertain_commitment",
            title=f"Confirm: {c.name}",
            description=f"${c.amount:,.2f} due {c.due_date} — amount/date uncertain",
            commitment_id=c.id,
            original_amount=c.amount,
            original_date=c.due_date,
            status="pending",
        ))

    # ── 2. Overdue commitments ─────────────────────────────────────────────────
    overdue_commitments = (
        db.query(Commitment)
        .filter(
            Commitment.business_id == business.id,
            Commitment.status == CommitmentStatus.OVERDUE,
        )
        .all()
    )
    for c in overdue_commitments:
        days_late = (today - c.due_date).days
        items.append(WeeklyReviewItem(
            session_id=session.id,
            item_type="overdue",
            title=f"Overdue Payment: {c.name}",
            description=f"${c.remaining_amount:,.2f} was due {days_late} day(s) ago on {c.due_date}",
            commitment_id=c.id,
            original_amount=c.amount,
            original_date=c.due_date,
            status="pending",
        ))

    # ── 3. Overdue receivables ─────────────────────────────────────────────────
    overdue_ar = (
        db.query(Receivable)
        .filter(
            Receivable.business_id == business.id,
            Receivable.status.in_([ReceivableStatus.EXPECTED, ReceivableStatus.OVERDUE]),
            Receivable.expected_date < today,
        )
        .all()
    )
    for r in overdue_ar:
        days_late = (today - r.expected_date).days
        items.append(WeeklyReviewItem(
            session_id=session.id,
            item_type="overdue",
            title=f"Expected Receipt Not Arrived: {r.name}",
            description=f"${r.remaining_amount:,.2f} from {r.customer_name or 'unknown'} was expected {days_late} day(s) ago",
            receivable_id=r.id,
            original_amount=r.amount,
            original_date=r.expected_date,
            status="pending",
        ))

    # ── 4. Unmatched transactions from the past week ──────────────────────────
    unmatched_txs = (
        db.query(Transaction)
        .filter(
            Transaction.business_id == business.id,
            Transaction.reconciliation_status == "unmatched",
            Transaction.transaction_date >= today - timedelta(days=14),
            Transaction.is_pending == False,
        )
        .all()
    )
    for tx in unmatched_txs:
        direction = "in" if tx.amount > ZERO else "out"
        items.append(WeeklyReviewItem(
            session_id=session.id,
            item_type="unmatched_transaction",
            title=f"Unmatched Transaction: {tx.description}",
            description=f"${abs(tx.amount):,.2f} {direction} on {tx.transaction_date} — not matched to any commitment/receivable",
            transaction_id=tx.id,
            original_amount=abs(tx.amount),
            original_date=tx.transaction_date,
            status="pending",
        ))

    # ── 5. Large upcoming commitments next week ────────────────────────────────
    next_week_start = today + timedelta(days=7)
    next_week_end = next_week_start + timedelta(days=6)
    large_upcoming = (
        db.query(Commitment)
        .filter(
            Commitment.business_id == business.id,
            Commitment.status == CommitmentStatus.SCHEDULED,
            Commitment.due_date.between(next_week_start, next_week_end),
            Commitment.amount >= Decimal("5000"),
        )
        .all()
    )
    for c in large_upcoming:
        items.append(WeeklyReviewItem(
            session_id=session.id,
            item_type="confirm_amount",
            title=f"Confirm Large Upcoming Payment: {c.name}",
            description=f"${c.amount:,.2f} due next week on {c.due_date} — please confirm",
            commitment_id=c.id,
            original_amount=c.amount,
            original_date=c.due_date,
            status="pending",
        ))

    for item in items:
        db.add(item)

    db.commit()
    db.refresh(session)
    return session


def action_review_item(
    db: Session,
    item: WeeklyReviewItem,
    action: str,
    confirmed_amount: Decimal | None = None,
    confirmed_date: date | None = None,
    match_transaction_id=None,
    user_id=None,
) -> WeeklyReviewItem:
    """Apply a user action to a review item."""
    item.action = action
    item.confirmed_amount = confirmed_amount
    item.confirmed_date = confirmed_date
    item.match_transaction_id = match_transaction_id
    item.status = "actioned"
    item.actioned_at = datetime.now(timezone.utc)
    item.actioned_by_user_id = user_id

    # Apply the action to the underlying entity
    if action == "confirm" and item.commitment_id:
        c = db.query(Commitment).get(item.commitment_id)
        if c:
            c.is_verified = True
            c.confidence_level = "high"
            if confirmed_amount:
                c.amount = confirmed_amount
            if confirmed_date:
                c.due_date = confirmed_date
            db.add(c)

    elif action == "confirm" and item.receivable_id:
        r = db.query(Receivable).get(item.receivable_id)
        if r:
            r.is_verified = True
            if confirmed_amount:
                r.amount = confirmed_amount
            if confirmed_date:
                r.expected_date = confirmed_date
            db.add(r)

    elif action == "mark_uncertain":
        if item.commitment_id:
            c = db.query(Commitment).get(item.commitment_id)
            if c:
                c.confidence_level = "uncertain"
                db.add(c)
        if item.receivable_id:
            r = db.query(Receivable).get(item.receivable_id)
            if r:
                r.confidence_level = "uncertain"
                db.add(r)

    elif action == "ignore" and item.transaction_id:
        tx = db.query(Transaction).get(item.transaction_id)
        if tx:
            tx.reconciliation_status = "ignored"
            db.add(tx)

    db.add(item)
    db.commit()
    db.refresh(item)
    return item
