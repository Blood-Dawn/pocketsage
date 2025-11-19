"""Tests to verify money representation and prevent float precision bugs.

Current state: The application uses float for money fields (Transaction.amount,
Liability.balance, etc.). This test suite documents the behavior and catches
regressions where floats might introduce precision errors.

Future improvement: Consider migrating to Decimal or integer cents for exact
money representation in production.
"""

from __future__ import annotations

from tests.conftest import assert_float_equal


class TestTransactionMoneyFields:
    """Tests for Transaction money field representation."""

    def test_transaction_amount_is_float(self, transaction_factory):
        """Transaction amount should be stored as float (current implementation)."""
        transaction = transaction_factory(amount=100.50)

        assert isinstance(transaction.amount, float)
        assert transaction.amount == 100.50

    def test_negative_amounts_for_expenses(self, transaction_factory):
        """Expense transactions should have negative amounts."""
        transaction = transaction_factory(amount=-50.75, memo="Groceries")

        assert transaction.amount < 0
        assert transaction.amount == -50.75

    def test_positive_amounts_for_income(self, transaction_factory):
        """Income transactions should have positive amounts."""
        transaction = transaction_factory(amount=1000.00, memo="Salary")

        assert transaction.amount > 0
        assert transaction.amount == 1000.00

    def test_zero_amount_transaction(self, transaction_factory):
        """Zero-amount transactions should be allowed."""
        transaction = transaction_factory(amount=0.00, memo="Zero transfer")

        assert transaction.amount == 0.00

    def test_small_cent_values(self, transaction_factory):
        """Small cent values should be represented correctly."""
        # This is where floats can have precision issues
        transaction = transaction_factory(amount=0.01, memo="One cent")

        # Use approximate comparison for floats
        assert_float_equal(transaction.amount, 0.01, tolerance=0.001)

    def test_large_money_values(self, transaction_factory):
        """Large money values should be handled correctly."""
        # Test with large amounts (e.g., house purchase)
        transaction = transaction_factory(amount=-500000.00, memo="House down payment")

        assert transaction.amount == -500000.00

    def test_many_decimal_places_gets_rounded(self, transaction_factory):
        """Amounts with many decimal places should be handled (may lose precision)."""
        # SQLite float storage may not preserve all decimal places
        # This documents the current behavior
        transaction = transaction_factory(amount=100.999999, memo="Many decimals")

        # Should be approximately equal (float precision limits)
        assert_float_equal(transaction.amount, 100.999999, tolerance=0.01)


class TestLiabilityMoneyFields:
    """Tests for Liability (debt) money field representation."""

    def test_liability_balance_is_float(self, liability_factory):
        """Liability balance should be stored as float."""
        liability = liability_factory(balance=5000.00)

        assert isinstance(liability.balance, float)
        assert liability.balance == 5000.00

    def test_liability_apr_percentage(self, liability_factory):
        """APR should be stored as float percentage (e.g., 18.0 for 18%)."""
        liability = liability_factory(apr=18.5)

        assert isinstance(liability.apr, float)
        assert liability.apr == 18.5

    def test_minimum_payment_precision(self, liability_factory):
        """Minimum payment should handle cents correctly."""
        liability = liability_factory(minimum_payment=35.99)

        assert_float_equal(liability.minimum_payment, 35.99)


class TestBudgetMoneyFields:
    """Tests for Budget money field representation."""

    def test_budget_line_planned_amount_is_float(self, budget_factory, category_factory):
        """BudgetLine planned_amount should be float."""
        category = category_factory(name="Groceries")

        budget = budget_factory(
            label="January Budget",
            lines=[
                {"category_id": category.id, "planned_amount": 500.00},
            ],
        )

        # Reload to verify persistence
        assert len(budget.lines) == 1
        assert isinstance(budget.lines[0].planned_amount, float)
        assert budget.lines[0].planned_amount == 500.00


class TestHoldingMoneyFields:
    """Tests for Portfolio Holding money field representation."""

    def test_holding_quantity_is_float(self, holding_factory):
        """Holding quantity (shares) should be float to support fractional shares."""
        holding = holding_factory(symbol="AAPL", quantity=10.5, avg_price=150.00)

        assert isinstance(holding.quantity, float)
        assert holding.quantity == 10.5

    def test_holding_avg_price_is_float(self, holding_factory):
        """Holding average price should be float."""
        holding = holding_factory(symbol="AAPL", quantity=10.0, avg_price=150.75)

        assert isinstance(holding.avg_price, float)
        assert holding.avg_price == 150.75

    def test_holding_cost_basis_calculation(self, holding_factory):
        """Cost basis (quantity * avg_price) should be calculated correctly."""
        holding = holding_factory(symbol="AAPL", quantity=10.0, avg_price=150.00)

        cost_basis = holding.quantity * holding.avg_price
        assert_float_equal(cost_basis, 1500.00)


class TestFloatPrecisionEdgeCases:
    """Tests for known float precision issues and workarounds."""

    def test_repeated_addition_accumulates_error(self, transaction_factory):
        """Repeated float addition can accumulate rounding errors.

        This test documents the issue. In production, consider using Decimal
        for exact arithmetic.
        """
        # Simulate repeated 0.1 additions (known float precision issue)
        total = 0.0
        for _ in range(10):
            total += 0.1

        # Due to float representation, this is NOT exactly 1.0
        # This is a known limitation of binary floating-point
        # With Decimal, we would get exactly 1.0
        assert abs(total - 1.0) < 0.0001  # Small tolerance needed

    def test_currency_conversion_precision(self):
        """Currency conversions should be done with care for precision."""
        # Example: converting USD to cents and back
        usd_amount = 19.99
        cents = int(usd_amount * 100)  # Convert to integer cents
        back_to_usd = cents / 100.0

        # Should round-trip correctly
        assert_float_equal(back_to_usd, usd_amount)

    def test_percentage_calculations_with_floats(self):
        """Percentage calculations should be within acceptable tolerance."""
        principal = 1000.00
        rate = 0.185  # 18.5%

        interest = principal * rate
        expected = 185.00

        # Float arithmetic should be close enough for this case
        assert_float_equal(interest, expected)

    def test_division_rounding_behavior(self):
        """Division should be handled carefully for money calculations."""
        # Example: splitting a bill 3 ways
        total = 100.00
        split = total / 3

        # Each person pays $33.33 (repeating)
        # With floats, we get an approximation
        assert abs(split - 33.333333) < 0.001

        # If we round each share to 2 decimals
        rounded_split = round(split, 2)
        assert rounded_split == 33.33

        # Note: 3 * 33.33 = 99.99, not 100.00
        # This is why we need careful rounding in real applications


class TestSummationAccuracy:
    """Tests for accuracy of summing money amounts."""

    def test_sum_transaction_amounts(self, transaction_factory):
        """Summing transaction amounts should be accurate within tolerance."""
        transactions = [
            transaction_factory(amount=100.00),
            transaction_factory(amount=-50.00),
            transaction_factory(amount=25.50),
            transaction_factory(amount=-10.75),
        ]

        total = sum(t.amount for t in transactions)
        expected = 64.75

        assert_float_equal(total, expected)

    def test_sum_large_number_of_transactions(self, transaction_factory):
        """Summing many transactions should not accumulate significant error."""
        # Create 100 transactions of $1.00 each
        transactions = [transaction_factory(amount=1.00) for _ in range(100)]

        total = sum(t.amount for t in transactions)
        expected = 100.00

        # Should be very close
        assert_float_equal(total, expected, tolerance=0.01)

    def test_net_cash_flow_calculation(self, transaction_factory):
        """Net cash flow (income - expenses) should be accurate."""
        # Income
        income_txs = [
            transaction_factory(amount=1000.00),
            transaction_factory(amount=500.00),
        ]

        # Expenses (negative amounts)
        expense_txs = [
            transaction_factory(amount=-200.00),
            transaction_factory(amount=-150.50),
            transaction_factory(amount=-75.25),
        ]

        total_income = sum(t.amount for t in income_txs if t.amount > 0)
        total_expenses = abs(sum(t.amount for t in expense_txs if t.amount < 0))
        net = total_income - total_expenses

        expected_net = 1500.00 - 425.75
        assert_float_equal(net, expected_net)


class TestRecommendationsForProduction:
    """Documentation tests for production best practices.

    These tests don't assert behavior but document recommendations for
    handling money in production systems.
    """

    def test_decimal_recommendation_for_exact_arithmetic(self):
        """For exact money arithmetic, use Decimal instead of float.

        from decimal import Decimal

        # Exact representation
        price = Decimal('19.99')
        quantity = Decimal('3')
        total = price * quantity  # Exactly 59.97

        # vs float:
        price_float = 19.99
        quantity_float = 3.0
        total_float = price_float * quantity_float  # May have precision error
        """
        from decimal import Decimal

        # Decimal version (exact)
        decimal_total = Decimal("19.99") * Decimal("3")
        assert decimal_total == Decimal("59.97")

        # Float version (approximate)
        float_total = 19.99 * 3.0
        assert_float_equal(float_total, 59.97, tolerance=0.01)

        # Decimal is exact, float needs tolerance

    def test_integer_cents_recommendation_for_storage(self):
        """Alternative: store money as integer cents.

        # Store as cents (integer)
        amount_cents = 1999  # $19.99
        amount_dollars = amount_cents / 100.0  # Convert for display

        # All arithmetic in cents (exact)
        total_cents = amount_cents * 3  # 5997 cents
        total_dollars = total_cents / 100.0  # $59.97

        This avoids float precision issues entirely.
        """
        # Store as integer cents
        amount_cents = 1999  # $19.99
        quantity = 3

        total_cents = amount_cents * quantity  # Exact integer arithmetic
        assert total_cents == 5997

        total_dollars = total_cents / 100.0
        assert_float_equal(total_dollars, 59.97)

    def test_rounding_recommendation_for_display(self):
        """Always round to 2 decimals before displaying to users.

        # Calculation may have many decimals
        calculated = 19.999999

        # Round for display
        display = round(calculated, 2)
        assert display == 20.00
        """
        calculated = 19.999999
        display = round(calculated, 2)

        assert display == 20.00
        assert isinstance(display, float)

    def test_round_half_up_for_financial_rounding(self):
        """Use ROUND_HALF_UP for financial rounding (banker's rounding alternative).

        from decimal import Decimal, ROUND_HALF_UP

        # Round to 2 decimal places
        amount = Decimal('19.995')
        rounded = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        # Result: 20.00 (rounds up from .5)
        """
        from decimal import ROUND_HALF_UP, Decimal

        amount = Decimal("19.995")
        rounded = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        assert rounded == Decimal("20.00")
