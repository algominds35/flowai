import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Scenario(Base):
    """A "Can I Afford This?" decision scenario.
    
    Computes before/after forecast impact of a proposed spending decision.
    """
    __tablename__ = "scenarios"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    scenario_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    # one_time_purchase | recurring_expense | new_hire | inventory_po | marketing
    # vehicle_equipment | owner_distribution | custom

    # Input parameters
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)
    start_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    frequency: Mapped[str | None] = mapped_column(sa.String(30), nullable=True)
    # For recurring: weekly | biweekly | monthly | quarterly | annually

    # Additional cost breakdown (for POs, hires etc.)
    additional_params: Mapped[dict] = mapped_column(sa.JSON, default=dict, nullable=False)

    # Computed results
    # Before scenario
    baseline_safe_to_spend: Mapped[Decimal | None] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=True)
    baseline_lowest_cash: Mapped[Decimal | None] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=True)
    baseline_lowest_cash_week: Mapped[date | None] = mapped_column(sa.Date, nullable=True)

    # After scenario
    projected_safe_to_spend: Mapped[Decimal | None] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=True)
    projected_lowest_cash: Mapped[Decimal | None] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=True)
    projected_lowest_cash_week: Mapped[date | None] = mapped_column(sa.Date, nullable=True)

    # Verdict
    can_afford: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    reserve_impact: Mapped[Decimal | None] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=True)
    # How much closer to (or past) reserve threshold

    affected_weeks: Mapped[list] = mapped_column(sa.JSON, default=list, nullable=False)
    # List of week start dates where cash drops below reserve

    verdict_message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    # State
    status: Mapped[str] = mapped_column(sa.String(20), default="draft", nullable=False)
    # draft | computed | saved | applied

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    business: Mapped["Business"] = relationship("Business", back_populates="scenarios")
    items: Mapped[list["ScenarioItem"]] = relationship(
        "ScenarioItem", back_populates="scenario", cascade="all, delete-orphan"
    )


class ScenarioItem(Base):
    """A weekly breakdown row in a scenario comparison."""
    __tablename__ = "scenario_items"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False
    )

    week_start: Mapped[date] = mapped_column(sa.Date, nullable=False)

    baseline_inflows: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)
    baseline_outflows: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)
    baseline_closing_cash: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)

    scenario_inflows: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)
    scenario_outflows: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)
    scenario_closing_cash: Mapped[Decimal] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=False)

    scenario_additional_outflow: Mapped[Decimal] = mapped_column(
        sa.Numeric(precision=18, scale=2), default=Decimal("0.00"), nullable=False
    )

    scenario: Mapped["Scenario"] = relationship("Scenario", back_populates="items")

