from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user, get_current_active_business
from app.models.user import User
from app.models.transaction import Transaction
from app.services.reconciliation import auto_reconcile, manually_match

router = APIRouter()


@router.get("/transactions")
def list_transactions(
    status: str | None = Query(default=None),
    from_date: date | None = None,
    to_date: date | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    q = db.query(Transaction).filter(Transaction.business_id == business.id)
    if status:
        q = q.filter(Transaction.reconciliation_status == status)
    if from_date:
        q = q.filter(Transaction.transaction_date >= from_date)
    if to_date:
        q = q.filter(Transaction.transaction_date <= to_date)
    return q.order_by(Transaction.transaction_date.desc()).all()


@router.post("/auto-match")
def trigger_auto_reconcile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run automatic transaction matching."""
    business = get_current_active_business(None, current_user, db)
    result = auto_reconcile(db, business)
    return result


@router.post("/match")
def manual_match(
    transaction_id: str,
    commitment_id: str | None = None,
    receivable_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually match a transaction to a commitment or receivable."""
    business = get_current_active_business(None, current_user, db)
    if not commitment_id and not receivable_id:
        raise HTTPException(status_code=400, detail="Provide commitment_id or receivable_id")
    
    result = manually_match(db, business, transaction_id, commitment_id, receivable_id)
    return result
