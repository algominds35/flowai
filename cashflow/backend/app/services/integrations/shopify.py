"""
Shopify Integration
===================

CREDENTIAL STATUS:
  - SHOPIFY_API_KEY:    Required — create app at https://partners.shopify.com/
  - SHOPIFY_API_SECRET: Required
  - SHOPIFY_REDIRECT_URI: Set in Shopify app config

BLOCKER: Requires Shopify Partner account and app creation.
  Until credentials available, realistic fixture data is returned.

Architecture:
  1. OAuth2 flow → user installs app on their Shopify store
  2. Backend receives shop + code, exchanges for access_token
  3. Sync pulls payouts from Shopify Payments
  4. Each payout becomes a Receivable with expected bank arrival date
  5. Actual payout → Receivable reconciled when bank transaction arrives
  6. Fees, refunds, chargebacks tracked separately
  
Key Rules:
  - A Shopify sale does NOT immediately create a receivable (payout hasn't settled)
  - Only PAYOUTS create receivables (Shopify batches sales into payouts)
  - Payout timing: typically T+2 from payout period end
  - Prevent double-counting: same payout id deduped by external_id
  - Shopify Payments refunds reduce payout amount (not separate outflow)
"""

from datetime import date, timedelta, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.business import Business
from app.models.integration import ShopifyShop
from app.models.receivable import Receivable, ReceivableStatus

FIXTURE_MODE = not (settings.SHOPIFY_API_KEY and settings.SHOPIFY_API_SECRET)


def get_oauth_url(shop_domain: str, state: str) -> str:
    """Generate Shopify OAuth authorization URL."""
    if FIXTURE_MODE:
        return f"/api/v1/integrations/shopify/callback?shop={shop_domain}&code=fixture&state={state}"

    from urllib.parse import urlencode
    scopes = "read_orders,read_finances,read_payments"
    params = {
        "client_id": settings.SHOPIFY_API_KEY,
        "scope": scopes,
        "redirect_uri": settings.SHOPIFY_REDIRECT_URI,
        "state": state,
    }
    return f"https://{shop_domain}/admin/oauth/authorize?{urlencode(params)}"


def handle_oauth_callback(
    db: Session,
    business: Business,
    shop_domain: str,
    code: str,
    state: str,
) -> ShopifyShop:
    """Exchange OAuth code for access_token."""
    if FIXTURE_MODE or code == "fixture":
        return _create_fixture_shop(db, business, shop_domain)

    import requests
    resp = requests.post(
        f"https://{shop_domain}/admin/oauth/access_token",
        json={
            "client_id": settings.SHOPIFY_API_KEY,
            "client_secret": settings.SHOPIFY_API_SECRET,
            "code": code,
        },
    )
    resp.raise_for_status()
    data = resp.json()

    shop_resp = requests.get(
        f"https://{shop_domain}/admin/api/2024-01/shop.json",
        headers={"X-Shopify-Access-Token": data["access_token"]},
    )
    shop_data = shop_resp.json().get("shop", {})

    shop = ShopifyShop(
        business_id=business.id,
        shop_domain=shop_domain,
        shop_name=shop_data.get("name"),
        access_token=data["access_token"],
        scope=data.get("scope"),
        status="active",
    )
    db.add(shop)
    db.commit()
    db.refresh(shop)
    return shop


def sync_payouts(db: Session, business: Business) -> dict:
    """Sync Shopify Payments payouts → Receivables."""
    shops = db.query(ShopifyShop).filter(
        ShopifyShop.business_id == business.id,
        ShopifyShop.status == "active",
    ).all()

    if not shops:
        return {"error": "No Shopify shop connected"}

    if FIXTURE_MODE:
        return _sync_fixture_payouts(db, business, shops[0] if shops else None)

    total_added = 0
    total_updated = 0

    for shop in shops:
        added, updated = _sync_shop_payouts(db, business, shop)
        total_added += added
        total_updated += updated

    return {"added": total_added, "updated": total_updated}


def _sync_shop_payouts(db: Session, business: Business, shop: ShopifyShop) -> tuple[int, int]:
    """Sync payouts for one Shopify shop."""
    import requests

    headers = {"X-Shopify-Access-Token": shop.access_token}
    url = f"https://{shop.shop_domain}/admin/api/2024-01/shopify_payments/payouts.json"
    params = {"status": "scheduled,in_transit,paid", "limit": 250}

    if shop.payouts_sync_cursor:
        params["since_id"] = shop.payouts_sync_cursor

    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    payouts = resp.json().get("payouts", [])

    added = 0
    updated = 0
    last_id = None

    for payout in payouts:
        last_id = str(payout["id"])
        ext_id = f"shopify-payout-{shop.id}-{payout['id']}"

        # Payout date = scheduled date or paid date
        payout_date_str = payout.get("date") or date.today().isoformat()
        payout_date = date.fromisoformat(payout_date_str)

        # Net amount (after Shopify fees, refunds, chargebacks)
        net_amount = Decimal(str(payout["amount"]))

        # Status mapping
        payout_status = payout.get("status", "")
        if payout_status in ("paid",):
            status = ReceivableStatus.RECEIVED
        elif payout_status in ("scheduled", "in_transit"):
            status = ReceivableStatus.EXPECTED
        else:
            status = ReceivableStatus.EXPECTED

        existing = db.query(Receivable).filter(Receivable.external_id == ext_id).first()

        summary = payout.get("summary", {})
        details = (
            f"Sales: ${Decimal(str(summary.get('charges_gross', 0))):,.2f} | "
            f"Refunds: -${Decimal(str(summary.get('refunds_gross', 0))):,.2f} | "
            f"Fees: -${Decimal(str(summary.get('charges_fee_amount', 0))):,.2f}"
        )

        if existing:
            existing.amount = net_amount
            existing.expected_date = payout_date
            existing.status = status
            if status == ReceivableStatus.RECEIVED:
                existing.amount_received = net_amount
            existing.description = details
            db.add(existing)
            updated += 1
        else:
            r = Receivable(
                business_id=business.id,
                name=f"Shopify Payout #{payout['id']}",
                description=details,
                receivable_type="payout",
                amount=net_amount,
                expected_date=payout_date,
                status=status,
                amount_received=net_amount if status == ReceivableStatus.RECEIVED else Decimal("0"),
                external_id=ext_id,
                external_source="shopify",
                shopify_shop_id=shop.id,
                confidence_level="high",
                is_verified=True,
            )
            db.add(r)
            added += 1

    if last_id:
        shop.payouts_sync_cursor = last_id
    shop.last_synced_at = datetime.now(timezone.utc)
    db.add(shop)
    db.commit()

    return added, updated


def _create_fixture_shop(db: Session, business: Business, shop_domain: str) -> ShopifyShop:
    domain = shop_domain or "demo-store.myshopify.com"
    existing = db.query(ShopifyShop).filter(
        ShopifyShop.business_id == business.id
    ).first()
    if existing:
        return existing

    shop = ShopifyShop(
        business_id=business.id,
        shop_domain=domain,
        shop_name="Demo Store (Fixture)",
        access_token="fixture-shopify-token",
        scope="read_orders,read_finances",
        status="active",
        payout_schedule="weekly",
        payout_day_lag=2,
    )
    db.add(shop)
    db.commit()
    db.refresh(shop)
    return shop


def _sync_fixture_payouts(db: Session, business: Business, shop: ShopifyShop | None) -> dict:
    """Return fixture Shopify payout data."""
    today = date.today()

    if not shop:
        shop = _create_fixture_shop(db, business, "demo-store.myshopify.com")

    fixture_payouts = [
        ("payout-001", Decimal("18500.00"), today + timedelta(days=2), ReceivableStatus.EXPECTED),
        ("payout-002", Decimal("21200.00"), today + timedelta(days=9), ReceivableStatus.EXPECTED),
        ("payout-003", Decimal("15800.00"), today - timedelta(days=5), ReceivableStatus.RECEIVED),
        ("payout-004", Decimal("19300.00"), today + timedelta(days=16), ReceivableStatus.EXPECTED),
    ]

    added = 0
    for payout_id, amount, expected_date, status in fixture_payouts:
        ext_id = f"shopify-payout-fixture-{payout_id}"
        existing = db.query(Receivable).filter(Receivable.external_id == ext_id).first()
        if not existing:
            r = Receivable(
                business_id=business.id,
                name=f"Shopify Payout #{payout_id}",
                description="Net payout after fees and refunds (fixture data)",
                receivable_type="payout",
                amount=amount,
                expected_date=expected_date,
                status=status,
                amount_received=amount if status == ReceivableStatus.RECEIVED else Decimal("0"),
                external_id=ext_id,
                external_source="shopify_fixture",
                shopify_shop_id=shop.id,
                confidence_level="high",
                is_verified=True,
            )
            db.add(r)
            added += 1

    db.commit()
    return {
        "added": added,
        "_fixture": True,
        "_message": "Using fixture data. Set SHOPIFY_API_KEY and SHOPIFY_API_SECRET for real Shopify payouts.",
    }
