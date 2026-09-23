import uuid
import enum
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class AlertType(str, enum.Enum):
    FUTURE_CASH_SHORTFALL = "future_cash_shortfall"
    RESERVE_VIOLATION = "reserve_violation"
    CASH_CLIFF = "cash_cliff"
    OVERDUE_AR = "overdue_ar"
    UPCOMING_LARGE_COMMITMENT = "upcoming_large_commitment"
    CREDIT_CARD_PAYMENT_DUE = "credit_card_payment_due"
    MISSING_EXPECTED_RECEIPT = "missing_expected_receipt"
    MISSING_EXPECTED_PAYOUT = "missing_expected_payout"
    UNVERIFIED_ASSUMPTIONS = "unverified_assumptions"
    POSSIBLE_DUPLICATE = "possible_duplicate"
    OVERDUE_COMMITMENT = "overdue_commitment"
    LOW_CASH = "low_cash"
    CUSTOM = "custom"


class AlertSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Alert(Base):
    """A generated alert/notification for the business."""
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    alert_type: Mapped[AlertType] = mapped_column(sa.Enum(AlertType), nullable=False, index=True)
    severity: Mapped[AlertSeverity] = mapped_column(
        sa.Enum(AlertSeverity), nullable=False, default=AlertSeverity.MEDIUM
    )

    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    message: Mapped[str] = mapped_column(sa.Text, nullable=False)

    # Contextual data
    related_amount: Mapped[Decimal | None] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=True)
    related_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(sa.JSON, default=dict, nullable=False)

    # References
    commitment_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("commitments.id", ondelete="SET NULL"), nullable=True
    )
    receivable_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("receivables.id", ondelete="SET NULL"), nullable=True
    )
    credit_card_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("credit_cards.id", ondelete="SET NULL"), nullable=True
    )

    # State
    is_read: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    is_dismissed: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    is_resolved: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    # Deduplication
    fingerprint: Mapped[str | None] = mapped_column(sa.String(255), nullable=True, index=True)

    fired_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    business: Mapped["Business"] = relationship("Business", back_populates="alerts")

    def __repr__(self) -> str:
        return f"<Alert {self.alert_type} severity={self.severity}>"

