"""
QuickBooks Online Integration
==============================

CREDENTIAL STATUS:
  - QBO_CLIENT_ID:     Required — create app at https://developer.intuit.com/
  - QBO_CLIENT_SECRET: Required
  - QBO_REDIRECT_URI:  Set to http://localhost:8000/api/v1/integrations/qbo/callback

BLOCKER: Requires Intuit Developer account and app creation.
  Until credentials are available, realistic fixture data is used.
  
Architecture:
  1. OAuth2 flow → user authorizes in Intuit
  2. Backend receives code, exchanges for access_token + refresh_token
  3. Sync pulls: Accounts, Invoices (AR), Bills (commitments), Transactions
  4. QBO items mapped to our domain model
  5. Idempotent sync via external_id (QBO entity ID + realm_id)
"""

from datetime import date, timedelta, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.business import Business
from app.models.integration import QBOConnection
from app.models.receivable import Receivable, ReceivableStatus
from app.models.commitment import Commitment, CommitmentCategory, CommitmentStatus

FIXTURE_MODE = not (settings.QBO_CLIENT_ID and settings.QBO_CLIENT_SECRET)
QBO_AUTH_BASE = "https://appcenter.intuit.com/connect/oauth2"
QBO_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
QBO_API_BASE = "https://quickbooks.api.intuit.com/v3/company"


def get_oauth_url(state: str) -> str:
    """Generate QBO OAuth authorization URL."""
    if FIXTURE_MODE:
        return f"/api/v1/integrations/qbo/callback?code=fixture&state={state}&realmId=fixture-realm"

    from urllib.parse import urlencode
    params = {
        "client_id": settings.QBO_CLIENT_ID,
        "scope": "com.intuit.quickbooks.accounting",
        "redirect_uri": settings.QBO_REDIRECT_URI,
        "response_type": "code",
        "state": state,
    }
    return f"{QBO_AUTH_BASE}?{urlencode(params)}"


def handle_oauth_callback(
    db: Session,
    business: Business,
    code: str,
    realm_id: str,
    state: str,
) -> QBOConnection:
    """Exchange OAuth code for tokens and create connection."""
    if FIXTURE_MODE or code == "fixture":
        return _create_fixture_connection(db, business, realm_id)

    import requests
    import base64

    credentials = base64.b64encode(
        f"{settings.QBO_CLIENT_ID}:{settings.QBO_CLIENT_SECRET}".encode()
    ).decode()

    resp = requests.post(
        QBO_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.QBO_REDIRECT_URI,
        },
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    resp.raise_for_status()
    tokens = resp.json()

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens["expires_in"])

    conn = QBOConnection(
        business_id=business.id,
        realm_id=realm_id,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_expires_at=expires_at,
        status="active",
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return conn


def sync_qbo(db: Session, business: Business) -> dict:
    """Full sync of QBO data → domain model."""
    conn = db.query(QBOConnection).filter(QBOConnection.business_id == business.id).first()
    if not conn:
        return {"error": "No QBO connection found"}

    if FIXTURE_MODE:
        return _sync_fixture_data(db, business)

    _refresh_token_if_needed(db, conn)

    results = {}
    results["invoices"] = _sync_invoices(db, business, conn)
    results["bills"] = _sync_bills(db, business, conn)

    conn.last_synced_at = datetime.now(timezone.utc)
    db.add(conn)
    db.commit()

    return results


def _sync_invoices(db: Session, business: Business, conn: QBOConnection) -> dict:
    """Sync open invoices → Receivables."""
    import requests
    headers = _auth_headers(conn)
    url = f"{QBO_API_BASE}/{conn.realm_id}/query"
    query = "SELECT * FROM Invoice WHERE Balance > 0"

    resp = requests.get(url, params={"query": query}, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    invoices = data.get("QueryResponse", {}).get("Invoice", [])
    added = 0
    updated = 0

    for inv in invoices:
        ext_id = f"qbo-inv-{conn.realm_id}-{inv['Id']}"
        existing = db.query(Receivable).filter(Receivable.external_id == ext_id).first()

        due_date = date.fromisoformat(inv.get("DueDate", date.today().isoformat()))
        amount = Decimal(str(inv["TotalAmt"]))
        balance = Decimal(str(inv["Balance"]))

        if existing:
            existing.amount = amount
            existing.amount_received = amount - balance
            existing.expected_date = due_date
            existing.status = (
                ReceivableStatus.OVERDUE if due_date < date.today() and balance > 0
                else ReceivableStatus.EXPECTED if balance > 0
                else ReceivableStatus.RECEIVED
            )
            db.add(existing)
            updated += 1
        else:
            r = Receivable(
                business_id=business.id,
                name=f"Invoice #{inv.get('DocNumber', inv['Id'])}",
                customer_name=inv.get("CustomerRef", {}).get("name"),
                invoice_number=inv.get("DocNumber"),
                amount=amount,
                amount_received=amount - balance,
                expected_date=due_date,
                invoice_date=date.fromisoformat(inv["TxnDate"]) if "TxnDate" in inv else None,
                status=ReceivableStatus.OVERDUE if due_date < date.today() else ReceivableStatus.EXPECTED,
                external_id=ext_id,
                external_source="qbo",
                confidence_level="high",
                is_verified=True,
            )
            db.add(r)
            added += 1

    db.flush()
    return {"added": added, "updated": updated}


def _sync_bills(db: Session, business: Business, conn: QBOConnection) -> dict:
    """Sync open bills → Commitments."""
    import requests
    headers = _auth_headers(conn)
    url = f"{QBO_API_BASE}/{conn.realm_id}/query"
    query = "SELECT * FROM Bill WHERE Balance > 0"

    resp = requests.get(url, params={"query": query}, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    bills = data.get("QueryResponse", {}).get("Bill", [])
    added = 0
    updated = 0

    for bill in bills:
        ext_id = f"qbo-bill-{conn.realm_id}-{bill['Id']}"
        existing = db.query(Commitment).filter(Commitment.external_id == ext_id).first()

        due_date = date.fromisoformat(bill.get("DueDate", date.today().isoformat()))
        amount = Decimal(str(bill["TotalAmt"]))
        balance = Decimal(str(bill["Balance"]))

        if existing:
            existing.amount = amount
            existing.amount_paid = amount - balance
            existing.due_date = due_date
            existing.status = (
                CommitmentStatus.OVERDUE if due_date < date.today() and balance > 0
                else CommitmentStatus.SCHEDULED if balance > 0
                else CommitmentStatus.PAID
            )
            db.add(existing)
            updated += 1
        else:
            c = Commitment(
                business_id=business.id,
                name=f"Bill #{bill.get('DocNumber', bill['Id'])}",
                vendor_name=bill.get("VendorRef", {}).get("name"),
                category=CommitmentCategory.VENDOR_BILL,
                amount=amount,
                amount_paid=amount - balance,
                due_date=due_date,
                status=CommitmentStatus.OVERDUE if due_date < date.today() else CommitmentStatus.SCHEDULED,
                external_id=ext_id,
                external_source="qbo",
                confidence_level="high",
                is_verified=True,
            )
            db.add(c)
            added += 1

    db.flush()
    return {"added": added, "updated": updated}


def _refresh_token_if_needed(db: Session, conn: QBOConnection) -> None:
    """Refresh access token if it's expired or about to expire."""
    buffer = timedelta(minutes=5)
    if conn.token_expires_at and datetime.now(timezone.utc) + buffer < conn.token_expires_at:
        return  # Still valid

    import requests, base64
    credentials = base64.b64encode(
        f"{settings.QBO_CLIENT_ID}:{settings.QBO_CLIENT_SECRET}".encode()
    ).decode()

    resp = requests.post(
        QBO_TOKEN_URL,
        data={"grant_type": "refresh_token", "refresh_token": conn.refresh_token},
        headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/x-www-form-urlencoded"},
    )
    resp.raise_for_status()
    tokens = resp.json()

    conn.access_token = tokens["access_token"]
    conn.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens["expires_in"])
    if "refresh_token" in tokens:
        conn.refresh_token = tokens["refresh_token"]
    db.add(conn)
    db.flush()


def _auth_headers(conn: QBOConnection) -> dict:
    return {
        "Authorization": f"Bearer {conn.access_token}",
        "Accept": "application/json",
    }


def _create_fixture_connection(db: Session, business: Business, realm_id: str = "fixture-realm") -> QBOConnection:
    existing = db.query(QBOConnection).filter(QBOConnection.business_id == business.id).first()
    if existing:
        return existing

    conn = QBOConnection(
        business_id=business.id,
        realm_id=realm_id,
        company_name="Demo Company (Fixture)",
        access_token="fixture-access-token",
        refresh_token="fixture-refresh-token",
        token_expires_at=datetime.now(timezone.utc) + timedelta(days=365),
        status="active",
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return conn


def _sync_fixture_data(db: Session, business: Business) -> dict:
    """Return fixture QBO data for development."""
    today = date.today()
    
    invoices_added = 0
    bills_added = 0

    fixture_invoices = [
        ("INV-001", "Acme Corp", Decimal("15000.00"), today + timedelta(days=14)),
        ("INV-002", "Beta LLC", Decimal("8500.00"), today + timedelta(days=21)),
        ("INV-003", "Gamma Inc", Decimal("22000.00"), today - timedelta(days=5)),  # overdue
    ]

    for inv_num, customer, amount, due_date in fixture_invoices:
        ext_id = f"qbo-fixture-inv-{inv_num}"
        existing = db.query(Receivable).filter(Receivable.external_id == ext_id).first()
        if not existing:
            r = Receivable(
                business_id=business.id,
                name=f"Invoice {inv_num}",
                customer_name=customer,
                invoice_number=inv_num,
                amount=amount,
                expected_date=due_date,
                status=ReceivableStatus.OVERDUE if due_date < today else ReceivableStatus.EXPECTED,
                external_id=ext_id,
                external_source="qbo_fixture",
                confidence_level="high",
                is_verified=True,
            )
            db.add(r)
            invoices_added += 1

    fixture_bills = [
        ("BILL-001", "Office Depot", Decimal("1200.00"), CommitmentCategory.VENDOR_BILL, today + timedelta(days=10)),
        ("BILL-002", "AT&T Business", Decimal("450.00"), CommitmentCategory.SUBSCRIPTION, today + timedelta(days=7)),
        ("BILL-003", "State Tax Board", Decimal("5500.00"), CommitmentCategory.TAX, today + timedelta(days=30)),
    ]

    for bill_num, vendor, amount, category, due_date in fixture_bills:
        ext_id = f"qbo-fixture-bill-{bill_num}"
        existing = db.query(Commitment).filter(Commitment.external_id == ext_id).first()
        if not existing:
            c = Commitment(
                business_id=business.id,
                name=f"Bill {bill_num} — {vendor}",
                vendor_name=vendor,
                category=category,
                amount=amount,
                due_date=due_date,
                status=CommitmentStatus.OVERDUE if due_date < today else CommitmentStatus.SCHEDULED,
                external_id=ext_id,
                external_source="qbo_fixture",
                confidence_level="high",
                is_verified=True,
            )
            db.add(c)
            bills_added += 1

    db.commit()
    return {
        "invoices": {"added": invoices_added},
        "bills": {"added": bills_added},
        "_fixture": True,
        "_message": "Using fixture data. Set QBO_CLIENT_ID and QBO_CLIENT_SECRET for real QuickBooks sync.",
    }
