"""
Credit Card timing and double-counting prevention tests.

Key rules:
1. Bank cash does NOT decrease when a CC purchase is made
2. Bank cash decreases only when the statement is paid
3. CC transactions → commitment on statement due date
4. No double counting between CC purchases and statement payment
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.cash_account import CashAccount
from app.models.credit_card import CreditCard, CreditCardTransaction, CreditCardStatement
from app.models.commitment import Commitment, CommitmentCategory, CommitmentStatus
from app.services.safe_to_spend import calculate_safe_to_spend
from .conftest import make_commitment

ZERO = Decimal("0.00")


@pytest.fixture
def demo_cc(db: Session, demo_business: Business) -> CreditCard:
    card = CreditCard(
        business_id=demo_business.id,
        name="Chase Ink Business",
        last_four="4242",
        statement_closing_day=25,
        payment_due_days=21,
        current_balance=ZERO,
        credit_limit=Decimal("50000.00"),
    )
    db.add(card)
    db.commit()
    return card


class TestCreditCardTiming:
    """Bank cash should not decrease on purchase — only on payment."""

    def test_cc_purchase_does_not_reduce_bank_cash(self, db, demo_business, demo_cash_account, demo_cc, today):
        """
        When a CC purchase is made, bank balance stays the same.
        Only the CC balance increases.
        """
        initial_cash = demo_cash_account.current_balance
        
        # Record a $5,000 purchase
        tx = CreditCardTransaction(
            credit_card_id=demo_cc.id,
            transaction_date=today,
            description="Inventory Purchase",
            amount=Decimal("5000.00"),
        )
        db.add(tx)
        demo_cc.current_balance += Decimal("5000.00")
        db.add(demo_cc)
        db.commit()
        db.refresh(demo_cash_account)

        # Bank cash should be unchanged
        assert demo_cash_account.current_balance == initial_cash
        # CC balance increased
        assert demo_cc.current_balance == Decimal("5000.00")

    def test_cc_payment_reduces_bank_cash_via_commitment(self, db, demo_business, demo_cash_account, demo_cc, today):
        """
        When statement is paid, the Commitment for that amount
        is what reduces the forecast (not the individual purchases).
        """
        # Create statement with $5,000 balance
        due_date = today + timedelta(days=21)
        stmt = CreditCardStatement(
            credit_card_id=demo_cc.id,
            period_start=today - timedelta(days=30),
            period_end=today,
            due_date=due_date,
            statement_balance=Decimal("5000.00"),
        )
        db.add(stmt)
        db.commit()

        # Create commitment from statement
        commitment = make_commitment(
            db, demo_business, "CC Payment: Chase Ink", Decimal("5000.00"),
            due_date=due_date,
            category=CommitmentCategory.CREDIT_CARD_PAYMENT,
        )
        db.commit()

        result = calculate_safe_to_spend(db, demo_business)
        # The $5k CC commitment reduces the forecast
        assert result.total_scheduled_outflows == Decimal("5000.00")

    def test_no_double_counting_purchase_and_payment(
        self, db, demo_business, demo_cash_account, demo_cc, today
    ):
        """
        CRITICAL: Purchases should NOT be counted AND the payment should NOT be counted.
        Only the payment commitment should flow through.
        """
        # Record purchases
        for amount, desc in [(Decimal("1000.00"), "Office"), (Decimal("2000.00"), "Supplies")]:
            tx = CreditCardTransaction(
                credit_card_id=demo_cc.id,
                transaction_date=today,
                description=desc,
                amount=amount,
            )
            db.add(tx)
        demo_cc.current_balance = Decimal("3000.00")
        db.add(demo_cc)
        db.commit()

        # Create statement commitment (the actual cash event)
        due_date = today + timedelta(days=21)
        stmt_commitment = make_commitment(
            db, demo_business, "CC Payment: Chase Ink", Decimal("3000.00"),
            due_date=due_date,
            category=CommitmentCategory.CREDIT_CARD_PAYMENT,
        )
        db.commit()

        result = calculate_safe_to_spend(db, demo_business)
        # Only ONE commitment in outflows — the payment, not the purchases
        assert result.total_scheduled_outflows == Decimal("3000.00")
        # Verify only 1 item in outflows
        all_outflow_items = [
            item
            for week in result.weeks
            for item in week["outflow_items"]
        ]
        assert len(all_outflow_items) == 1
        assert all_outflow_items[0]["name"] == "CC Payment: Chase Ink"

    def test_cc_statement_timing(self, db, demo_business, demo_cash_account, demo_cc, today):
        """CC payment shows up in forecast on due date, not purchase date."""
        purchase_date = today - timedelta(days=5)  # 5 days ago
        due_date = today + timedelta(days=16)  # statement due in 16 days

        stmt = CreditCardStatement(
            credit_card_id=demo_cc.id,
            period_start=today - timedelta(days=30),
            period_end=today,
            due_date=due_date,
            statement_balance=Decimal("8000.00"),
        )
        db.add(stmt)

        commitment = make_commitment(
            db, demo_business, "CC Payment: Chase Ink", Decimal("8000.00"),
            due_date=due_date,
            category=CommitmentCategory.CREDIT_CARD_PAYMENT,
        )
        db.commit()

        result = calculate_safe_to_spend(db, demo_business, horizon_weeks=8)
        
        # Find the week containing the due date
        due_week = next(
            (w for w in result.weeks if w["week_start"] <= due_date <= w["week_end"]),
            None
        )
        assert due_week is not None
        assert due_week["expected_outflows"] == Decimal("8000.00")

        # Verify no outflow in past weeks
        past_weeks = [w for w in result.weeks if w["week_end"] < due_date]
        for w in past_weeks:
            assert w["expected_outflows"] == ZERO


class TestCCReconciliation:
    """Tests for credit card payment reconciliation."""

    def test_paid_statement_removes_commitment_from_forecast(
        self, db, demo_business, demo_cash_account, demo_cc, today
    ):
        """After marking statement paid, the commitment is removed from forecast."""
        due_date = today + timedelta(days=10)
        commitment = make_commitment(
            db, demo_business, "CC Payment", Decimal("5000.00"),
            due_date=due_date,
            category=CommitmentCategory.CREDIT_CARD_PAYMENT,
        )
        db.commit()

        # Verify it's in forecast
        result_before = calculate_safe_to_spend(db, demo_business)
        assert result_before.total_scheduled_outflows == Decimal("5000.00")

        # Mark as paid
        commitment.status = CommitmentStatus.PAID
        commitment.amount_paid = Decimal("5000.00")
        db.add(commitment)
        db.commit()

        # Verify it's gone from forecast
        result_after = calculate_safe_to_spend(db, demo_business)
        assert result_after.total_scheduled_outflows == ZERO
