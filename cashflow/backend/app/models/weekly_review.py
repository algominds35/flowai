import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class WeeklyReviewSession(Base):
    """A weekly review session where the user verifies uncertain items."""
    __tablename__ = "weekly_review_sessions"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    week_start: Mapped[date] = mapped_column(sa.Date, nullable=False)
    week_end: Mapped[date] = mapped_column(sa.Date, nullable=False)

    status: Mapped[str] = mapped_column(
        sa.String(20), default="pending", nullable=False
    )  # pending | in_progress | completed

    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    completed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    business: Mapped["Business"] = relationship("Business", back_populates="weekly_review_sessions")
    items: Mapped[list["WeeklyReviewItem"]] = relationship(
        "WeeklyReviewItem", back_populates="session", cascade="all, delete-orphan"
    )


class WeeklyReviewItem(Base):
    """A single item in a weekly review — uncertain amount, date, match, etc."""
    __tablename__ = "weekly_review_items"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("weekly_review_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    item_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    # uncertain_commitment | uncertain_receivable | missing_commitment | missing_receipt
    # possible_duplicate | unmatched_transaction | overdue | confirm_amount | confirm_date

    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    # References
    commitment_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("commitments.id", ondelete="SET NULL"), nullable=True
    )
    receivable_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("receivables.id", ondelete="SET NULL"), nullable=True
    )
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )

    # Original values (preserved)
    original_amount: Mapped[Decimal | None] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=True)
    original_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)

    # User action
    action: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    # confirm | change_amount | change_date | match | ignore | mark_uncertain | add_commitment

    confirmed_amount: Mapped[Decimal | None] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=True)
    confirmed_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    match_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[str] = mapped_column(
        sa.String(20), default="pending", nullable=False
    )  # pending | actioned | ignored | skipped

    actioned_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    actioned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    session: Mapped["WeeklyReviewSession"] = relationship("WeeklyReviewSession", back_populates="items")

