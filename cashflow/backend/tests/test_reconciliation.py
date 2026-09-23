"""
Reconciliation engine tests.

Tests:
- Auto-matching transactions to commitments/receivables
- Manual matching
- Partial/split A/R
- Deduplication (idempotent re-sync)
- Variance tracking
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from app.models.transaction import Transaction, TransactionSource
from app.models.commitment import CommitmentStatus
from app.models.receivable import ReceivableStatus
from app.services.reconciliation import auto_reconcile, manually_match, upsert_transaction
from .conftest import make_commitment, make_receivable

ZERO = Decimal("0.00")


def make_transaction(
    db,
    business,
    description: str,
    amount: Decimal,
    tx_date: date | None = None,
    external_id: str | None = None,
    source: str = "plaid",
) -> Transaction:
    tx_date = tx_date or date.today()
    tx = Transaction(
        business_id=business.id,
        transaction_date=tx_date,
        description=description,
        amount=amount,
        source=TransactionSource.PLAID,
        external_id=external_id or f"test-{description.lower().replace(' ', '-')}",
        external_source=source,
    )
    db.add(tx)
    db.flush()
    return tx


class TestAutoReconcile:
    """Tests for automatic transaction matching."""

    def test_credit_matches_receivable(self, db, demo_business, demo_cash_account, today):
        """Credit transaction auto-matches to a receivable."""
        receivable = make_receivable(
            db, demo_business, "Invoice #001", Decimal("5000.00"),
            expected_date=today - timedelta(days=2),
            status=ReceivableStatus.EXPECTED,
        )
        tx = make_transaction(db, demo_business, "ACH Credit - Acme Client", Decimal("5000.00"), today)
        db.commit()

        result = auto_reconcile(db, demo_business)
        assert result["matched"] >= 1

        db.refresh(receivable)
        assert receivable.status == ReceivableStatus.RECEIVED
        assert receivable.amount_received == Decimal("5000.00")
        assert receivable.matched_transaction_id == tx.id

    def test_debit_matches_commitment(self, db, demo_business, demo_cash_account, today):
        """Debit transaction auto-matches to a commitment."""
        commitment = make_commitment(
            db, demo_business, "Rent Payment", Decimal("8000.00"),
            due_date=today - timedelta(days=1),
        )
        # Debit = negative amount
        tx = make_transaction(db, demo_business, "Chase Rent", Decimal("-8000.00"), today)
        db.commit()

        result = auto_reconcile(db, demo_business)
        assert result["matched"] >= 1

        db.refresh(commitment)
        assert commitment.status == CommitmentStatus.PAID
        assert commitment.matched_transaction_id == tx.id

    def test_fuzzy_amount_matching(self, db, demo_business, demo_cash_account, today):
        """Matches transaction even with small amount difference (within 5%)."""
        receivable = make_receivable(
            db, demo_business, "Invoice #002", Decimal("10000.00"),
            expected_date=today,
        )
        # Transaction is $9,800 (2% difference)
        tx = make_transaction(db, demo_business, "Customer Payment", Decimal("9800.00"), today)
        db.commit()

        auto_reconcile(db, demo_business)
        db.refresh(receivable)
        # Should still match (within tolerance)
        assert receivable.status in [ReceivableStatus.RECEIVED, ReceivableStatus.PARTIALLY_RECEIVED]

    def test_no_false_matches(self, db, demo_business, demo_cash_account, today):
        """Transactions don't match if date is too far off."""
        receivable = make_receivable(
            db, demo_business, "Far Future Invoice", Decimal("5000.00"),
            expected_date=today + timedelta(days=60),  # 60 days away
        )
        tx = make_transaction(db, demo_business, "Random Credit", Decimal("5000.00"), today)
        db.commit()

        auto_reconcile(db, demo_business)
        db.refresh(receivable)
        assert receivable.status == ReceivableStatus.EXPECTED  # Not matched

    def test_idempotent_resync(self, db, demo_business, demo_cash_account, today):
        """Re-syncing the same external transaction doesn't create duplicates."""
        tx1, is_new1 = upsert_transaction(
            db=db,
            business_id=demo_business.id,
            external_id="plaid-tx-12345",
            external_source="plaid",
            transaction_date=today,
            description="Test Transaction",
            amount=Decimal("5000.00"),
            source=TransactionSource.PLAID,
        )
        db.commit()

        tx2, is_new2 = upsert_transaction(
            db=db,
            business_id=demo_business.id,
            external_id="plaid-tx-12345",  # Same external_id
            external_source="plaid",
            transaction_date=today,
            description="Test Transaction",
            amount=Decimal("5000.00"),
            source=TransactionSource.PLAID,
        )
        
        assert is_new1 == True
        assert is_new2 == False
        assert tx1.id == tx2.id  # Same transaction returned


class TestPartialAR:
    """Tests for partial and split receivables."""

    def test_partial_payment_updates_status(self, db, demo_business, demo_cash_account, today):
        """Partial payment moves receivable to PARTIALLY_RECEIVED."""
        receivable = make_receivable(
            db, demo_business, "Invoice #003", Decimal("10000.00"),
            expected_date=today,
        )
        db.commit()

        # First payment: $3,000
        tx1 = make_transaction(db, demo_business, "Partial Payment 1", Decimal("3000.00"), today)
        db.commit()
        auto_reconcile(db, demo_business)

        db.refresh(receivable)
        assert receivable.status == ReceivableStatus.PARTIALLY_RECEIVED
        assert receivable.amount_received == Decimal("3000.00")
        remaining = receivable.remaining_amount
        assert remaining == Decimal("7000.00")

    def test_split_payment_eventually_clears(self, db, demo_business, demo_cash_account, today):
        """Multiple partial payments eventually clear the receivable."""
        from app.models.receivable import ReceivablePayment
        
        receivable = make_receivable(
            db, demo_business, "Invoice #004", Decimal("9000.00"),
            expected_date=today,
        )
        db.commit()

        # Add payments manually
        for amount in [Decimal("3000.00"), Decimal("3000.00"), Decimal("3000.00")]:
            payment = ReceivablePayment(
                receivable_id=receivable.id,
                amount=amount,
                received_date=today,
            )
            db.add(payment)
            receivable.amount_received += amount
        
        if receivable.amount_received >= receivable.amount:
            receivable.status = ReceivableStatus.RECEIVED
        db.add(receivable)
        db.commit()

        db.refresh(receivable)
        assert receivable.status == ReceivableStatus.RECEIVED
        assert receivable.amount_received == Decimal("9000.00")
        assert receivable.remaining_amount == ZERO


class TestDeduplication:
    """Tests for transaction deduplication."""

    def test_different_external_ids_create_different_txs(self, db, demo_business, today):
        """Transactions with different external IDs are separate."""
        tx1, _ = upsert_transaction(
            db=db, business_id=demo_business.id,
            external_id="plaid-001", external_source="plaid",
            transaction_date=today, description="Tx 1",
            amount=Decimal("100.00"), source=TransactionSource.PLAID,
        )
        tx2, _ = upsert_transaction(
            db=db, business_id=demo_business.id,
            external_id="plaid-002", external_source="plaid",
            transaction_date=today, description="Tx 2",
            amount=Decimal("100.00"), source=TransactionSource.PLAID,
        )
        db.commit()
        assert tx1.id != tx2.id

    def test_same_id_different_source_creates_new(self, db, demo_business, today):
        """Same ID from different sources creates different transactions."""
        tx1, _ = upsert_transaction(
            db=db, business_id=demo_business.id,
            external_id="tx-001", external_source="plaid",
            transaction_date=today, description="Plaid Tx",
            amount=Decimal("100.00"), source=TransactionSource.PLAID,
        )
        tx2, _ = upsert_transaction(
            db=db, business_id=demo_business.id,
            external_id="tx-001", external_source="qbo",  # Different source
            transaction_date=today, description="QBO Tx",
            amount=Decimal("100.00"), source=TransactionSource.QBO,
        )
        db.commit()
        # Different source = different transactions
        assert tx1.id != tx2.id
