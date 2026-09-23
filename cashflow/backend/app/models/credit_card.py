import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class CreditCard(Base):
    """A business credit card — purchases don't immediately reduce bank cash."""
    __tablename__ = "credit_cards"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    last_four: Mapped[str | None] = mapped_column(sa.String(4), nullable=True)
    card_network: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)  # visa | mc | amex
    issuing_bank: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)

    # Statement dates
    statement_closing_day: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)  # day of month
    payment_due_days: Mapped[int] = mapped_column(sa.Integer, default=21, nullable=False)  # days after statement close

    # Current state
    current_balance: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=18, scale=2), default=Decimal("0.00"), nullable=False
    )  # Outstanding balance (what's owed to CC company)
    credit_limit: Mapped[Decimal | None] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=True)

    # The cash account that pays this card
    payment_cash_account_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("cash_accounts.id", ondelete="SET NULL"), nullable=True
    )

    # Plaid link
    plaid_account_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("plaid_accounts.id", ondelete="SET NULL"), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    business: Mapped["Business"] = relationship("Business", back_populates="credit_cards")
    transactions: Mapped[list["CreditCardTransaction"]] = relationship(
        "CreditCardTransaction", back_populates="credit_card", cascade="all, delete-orphan"
    )
    statements: Mapped[list["CreditCardStatement"]] = relationship(
        "CreditCardStatement", back_populates="credit_card", cascade="all, delete-orphan"
    )
    payment_cash_account: Mapped[Optional["CashAccount"]] = relationship(
        "CashAccount", foreign_keys=[payment_cash_account_id]
    )

    def __repr__(self) -> str:
        return f"<CreditCard {self.name} *{self.last_four}>"


class CreditCardTransaction(Base):
    """A charge or credit on a credit card.
    
    Key rule: bank cash does NOT decrease when a purchase is made.
    Bank cash decreases only when the card statement is paid.
    This transaction creates a future commitment for the statement due date.
    """
    __tablename__ = "credit_card_transactions"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    credit_card_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("credit_cards.id", ondelete="CASCADE"), nullable=False, index=True
    )

    transaction_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    posted_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)

    description: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=18, scale=2), nullable=False
    )  # positive = charge, negative = credit/refund

    merchant_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)

    # Which statement this belongs to
    statement_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("credit_card_statements.id", ondelete="SET NULL"), nullable=True
    )

    # The commitment this creates (for the statement payment)
    commitment_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("commitments.id", ondelete="SET NULL"), nullable=True
    )

    # External deduplication
    external_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True, index=True)
    external_source: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)

    is_pending: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    credit_card: Mapped["CreditCard"] = relationship("CreditCard", back_populates="transactions")
    statement: Mapped[Optional["CreditCardStatement"]] = relationship(
        "CreditCardStatement", back_populates="transactions", foreign_keys=[statement_id]
    )

    __table_args__ = (
        sa.Index("ix_cc_tx_external", "external_id", "external_source"),
    )


class CreditCardStatement(Base):
    """A billing cycle / statement period for a credit card.
    
    When the statement closes, a Commitment is created for the due date.
    """
    __tablename__ = "credit_card_statements"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    credit_card_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("credit_cards.id", ondelete="CASCADE"), nullable=False, index=True
    )

    period_start: Mapped[date] = mapped_column(sa.Date, nullable=False)
    period_end: Mapped[date] = mapped_column(sa.Date, nullable=False)
    due_date: Mapped[date] = mapped_column(sa.Date, nullable=False, index=True)

    statement_balance: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)
    minimum_payment: Mapped[Decimal | None] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=True)

    # The commitment created to pay this statement
    commitment_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("commitments.id", ondelete="SET NULL"), nullable=True
    )

    is_paid: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    paid_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    paid_amount: Mapped[Decimal | None] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    credit_card: Mapped["CreditCard"] = relationship("CreditCard", back_populates="statements")
    transactions: Mapped[list["CreditCardTransaction"]] = relationship(
        "CreditCardTransaction", back_populates="statement", foreign_keys=[CreditCardTransaction.statement_id]
    )
    commitment: Mapped[Optional["Commitment"]] = relationship(
        "Commitment", foreign_keys=[commitment_id]
    )

