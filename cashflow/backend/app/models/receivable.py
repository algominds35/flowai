import uuid
import enum
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class ReceivableStatus(str, enum.Enum):
    EXPECTED = "expected"
    OVERDUE = "overdue"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    WRITTEN_OFF = "written_off"
    DISPUTED = "disputed"


class Receivable(Base):
    """Expected incoming cash — invoices, settlements, deposits, etc."""
    __tablename__ = "receivables"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Identification
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    receivable_type: Mapped[str] = mapped_column(
        sa.String(50), default="invoice", nullable=False
    )  # invoice | settlement | deposit | payout | refund | other
    customer_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)

    # Amount
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)
    amount_received: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=18, scale=2), default=Decimal("0.00"), nullable=False
    )
    currency: Mapped[str] = mapped_column(sa.String(3), default="USD", nullable=False)

    # Dates
    invoice_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    expected_date: Mapped[date] = mapped_column(sa.Date, nullable=False, index=True)
    received_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)

    # Status
    status: Mapped[ReceivableStatus] = mapped_column(
        sa.Enum(ReceivableStatus), nullable=False, default=ReceivableStatus.EXPECTED, index=True
    )

    # Confidence / verification
    confidence_level: Mapped[str] = mapped_column(
        sa.String(20), default="high", nullable=False
    )  # high | medium | low | uncertain
    is_verified: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    requires_review: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)

    # Integration source
    external_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True, index=True)
    external_source: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    # shopify | amazon | qbo | plaid | manual

    # Ecommerce fields
    shopify_shop_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("shopify_shops.id", ondelete="SET NULL"), nullable=True
    )
    amazon_account_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("amazon_seller_accounts.id", ondelete="SET NULL"), nullable=True
    )

    # Reconciliation
    matched_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    reconciled_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

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
    business: Mapped["Business"] = relationship("Business", back_populates="receivables")
    payments: Mapped[list["ReceivablePayment"]] = relationship(
        "ReceivablePayment", back_populates="receivable", cascade="all, delete-orphan"
    )
    matched_transaction: Mapped[Optional["Transaction"]] = relationship(
        "Transaction", foreign_keys=[matched_transaction_id]
    )

    @property
    def remaining_amount(self) -> Decimal:
        return self.amount - self.amount_received

    def __repr__(self) -> str:
        return f"<Receivable {self.name} ${self.amount} expected={self.expected_date}>"


class ReceivablePayment(Base):
    """Records a partial or full payment against a receivable."""
    __tablename__ = "receivable_payments"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    receivable_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("receivables.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)
    received_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    receivable: Mapped["Receivable"] = relationship("Receivable", back_populates="payments")
    transaction: Mapped[Optional["Transaction"]] = relationship("Transaction", foreign_keys=[transaction_id])

