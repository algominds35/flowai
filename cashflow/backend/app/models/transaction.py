import uuid
import enum
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class TransactionSource(str, enum.Enum):
    PLAID = "plaid"
    QBO = "qbo"
    SHOPIFY = "shopify"
    AMAZON = "amazon"
    MANUAL = "manual"
    IMPORT = "import"


class Transaction(Base):
    """An actual bank / financial transaction.
    
    Used for reconciliation against expected commitments and receivables.
    Idempotency: (external_id, source) must be unique to prevent double-importing.
    """
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    cash_account_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("cash_accounts.id", ondelete="SET NULL"), nullable=True
    )

    transaction_date: Mapped[date] = mapped_column(sa.Date, nullable=False, index=True)
    posted_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)

    description: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    merchant_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)

    amount: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)
    # Positive = money in (credit), Negative = money out (debit)
    # Convention: positive = inflow, negative = outflow

    currency: Mapped[str] = mapped_column(sa.String(3), default="USD", nullable=False)

    transaction_type: Mapped[str] = mapped_column(
        sa.String(20), default="unknown", nullable=False
    )  # credit | debit | transfer | unknown

    category: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)

    source: Mapped[TransactionSource] = mapped_column(
        sa.Enum(TransactionSource), nullable=False, default=TransactionSource.MANUAL
    )

    # External deduplication key
    external_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    external_source: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)

    # Reconciliation state
    reconciliation_status: Mapped[str] = mapped_column(
        sa.String(30), default="unmatched", nullable=False
    )  # unmatched | matched | ignored | duplicate

    is_pending: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)

    metadata_json: Mapped[dict] = mapped_column(sa.JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        sa.UniqueConstraint("external_id", "external_source", name="uq_transaction_external"),
        sa.Index("ix_transaction_date_business", "business_id", "transaction_date"),
    )

    business: Mapped["Business"] = relationship("Business", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction {self.description} ${self.amount} on {self.transaction_date}>"

