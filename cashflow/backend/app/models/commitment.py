import uuid
import enum
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class CommitmentCategory(str, enum.Enum):
    VENDOR_BILL = "vendor_bill"
    PAYROLL = "payroll"
    TAX = "tax"
    RENT = "rent"
    INSURANCE = "insurance"
    LOAN = "loan"
    SUBSCRIPTION = "subscription"
    RECURRING_EXPENSE = "recurring_expense"
    CREDIT_CARD_PAYMENT = "credit_card_payment"
    INVENTORY_PO = "inventory_po"
    SUPPLIER_DEPOSIT = "supplier_deposit"
    MANUAL = "manual"
    OTHER = "other"


class CommitmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    OVERDUE = "overdue"
    PAID = "paid"
    CANCELLED = "cancelled"
    PARTIALLY_PAID = "partially_paid"


class RecurringFrequency(str, enum.Enum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    SEMIMONTHLY = "semimonthly"  # 1st and 15th
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
    CUSTOM = "custom"


class Commitment(Base):
    """A known or expected future cash outflow (bill, payroll, tax, etc.)."""
    __tablename__ = "commitments"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Identification
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    category: Mapped[CommitmentCategory] = mapped_column(
        sa.Enum(CommitmentCategory), nullable=False, default=CommitmentCategory.MANUAL, index=True
    )
    vendor_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)

    # Amount
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=18, scale=2), default=Decimal("0.00"), nullable=False
    )
    currency: Mapped[str] = mapped_column(sa.String(3), default="USD", nullable=False)

    # Dates
    due_date: Mapped[date] = mapped_column(sa.Date, nullable=False, index=True)
    paid_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)

    # Status
    status: Mapped[CommitmentStatus] = mapped_column(
        sa.Enum(CommitmentStatus), nullable=False, default=CommitmentStatus.SCHEDULED, index=True
    )
    is_verified: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    confidence_level: Mapped[str] = mapped_column(
        sa.String(20), default="high", nullable=False
    )  # high | medium | low | uncertain

    # Recurring
    is_recurring: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    recurring_frequency: Mapped[RecurringFrequency | None] = mapped_column(
        sa.Enum(RecurringFrequency), nullable=True
    )
    recurring_day_of_month: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    recurring_end_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    parent_commitment_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("commitments.id", ondelete="SET NULL"), nullable=True
    )

    # Credit card link
    credit_card_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("credit_cards.id", ondelete="SET NULL"), nullable=True
    )
    credit_card_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("credit_card_transactions.id", ondelete="SET NULL"), nullable=True
    )

    # Purchase order link
    purchase_order_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True
    )
    po_installment_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("po_installments.id", ondelete="SET NULL"), nullable=True
    )

    # Reconciliation
    matched_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    reconciled_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    reconciled_amount: Mapped[Decimal | None] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=True)

    # External reference
    external_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True, index=True)
    external_source: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)

    # Metadata
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    tags: Mapped[list] = mapped_column(sa.JSON, default=list, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    business: Mapped["Business"] = relationship("Business", back_populates="commitments")
    credit_card: Mapped[Optional["CreditCard"]] = relationship(
        "CreditCard", foreign_keys=[credit_card_id]
    )
    credit_card_transaction: Mapped[Optional["CreditCardTransaction"]] = relationship(
        "CreditCardTransaction", foreign_keys=[credit_card_transaction_id]
    )
    purchase_order: Mapped[Optional["PurchaseOrder"]] = relationship(
        "PurchaseOrder", foreign_keys=[purchase_order_id], back_populates="commitment_items"
    )
    po_installment: Mapped[Optional["POInstallment"]] = relationship(
        "POInstallment", foreign_keys=[po_installment_id]
    )
    matched_transaction: Mapped[Optional["Transaction"]] = relationship(
        "Transaction", foreign_keys=[matched_transaction_id]
    )
    children: Mapped[list["Commitment"]] = relationship(
        "Commitment", foreign_keys=[parent_commitment_id]
    )

    @property
    def remaining_amount(self) -> Decimal:
        return self.amount - self.amount_paid

    def __repr__(self) -> str:
        return f"<Commitment {self.name} ${self.amount} due={self.due_date}>"

