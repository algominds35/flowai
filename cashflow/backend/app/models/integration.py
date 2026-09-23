import uuid
import enum
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class IntegrationProvider(str, enum.Enum):
    PLAID = "plaid"
    QUICKBOOKS = "quickbooks"
    SHOPIFY = "shopify"
    AMAZON = "amazon"


class IntegrationConnection(Base):
    """Tracks all integration connections for a business."""
    __tablename__ = "integration_connections"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    provider: Mapped[IntegrationProvider] = mapped_column(
        sa.Enum(IntegrationProvider), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        sa.String(30), default="active", nullable=False
    )  # active | error | expired | disconnected | pending_setup

    # Credentials stored encrypted (in production use secrets manager)
    access_token: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    # Provider-specific external IDs
    external_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)

    # Sync state
    last_synced_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    last_sync_error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    sync_cursor: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)

    # Provider config
    config: Mapped[dict] = mapped_column(sa.JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        sa.UniqueConstraint("business_id", "provider", name="uq_business_provider"),
    )

    business: Mapped["Business"] = relationship("Business", back_populates="integration_connections")


# ─── Plaid ───────────────────────────────────────────────────────────────────

class PlaidItem(Base):
    """A Plaid Item (represents a single institution connection)."""
    __tablename__ = "plaid_items"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    plaid_item_id: Mapped[str] = mapped_column(sa.String(255), unique=True, nullable=False)
    plaid_access_token: Mapped[str] = mapped_column(sa.Text, nullable=False)
    institution_id: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    institution_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)

    status: Mapped[str] = mapped_column(sa.String(30), default="active", nullable=False)
    # active | login_required | error | disconnected

    # Webhook
    webhook_url: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    error_code: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)

    last_synced_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    accounts: Mapped[list["PlaidAccount"]] = relationship(
        "PlaidAccount", back_populates="plaid_item", cascade="all, delete-orphan"
    )


class PlaidAccount(Base):
    """A single account within a Plaid Item."""
    __tablename__ = "plaid_accounts"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    plaid_item_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("plaid_items.id", ondelete="CASCADE"), nullable=False
    )

    plaid_account_id: Mapped[str] = mapped_column(sa.String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    official_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    account_type: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    account_subtype: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    mask: Mapped[str | None] = mapped_column(sa.String(10), nullable=True)

    current_balance: Mapped[Decimal | None] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=True)
    available_balance: Mapped[Decimal | None] = mapped_column(sa.Numeric(precision=18, scale=2), nullable=True)
    iso_currency_code: Mapped[str | None] = mapped_column(sa.String(3), nullable=True)

    last_synced_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    plaid_item: Mapped["PlaidItem"] = relationship("PlaidItem", back_populates="accounts")


# ─── QuickBooks Online ────────────────────────────────────────────────────────

class QBOConnection(Base):
    """QuickBooks Online OAuth connection."""
    __tablename__ = "qbo_connections"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("businesses.id", ondelete="CASCADE"),
        unique=True, nullable=False
    )

    realm_id: Mapped[str] = mapped_column(sa.String(100), nullable=False)  # QBO company id
    company_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)

    access_token: Mapped[str] = mapped_column(sa.Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(sa.Text, nullable=False)
    token_expires_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)

    status: Mapped[str] = mapped_column(sa.String(30), default="active", nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    last_sync_error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    # Sync cursors (QBO uses change data tokens)
    accounts_sync_token: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    invoices_sync_token: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    bills_sync_token: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    transactions_sync_token: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


# ─── Shopify ─────────────────────────────────────────────────────────────────

class ShopifyShop(Base):
    """A connected Shopify store."""
    __tablename__ = "shopify_shops"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    shop_domain: Mapped[str] = mapped_column(sa.String(255), unique=True, nullable=False)
    shop_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)

    access_token: Mapped[str] = mapped_column(sa.Text, nullable=False)
    scope: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    status: Mapped[str] = mapped_column(sa.String(30), default="active", nullable=False)

    # Payout settings
    payout_schedule: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    # daily | weekly | biweekly | monthly
    payout_day_lag: Mapped[int] = mapped_column(sa.Integer, default=2, nullable=False)
    # Typical days after period end before payout arrives in bank

    last_synced_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    last_sync_error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    payouts_sync_cursor: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


# ─── Amazon Marketplace ───────────────────────────────────────────────────────

class AmazonSellerAccount(Base):
    """A connected Amazon Seller account (SP-API)."""
    __tablename__ = "amazon_seller_accounts"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    merchant_id: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    marketplace_id: Mapped[str] = mapped_column(sa.String(50), default="ATVPDKIKX0DER", nullable=False)
    # Default: US marketplace

    # LWA (Login with Amazon) OAuth
    lwa_access_token: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    lwa_refresh_token: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    lwa_token_expires_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    # SP-API requires AWS role ARN for application-based auth
    # BLOCKER: Requires Amazon SP-API app approval (contact Amazon to apply)
    # Status: implementing complete interface; credentials not yet obtained
    sp_api_role_arn: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)

    status: Mapped[str] = mapped_column(sa.String(30), default="pending_setup", nullable=False)

    # Payout / settlement settings
    # Amazon pays every 14 days by default
    settlement_cycle_days: Mapped[int] = mapped_column(sa.Integer, default=14, nullable=False)
    last_settlement_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)

    last_synced_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    last_sync_error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    settlements_sync_cursor: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

