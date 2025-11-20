"""Unit tests for repository implementations."""

import tempfile
from datetime import date, datetime
from pathlib import Path

import pytest
from pocketsage.infra.repositories import (
    SQLModelAccountRepository,
    SQLModelCategoryRepository,
    SQLModelHabitRepository,
    SQLModelTransactionRepository,
)
from pocketsage.models import Account, Category, Habit, HabitEntry, Transaction, User
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture
def db_engine():
    """Create a temporary in-memory database for testing."""
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    engine = create_engine(f"sqlite:///{db_path}")

    # Create all tables
    SQLModel.metadata.create_all(engine)

    yield engine

    # Cleanup
    engine.dispose()
    db_path.unlink(missing_ok=True)


@pytest.fixture
def session_factory(db_engine):
    """Create a session factory for testing."""

    # Bootstrap a user for scoping
    with Session(db_engine) as session:
        user = User(username="repo-user", password_hash="dummy-hash", role="admin")
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = user.id

    def factory():
        """Create a new session context manager."""
        from contextlib import contextmanager

        @contextmanager
        def session_context():
            session = Session(db_engine)
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

        return session_context()

    factory.user_id = user_id  # type: ignore[attr-defined]
    return factory


def test_category_repository_crud(session_factory):
    """Test category repository CRUD operations."""
    repo = SQLModelCategoryRepository(session_factory)
    uid = session_factory.user_id

    # Create
    category = Category(
        user_id=uid, name="Groceries", slug="groceries", category_type="expense", color="#FF5733"
    )
    created = repo.create(category, user_id=uid)

    assert created.id is not None
    assert created.name == "Groceries"

    # Read
    fetched = repo.get_by_id(created.id, user_id=uid)
    assert fetched is not None
    assert fetched.name == "Groceries"

    # Update
    fetched.name = "Food & Groceries"
    updated = repo.update(fetched, user_id=uid)
    assert updated.name == "Food & Groceries"

    # List
    all_categories = repo.list_all(user_id=uid)
    assert len(all_categories) == 1

    # Delete
    repo.delete(created.id, user_id=uid)
    deleted = repo.get_by_id(created.id, user_id=uid)
    assert deleted is None


def test_category_repository_upsert(session_factory):
    """Test category upsert by slug."""
    repo = SQLModelCategoryRepository(session_factory)
    uid = session_factory.user_id

    # Insert new
    category1 = Category(user_id=uid, name="Transport", slug="transport", category_type="expense")
    upserted1 = repo.upsert_by_slug(category1, user_id=uid)
    assert upserted1.id is not None

    # Update existing
    category2 = Category(
        user_id=uid,
        name="Transportation",
        slug="transport",
        category_type="expense",
        color="#0000FF",
    )
    upserted2 = repo.upsert_by_slug(category2, user_id=uid)

    # Should have same ID
    assert upserted2.id == upserted1.id
    assert upserted2.name == "Transportation"
    assert upserted2.color == "#0000FF"


def test_account_repository_crud(session_factory):
    """Test account repository CRUD operations."""
    repo = SQLModelAccountRepository(session_factory)
    uid = session_factory.user_id

    # Create
    account = Account(name="Checking", currency="USD", user_id=uid)
    created = repo.create(account, user_id=uid)

    assert created.id is not None
    assert created.name == "Checking"

    # Get by name
    fetched = repo.get_by_name("Checking", user_id=uid)
    assert fetched is not None
    assert fetched.id == created.id

    # List all
    accounts = repo.list_all(user_id=uid)
    assert len(accounts) == 1

    # Delete
    repo.delete(created.id, user_id=uid)
    deleted = repo.get_by_id(created.id, user_id=uid)
    assert deleted is None


def test_transaction_repository_crud(session_factory):
    """Test transaction repository CRUD operations."""
    repo = SQLModelTransactionRepository(session_factory)
    uid = session_factory.user_id

    # Create
    transaction = Transaction(
        user_id=uid,
        amount=-50.00,
        memo="Groceries at Whole Foods",
        occurred_at=datetime.now(),
    )
    created = repo.create(transaction, user_id=uid)

    assert created.id is not None
    assert created.amount == -50.00

    # List all
    transactions = repo.list_all(limit=10, user_id=uid)
    assert len(transactions) == 1

    # Update
    created.memo = "Groceries at Trader Joe's"
    updated = repo.update(created, user_id=uid)
    assert updated.memo == "Groceries at Trader Joe's"

    # Delete
    repo.delete(created.id, user_id=uid)
    deleted = repo.get_by_id(created.id, user_id=uid)
    assert deleted is None


def test_transaction_repository_date_filter(session_factory):
    """Test transaction filtering by date range."""
    repo = SQLModelTransactionRepository(session_factory)
    uid = session_factory.user_id

    # Create transactions with different dates
    today = datetime.now()
    yesterday = today.replace(day=today.day - 1) if today.day > 1 else today

    t1 = Transaction(user_id=uid, amount=-25.00, memo="Yesterday", occurred_at=yesterday)
    t2 = Transaction(user_id=uid, amount=-30.00, memo="Today", occurred_at=today)

    repo.create(t1, user_id=uid)
    repo.create(t2, user_id=uid)

    # Filter by date range
    start = today.replace(hour=0, minute=0, second=0, microsecond=0)
    end = today.replace(hour=23, minute=59, second=59, microsecond=999999)

    filtered = repo.filter_by_date_range(start, end, user_id=uid)
    assert len(filtered) == 1
    assert filtered[0].memo == "Today"


def test_habit_repository_crud(session_factory):
    """Test habit repository CRUD operations."""
    repo = SQLModelHabitRepository(session_factory)
    uid = session_factory.user_id

    # Create
    habit = Habit(name="Exercise", description="30 minutes daily", is_active=True, user_id=uid)
    created = repo.create(habit, user_id=uid)

    assert created.id is not None
    assert created.name == "Exercise"

    # List active
    active_habits = repo.list_active(user_id=uid)
    assert len(active_habits) == 1

    # Update
    created.is_active = False
    updated = repo.update(created, user_id=uid)
    assert updated.is_active is False

    # List active (should be empty now)
    active_habits = repo.list_active(user_id=uid)
    assert len(active_habits) == 0

    # List all (including inactive)
    all_habits = repo.list_all(user_id=uid, include_inactive=True)
    assert len(all_habits) == 1


def test_habit_entry_upsert(session_factory):
    """Test habit entry upsert."""
    repo = SQLModelHabitRepository(session_factory)
    uid = session_factory.user_id

    # Create habit first
    habit = Habit(name="Meditation", user_id=uid)
    habit = repo.create(habit, user_id=uid)

    # Create entry
    today = date.today()
    entry1 = HabitEntry(habit_id=habit.id, occurred_on=today, value=1, user_id=uid)
    upserted1 = repo.upsert_entry(entry1, user_id=uid)

    assert upserted1.value == 1

    # Update entry
    entry2 = HabitEntry(habit_id=habit.id, occurred_on=today, value=2, user_id=uid)
    upserted2 = repo.upsert_entry(entry2, user_id=uid)

    # Should update, not create new
    assert upserted2.value == 2

    # Verify only one entry exists
    entries = repo.get_entries_for_habit(habit.id, today, today, user_id=uid)
    assert len(entries) == 1
    assert entries[0].value == 2


def test_transaction_monthly_summary(session_factory):
    """Test monthly summary calculation."""
    repo = SQLModelTransactionRepository(session_factory)
    uid = session_factory.user_id

    # Create some transactions for current month
    today = datetime.now()
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Income transactions
    repo.create(
        Transaction(user_id=uid, amount=1000.00, memo="Salary", occurred_at=month_start),
        user_id=uid,
    )
    repo.create(
        Transaction(user_id=uid, amount=500.00, memo="Bonus", occurred_at=month_start),
        user_id=uid,
    )

    # Expense transactions
    repo.create(
        Transaction(user_id=uid, amount=-200.00, memo="Rent", occurred_at=month_start),
        user_id=uid,
    )
    repo.create(
        Transaction(user_id=uid, amount=-50.00, memo="Groceries", occurred_at=month_start),
        user_id=uid,
    )

    # Get summary
    summary = repo.get_monthly_summary(today.year, today.month, user_id=uid)

    assert summary["income"] == 1500.00
    assert summary["expenses"] == 250.00
    assert summary["net"] == 1250.00
