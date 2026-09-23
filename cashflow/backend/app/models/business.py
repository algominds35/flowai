import uuid
from datetime import datetime, timezone
from decimal import Decimal
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    industry: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    fiscal_year_start_month: Mapped[int] = mapped_column(sa.Integer, default=1, nullable=False)
    currency: Mapped[str] = mapped_column(sa.String(3), default="USD", nullable=False)

    # Minimum cash reserve
    minimum_cash_reserve: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=18, scale=2), default=Decimal("0.00"), nullable=False
    )

    # Onboarding
    onboarding_completed: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    onboarding_step: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    members: Mapped[list["BusinessMember"]] = relationship(
        "BusinessMember", back_populates="business", cascade="all, delete-orphan"
    )
    cash_accounts: Mapped[list["CashAccount"]] = relationship(
        "CashAccount", back_populates="business", cascade="all, delete-orphan"
    )
    commitments: Mapped[list["Commitment"]] = relationship(
        "Commitment", back_populates="business", cascade="all, delete-orphan"
    )
    receivables: Mapped[list["Receivable"]] = relationship(
        "Receivable", back_populates="business", cascade="all, delete-orphan"
    )
    credit_cards: Mapped[list["CreditCard"]] = relationship(
        "CreditCard", back_populates="business", cascade="all, delete-orphan"
    )
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(
        "PurchaseOrder", back_populates="business", cascade="all, delete-orphan"
    )
    forecast_snapshots: Mapped[list["ForecastSnapshot"]] = relationship(
        "ForecastSnapshot", back_populates="business", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert", back_populates="business", cascade="all, delete-orphan"
    )
    weekly_review_sessions: Mapped[list["WeeklyReviewSession"]] = relationship(
        "WeeklyReviewSession", back_populates="business", cascade="all, delete-orphan"
    )
    scenarios: Mapped[list["Scenario"]] = relationship(
        "Scenario", back_populates="business", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="business", cascade="all, delete-orphan"
    )
    integration_connections: Mapped[list["IntegrationConnection"]] = relationship(
        "IntegrationConnection", back_populates="business", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Business {self.name}>"


class BusinessMember(Base):
    __tablename__ = "business_members"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid.uuid4
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(
        sa.String(50), default="owner", nullable=False
    )  # owner | admin | viewer
    is_primary: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        sa.UniqueConstraint("business_id", "user_id", name="uq_business_member"),
    )

    # Relationships
    business: Mapped["Business"] = relationship("Business", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="business_memberships")

