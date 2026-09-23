import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class ForecastSnapshot(Base):
    """A complete forecast computed at a point in time.
    
    Snapshots are taken weekly (or on demand) so we can track
    forecast vs actual and variance over time.
    """
    __tablename__ = "forecast_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # When this forecast was computed
    computed_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # The "as of" date for this forecast
    as_of_date: Mapped[date] = mapped_column(sa.Date, nullable=False, index=True)

    # Horizon: 8 or 13 weeks
    horizon_weeks: Mapped[int] = mapped_column(sa.Integer, default=13, nullable=False)

    # Current cash at time of forecast
    opening_cash: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)

    # Safe-to-Spend summary
    safe_to_spend: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)
    minimum_cash_reserve: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)
    lowest_projected_cash: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)
    lowest_cash_week: Mapped[date | None] = mapped_column(sa.Date, nullable=True)

    # Has a cash cliff been detected?
    has_cash_cliff: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    cash_cliff_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    cash_cliff_amount: Mapped[Decimal | None] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=True)

    is_current: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    business: Mapped["Business"] = relationship("Business", back_populates="forecast_snapshots")
    weeks: Mapped[list["ForecastWeek"]] = relationship(
        "ForecastWeek", back_populates="snapshot", cascade="all, delete-orphan",
        order_by="ForecastWeek.week_start"
    )

    def __repr__(self) -> str:
        return f"<ForecastSnapshot as_of={self.as_of_date} S2S={self.safe_to_spend}>"


class ForecastWeek(Base):
    """One week in the rolling forecast."""
    __tablename__ = "forecast_weeks"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("forecast_snapshots.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    week_number: Mapped[int] = mapped_column(sa.Integer, nullable=False)  # 1 = current week
    week_start: Mapped[date] = mapped_column(sa.Date, nullable=False)
    week_end: Mapped[date] = mapped_column(sa.Date, nullable=False)

    # Forecast
    opening_cash: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)
    expected_inflows: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)
    expected_outflows: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)
    closing_cash: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)
    reserve_threshold: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)
    below_reserve: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)

    # Actual (filled in after the week closes)
    actual_inflows: Mapped[Decimal | None] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=True)
    actual_outflows: Mapped[Decimal | None] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=True)
    actual_closing_cash: Mapped[Decimal | None] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=True)

    # Variance
    inflow_variance: Mapped[Decimal | None] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=True)
    outflow_variance: Mapped[Decimal | None] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=True)
    cash_variance: Mapped[Decimal | None] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=True)

    snapshot: Mapped["ForecastSnapshot"] = relationship("ForecastSnapshot", back_populates="weeks")
    items: Mapped[list["ForecastItem"]] = relationship(
        "ForecastItem", back_populates="week", cascade="all, delete-orphan"
    )


class ForecastItem(Base):
    """A single line item driving a forecast week (commitment or receivable)."""
    __tablename__ = "forecast_items"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    week_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("forecast_weeks.id", ondelete="CASCADE"), nullable=False
    )

    item_type: Mapped[str] = mapped_column(sa.String(20), nullable=False)  # inflow | outflow
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)
    label: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    expected_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    confidence: Mapped[str] = mapped_column(sa.String(20), default="high", nullable=False)

    # Source references
    commitment_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("commitments.id", ondelete="SET NULL"), nullable=True
    )
    receivable_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("receivables.id", ondelete="SET NULL"), nullable=True
    )

    week: Mapped["ForecastWeek"] = relationship("ForecastWeek", back_populates="items")

