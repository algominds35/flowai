import uuid
import enum
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class POStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PARTIALLY_PAID = "partially_paid"
    FULLY_PAID = "fully_paid"
    CANCELLED = "cancelled"
    RECEIVED = "received"


class PurchaseOrder(Base):
    """A purchase order with multiple payment installments.
    
    A PO may have: deposit, production payment, freight, duties, final payment.
    Each installment becomes a separate Commitment with its own due date.
    """
    __tablename__ = "purchase_orders"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    po_number: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    supplier_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    # Totals
    total_amount: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)
    deposit_amount: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=18, scale=2), default=Decimal("0.00"), nullable=False
    )
    production_amount: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=18, scale=2), default=Decimal("0.00"), nullable=False
    )
    freight_amount: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=18, scale=2), default=Decimal("0.00"), nullable=False
    )
    duties_amount: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=18, scale=2), default=Decimal("0.00"), nullable=False
    )
    final_payment_amount: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=18, scale=2), default=Decimal("0.00"), nullable=False
    )
    other_amount: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=18, scale=2), default=Decimal("0.00"), nullable=False
    )

    amount_paid: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=18, scale=2), default=Decimal("0.00"), nullable=False
    )

    currency: Mapped[str] = mapped_column(sa.String(3), default="USD", nullable=False)

    # Dates
    order_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    expected_delivery_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)

    status: Mapped[POStatus] = mapped_column(
        sa.Enum(POStatus), nullable=False, default=POStatus.DRAFT, index=True
    )

    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    business: Mapped["Business"] = relationship("Business", back_populates="purchase_orders")
    installments: Mapped[list["POInstallment"]] = relationship(
        "POInstallment", back_populates="purchase_order", cascade="all, delete-orphan",
        order_by="POInstallment.due_date"
    )
    commitment_items: Mapped[list["Commitment"]] = relationship(
        "Commitment", back_populates="purchase_order", foreign_keys="Commitment.purchase_order_id"
    )

    @property
    def remaining_amount(self) -> Decimal:
        return self.total_amount - self.amount_paid

    def __repr__(self) -> str:
        return f"<PurchaseOrder {self.po_number} from {self.supplier_name}>"


class POInstallment(Base):
    """A single payment milestone within a PurchaseOrder."""
    __tablename__ = "po_installments"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False
    )

    installment_type: Mapped[str] = mapped_column(
        sa.String(50), nullable=False
    )  # deposit | production | freight | duties | final | other

    label: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)
    due_date: Mapped[date] = mapped_column(sa.Date, nullable=False)

    is_paid: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    paid_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    paid_amount: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=18, scale=2), default=Decimal("0.00"), nullable=False
    )

    # Linked commitment
    commitment_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("commitments.id", ondelete="SET NULL"), nullable=True
    )

    sort_order: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)

    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="installments")
    commitment: Mapped[Optional["Commitment"]] = relationship(
        "Commitment", foreign_keys=[commitment_id]
    )

