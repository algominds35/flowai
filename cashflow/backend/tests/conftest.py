"""
Test configuration and shared fixtures.

Demo business: "Acme Trading Co" — an ecommerce business selling on Shopify + Amazon.
Uses realistic financial data to verify calculations manually.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.db.base import Base
from app.models.user import User
from app.models.business import Business, BusinessMember
from app.models.cash_account import CashAccount
from app.models.commitment import Commitment, CommitmentCategory, CommitmentStatus, RecurringFrequency
from app.models.receivable import Receivable, ReceivableStatus
from app.models.credit_card import CreditCard, CreditCardTransaction, CreditCardStatement
from app.models.purchase_order import PurchaseOrder, POInstallment, POStatus
from app.core.security import get_password_hash

ZERO = Decimal("0.00")


@pytest.fixture(scope="function")
def db() -> Session:
    """In-memory SQLite database for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def demo_user(db: Session) -> User:
    user = User(
        email="owner@acmetrading.com",
        hashed_password=get_password_hash("password123"),
        full_name="Alice Smith",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def demo_business(db: Session, demo_user: User) -> Business:
    """
    Acme Trading Co — an ecommerce business.
    
    Financial profile:
    - Revenue: ~$200k/month (Shopify + Amazon)
    - Payroll: $45k biweekly
    - Rent: $12k/month
    - Minimum reserve: $25,000
    """
    business = Business(
        name="Acme Trading Co",
        industry="ecommerce",
        currency="USD",
        minimum_cash_reserve=Decimal("25000.00"),
        onboarding_completed=True,
    )
    db.add(business)
    db.flush()

    member = BusinessMember(
        business_id=business.id,
        user_id=demo_user.id,
        role="owner",
        is_primary=True,
    )
    db.add(member)
    db.commit()
    return business


@pytest.fixture
def demo_cash_account(db: Session, demo_business: Business) -> CashAccount:
    """Chase Business Checking with $125,000 balance."""
    account = CashAccount(
        business_id=demo_business.id,
        name="Chase Business Checking",
        account_type="checking",
        institution_name="Chase Bank",
        current_balance=Decimal("125000.00"),
        balance_as_of=date.today(),
    )
    db.add(account)
    db.commit()
    return account


@pytest.fixture
def demo_savings_account(db: Session, demo_business: Business) -> CashAccount:
    """Business savings account with $50,000."""
    account = CashAccount(
        business_id=demo_business.id,
        name="Business Savings",
        account_type="savings",
        current_balance=Decimal("50000.00"),
        balance_as_of=date.today(),
    )
    db.add(account)
    db.commit()
    return account


@pytest.fixture
def today():
    return date.today()


def make_commitment(
    db: Session,
    business: Business,
    name: str,
    amount: Decimal,
    due_date: date,
    category: CommitmentCategory = CommitmentCategory.MANUAL,
    status: CommitmentStatus | None = None,
    confidence_level: str = "high",
    amount_paid: Decimal = ZERO,
    is_recurring: bool = False,
    recurring_frequency: RecurringFrequency | None = None,
) -> Commitment:
    if status is None:
        status = CommitmentStatus.OVERDUE if due_date < date.today() else CommitmentStatus.SCHEDULED
    c = Commitment(
        business_id=business.id,
        name=name,
        category=category,
        amount=amount,
        amount_paid=amount_paid,
        due_date=due_date,
        status=status,
        confidence_level=confidence_level,
        is_recurring=is_recurring,
        recurring_frequency=recurring_frequency,
    )
    db.add(c)
    db.flush()
    return c


def make_receivable(
    db: Session,
    business: Business,
    name: str,
    amount: Decimal,
    expected_date: date,
    status: ReceivableStatus | None = None,
    customer_name: str = "Customer",
    amount_received: Decimal = ZERO,
    confidence_level: str = "high",
) -> Receivable:
    if status is None:
        status = ReceivableStatus.OVERDUE if expected_date < date.today() else ReceivableStatus.EXPECTED
    r = Receivable(
        business_id=business.id,
        name=name,
        customer_name=customer_name,
        amount=amount,
        amount_received=amount_received,
        expected_date=expected_date,
        status=status,
        confidence_level=confidence_level,
    )
    db.add(r)
    db.flush()
    return r
