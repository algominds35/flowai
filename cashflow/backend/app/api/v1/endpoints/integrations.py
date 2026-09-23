"""
Integration endpoints for Plaid, QuickBooks, Shopify, and Amazon.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user, get_current_active_business
from app.models.user import User
from app.services.integrations import plaid, quickbooks, shopify, amazon

router = APIRouter()


# ─── Plaid ────────────────────────────────────────────────────────────────────

@router.get("/plaid/link-token")
def plaid_link_token(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get Plaid Link token for bank connection widget."""
    business = get_current_active_business(None, current_user, db)
    return plaid.get_link_token(str(current_user.id), str(business.id))


@router.post("/plaid/exchange")
def plaid_exchange(
    public_token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Exchange Plaid public token for access token after Link success."""
    business = get_current_active_business(None, current_user, db)
    item = plaid.exchange_public_token(db, business, public_token)
    return {"status": "connected", "institution": item.institution_name, "item_id": str(item.id)}


@router.post("/plaid/sync")
def plaid_sync(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually trigger Plaid transaction sync."""
    business = get_current_active_business(None, current_user, db)
    result = plaid.sync_transactions(db, business)
    return result


@router.post("/plaid/webhook")
async def plaid_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Plaid webhooks. Register this URL in the Plaid dashboard."""
    payload = await request.json()
    result = plaid.handle_webhook(db, payload)
    return result


# ─── QuickBooks Online ────────────────────────────────────────────────────────

@router.get("/qbo/connect")
def qbo_connect(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get QBO OAuth URL to redirect user for authorization."""
    import secrets
    state = secrets.token_urlsafe(16)
    url = quickbooks.get_oauth_url(state)
    return {"oauth_url": url, "state": state}


@router.get("/qbo/callback")
def qbo_callback(
    code: str = Query(...),
    realm_id: str = Query(...),
    state: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Handle QBO OAuth callback."""
    business = get_current_active_business(None, current_user, db)
    conn = quickbooks.handle_oauth_callback(db, business, code, realm_id, state)
    return {"status": "connected", "company": conn.company_name, "realm_id": conn.realm_id}


@router.post("/qbo/sync")
def qbo_sync(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sync QuickBooks Online data (invoices, bills)."""
    business = get_current_active_business(None, current_user, db)
    result = quickbooks.sync_qbo(db, business)
    return result


# ─── Shopify ─────────────────────────────────────────────────────────────────

@router.get("/shopify/connect")
def shopify_connect(
    shop: str = Query(..., description="Shopify store domain e.g. mystore.myshopify.com"),
    current_user: User = Depends(get_current_user),
):
    """Get Shopify OAuth URL for app installation."""
    import secrets
    state = secrets.token_urlsafe(16)
    url = shopify.get_oauth_url(shop, state)
    return {"oauth_url": url, "state": state}


@router.get("/shopify/callback")
def shopify_callback(
    shop: str = Query(...),
    code: str = Query(...),
    state: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Handle Shopify OAuth callback."""
    business = get_current_active_business(None, current_user, db)
    shop_obj = shopify.handle_oauth_callback(db, business, shop, code, state)
    return {"status": "connected", "shop": shop_obj.shop_name, "domain": shop_obj.shop_domain}


@router.post("/shopify/sync")
def shopify_sync(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sync Shopify payouts."""
    business = get_current_active_business(None, current_user, db)
    result = shopify.sync_payouts(db, business)
    return result


# ─── Amazon ──────────────────────────────────────────────────────────────────

@router.get("/amazon/connect")
def amazon_connect(
    current_user: User = Depends(get_current_user),
):
    """
    Get Amazon SP-API OAuth URL.
    
    ⚠️  BLOCKER: Requires approved SP-API application.
    See services/integrations/amazon.py for details.
    """
    import secrets
    state = secrets.token_urlsafe(16)
    url = amazon.get_oauth_url(state)
    return {
        "oauth_url": url,
        "state": state,
        "_blocker": (
            "Amazon SP-API requires application approval from Amazon. "
            "Apply at: https://developer.amazonservices.com/ "
            "Set AMAZON_APP_ID, AMAZON_CLIENT_ID, AMAZON_CLIENT_SECRET once approved."
        ),
    }


@router.get("/amazon/callback")
def amazon_callback(
    code: str = Query(...),
    state: str = Query(None),
    selling_partner_id: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Handle Amazon OAuth callback."""
    business = get_current_active_business(None, current_user, db)
    account = amazon.handle_oauth_callback(
        db, business, code, merchant_id=selling_partner_id, state=state
    )
    return {"status": "connected", "merchant_id": account.merchant_id}


@router.post("/amazon/sync")
def amazon_sync(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sync Amazon settlement data."""
    business = get_current_active_business(None, current_user, db)
    result = amazon.sync_settlements(db, business)
    return result


# ─── Status ──────────────────────────────────────────────────────────────────

@router.get("/status")
def integration_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get connection status for all integrations."""
    business = get_current_active_business(None, current_user, db)
    
    from app.models.integration import PlaidItem, QBOConnection, ShopifyShop, AmazonSellerAccount
    
    plaid_items = db.query(PlaidItem).filter(PlaidItem.business_id == business.id).all()
    qbo = db.query(QBOConnection).filter(QBOConnection.business_id == business.id).first()
    shopify_shops = db.query(ShopifyShop).filter(ShopifyShop.business_id == business.id).all()
    amazon_accounts = db.query(AmazonSellerAccount).filter(AmazonSellerAccount.business_id == business.id).all()
    
    return {
        "plaid": {
            "connected": len(plaid_items) > 0,
            "items": [{"institution": i.institution_name, "status": i.status} for i in plaid_items],
            "mode": "fixture" if plaid.FIXTURE_MODE else "live",
        },
        "quickbooks": {
            "connected": qbo is not None,
            "company": qbo.company_name if qbo else None,
            "status": qbo.status if qbo else "not_connected",
            "mode": "fixture" if quickbooks.FIXTURE_MODE else "live",
        },
        "shopify": {
            "connected": len(shopify_shops) > 0,
            "shops": [{"domain": s.shop_domain, "status": s.status} for s in shopify_shops],
            "mode": "fixture" if shopify.FIXTURE_MODE else "live",
        },
        "amazon": {
            "connected": len(amazon_accounts) > 0,
            "accounts": [{"merchant_id": a.merchant_id, "status": a.status} for a in amazon_accounts],
            "mode": "fixture" if amazon.FIXTURE_MODE else "live",
            "_blocker": "Amazon SP-API requires application approval" if amazon.FIXTURE_MODE else None,
        },
    }
