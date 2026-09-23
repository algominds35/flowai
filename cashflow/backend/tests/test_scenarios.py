"""
Decision engine (Can I Afford This?) tests.

Tests:
- One-time purchases
- Recurring expenses
- PO installments
- Reserve impact
- Affected weeks
- Verdict logic
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from app.models.scenario import Scenario
from app.services.scenarios import compute_scenario
from .conftest import make_commitment, make_receivable

ZERO = Decimal("0.00")


@pytest.fixture
def scenario_factory(db, demo_business):
    def factory(
        name="Test Scenario",
        scenario_type="one_time_purchase",
        amount=Decimal("10000.00"),
        start_date=None,
        frequency=None,
        end_date=None,
        additional_params=None,
    ):
        start_date = start_date or date.today() + timedelta(days=7)
        s = Scenario(
            business_id=demo_business.id,
            name=name,
            scenario_type=scenario_type,
            amount=amount,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            additional_params=additional_params or {},
            status="draft",
        )
        db.add(s)
        db.flush()
        return s
    return factory


class TestOneTimePurchase:
    """Tests for one-time purchase scenarios."""

    def test_can_afford_within_s2s(self, db, demo_business, demo_cash_account, scenario_factory, today):
        """Purchase within Safe-to-Spend is affordable."""
        # S2S = $100k, purchase = $50k → still has $25k buffer
        scenario = scenario_factory(
            amount=Decimal("50000.00"),
            start_date=today + timedelta(days=7),
        )
        result = compute_scenario(db, demo_business, scenario)
        
        assert result.can_afford == True
        assert result.baseline_safe_to_spend == Decimal("100000.00")
        assert result.projected_safe_to_spend < Decimal("100000.00")
        assert result.projected_safe_to_spend >= ZERO

    def test_cannot_afford_when_exceeds_reserve(self, db, demo_business, demo_cash_account, scenario_factory, today):
        """Purchase that drops cash below reserve is not affordable."""
        # Cash = $125k, Reserve = $25k
        # Purchase $105k → cash = $20k < $25k reserve → cannot afford
        scenario = scenario_factory(
            amount=Decimal("105000.00"),
            start_date=today + timedelta(days=7),
        )
        result = compute_scenario(db, demo_business, scenario)
        
        assert result.can_afford == False
        assert result.projected_lowest_cash < demo_business.minimum_cash_reserve

    def test_shows_before_after_s2s(self, db, demo_business, demo_cash_account, scenario_factory, today):
        """Scenario shows before and after S2S."""
        scenario = scenario_factory(amount=Decimal("20000.00"))
        result = compute_scenario(db, demo_business, scenario)
        
        assert result.baseline_safe_to_spend is not None
        assert result.projected_safe_to_spend is not None
        assert result.projected_safe_to_spend < result.baseline_safe_to_spend

    def test_shows_reserve_impact(self, db, demo_business, demo_cash_account, scenario_factory, today):
        """Reserve impact shows how much closer to reserve threshold."""
        scenario = scenario_factory(amount=Decimal("30000.00"))
        result = compute_scenario(db, demo_business, scenario)
        
        # Reserve impact = baseline lowest - projected lowest
        assert result.reserve_impact is not None
        assert result.reserve_impact > ZERO

    def test_affected_weeks_listed(self, db, demo_business, demo_cash_account, scenario_factory, today):
        """Affected weeks are listed when cash drops below reserve."""
        # Make a huge purchase that pushes below reserve
        scenario = scenario_factory(amount=Decimal("110000.00"))
        result = compute_scenario(db, demo_business, scenario)
        
        if not result.can_afford:
            # Should list which weeks are affected
            assert len(result.affected_weeks) > 0


class TestRecurringExpenseScenario:
    """Tests for recurring expense scenarios."""

    def test_recurring_expense_compounds_outflows(
        self, db, demo_business, demo_cash_account, scenario_factory, today
    ):
        """Recurring expense shows cumulative impact."""
        # Monthly expense of $5k
        scenario = scenario_factory(
            name="New Marketing Subscription",
            scenario_type="recurring_expense",
            amount=Decimal("5000.00"),
            frequency="monthly",
            start_date=today,
        )
        result = compute_scenario(db, demo_business, scenario)
        
        assert result.baseline_safe_to_spend is not None
        assert result.projected_safe_to_spend is not None
        # Multiple months of $5k reduces S2S more than a one-time $5k
        assert len(result.items) > 0


class TestNewHireScenario:
    """Tests for new hire scenarios."""

    def test_new_hire_monthly_recurring(self, db, demo_business, demo_cash_account, scenario_factory, today):
        """New hire at $8k/month is recurring expense."""
        scenario = scenario_factory(
            name="New Sales Manager - $8k/month",
            scenario_type="new_hire",
            amount=Decimal("8000.00"),
            frequency="monthly",
            start_date=today + timedelta(days=14),
        )
        result = compute_scenario(db, demo_business, scenario)
        assert result.status == "computed"


class TestScenarioWithExistingCommitments:
    """Tests that scenario layering works with existing commitments."""

    def test_scenario_adds_to_existing_commitments(
        self, db, demo_business, demo_cash_account, scenario_factory, today
    ):
        """Scenario impact is on top of existing commitments."""
        # Add existing payroll
        make_commitment(db, demo_business, "Payroll", Decimal("45000.00"),
                       due_date=today + timedelta(days=5))
        db.commit()

        # Now add scenario
        scenario = scenario_factory(amount=Decimal("30000.00"), start_date=today + timedelta(days=7))
        result = compute_scenario(db, demo_business, scenario)
        
        # Baseline S2S should already account for payroll ($125k - $45k - $25k = $55k)
        assert result.baseline_safe_to_spend == Decimal("55000.00")
        # Scenario reduces it further
        assert result.projected_safe_to_spend < result.baseline_safe_to_spend


class TestPurchaseOrderScenario:
    """Tests for PO with installments."""

    def test_po_scenario_with_installments(
        self, db, demo_business, demo_cash_account, scenario_factory, today
    ):
        """PO scenario with multiple installments."""
        scenario = scenario_factory(
            name="Inventory PO - China Supplier",
            scenario_type="inventory_po",
            amount=Decimal("50000.00"),
            start_date=today + timedelta(days=5),  # Deposit today
            additional_params={
                "installments": [
                    {"date": (today + timedelta(days=5)).isoformat(), "amount": "15000"},  # Deposit 30%
                    {"date": (today + timedelta(days=35)).isoformat(), "amount": "20000"},  # Production
                    {"date": (today + timedelta(days=60)).isoformat(), "amount": "15000"},  # Balance
                ]
            },
        )
        result = compute_scenario(db, demo_business, scenario)
        assert result.status == "computed"
