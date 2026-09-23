from pydantic import BaseModel
import uuid
from decimal import Decimal
from datetime import date, datetime
from app.models.purchase_order import POStatus


class POInstallmentCreate(BaseModel):
    installment_type: str
    label: str
    amount: Decimal
    due_date: date
    sort_order: int = 0


class PurchaseOrderCreate(BaseModel):
    supplier_name: str
    po_number: str | None = None
    description: str | None = None
    total_amount: Decimal
    deposit_amount: Decimal = Decimal("0.00")
    production_amount: Decimal = Decimal("0.00")
    freight_amount: Decimal = Decimal("0.00")
    duties_amount: Decimal = Decimal("0.00")
    final_payment_amount: Decimal = Decimal("0.00")
    other_amount: Decimal = Decimal("0.00")
    currency: str = "USD"
    order_date: date | None = None
    expected_delivery_date: date | None = None
    notes: str | None = None
    installments: list[POInstallmentCreate] = []


class PurchaseOrderUpdate(BaseModel):
    supplier_name: str | None = None
    po_number: str | None = None
    status: POStatus | None = None
    expected_delivery_date: date | None = None
    notes: str | None = None


class POInstallmentResponse(BaseModel):
    id: uuid.UUID
    installment_type: str
    label: str
    amount: Decimal
    due_date: date
    is_paid: bool
    paid_date: date | None
    commitment_id: uuid.UUID | None

    model_config = {"from_attributes": True}


class PurchaseOrderResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    po_number: str | None
    supplier_name: str
    description: str | None
    total_amount: Decimal
    amount_paid: Decimal
    remaining_amount: Decimal
    currency: str
    order_date: date | None
    expected_delivery_date: date | None
    status: POStatus
    notes: str | None
    installments: list[POInstallmentResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}
