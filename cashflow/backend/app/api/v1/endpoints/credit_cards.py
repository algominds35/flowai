"""
Credit Card endpoints.

Key rule enforced here:
  - Recording a CC transaction does NOT touch bank cash.
  - Bank cash only decreases when a statement is paid.
  - Each new statement automatically creates a Commitment due on the payment due date.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, timedelta
from decimal import Decimal
import uuid
import calendar

from app.db.session import get_db
from app.core.deps import get_current_user, get_current_active_business
from app.models.user import User
from app.models.credit_card import CreditCard, CreditCardTransaction, CreditCardStatement
from app.models.commitment import Commitment, CommitmentCategory, CommitmentStatus
from app.schemas.credit_card import (
    CreditCardCreate,
    CreditCardUpdate,
    CreditCardResponse,
    CreditCardTransactionResponse,
    CreditCardStatementResponse,
)

router = APIRouter()


@router.get("", response_model=list[CreditCardResponse])
def list_credit_cards(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    return db.query(CreditCard).filter(
        CreditCard.business_id == business.id,
        CreditCard.is_active == True,
    ).all()


@router.post("", response_model=CreditCardResponse, status_code=201)
def create_credit_card(
    card_in: CreditCardCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    card = CreditCard(
        business_id=business.id,
        name=card_in.name,
        last_four=card_in.last_four,
        card_network=card_in.card_network,
        issuing_bank=card_in.issuing_bank,
        statement_closing_day=card_in.statement_closing_day,
        payment_due_days=card_in.payment_due_days,
        credit_limit=card_in.credit_limit,
        current_balance=card_in.current_balance,
        payment_cash_account_id=card_in.payment_cash_account_id,
    )
    db.add(card)
    db.commit()
    db.refresh(card)

    # If there's an existing balance, create a commitment for it
    if card_in.current_balance and card_in.current_balance > Decimal("0"):
        _create_statement_commitment(db, card, card_in.current_balance, date.today())

    return card


@router.post("/{card_id}/transactions", response_model=CreditCardTransactionResponse, status_code=201)
def add_cc_transaction(
    card_id: str,
    transaction_date: date,
    description: str,
    amount: Decimal,
    merchant_name: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Record a credit card purchase.
    
    IMPORTANT: This does NOT reduce bank cash. Bank cash only
    reduces when the statement is paid via mark_statement_paid().
    The balance accumulates on the card's current_balance.
    """
    business = get_current_active_business(None, current_user, db)
    card = _get_card(db, card_id, business)

    # Find or create current statement
    stmt = _get_or_create_current_statement(db, card, transaction_date)

    tx = CreditCardTransaction(
        credit_card_id=card.id,
        transaction_date=transaction_date,
        description=description,
        amount=amount,  # positive = charge
        merchant_name=merchant_name,
        statement_id=stmt.id,
    )
    db.add(tx)

    # Update card balance
    card.current_balance += amount
    db.add(card)

    # Update statement balance
    stmt.statement_balance += amount
    db.add(stmt)

    db.commit()
    db.refresh(tx)
    return tx


@router.post("/{card_id}/statements/{statement_id}/close", response_model=CreditCardStatementResponse)
def close_statement(
    card_id: str,
    statement_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Close a statement and create a Commitment for the due date.
    This is when the card balance becomes a scheduled cash outflow.
    """
    business = get_current_active_business(None, current_user, db)
    card = _get_card(db, card_id, business)
    stmt = db.query(CreditCardStatement).filter(
        CreditCardStatement.id == uuid.UUID(statement_id),
        CreditCardStatement.credit_card_id == card.id,
    ).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")

    # Create commitment for the payment
    commitment = _create_statement_commitment(db, card, stmt.statement_balance, stmt.due_date)
    stmt.commitment_id = commitment.id
    db.add(stmt)
    db.commit()
    db.refresh(stmt)
    return stmt


@router.post("/{card_id}/statements/{statement_id}/pay", response_model=CreditCardStatementResponse)
def mark_statement_paid(
    card_id: str,
    statement_id: str,
    paid_amount: Decimal,
    paid_date: date | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Mark a statement as paid.
    THIS is when bank cash decreases (not when purchases were made).
    """
    business = get_current_active_business(None, current_user, db)
    card = _get_card(db, card_id, business)
    stmt = db.query(CreditCardStatement).filter(
        CreditCardStatement.id == uuid.UUID(statement_id),
        CreditCardStatement.credit_card_id == card.id,
    ).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")

    actual_date = paid_date or date.today()
    stmt.is_paid = True
    stmt.paid_date = actual_date
    stmt.paid_amount = paid_amount
    db.add(stmt)

    # Reduce card's outstanding balance
    card.current_balance -= paid_amount
    db.add(card)

    # Mark linked commitment as paid
    if stmt.commitment_id:
        c = db.query(Commitment).filter(Commitment.id == stmt.commitment_id).first()
        if c:
            c.status = CommitmentStatus.PAID
            c.amount_paid = paid_amount
            c.paid_date = actual_date
            db.add(c)

    db.commit()
    db.refresh(stmt)
    return stmt


@router.get("/{card_id}/statements", response_model=list[CreditCardStatementResponse])
def list_statements(
    card_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    card = _get_card(db, card_id, business)
    return db.query(CreditCardStatement).filter(
        CreditCardStatement.credit_card_id == card.id,
    ).order_by(CreditCardStatement.due_date.desc()).all()


@router.get("/{card_id}/transactions", response_model=list[CreditCardTransactionResponse])
def list_cc_transactions(
    card_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    card = _get_card(db, card_id, business)
    return db.query(CreditCardTransaction).filter(
        CreditCardTransaction.credit_card_id == card.id,
    ).order_by(CreditCardTransaction.transaction_date.desc()).all()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_card(db, card_id: str, business) -> CreditCard:
    card = db.query(CreditCard).filter(
        CreditCard.id == uuid.UUID(card_id),
        CreditCard.business_id == business.id,
    ).first()
    if not card:
        raise HTTPException(status_code=404, detail="Credit card not found")
    return card


def _get_or_create_current_statement(
    db: Session, card: CreditCard, tx_date: date
) -> CreditCardStatement:
    """Get the open statement for the given date, or create one."""
    # Find statement that covers this date
    stmt = db.query(CreditCardStatement).filter(
        CreditCardStatement.credit_card_id == card.id,
        CreditCardStatement.period_start <= tx_date,
        CreditCardStatement.period_end >= tx_date,
    ).first()

    if stmt:
        return stmt

    # Create new statement period
    if card.statement_closing_day:
        # Calculate statement period based on closing day
        if tx_date.day <= card.statement_closing_day:
            # Statement closes this month
            period_end = tx_date.replace(day=card.statement_closing_day)
            # Period start = day after last close
            if period_end.month == 1:
                last_month = 12
                last_year = period_end.year - 1
            else:
                last_month = period_end.month - 1
                last_year = period_end.year
            last_close_day = min(card.statement_closing_day, calendar.monthrange(last_year, last_month)[1])
            period_start = date(last_year, last_month, last_close_day) + timedelta(days=1)
        else:
            # Statement closes next month
            next_month = tx_date.month + 1 if tx_date.month < 12 else 1
            next_year = tx_date.year if tx_date.month < 12 else tx_date.year + 1
            close_day = min(card.statement_closing_day, calendar.monthrange(next_year, next_month)[1])
            period_end = date(next_year, next_month, close_day)
            period_start = tx_date.replace(day=card.statement_closing_day + 1)
    else:
        # No closing day set — use monthly periods
        period_start = tx_date.replace(day=1)
        period_end = tx_date.replace(day=calendar.monthrange(tx_date.year, tx_date.month)[1])

    due_date = period_end + timedelta(days=card.payment_due_days)

    stmt = CreditCardStatement(
        credit_card_id=card.id,
        period_start=period_start,
        period_end=period_end,
        due_date=due_date,
        statement_balance=Decimal("0.00"),
    )
    db.add(stmt)
    db.flush()
    return stmt


def _create_statement_commitment(
    db: Session, card: CreditCard, amount: Decimal, due_date: date
) -> Commitment:
    """Create a Commitment for a credit card statement payment."""
    commitment = Commitment(
        business_id=card.business_id,
        name=f"Credit Card Payment: {card.name}",
        category=CommitmentCategory.CREDIT_CARD_PAYMENT,
        amount=amount,
        due_date=due_date,
        credit_card_id=card.id,
        status=CommitmentStatus.OVERDUE if due_date < date.today() else CommitmentStatus.SCHEDULED,
        confidence_level="high",
        is_verified=True,
    )
    db.add(commitment)
    db.flush()
    return commitment
