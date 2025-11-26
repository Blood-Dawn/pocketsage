"""Pytest configuration and shared fixtures for PocketSage tests.

This module provides database fixtures, test data factories, and helper utilities
for testing domain logic, repositories, and services without touching the real app database.
"""

from __future__ import annotations

import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

import pytest

# Import all models to ensure they're registered with SQLModel metadata
from pocketsage.models import (
    Account,
    Budget,
    BudgetLine,
    Category,
    Habit,
    Liability,
    Transaction,
    User,
)
from pocketsage.models.portfolio import Holding
from sqlmodel import Session, SQLModel, create_engine, select

# Ensure stdout/stderr use UTF-8 and safe flush to avoid encoding/invalid-handle issues on Windows CI/console
def _safe_stream(stream):
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    class _Wrapper:
        def __init__(self, inner):
            self._inner = inner
        def write(self, data):
            return self._inner.write(data)
        def flush(self):
            try:
                return self._inner.flush()
            except OSError:
                return None
        def __getattr__(self, name):
            return getattr(self._inner, name)
    return _Wrapper(stream)

# Apply immediately on import to influence pytest's terminal streams
sys.stdout = _safe_stream(sys.stdout)
sys.stderr = _safe_stream(sys.stderr)
sys.__stdout__ = _safe_stream(sys.__stdout__)
sys.__stderr__ = _safe_stream(sys.__stderr__)


def pytest_sessionstart(session):
    """Normalize stdout/stderr encoding before tests run."""
    sys.stdout = _safe_stream(sys.stdout)
    sys.stderr = _safe_stream(sys.stderr)
    sys.__stdout__ = _safe_stream(sys.__stdout__)
    sys.__stderr__ = _safe_stream(sys.__stderr__)


def pytest_unconfigure(config):
    """Re-apply safe streams before pytest finalizes (avoids flush OSError on Windows)."""
    sys.stdout = _safe_stream(sys.stdout)
    sys.stderr = _safe_stream(sys.stderr)
    sys.__stdout__ = _safe_stream(sys.__stdout__)
    sys.__stderr__ = _safe_stream(sys.__stderr__)

# =============================================================================
# Database Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def db_engine():
    """Create an isolated in-memory SQLite database for each test.

    Each test gets a fresh database with all tables created.
    The database is automatically cleaned up after the test.

    Yields:
        Engine: SQLModel engine connected to test database
    """
    # Create temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    # Create engine with test database
    engine = create_engine(f"sqlite:///{db_path}", echo=False)

    # Create all tables from SQLModel metadata
    SQLModel.metadata.create_all(engine)

    yield engine

    # Cleanup: close connections and delete database file
    engine.dispose()
    db_path.unlink(missing_ok=True)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a database session for a single test.

    The session is automatically rolled back after the test to ensure isolation.

    Args:
        db_engine: Database engine fixture

    Yields:
        Session: SQLModel session for test
    """
    session = Session(db_engine, expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@pytest.fixture(scope="function")
def session_factory(db_engine):
    """Create a session factory for repositories that expect Callable[[], Session].

    This fixture returns a function that creates context managers for sessions,
    matching the pattern used in repository implementations.

    Args:
        db_engine: Database engine fixture

    Returns:
        Callable: Factory function that returns session context managers
    """

    def factory():
        """Create a new Session with expire_on_commit disabled."""

        def session_context():
            return Session(db_engine, expire_on_commit=False)

        return session_context()

    # Bootstrap a default user for tests
    with factory() as session:
        existing = session.exec(select(User).limit(1)).first()
        if existing is None:
            user_row = User(username="tester", password_hash="dummy-hash", role="admin")
            session.add(user_row)
            session.commit()
            session.refresh(user_row)
            existing = user_row
        factory.user = existing  # type: ignore[attr-defined]

    return factory


# =============================================================================
# Test Data Factories
# =============================================================================


@pytest.fixture
def user(db_session) -> User:
    """Create a default user for scoping data."""

    existing = db_session.exec(select(User).where(User.username == "tester")).first()
    if existing:
        return existing
    u = User(username="tester", password_hash="dummy-hash", role="admin")
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def category_factory(db_session, user):
    """Factory for creating test categories.

    Returns:
        Callable: Function that creates and persists Category instances
    """

    def _create_category(
        name: str = "Test Category",
        slug: str | None = None,
        category_type: str = "expense",
        color: str = "#FF5733",
        owner: User | None = None,
    ) -> Category:
        """Create a test category with sensible defaults.

        Args:
            name: Category display name
            slug: URL-safe identifier (auto-generated from name if not provided)
            category_type: Either 'income' or 'expense'
            color: Hex color code

        Returns:
            Category: Persisted category instance
        """
        if slug is None:
            slug = name.lower().replace(" ", "-")

        owner = owner or user
        category = Category(
            user_id=owner.id,
            name=name,
            slug=slug,
            category_type=category_type,
            color=color,
        )
        db_session.add(category)
        db_session.commit()
        db_session.refresh(category)
        return category

    return _create_category


@pytest.fixture
def account_factory(db_session, user):
    """Factory for creating test accounts.

    Returns:
        Callable: Function that creates and persists Account instances
    """

    def _create_account(
        name: str = "Test Account",
        currency: str = "USD",
        owner: User | None = None,
    ) -> Account:
        """Create a test account with sensible defaults.

        Args:
            name: Account display name
            currency: ISO-4217 currency code (e.g., 'USD', 'EUR')

        Returns:
            Account: Persisted account instance
        """
        owner = owner or user
        account = Account(name=name, currency=currency, user_id=owner.id)
        db_session.add(account)
        db_session.commit()
        db_session.refresh(account)
        return account

    return _create_account


@pytest.fixture
def transaction_factory(db_session, user):
    """Factory for creating test transactions.

    Returns:
        Callable: Function that creates and persists Transaction instances
    """

    def _create_transaction(
        amount: float,
        memo: str = "Test transaction",
        occurred_at: datetime | None = None,
        category_id: int | None = None,
        account_id: int | None = None,
        external_id: str | None = None,
        currency: str = "USD",
        owner: User | None = None,
    ) -> Transaction:
        """Create a test transaction with sensible defaults.

        Args:
            amount: Transaction amount (positive for income, negative for expense)
            memo: Description of transaction
            occurred_at: Transaction timestamp (defaults to now)
            category_id: Foreign key to category
            account_id: Foreign key to account
            external_id: External system identifier for dedupe
            currency: ISO-4217 currency code

        Returns:
            Transaction: Persisted transaction instance
        """
        if occurred_at is None:
            occurred_at = datetime.now()

        owner = owner or user
        transaction = Transaction(
            user_id=owner.id,
            amount=amount,
            memo=memo,
            occurred_at=occurred_at,
            category_id=category_id,
            account_id=account_id,
            external_id=external_id,
            currency=currency,
        )
        db_session.add(transaction)
        db_session.commit()
        db_session.refresh(transaction)
        return transaction

    return _create_transaction


@pytest.fixture
def liability_factory(db_session, user):
    """Factory for creating test liabilities (debts).

    Returns:
        Callable: Function that creates and persists Liability instances
    """

    def _create_liability(
        name: str = "Test Debt",
        balance: float = 1000.00,
        apr: float = 18.0,
        minimum_payment: float = 25.00,
        due_day: int = 15,
        payoff_strategy: str = "snowball",
        owner: User | None = None,
    ) -> Liability:
        """Create a test liability with sensible defaults.

        Args:
            name: Debt name/description
            balance: Current outstanding balance
            apr: Annual percentage rate (e.g., 18.0 for 18%)
            minimum_payment: Minimum monthly payment
            due_day: Day of month payment is due (1-28)
            payoff_strategy: Either 'snowball' or 'avalanche'

        Returns:
            Liability: Persisted liability instance
        """
        owner = owner or user
        liability = Liability(
            user_id=owner.id,
            name=name,
            balance=balance,
            apr=apr,
            minimum_payment=minimum_payment,
            due_day=due_day,
            payoff_strategy=payoff_strategy,
        )
        db_session.add(liability)
        db_session.commit()
        db_session.refresh(liability)
        return liability

    return _create_liability


@pytest.fixture
def habit_factory(db_session, user):
    """Factory for creating test habits.

    Returns:
        Callable: Function that creates and persists Habit instances
    """

    def _create_habit(
        name: str = "Test Habit",
        description: str = "Test habit description",
        cadence: str = "daily",
        is_active: bool = True,
        owner: User | None = None,
    ) -> Habit:
        """Create a test habit with sensible defaults.

        Args:
            name: Habit name
            description: Habit description
            cadence: Frequency cadence (e.g., 'daily', 'weekly')
            is_active: Whether habit is currently active

        Returns:
            Habit: Persisted habit instance
        """
        owner = owner or user
        habit = Habit(
            user_id=owner.id,
            name=name,
            description=description,
            cadence=cadence,
            is_active=is_active,
        )
        db_session.add(habit)
        db_session.commit()
        db_session.refresh(habit)
        return habit

    return _create_habit


@pytest.fixture
def budget_factory(db_session, user):
    """Factory for creating test budgets with budget lines.

    Returns:
        Callable: Function that creates and persists Budget instances
    """

    def _create_budget(
        period_start: date | None = None,
        period_end: date | None = None,
        label: str = "Test Budget",
        lines: list[dict] | None = None,
        owner: User | None = None,
    ) -> Budget:
        """Create a test budget with optional budget lines.

        Args:
            period_start: Budget start date (defaults to first day of current month)
            period_end: Budget end date (defaults to last day of current month)
            label: Budget label/description
            lines: List of dicts with keys: category_id, planned_amount, rollover_enabled

        Returns:
            Budget: Persisted budget instance with lines
        """
        if period_start is None:
            today = date.today()
            period_start = date(today.year, today.month, 1)

        if period_end is None:
            # Calculate last day of month
            from calendar import monthrange

            today = date.today()
            last_day = monthrange(today.year, today.month)[1]
            period_end = date(today.year, today.month, last_day)

        owner = owner or user
        budget = Budget(
            user_id=owner.id,
            period_start=period_start,
            period_end=period_end,
            label=label,
        )
        db_session.add(budget)
        db_session.commit()
        db_session.refresh(budget)

        # Add budget lines if provided
        if lines:
            for line_data in lines:
                line = BudgetLine(
                    user_id=owner.id,
                    budget_id=budget.id,
                    category_id=line_data["category_id"],
                    planned_amount=line_data.get("planned_amount", 0.0),
                    rollover_enabled=line_data.get("rollover_enabled", False),
                )
                db_session.add(line)

            db_session.commit()
            db_session.refresh(budget)

        return budget

    return _create_budget


@pytest.fixture
def holding_factory(db_session, user):
    """Factory for creating test portfolio holdings.

    Returns:
        Callable: Function that creates and persists Holding instances
    """

    def _create_holding(
        symbol: str = "TEST",
        quantity: float = 10.0,
        avg_price: float = 100.00,
        account_id: int | None = None,
        currency: str = "USD",
        owner: User | None = None,
    ) -> Holding:
        """Create a test portfolio holding with sensible defaults.

        Args:
            symbol: Stock/asset ticker symbol
            quantity: Number of shares/units
            avg_price: Average cost basis per share
            account_id: Foreign key to account (optional)
            currency: ISO-4217 currency code

        Returns:
            Holding: Persisted holding instance
        """
        owner = owner or user
        holding = Holding(
            user_id=owner.id,
            symbol=symbol,
            quantity=quantity,
            avg_price=avg_price,
            account_id=account_id,
            currency=currency,
        )
        db_session.add(holding)
        db_session.commit()
        db_session.refresh(holding)
        return holding

    return _create_holding


# =============================================================================
# Seed Data Fixtures
# =============================================================================


@pytest.fixture
def seed_categories(category_factory):
    """Create a standard set of categories for testing.

    Returns:
        dict: Dictionary mapping category slugs to Category instances
    """
    categories = {
        "groceries": category_factory(
            name="Groceries",
            slug="groceries",
            category_type="expense",
            color="#FF5733",
        ),
        "salary": category_factory(
            name="Salary",
            slug="salary",
            category_type="income",
            color="#33FF57",
        ),
        "rent": category_factory(
            name="Rent",
            slug="rent",
            category_type="expense",
            color="#3357FF",
        ),
        "utilities": category_factory(
            name="Utilities",
            slug="utilities",
            category_type="expense",
            color="#FF33A1",
        ),
    }
    return categories


@pytest.fixture
def seed_accounts(account_factory):
    """Create a standard set of accounts for testing.

    Returns:
        dict: Dictionary mapping account names to Account instances
    """
    accounts = {
        "checking": account_factory(name="Checking Account", currency="USD"),
        "savings": account_factory(name="Savings Account", currency="USD"),
    }
    return accounts


# =============================================================================
# Helper Utilities
# =============================================================================


def assert_float_equal(actual: float, expected: float, tolerance: float = 0.01):
    """Assert that two floats are equal within a tolerance.

    This is necessary because financial calculations with floats can have
    small rounding differences. For production code, consider using Decimal.

    Args:
        actual: Actual value
        expected: Expected value
        tolerance: Maximum allowed difference (default 0.01 = 1 cent)

    Raises:
        AssertionError: If values differ by more than tolerance
    """
    assert (
        abs(actual - expected) < tolerance
    ), f"Expected {expected}, got {actual} (diff: {abs(actual - expected)})"
