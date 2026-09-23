from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, timedelta
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user, get_current_active_business
from app.models.user import User
from app.models.commitment import Commitment, CommitmentStatus, CommitmentCategory, RecurringFrequency
from app.schemas.commitment import CommitmentCreate, CommitmentUpdate, CommitmentResponse

router = APIRouter()


@router.get("", response_model=list[CommitmentResponse])
def list_commitments(
    status: CommitmentStatus | None = None,
    category: CommitmentCategory | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    overdue_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    q = db.query(Commitment).filter(Commitment.business_id == business.id)
    
    if status:
        q = q.filter(Commitment.status == status)
    if category:
        q = q.filter(Commitment.category == category)
    if from_date:
        q = q.filter(Commitment.due_date >= from_date)
    if to_date:
        q = q.filter(Commitment.due_date <= to_date)
    if overdue_only:
        q = q.filter(Commitment.due_date < date.today(), Commitment.status != CommitmentStatus.PAID)
    
    return q.order_by(Commitment.due_date).all()


@router.post("", response_model=CommitmentResponse, status_code=201)
def create_commitment(
    commitment_in: CommitmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    
    commitment = Commitment(
        business_id=business.id,
        name=commitment_in.name,
        description=commitment_in.description,
        category=commitment_in.category,
        vendor_name=commitment_in.vendor_name,
        amount=commitment_in.amount,
        due_date=commitment_in.due_date,
        currency=commitment_in.currency,
        confidence_level=commitment_in.confidence_level,
        is_recurring=commitment_in.is_recurring,
        recurring_frequency=commitment_in.recurring_frequency,
        recurring_day_of_month=commitment_in.recurring_day_of_month,
        recurring_end_date=commitment_in.recurring_end_date,
        notes=commitment_in.notes,
        tags=commitment_in.tags,
        credit_card_id=commitment_in.credit_card_id,
        status=(
            CommitmentStatus.OVERDUE
            if commitment_in.due_date < date.today()
            else CommitmentStatus.SCHEDULED
        ),
    )
    db.add(commitment)
    db.commit()
    db.refresh(commitment)
    return commitment


@router.get("/{commitment_id}", response_model=CommitmentResponse)
def get_commitment(
    commitment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    c = db.query(Commitment).filter(
        Commitment.id == uuid.UUID(commitment_id),
        Commitment.business_id == business.id,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Commitment not found")
    return c


@router.patch("/{commitment_id}", response_model=CommitmentResponse)
def update_commitment(
    commitment_id: str,
    commitment_in: CommitmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    c = db.query(Commitment).filter(
        Commitment.id == uuid.UUID(commitment_id),
        Commitment.business_id == business.id,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Commitment not found")
    
    update_data = commitment_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(c, field, value)
    
    # Auto-update status based on dates
    if "due_date" in update_data and c.status == CommitmentStatus.SCHEDULED:
        if c.due_date < date.today():
            c.status = CommitmentStatus.OVERDUE

    if "amount_paid" in update_data:
        if c.amount_paid >= c.amount:
            c.status = CommitmentStatus.PAID
        elif c.amount_paid > 0:
            c.status = CommitmentStatus.PARTIALLY_PAID
    
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.post("/{commitment_id}/mark-paid", response_model=CommitmentResponse)
def mark_paid(
    commitment_id: str,
    paid_date: date | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    c = db.query(Commitment).filter(
        Commitment.id == uuid.UUID(commitment_id),
        Commitment.business_id == business.id,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Commitment not found")
    
    c.status = CommitmentStatus.PAID
    c.amount_paid = c.amount
    c.paid_date = paid_date or date.today()
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.delete("/{commitment_id}", status_code=204)
def delete_commitment(
    commitment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    c = db.query(Commitment).filter(
        Commitment.id == uuid.UUID(commitment_id),
        Commitment.business_id == business.id,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Commitment not found")
    db.delete(c)
    db.commit()


@router.post("/{commitment_id}/generate-recurring", response_model=list[CommitmentResponse])
def generate_recurring(
    commitment_id: str,
    weeks_ahead: int = 13,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate future occurrences of a recurring commitment."""
    business = get_current_active_business(None, current_user, db)
    parent = db.query(Commitment).filter(
        Commitment.id == uuid.UUID(commitment_id),
        Commitment.business_id == business.id,
    ).first()
    if not parent or not parent.is_recurring:
        raise HTTPException(status_code=400, detail="Not a recurring commitment")
    
    horizon = date.today() + timedelta(weeks=weeks_ahead)
    generated = []
    
    # Generate next occurrences (skip if already exist)
    from app.services.forecast import project_recurring_commitments
    projections = project_recurring_commitments(
        [parent], from_date=date.today(), to_date=horizon
    )
    
    for proj in projections:
        proj_date = date.fromisoformat(proj["due_date"])
        # Check if already exists
        existing = db.query(Commitment).filter(
            Commitment.business_id == business.id,
            Commitment.parent_commitment_id == parent.id,
            Commitment.due_date == proj_date,
        ).first()
        if not existing:
            new_c = Commitment(
                business_id=business.id,
                name=parent.name,
                category=parent.category,
                amount=parent.amount,
                due_date=proj_date,
                currency=parent.currency,
                confidence_level=parent.confidence_level,
                is_recurring=True,
                recurring_frequency=parent.recurring_frequency,
                parent_commitment_id=parent.id,
                vendor_name=parent.vendor_name,
                status=CommitmentStatus.OVERDUE if proj_date < date.today() else CommitmentStatus.SCHEDULED,
            )
            db.add(new_c)
            db.flush()
            generated.append(new_c)
    
    db.commit()
    return generated
