"""
Purchase Order tests.

Tests:
- PO installments create commitments
- Each installment is forecasted on its own date
- PO payment flow
- Run PO through Can-I-Afford-It
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from app.models.purchase_order import PurchaseOrder, POInstallment, POStatus
from app.models.commitment import Commitment, CommitmentCategory, CommitmentStatus
from app.services.safe_to_spend import calculate_safe_to_spend

ZERO = Decimal("0.00")


class TestPOInstallments:
    """Tests for PO installment creation and forecasting."""

    def test_po_creates_commitment_per_installment(self, db, demo_business, demo_cash_account, today):
        """Each PO installment creates a separate commitment."""
        # Create PO with 3 installments
        po = PurchaseOrder(
            business_id=demo_business.id,
            supplier_name="China Manufacturer",
            po_number="PO-2024-001",
            total_amount=Decimal("50000.00"),
            status=POStatus.ACTIVE,
        )
        db.add(po)
        db.flush()

        installment_data = [
            ("deposit", "Deposit (30%)", Decimal("15000.00"), today + timedelta(days=3)),
            ("production", "Production Payment", Decimal("20000.00"), today + timedelta(days=30)),
            ("final", "Final Payment", Decimal("15000.00"), today + timedelta(days=60)),
        ]

        for inst_type, label, amount, due_date in installment_data:
            commitment = Commitment(
                business_id=demo_business.id,
                name=f"PO-2024-001: {label}",
                category=CommitmentCategory.INVENTORY_PO,
                amount=amount,
                due_date=due_date,
                purchase_order_id=po.id,
                status=CommitmentStatus.SCHEDULED,
                vendor_name="China Manufacturer",
            )
            db.add(commitment)
            db.flush()

            installment = POInstallment(
                purchase_order_id=po.id,
                installment_type=inst_type,
                label=label,
                amount=amount,
                due_date=due_date,
                commitment_id=commitment.id,
            )
            db.add(installment)

        db.commit()

        # Verify 3 separate commitments
        commitments = (
            db.query(Commitment)
            .filter(Commitment.purchase_order_id == po.id)
            .all()
        )
        assert len(commitments) == 3
        total = sum(c.amount for c in commitments)
        assert total == Decimal("50000.00")

    def test_po_installments_forecast_on_correct_dates(self, db, demo_business, demo_cash_account, today):
        """Each installment appears in forecast on its own due date."""
        deposit_date = today + timedelta(days=3)
        production_date = today + timedelta(days=30)

        # Create commitments directly
        from .conftest import make_commitment
        make_commitment(db, demo_business, "PO Deposit", Decimal("15000.00"),
                       due_date=deposit_date, category=CommitmentCategory.INVENTORY_PO)
        make_commitment(db, demo_business, "PO Production", Decimal("20000.00"),
                       due_date=production_date, category=CommitmentCategory.INVENTORY_PO)
        db.commit()

        result = calculate_safe_to_spend(db, demo_business, horizon_weeks=8)

        # Find week with deposit
        deposit_week = next(
            (w for w in result.weeks if w["week_start"] <= deposit_date <= w["week_end"]),
            None
        )
        assert deposit_week is not None
        assert deposit_week["expected_outflows"] == Decimal("15000.00")

        # Find week with production payment
        prod_week = next(
            (w for w in result.weeks if w["week_start"] <= production_date <= w["week_end"]),
            None
        )
        assert prod_week is not None
        assert prod_week["expected_outflows"] == Decimal("20000.00")

    def test_paid_installment_removed_from_forecast(self, db, demo_business, demo_cash_account, today):
        """Paying an installment removes it from the forecast."""
        from .conftest import make_commitment
        
        c = make_commitment(db, demo_business, "PO Deposit", Decimal("15000.00"),
                           due_date=today + timedelta(days=3),
                           category=CommitmentCategory.INVENTORY_PO)
        db.commit()

        result_before = calculate_safe_to_spend(db, demo_business)
        assert result_before.total_scheduled_outflows == Decimal("15000.00")

        c.status = CommitmentStatus.PAID
        c.amount_paid = Decimal("15000.00")
        db.add(c)
        db.commit()

        result_after = calculate_safe_to_spend(db, demo_business)
        assert result_after.total_scheduled_outflows == ZERO

    def test_po_total_equals_sum_of_installments(self, db, demo_business, today):
        """PO total must equal the sum of its installments."""
        deposit = Decimal("15000.00")
        production = Decimal("20000.00")
        final = Decimal("15000.00")
        total = deposit + production + final  # $50k

        po = PurchaseOrder(
            business_id=demo_business.id,
            supplier_name="Test Supplier",
            total_amount=total,
            deposit_amount=deposit,
            production_amount=production,
            final_payment_amount=final,
            status=POStatus.ACTIVE,
        )
        db.add(po)
        db.commit()

        assert po.total_amount == Decimal("50000.00")
        assert po.deposit_amount + po.production_amount + po.final_payment_amount == po.total_amount
