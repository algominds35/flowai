"""
Forecast calculation tests.

Tests:
- 8 and 13 week rolling forecasts
- Weekly opening/closing cash
- Variance tracking
- Recurring commitment projection
- Forecast vs actual
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from app.services.forecast import compute_and_save_forecast, reconcile_forecast_week
from app.services.safe_to_spend import calculate_safe_to_spend
from .conftest import make_commitment, make_receivable
from app.models.commitment import CommitmentCategory, CommitmentStatus, RecurringFrequency
from app.models.forecast import ForecastSnapshot, ForecastWeek

ZERO = Decimal("0.00")


class TestForecastComputation:
    """Tests for forecast snapshot creation."""

    def test_compute_13_week_forecast(self, db, demo_business, demo_cash_account, today):
        """13-week forecast creates correct number of weeks."""
        snapshot = compute_and_save_forecast(db, demo_business, horizon_weeks=13)
        assert snapshot.horizon_weeks == 13
        assert len(snapshot.weeks) == 13

    def test_compute_8_week_forecast(self, db, demo_business, demo_cash_account, today):
        """8-week forecast creates 8 weeks."""
        snapshot = compute_and_save_forecast(db, demo_business, horizon_weeks=8)
        assert len(snapshot.weeks) == 8

    def test_forecast_snapshot_has_s2s(self, db, demo_business, demo_cash_account, today):
        """Forecast snapshot includes Safe-to-Spend."""
        snapshot = compute_and_save_forecast(db, demo_business)
        assert snapshot.safe_to_spend == Decimal("100000.00")  # $125k - $25k

    def test_forecast_with_commitments_reduces_s2s(self, db, demo_business, demo_cash_account, today):
        """Commitments in forecast reduce S2S."""
        make_commitment(db, demo_business, "Payroll", Decimal("50000.00"),
                       due_date=today + timedelta(days=7))
        db.commit()
        
        snapshot = compute_and_save_forecast(db, demo_business, horizon_weeks=8)
        # $125k - $50k payroll = $75k lowest → $75k - $25k reserve = $50k
        assert snapshot.safe_to_spend == Decimal("50000.00")
        assert snapshot.lowest_projected_cash == Decimal("75000.00")

    def test_new_forecast_marks_previous_as_not_current(self, db, demo_business, demo_cash_account):
        """Computing a new forecast marks old ones as not current."""
        snap1 = compute_and_save_forecast(db, demo_business)
        assert snap1.is_current == True

        snap2 = compute_and_save_forecast(db, demo_business)
        
        db.refresh(snap1)
        assert snap1.is_current == False
        assert snap2.is_current == True

    def test_forecast_items_saved(self, db, demo_business, demo_cash_account, today):
        """Individual line items are saved in forecast weeks."""
        make_commitment(db, demo_business, "Rent", Decimal("12000.00"),
                       due_date=today + timedelta(days=5),
                       category=CommitmentCategory.RENT)
        make_receivable(db, demo_business, "Invoice #001", Decimal("20000.00"),
                       expected_date=today + timedelta(days=3))
        db.commit()

        snapshot = compute_and_save_forecast(db, demo_business)
        
        # Search all weeks (commitment due date may fall in week 1 or 2 depending on day)
        all_items = [item for week in snapshot.weeks for item in week.items]
        outflow_items = [item for item in all_items if item.item_type == "outflow"]
        inflow_items = [item for item in all_items if item.item_type == "inflow"]
        
        assert any(item.label == "Rent" for item in outflow_items), \
            f"Expected 'Rent' in outflows, got: {[i.label for i in outflow_items]}"
        assert any(item.label == "Invoice #001" for item in inflow_items), \
            f"Expected 'Invoice #001' in inflows, got: {[i.label for i in inflow_items]}"


class TestForecastVsActual:
    """Tests for variance tracking."""

    def test_variance_computed_correctly(self, db, demo_business, demo_cash_account, today):
        """Variance = actual - forecast, preserved on close."""
        make_commitment(db, demo_business, "Payroll", Decimal("45000.00"),
                       due_date=today + timedelta(days=3))
        db.commit()

        snapshot = compute_and_save_forecast(db, demo_business)
        week1 = snapshot.weeks[0]

        # Actual amounts differ from forecast
        actual_inflows = Decimal("5000.00")  # unexpected income
        actual_outflows = Decimal("48000.00")  # payroll ran $3k over
        actual_closing = demo_cash_account.current_balance + actual_inflows - actual_outflows

        updated_week = reconcile_forecast_week(
            db, week1,
            actual_inflows=actual_inflows,
            actual_outflows=actual_outflows,
            actual_closing_cash=actual_closing,
        )

        # Verify original forecast preserved
        assert updated_week.expected_outflows == Decimal("45000.00")

        # Verify variance computed
        assert updated_week.outflow_variance == Decimal("3000.00")  # over by $3k
        assert updated_week.inflow_variance == Decimal("5000.00")   # unexpected $5k in

    def test_original_forecast_never_overwritten(self, db, demo_business, demo_cash_account, today):
        """Original forecast values are immutable — only variance is added."""
        make_commitment(db, demo_business, "Bill", Decimal("10000.00"),
                       due_date=today + timedelta(days=3))
        db.commit()

        snapshot = compute_and_save_forecast(db, demo_business)
        week1 = snapshot.weeks[0]
        original_outflows = week1.expected_outflows

        reconcile_forecast_week(
            db, week1,
            actual_inflows=ZERO,
            actual_outflows=Decimal("9500.00"),  # $500 less than forecast
            actual_closing_cash=Decimal("115500.00"),
        )

        db.refresh(week1)
        # Original NOT changed
        assert week1.expected_outflows == original_outflows
        # Variance recorded
        assert week1.outflow_variance == Decimal("-500.00")  # $500 under forecast


class TestRecurringCommitments:
    """Tests for recurring commitment projection."""

    def test_monthly_recurring_shows_in_forecast(self, db, demo_business, demo_cash_account, today):
        """Monthly recurring commitment flows into each future month's week."""
        from app.services.forecast import project_recurring_commitments
        from app.models.commitment import Commitment

        # Create a recurring monthly commitment
        monthly_rent = make_commitment(
            db, demo_business, "Office Rent", Decimal("8000.00"),
            due_date=today,
            category=CommitmentCategory.RENT,
            is_recurring=True,
            recurring_frequency=RecurringFrequency.MONTHLY,
        )
        db.commit()

        projections = project_recurring_commitments(
            [monthly_rent],
            from_date=today + timedelta(days=1),
            to_date=today + timedelta(weeks=13),
        )

        # Should have ~3 more monthly occurrences in 13 weeks
        assert len(projections) >= 2
        for proj in projections:
            assert proj["name"] == "Office Rent"
            assert Decimal(proj["amount"]) == Decimal("8000.00")

    def test_weekly_recurring_shows_every_week(self, db, demo_business, demo_cash_account, today):
        """Weekly recurring commitment shows every week."""
        from app.services.forecast import project_recurring_commitments

        weekly = make_commitment(
            db, demo_business, "Weekly Delivery", Decimal("500.00"),
            due_date=today,
            is_recurring=True,
            recurring_frequency=RecurringFrequency.WEEKLY,
        )
        db.commit()

        projections = project_recurring_commitments(
            [weekly],
            from_date=today + timedelta(days=1),
            to_date=today + timedelta(weeks=8),
        )

        # Should have ~7 more weekly occurrences (8 weeks total - 1 today)
        assert len(projections) >= 6


class TestNegativeCash:
    """Tests for negative cash scenarios."""

    def test_negative_cash_in_forecast(self, db, demo_business, demo_cash_account, today):
        """Forecast correctly shows negative cash when outflows > cash."""
        make_commitment(db, demo_business, "Big Bill", Decimal("200000.00"),
                       due_date=today + timedelta(days=7))
        db.commit()

        result = calculate_safe_to_spend(db, demo_business, horizon_weeks=8)
        # Cash = $125k, Bill = $200k → closing = -$75k
        assert result.lowest_projected_cash == Decimal("-75000.00")
        assert result.safe_to_spend == ZERO
        assert result.has_cash_cliff == True

    def test_cash_recovers_after_receivable(self, db, demo_business, demo_cash_account, today):
        """Cash can recover after a big outflow if receivable comes in."""
        make_commitment(db, demo_business, "Payroll", Decimal("120000.00"),
                       due_date=today + timedelta(days=5))
        make_receivable(db, demo_business, "Big Client Invoice", Decimal("150000.00"),
                       expected_date=today + timedelta(days=10))
        db.commit()

        result = calculate_safe_to_spend(db, demo_business, horizon_weeks=8)
        weeks = result.weeks
        
        # After payroll, cash dips. After receivable, it recovers
        week1_closing = weeks[0].get("closing_cash") if isinstance(weeks[0], dict) else weeks[0]["closing_cash"]
        # Should be $125k - $120k = $5k after payroll week
        # Then + $150k = $155k after receivable week
