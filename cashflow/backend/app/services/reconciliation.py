"""
Reconciliation Engine
=====================

Matches actual bank transactions against expected commitments and receivables.

Rules:
- Expected vs actual amount → variance tracked
- Expected vs actual date → date variance tracked
- Original forecast preserved — only variance fields updated
- Deduplication via external_id + source (idempotent re-sync)
- Matched items prevent double counting
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.commitment import Commitment, CommitmentStatus
from app.models.receivable import Receivable, ReceivableStatus, ReceivablePayment
from app.models.transaction import Transaction

ZERO = Decimal("0.00")
DATE_TOLERANCE_DAYS = 7   # Match if dates are within 7 days
AMOUNT_TOLERANCE_PCT = Decimal("0.05")  # 5% amount tolerance for fuzzy match


def auto_reconcile(db: Session, business: Business) -> dict:
    """
    Run automatic matching for unmatched transactions.
    
    Returns summary of what was matched.
    """
    unmatched_txs = (
        db.query(Transaction)
        .filter(
            Transaction.business_id == business.id,
            Transaction.reconciliation_status == "unmatched",
            Transaction.is_pending == False,
        )
        .order_by(Transaction.transaction_date)
        .all()
    )

    matched_count = 0
    unmatched_remaining = 0

    for tx in unmatched_txs:
        matched = False

        if tx.amount > ZERO:
            # Inflow — try to match against receivables
            matched = _match_receivable(db, business, tx)
        else:
            # Outflow — try to match against commitments
            matched = _match_commitment(db, business, tx)

        if matched:
            matched_count += 1
        else:
            unmatched_remaining += 1

    db.commit()
    return {
        "matched": matched_count,
        "unmatched": unmatched_remaining,
        "total_processed": len(unmatched_txs),
    }


def _match_receivable(db: Session, business: Business, tx: Transaction) -> bool:
    """Try to match a credit transaction against an open receivable."""
    tx_amount = abs(tx.amount)
    tx_date = tx.transaction_date

    candidates = (
        db.query(Receivable)
        .filter(
            Receivable.business_id == business.id,
            Receivable.status.in_([ReceivableStatus.EXPECTED, ReceivableStatus.OVERDUE, ReceivableStatus.PARTIALLY_RECEIVED]),
            Receivable.matched_transaction_id == None,
        )
        .all()
    )

    best_match: Optional[Receivable] = None
    best_score = Decimal("-1")

    for r in candidates:
        remaining = r.remaining_amount
        if remaining <= ZERO:
            continue

        # Date score
        date_delta = abs((tx_date - r.expected_date).days)
        if date_delta > DATE_TOLERANCE_DAYS * 3:
            continue

        # Amount match — allow partial payments (tx smaller than remaining)
        # Skip only if tx is larger than remaining by >20% (possible duplicate / wrong match)
        if tx_amount > remaining * Decimal("1.20"):
            continue
        amount_diff_pct = abs(tx_amount - remaining) / max(remaining, Decimal("1"))
        score = Decimal("1") - amount_diff_pct - Decimal(str(date_delta)) * Decimal("0.01")
        if score > best_score:
            best_score = score
            best_match = r

    if best_match:
        _apply_receivable_match(db, best_match, tx)
        return True
    return False


def _match_commitment(db: Session, business: Business, tx: Transaction) -> bool:
    """Try to match a debit transaction against a pending commitment."""
    tx_amount = abs(tx.amount)
    tx_date = tx.transaction_date

    candidates = (
        db.query(Commitment)
        .filter(
            Commitment.business_id == business.id,
            Commitment.status.in_([CommitmentStatus.SCHEDULED, CommitmentStatus.OVERDUE, CommitmentStatus.PARTIALLY_PAID]),
            Commitment.matched_transaction_id == None,
        )
        .all()
    )

    best_match: Optional[Commitment] = None
    best_score = Decimal("-1")

    for c in candidates:
        remaining = c.remaining_amount
        if remaining <= ZERO:
            continue

        date_delta = abs((tx_date - c.due_date).days)
        if date_delta > DATE_TOLERANCE_DAYS * 4:
            continue

        amount_diff_pct = abs(tx_amount - remaining) / max(remaining, Decimal("1"))
        if amount_diff_pct > Decimal("0.20"):
            continue

        score = Decimal("1") - amount_diff_pct - Decimal(str(date_delta)) * Decimal("0.01")
        if score > best_score:
            best_score = score
            best_match = c

    if best_match:
        _apply_commitment_match(db, best_match, tx)
        return True
    return False


def _apply_receivable_match(db: Session, receivable: Receivable, tx: Transaction) -> None:
    """Apply a transaction match to a receivable."""
    tx_amount = abs(tx.amount)

    # Record partial payment
    payment = ReceivablePayment(
        receivable_id=receivable.id,
        amount=tx_amount,
        received_date=tx.transaction_date,
        transaction_id=tx.id,
    )
    db.add(payment)

    receivable.amount_received += tx_amount
    if receivable.amount_received >= receivable.amount:
        receivable.status = ReceivableStatus.RECEIVED
        receivable.received_date = tx.transaction_date
    else:
        receivable.status = ReceivableStatus.PARTIALLY_RECEIVED

    receivable.matched_transaction_id = tx.id
    from datetime import datetime, timezone
    receivable.reconciled_at = datetime.now(timezone.utc)

    tx.reconciliation_status = "matched"
    db.add(receivable)
    db.add(tx)


def _apply_commitment_match(db: Session, commitment: Commitment, tx: Transaction) -> None:
    """Apply a transaction match to a commitment."""
    tx_amount = abs(tx.amount)

    commitment.amount_paid += tx_amount
    if commitment.amount_paid >= commitment.amount:
        commitment.status = CommitmentStatus.PAID
        commitment.paid_date = tx.transaction_date
    else:
        commitment.status = CommitmentStatus.PARTIALLY_PAID

    commitment.reconciled_amount = tx_amount
    commitment.matched_transaction_id = tx.id
    from datetime import datetime, timezone
    commitment.reconciled_at = datetime.now(timezone.utc)

    tx.reconciliation_status = "matched"
    db.add(commitment)
    db.add(tx)


def manually_match(
    db: Session,
    business: Business,
    transaction_id: str,
    commitment_id: str | None = None,
    receivable_id: str | None = None,
) -> dict:
    """Manually link a transaction to a commitment or receivable."""
    import uuid
    tx = db.query(Transaction).filter(
        Transaction.id == uuid.UUID(transaction_id),
        Transaction.business_id == business.id,
    ).first()
    if not tx:
        raise ValueError("Transaction not found")

    if commitment_id:
        c = db.query(Commitment).filter(
            Commitment.id == uuid.UUID(commitment_id),
            Commitment.business_id == business.id,
        ).first()
        if not c:
            raise ValueError("Commitment not found")
        _apply_commitment_match(db, c, tx)
        db.commit()
        return {"matched": "commitment", "id": commitment_id}

    if receivable_id:
        r = db.query(Receivable).filter(
            Receivable.id == uuid.UUID(receivable_id),
            Receivable.business_id == business.id,
        ).first()
        if not r:
            raise ValueError("Receivable not found")
        _apply_receivable_match(db, r, tx)
        db.commit()
        return {"matched": "receivable", "id": receivable_id}

    raise ValueError("Must provide commitment_id or receivable_id")


def upsert_transaction(
    db: Session,
    business_id,
    external_id: str,
    external_source: str,
    **kwargs,
) -> tuple[Transaction, bool]:
    """Idempotent transaction upsert — prevents double-import."""
    existing = db.query(Transaction).filter(
        Transaction.external_id == external_id,
        Transaction.external_source == external_source,
    ).first()

    if existing:
        return existing, False  # Already exists

    tx = Transaction(
        business_id=business_id,
        external_id=external_id,
        external_source=external_source,
        **kwargs,
    )
    db.add(tx)
    db.flush()
    return tx, True  # New
