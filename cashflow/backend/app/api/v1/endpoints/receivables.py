from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user, get_current_active_business
from app.models.user import User
from app.models.receivable import Receivable, ReceivablePayment, ReceivableStatus
from app.schemas.receivable import (
    ReceivableCreate,
    ReceivableUpdate,
    ReceivableResponse,
    ReceivablePaymentCreate,
)

router = APIRouter()


@router.get("", response_model=list[ReceivableResponse])
def list_receivables(
    status: ReceivableStatus | None = None,
    overdue_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    q = db.query(Receivable).filter(Receivable.business_id == business.id)
    if status:
        q = q.filter(Receivable.status == status)
    if overdue_only:
        q = q.filter(
            Receivable.expected_date < date.today(),
            Receivable.status != ReceivableStatus.RECEIVED,
        )
    return q.order_by(Receivable.expected_date).all()


@router.post("", response_model=ReceivableResponse, status_code=201)
def create_receivable(
    receivable_in: ReceivableCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    r = Receivable(
        business_id=business.id,
        name=receivable_in.name,
        description=receivable_in.description,
        receivable_type=receivable_in.receivable_type,
        customer_name=receivable_in.customer_name,
        invoice_number=receivable_in.invoice_number,
        amount=receivable_in.amount,
        expected_date=receivable_in.expected_date,
        invoice_date=receivable_in.invoice_date,
        currency=receivable_in.currency,
        confidence_level=receivable_in.confidence_level,
        notes=receivable_in.notes,
        status=(
            ReceivableStatus.OVERDUE
            if receivable_in.expected_date < date.today()
            else ReceivableStatus.EXPECTED
        ),
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.get("/{receivable_id}", response_model=ReceivableResponse)
def get_receivable(
    receivable_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    r = db.query(Receivable).filter(
        Receivable.id == uuid.UUID(receivable_id),
        Receivable.business_id == business.id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Receivable not found")
    return r


@router.patch("/{receivable_id}", response_model=ReceivableResponse)
def update_receivable(
    receivable_id: str,
    receivable_in: ReceivableUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    r = db.query(Receivable).filter(
        Receivable.id == uuid.UUID(receivable_id),
        Receivable.business_id == business.id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Receivable not found")
    
    for field, value in receivable_in.model_dump(exclude_unset=True).items():
        setattr(r, field, value)
    
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.post("/{receivable_id}/payments", response_model=ReceivableResponse)
def record_payment(
    receivable_id: str,
    payment_in: ReceivablePaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record a partial or full payment against a receivable."""
    business = get_current_active_business(None, current_user, db)
    r = db.query(Receivable).filter(
        Receivable.id == uuid.UUID(receivable_id),
        Receivable.business_id == business.id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Receivable not found")
    
    payment = ReceivablePayment(
        receivable_id=r.id,
        amount=payment_in.amount,
        received_date=payment_in.received_date,
        notes=payment_in.notes,
    )
    db.add(payment)
    
    r.amount_received += payment_in.amount
    if r.amount_received >= r.amount:
        r.status = ReceivableStatus.RECEIVED
        r.received_date = payment_in.received_date
    else:
        r.status = ReceivableStatus.PARTIALLY_RECEIVED
    
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.delete("/{receivable_id}", status_code=204)
def delete_receivable(
    receivable_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    r = db.query(Receivable).filter(
        Receivable.id == uuid.UUID(receivable_id),
        Receivable.business_id == business.id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Receivable not found")
    db.delete(r)
    db.commit()
