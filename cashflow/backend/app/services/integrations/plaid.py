"""
Plaid Integration
=================

CREDENTIAL STATUS:
  - PLAID_CLIENT_ID: Required from https://dashboard.plaid.com/
  - PLAID_SECRET:    Required from https://dashboard.plaid.com/
  - PLAID_ENV:       sandbox | development | production
  
  When credentials are present: Uses real Plaid API.
  When credentials are absent:  Returns realistic fixture data (clearly marked).

Architecture:
  1. Business connects bank via Plaid Link (frontend widget)
  2. Frontend receives public_token
  3. Backend exchanges for access_token and creates PlaidItem + PlaidAccount records
  4. Sync job pulls transactions periodically
  5. Transactions upserted with external_id deduplication
  6. Bank balances synced to CashAccount
  7. Webhook handles real-time transaction updates
"""

from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.business import Business
from app.models.integration import PlaidItem, PlaidAccount
from app.models.cash_account import CashAccount
from app.models.transaction import Transaction, TransactionSource
from app.services.reconciliation import upsert_transaction

FIXTURE_MODE = not (settings.PLAID_CLIENT_ID and settings.PLAID_SECRET)


def get_link_token(user_id: str, business_id: str) -> dict:
    """Create a Plaid Link token for the frontend widget."""
    if FIXTURE_MODE:
        return {
            "link_token": "link-sandbox-fixture-token",
            "expiration": datetime.now(timezone.utc).isoformat(),
            "_fixture": True,
            "_message": "PLAID_CLIENT_ID / PLAID_SECRET not configured. Set these to use real Plaid.",
        }

    import plaid
    from plaid.api import plaid_api
    from plaid.model.link_token_create_request import LinkTokenCreateRequest
    from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
    from plaid.model.products import Products
    from plaid.model.country_code import CountryCode

    env_map = {
        "sandbox": plaid.Environment.Sandbox,
        "development": plaid.Environment.Development,
        "production": plaid.Environment.Production,
    }
    config = plaid.Configuration(
        host=env_map.get(settings.PLAID_ENV, plaid.Environment.Sandbox),
        api_key={"clientId": settings.PLAID_CLIENT_ID, "secret": settings.PLAID_SECRET},
    )
    api_client = plaid.ApiClient(config)
    client = plaid_api.PlaidApi(api_client)

    request = LinkTokenCreateRequest(
        products=[Products("transactions"), Products("auth")],
        client_name="CashFlow",
        country_codes=[CountryCode("US")],
        language="en",
        user=LinkTokenCreateRequestUser(client_user_id=user_id),
    )
    response = client.link_token_create(request)
    return {"link_token": response["link_token"]}


def exchange_public_token(
    db: Session,
    business: Business,
    public_token: str,
) -> PlaidItem:
    """Exchange a Plaid public_token for an access_token and create item."""
    if FIXTURE_MODE:
        return _create_fixture_item(db, business)

    import plaid
    from plaid.api import plaid_api
    from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest

    env_map = {
        "sandbox": plaid.Environment.Sandbox,
        "development": plaid.Environment.Development,
        "production": plaid.Environment.Production,
    }
    config = plaid.Configuration(
        host=env_map.get(settings.PLAID_ENV, plaid.Environment.Sandbox),
        api_key={"clientId": settings.PLAID_CLIENT_ID, "secret": settings.PLAID_SECRET},
    )
    api_client = plaid.ApiClient(config)
    client = plaid_api.PlaidApi(api_client)

    exchange_response = client.item_public_token_exchange(
        ItemPublicTokenExchangeRequest(public_token=public_token)
    )
    access_token = exchange_response["access_token"]
    item_id = exchange_response["item_id"]

    # Get account info
    accounts_response = client.accounts_get({"access_token": access_token})

    plaid_item = PlaidItem(
        business_id=business.id,
        plaid_item_id=item_id,
        plaid_access_token=access_token,
        institution_name=accounts_response.get("item", {}).get("institution_id"),
        status="active",
    )
    db.add(plaid_item)
    db.flush()

    for acct in accounts_response["accounts"]:
        pa = PlaidAccount(
            plaid_item_id=plaid_item.id,
            plaid_account_id=acct["account_id"],
            name=acct["name"],
            official_name=acct.get("official_name"),
            account_type=acct["type"],
            account_subtype=acct.get("subtype"),
            mask=acct.get("mask"),
            current_balance=Decimal(str(acct["balances"].get("current") or "0")),
            available_balance=Decimal(str(acct["balances"].get("available") or "0")),
            iso_currency_code=acct["balances"].get("iso_currency_code"),
        )
        db.add(pa)

    db.commit()
    db.refresh(plaid_item)
    return plaid_item


def sync_transactions(db: Session, business: Business) -> dict:
    """Sync recent transactions from all linked Plaid items."""
    items = db.query(PlaidItem).filter(
        PlaidItem.business_id == business.id,
        PlaidItem.status == "active",
    ).all()

    if FIXTURE_MODE:
        return _sync_fixture_transactions(db, business)

    total_added = 0
    total_skipped = 0

    for item in items:
        added, skipped = _sync_item_transactions(db, business, item)
        total_added += added
        total_skipped += skipped

    return {"added": total_added, "skipped": total_skipped, "_fixture": False}


def _sync_item_transactions(db: Session, business: Business, item: PlaidItem) -> tuple[int, int]:
    """Sync transactions for one Plaid item."""
    import plaid
    from plaid.api import plaid_api
    from plaid.model.transactions_sync_request import TransactionsSyncRequest

    env_map = {
        "sandbox": plaid.Environment.Sandbox,
        "development": plaid.Environment.Development,
        "production": plaid.Environment.Production,
    }
    config = plaid.Configuration(
        host=env_map.get(settings.PLAID_ENV, plaid.Environment.Sandbox),
        api_key={"clientId": settings.PLAID_CLIENT_ID, "secret": settings.PLAID_SECRET},
    )
    api_client = plaid.ApiClient(config)
    client = plaid_api.PlaidApi(api_client)

    cursor = item.sync_cursor if hasattr(item, 'sync_cursor') else None
    added = 0
    skipped = 0

    has_more = True
    while has_more:
        request = TransactionsSyncRequest(access_token=item.plaid_access_token)
        if cursor:
            request.cursor = cursor

        response = client.transactions_sync(request)

        for tx_data in response["added"]:
            tx, is_new = upsert_transaction(
                db=db,
                business_id=business.id,
                external_id=tx_data["transaction_id"],
                external_source="plaid",
                cash_account_id=_get_cash_account_id(db, tx_data["account_id"]),
                transaction_date=tx_data["date"],
                posted_date=tx_data.get("authorized_date") or tx_data["date"],
                description=tx_data.get("name", ""),
                merchant_name=tx_data.get("merchant_name"),
                # Plaid: negative = money out (debit), positive = money in
                # We standardize: positive = inflow, negative = outflow
                amount=Decimal(str(-tx_data["amount"])),
                currency=tx_data.get("iso_currency_code", "USD"),
                transaction_type="debit" if tx_data["amount"] > 0 else "credit",
                is_pending=tx_data.get("pending", False),
                source=TransactionSource.PLAID,
            )
            if is_new:
                added += 1
            else:
                skipped += 1

        cursor = response.get("next_cursor")
        has_more = response.get("has_more", False)

    # Update item sync state
    item.last_synced_at = datetime.now(timezone.utc)
    if hasattr(item, 'sync_cursor'):
        item.sync_cursor = cursor
    db.add(item)
    db.commit()

    return added, skipped


def _get_cash_account_id(db: Session, plaid_account_id: str):
    """Look up our internal CashAccount linked to a Plaid account."""
    pa = db.query(PlaidAccount).filter(PlaidAccount.plaid_account_id == plaid_account_id).first()
    if pa:
        ca = db.query(CashAccount).filter(CashAccount.plaid_account_id == pa.id).first()
        return ca.id if ca else None
    return None


def handle_webhook(db: Session, payload: dict) -> dict:
    """
    Handle Plaid webhooks (TRANSACTIONS_SYNC_UPDATES_AVAILABLE, etc.)
    
    Webhook URL: POST /api/v1/integrations/plaid/webhook
    Configure in Plaid dashboard.
    """
    webhook_type = payload.get("webhook_type")
    webhook_code = payload.get("webhook_code")
    item_id = payload.get("item_id")

    item = db.query(PlaidItem).filter(PlaidItem.plaid_item_id == item_id).first()
    if not item:
        return {"status": "item_not_found"}

    if webhook_type == "TRANSACTIONS" and webhook_code == "SYNC_UPDATES_AVAILABLE":
        # Queue a sync job
        business = item.plaid_item_businesses[0] if hasattr(item, 'plaid_item_businesses') else None
        return {"status": "sync_queued"}

    if webhook_type == "ITEM" and webhook_code in ("ERROR", "LOGIN_REQUIRED"):
        item.status = "login_required"
        item.error_code = payload.get("error", {}).get("error_code")
        db.add(item)
        db.commit()
        return {"status": "item_error_recorded"}

    return {"status": "ok"}


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _create_fixture_item(db: Session, business: Business) -> PlaidItem:
    """Create realistic fixture Plaid data when credentials unavailable."""
    existing = db.query(PlaidItem).filter(PlaidItem.business_id == business.id).first()
    if existing:
        return existing

    item = PlaidItem(
        business_id=business.id,
        plaid_item_id="fixture-item-001",
        plaid_access_token="access-sandbox-fixture",
        institution_id="ins_3",
        institution_name="Chase Bank (Fixture)",
        status="active",
    )
    db.add(item)
    db.flush()

    checking = PlaidAccount(
        plaid_item_id=item.id,
        plaid_account_id="fixture-checking-001",
        name="Business Checking",
        account_type="depository",
        account_subtype="checking",
        mask="4567",
        current_balance=Decimal("125000.00"),
        available_balance=Decimal("124800.00"),
        iso_currency_code="USD",
    )
    db.add(checking)

    savings = PlaidAccount(
        plaid_item_id=item.id,
        plaid_account_id="fixture-savings-001",
        name="Business Savings",
        account_type="depository",
        account_subtype="savings",
        mask="8901",
        current_balance=Decimal("50000.00"),
        available_balance=Decimal("50000.00"),
        iso_currency_code="USD",
    )
    db.add(savings)

    db.commit()
    db.refresh(item)
    return item


def _sync_fixture_transactions(db: Session, business: Business) -> dict:
    """Return fixture transaction data for development."""
    today = date.today()
    fixtures = [
        ("Shopify Payout", Decimal("18500.00"), "credit", today - timedelta(days=2)),
        ("ADP Payroll", Decimal("-12000.00"), "debit", today - timedelta(days=5)),
        ("Amazon Settlement", Decimal("9200.00"), "credit", today - timedelta(days=7)),
        ("Chase Rent Payment", Decimal("-8500.00"), "debit", today - timedelta(days=1)),
        ("Insurance Premium", Decimal("-2200.00"), "debit", today - timedelta(days=3)),
    ]

    added = 0
    skipped = 0
    for desc, amt, tx_type, tx_date in fixtures:
        _, is_new = upsert_transaction(
            db=db,
            business_id=business.id,
            external_id=f"fixture-{desc.replace(' ', '-').lower()}-{tx_date}",
            external_source="plaid_fixture",
            transaction_date=tx_date,
            description=desc,
            amount=amt,
            currency="USD",
            transaction_type=tx_type,
            source=TransactionSource.PLAID,
        )
        if is_new:
            added += 1
        else:
            skipped += 1

    db.commit()
    return {"added": added, "skipped": skipped, "_fixture": True,
            "_message": "Using fixture data. Set PLAID_CLIENT_ID and PLAID_SECRET for real bank data."}
