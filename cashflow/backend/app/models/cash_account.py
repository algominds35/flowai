import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class CashAccount(Base):
    """Represents a bank account or cash position."""
    __tablename__ = "cash_accounts"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(
        sa.String(50), default="checking", nullable=False
    )  # checking | savings | money_market | credit_line
    institution_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    last_four: Mapped[str | None] = mapped_column(sa.String(4), nullable=True)

    # Current balance — set manually or synced from integration
    current_balance: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=18, scale=2), default=Decimal("0.00"), nullable=False
    )
    balance_as_of: Mapped[date | None] = mapped_column(sa.Date, nullable=True)

    # Integration link (Plaid account id)
    plaid_account_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("plaid_accounts.id", ondelete="SET NULL"), nullable=True
    )
    qbo_account_ref: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)

    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    include_in_cash_position: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    business: Mapped["Business"] = relationship("Business", back_populates="cash_accounts")
    snapshots: Mapped[list["CashAccountSnapshot"]] = relationship(
        "CashAccountSnapshot", back_populates="account", cascade="all, delete-orphan"
    )
    plaid_account: Mapped["PlaidAccount | None"] = relationship("PlaidAccount", foreign_keys=[plaid_account_id])

    def __repr__(self) -> str:
        return f"<CashAccount {self.name} ${self.current_balance}>"


class CashAccountSnapshot(Base):
    """Daily snapshot of account balance for historical tracking."""
    __tablename__ = "cash_account_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("cash_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    balance: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)
    source: Mapped[str] = mapped_column(sa.String(50), default="manual", nullable=False)

    __table_args__ = (
        sa.UniqueConstraint("account_id", "snapshot_date", name="uq_snapshot_date"),
    )

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    account: Mapped["CashAccount"] = relationship("CashAccount", back_populates="snapshots")

