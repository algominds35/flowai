from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user, get_current_active_business
from app.models.user import User
from app.models.purchase_order import PurchaseOrder, POInstallment, POStatus
from app.models.commitment import Commitment, CommitmentCategory, CommitmentStatus
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderUpdate,
    PurchaseOrderResponse,
)

router = APIRouter()


@router.get("", response_model=list[PurchaseOrderResponse])
def list_purchase_orders(
    status: POStatus | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    q = db.query(PurchaseOrder).filter(PurchaseOrder.business_id == business.id)
    if status:
        q = q.filter(PurchaseOrder.status == status)
    return q.order_by(PurchaseOrder.created_at.desc()).all()


@router.post("", response_model=PurchaseOrderResponse, status_code=201)
def create_purchase_order(
    po_in: PurchaseOrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a PO with installments.
    Each installment automatically becomes a Commitment.
    """
    business = get_current_active_business(None, current_user, db)

    po = PurchaseOrder(
        business_id=business.id,
        po_number=po_in.po_number,
        supplier_name=po_in.supplier_name,
        description=po_in.description,
        total_amount=po_in.total_amount,
        deposit_amount=po_in.deposit_amount,
        production_amount=po_in.production_amount,
        freight_amount=po_in.freight_amount,
        duties_amount=po_in.duties_amount,
        final_payment_amount=po_in.final_payment_amount,
        other_amount=po_in.other_amount,
        currency=po_in.currency,
        order_date=po_in.order_date,
        expected_delivery_date=po_in.expected_delivery_date,
        notes=po_in.notes,
        status=POStatus.ACTIVE,
    )
    db.add(po)
    db.flush()

    # Create installments and linked commitments
    installments_to_create = po_in.installments or _default_installments(po_in)
    
    for idx, inst_data in enumerate(installments_to_create):
        # Create commitment
        commitment = Commitment(
            business_id=business.id,
            name=f"PO {po_in.po_number or po_in.supplier_name}: {inst_data.label}",
            category=CommitmentCategory.INVENTORY_PO,
            amount=inst_data.amount,
            due_date=inst_data.due_date,
            currency=po_in.currency,
            purchase_order_id=po.id,
            status=CommitmentStatus.OVERDUE if inst_data.due_date < date.today() else CommitmentStatus.SCHEDULED,
            confidence_level="high",
            is_verified=True,
            vendor_name=po_in.supplier_name,
        )
        db.add(commitment)
        db.flush()

        installment = POInstallment(
            purchase_order_id=po.id,
            installment_type=inst_data.installment_type,
            label=inst_data.label,
            amount=inst_data.amount,
            due_date=inst_data.due_date,
            sort_order=idx,
            commitment_id=commitment.id,
        )
        db.add(installment)

    db.commit()
    db.refresh(po)
    return po


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
def get_purchase_order(
    po_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    po = db.query(PurchaseOrder).filter(
        PurchaseOrder.id == uuid.UUID(po_id),
        PurchaseOrder.business_id == business.id,
    ).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po


@router.patch("/{po_id}", response_model=PurchaseOrderResponse)
def update_purchase_order(
    po_id: str,
    po_in: PurchaseOrderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    po = db.query(PurchaseOrder).filter(
        PurchaseOrder.id == uuid.UUID(po_id),
        PurchaseOrder.business_id == business.id,
    ).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    for field, value in po_in.model_dump(exclude_unset=True).items():
        setattr(po, field, value)
    
    db.add(po)
    db.commit()
    db.refresh(po)
    return po


@router.post("/{po_id}/installments/{installment_id}/pay", response_model=PurchaseOrderResponse)
def mark_installment_paid(
    po_id: str,
    installment_id: str,
    paid_date: date | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    po = db.query(PurchaseOrder).filter(
        PurchaseOrder.id == uuid.UUID(po_id),
        PurchaseOrder.business_id == business.id,
    ).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    installment = db.query(POInstallment).filter(
        POInstallment.id == uuid.UUID(installment_id),
        POInstallment.purchase_order_id == po.id,
    ).first()
    if not installment:
        raise HTTPException(status_code=404, detail="Installment not found")

    actual_date = paid_date or date.today()
    installment.is_paid = True
    installment.paid_date = actual_date
    installment.paid_amount = installment.amount
    db.add(installment)

    # Update PO paid amount
    po.amount_paid += installment.amount
    if po.amount_paid >= po.total_amount:
        po.status = POStatus.FULLY_PAID
    else:
        po.status = POStatus.PARTIALLY_PAID
    db.add(po)

    # Mark commitment as paid
    if installment.commitment_id:
        c = db.query(Commitment).filter(Commitment.id == installment.commitment_id).first()
        if c:
            c.status = CommitmentStatus.PAID
            c.amount_paid = installment.amount
            c.paid_date = actual_date
            db.add(c)

    db.commit()
    db.refresh(po)
    return po


def _default_installments(po_in: PurchaseOrderCreate) -> list:
    """Generate default installments from PO amounts if none provided."""
    from app.schemas.purchase_order import POInstallmentCreate
    from datetime import timedelta
    
    installments = []
    today = date.today()
    
    if po_in.deposit_amount > 0:
        installments.append(POInstallmentCreate(
            installment_type="deposit",
            label="Deposit",
            amount=po_in.deposit_amount,
            due_date=today,
            sort_order=0,
        ))
    if po_in.production_amount > 0:
        installments.append(POInstallmentCreate(
            installment_type="production",
            label="Production Payment",
            amount=po_in.production_amount,
            due_date=today + timedelta(days=30),
            sort_order=1,
        ))
    if po_in.freight_amount > 0:
        installments.append(POInstallmentCreate(
            installment_type="freight",
            label="Freight",
            amount=po_in.freight_amount,
            due_date=today + timedelta(days=45),
            sort_order=2,
        ))
    if po_in.duties_amount > 0:
        installments.append(POInstallmentCreate(
            installment_type="duties",
            label="Duties & Customs",
            amount=po_in.duties_amount,
            due_date=today + timedelta(days=50),
            sort_order=3,
        ))
    if po_in.final_payment_amount > 0:
        installments.append(POInstallmentCreate(
            installment_type="final",
            label="Final Payment",
            amount=po_in.final_payment_amount,
            due_date=today + timedelta(days=60),
            sort_order=4,
        ))
    if po_in.other_amount > 0:
        installments.append(POInstallmentCreate(
            installment_type="other",
            label="Other",
            amount=po_in.other_amount,
            due_date=today + timedelta(days=60),
            sort_order=5,
        ))
    
    # If no specific amounts, create single payment
    if not installments:
        installments.append(POInstallmentCreate(
            installment_type="final",
            label="Full Payment",
            amount=po_in.total_amount,
            due_date=today + timedelta(days=30),
            sort_order=0,
        ))
    
    return installments
