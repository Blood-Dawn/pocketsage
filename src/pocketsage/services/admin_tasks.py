"""Admin utilities for the desktop app (demo seed, exports, retention)."""
# TODO(@pocketsage-admin): Support light vs heavy seed profiles and measure seed performance.
# TODO(@pocketsage-admin): Add safety checks before destructive reset operations.

# TODO(@codex): Admin service functions for data management
#    - Demo data seeding (run_demo_seed) - creates sample data (DONE)
#    - Backup export (backup_database) - exports all data to zip (DONE)
#    - Restore from backup (restore_database) - imports from zip (DONE)
#    - Reset database (reset_demo_database) - clears user data (DONE)
#    - Export reports (run_export) - generates charts and CSVs (DONE)
#    - Ensure idempotent seeding (no duplicates on re-run)
#    - Log operations for debugging

from __future__ import annotations

import os
import random
from calendar import monthrange
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Iterator, Optional
from zipfile import ZipFile

from sqlalchemy import func
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, select

from ..config import BaseConfig
from ..infra.database import create_db_engine, init_database
from ..infra.database import session_scope as infra_session_scope
from ..models import Account, Budget, BudgetLine, Category, Habit, HabitEntry, Holding, Liability, Transaction
from .export_csv import export_transactions_csv
from .reports import export_spending_png

SessionFactory = Callable[[], AbstractContextManager[Session]]

_ENGINE = None


@dataclass(frozen=True)
class SeedSummary:
    """Aggregate counts returned after demo seeding."""

    transactions: int
    categories: int
    accounts: int
    habits: int
    liabilities: int
    budgets: int


def _get_engine():
    """Initialize and cache the SQLModel engine for background tasks."""

    global _ENGINE
    if _ENGINE is None:
        config = BaseConfig()
        _ENGINE = create_db_engine(config)
        init_database(_ENGINE)
    return _ENGINE


@contextmanager
def _get_session(session_factory: Optional[SessionFactory] = None) -> Iterator[Session]:
    """Yield a session from the provided factory or the shared engine."""

    if session_factory is not None:
        with session_factory() as session:
            yield session
        return

    engine = _get_engine()
    with infra_session_scope(engine) as session:
        yield session


def _resolve_engine(session_factory: Optional[SessionFactory]) -> Engine:
    """Resolve the engine used by the provided session factory if possible."""

    if session_factory is None:
        return _get_engine()

    with session_factory() as session:
        bind = session.get_bind()
        if bind is None:  # pragma: no cover - defensive guard
            raise RuntimeError("Session is not bound to an engine")
        if isinstance(bind, Connection):
            return bind.engine
        if isinstance(bind, Engine):
            return bind
        raise RuntimeError(f"Unsupported bind type: {type(bind)!r}")


def _seed_categories(session: Session, user_id: int) -> dict[str, Category]:
    # Core set aligns with dashboards/graphs and heavy seed generator.
    categories_seed = [
        # Expenses
        {"name": "Groceries", "slug": "groceries", "category_type": "expense", "color": "#4CAF50"},
        {"name": "Dining Out", "slug": "dining-out", "category_type": "expense", "color": "#FF7043"},
        {"name": "Rent", "slug": "rent", "category_type": "expense", "color": "#8D6E63"},
        {"name": "Mortgage", "slug": "mortgage", "category_type": "expense", "color": "#5D4037"},
        {"name": "Utilities", "slug": "utilities", "category_type": "expense", "color": "#29B6F6"},
        {"name": "Internet", "slug": "internet", "category_type": "expense", "color": "#0277BD"},
        {"name": "Phone", "slug": "phone", "category_type": "expense", "color": "#5C6BC0"},
        {"name": "Insurance", "slug": "insurance", "category_type": "expense", "color": "#546E7A"},
        {"name": "Gas", "slug": "gas", "category_type": "expense", "color": "#AB47BC"},
        {"name": "Transit", "slug": "transit", "category_type": "expense", "color": "#7E57C2"},
        {"name": "Medical", "slug": "medical", "category_type": "expense", "color": "#C62828"},
        {"name": "Subscriptions", "slug": "subscriptions", "category_type": "expense", "color": "#6D4C41"},
        {"name": "Gaming", "slug": "gaming", "category_type": "expense", "color": "#9C27B0"},
        {"name": "Clothing", "slug": "clothing", "category_type": "expense", "color": "#8E24AA"},
        {"name": "Gifts", "slug": "gifts", "category_type": "expense", "color": "#D81B60"},
        {"name": "Travel", "slug": "travel", "category_type": "expense", "color": "#00897B"},
        {"name": "Education", "slug": "education", "category_type": "expense", "color": "#039BE5"},
        {"name": "Pets", "slug": "pets", "category_type": "expense", "color": "#6D4C41"},
        {"name": "Household", "slug": "household", "category_type": "expense", "color": "#9E9D24"},
        {"name": "Entertainment", "slug": "entertainment", "category_type": "expense", "color": "#F4511E"},
        {"name": "Coffee", "slug": "coffee", "category_type": "expense", "color": "#795548"},
        {"name": "Wellness", "slug": "wellness", "category_type": "expense", "color": "#8D6E63"},
        {"name": "Childcare", "slug": "childcare", "category_type": "expense", "color": "#F57C00"},
        {"name": "Charity", "slug": "charity", "category_type": "expense", "color": "#AD1457"},
        # Income / transfers
        {"name": "Salary", "slug": "salary", "category_type": "income", "color": "#2E7D32"},
        {"name": "Bonus", "slug": "bonus", "category_type": "income", "color": "#4CAF50"},
        {"name": "Interest", "slug": "interest", "category_type": "income", "color": "#1B5E20"},
        {"name": "Dividends", "slug": "dividends", "category_type": "income", "color": "#00796B"},
        {"name": "Side Hustle", "slug": "side-hustle", "category_type": "income", "color": "#00695C"},
        {"name": "Refund", "slug": "refund", "category_type": "income", "color": "#558B2F"},
        {"name": "Transfer In", "slug": "transfer-in", "category_type": "income", "color": "#00796B"},
        {"name": "Transfer Out", "slug": "transfer-out", "category_type": "expense", "color": "#00838F"},
        {"name": "Payment", "slug": "payment", "category_type": "expense", "color": "#AD1457"},
        {"name": "Rebalance", "slug": "rebalance", "category_type": "income", "color": "#00695C"},
    ]
    categories: dict[str, Category] = {}
    for payload in categories_seed:
        existing = session.exec(
            select(Category).where(Category.slug == payload["slug"], Category.user_id == user_id)
        ).first()
        if existing:
            categories[payload["slug"]] = existing
            continue
        category = Category(user_id=user_id, **payload)
        session.add(category)
        session.flush()
        categories[payload["slug"]] = category
    session.flush()
    return categories


def _seed_accounts(session: Session, user_id: int) -> dict[str, Account]:
    accounts_seed = [
        # Core banking accounts
        {"name": "Primary Checking", "currency": "USD", "account_type": "checking", "balance": 4250.00},
        {"name": "Joint Checking", "currency": "USD", "account_type": "checking", "balance": 1875.50},
        {"name": "Emergency Fund", "currency": "USD", "account_type": "savings", "balance": 12500.00},
        {"name": "Vacation Savings", "currency": "USD", "account_type": "savings", "balance": 3200.00},
        {"name": "Cash on Hand", "currency": "USD", "account_type": "cash", "balance": 185.00},

        # Credit cards
        {"name": "Chase Sapphire", "currency": "USD", "account_type": "credit", "balance": -2340.67},
        {"name": "Amazon Prime Card", "currency": "USD", "account_type": "credit", "balance": -567.89},
        {"name": "Capital One Quicksilver", "currency": "USD", "account_type": "credit", "balance": -125.00},

        # Loans
        {"name": "Auto Loan - Honda", "currency": "USD", "account_type": "loan", "balance": -18750.00},
        {"name": "Personal Loan", "currency": "USD", "account_type": "loan", "balance": -4500.00},
        {"name": "Home Mortgage", "currency": "USD", "account_type": "mortgage", "balance": -267500.00},

        # Investment accounts
        {"name": "Fidelity Brokerage", "currency": "USD", "account_type": "brokerage", "balance": 45000.00},
        {"name": "Vanguard IRA", "currency": "USD", "account_type": "retirement", "balance": 78500.00},
        {"name": "Company 401(k)", "currency": "USD", "account_type": "retirement", "balance": 142000.00},
        {"name": "Robinhood", "currency": "USD", "account_type": "investment", "balance": 8750.00},

        # Crypto
        {"name": "Coinbase", "currency": "USD", "account_type": "crypto", "balance": 6200.00},
        {"name": "Ledger Cold Wallet", "currency": "USD", "account_type": "crypto", "balance": 12500.00},

        # Other
        {"name": "Etsy Shop", "currency": "USD", "account_type": "business", "balance": 2340.00},
        {"name": "Starbucks Card", "currency": "USD", "account_type": "prepaid", "balance": 45.50},
        {"name": "HSA Account", "currency": "USD", "account_type": "other", "balance": 3200.00},
    ]
    accounts: dict[str, Account] = {}
    for payload in accounts_seed:
        existing = session.exec(
            select(Account).where(Account.name == payload["name"], Account.user_id == user_id)
        ).first()
        if existing:
            accounts[payload["name"]] = existing
            continue
        account = Account(user_id=user_id, **payload)
        session.add(account)
        session.flush()
        accounts[payload["name"]] = account
    session.flush()
    return accounts


def _seed_transactions(
    session: Session,
    categories: dict[str, Category],
    accounts: dict[str, Account],
    user_id: int,
) -> None:
    now = datetime.now()
    transaction_specs = [
        {
            "external_id": "demo-tx-001",
            "occurred_at": datetime(2024, 1, 5, 13, 30),
            "amount": -58.23,
            "memo": "Grocery Run",
            "category_slug": "groceries",
        },
        {
            "external_id": "demo-tx-002",
            "occurred_at": datetime(2024, 1, 8, 19, 45),
            "amount": -32.5,
            "memo": "Dinner with friends",
            "category_slug": "dining-out",
        },
        {
            "external_id": "demo-tx-003",
            "occurred_at": datetime(2024, 1, 10, 8, 0),
            "amount": -90.0,
            "memo": "Electric bill",
            "category_slug": "utilities",
        },
        {
            "external_id": "demo-tx-004",
            "occurred_at": datetime(2024, 1, 15, 12, 0),
            "amount": 2800.0,
            "memo": "Monthly salary",
            "category_slug": "salary",
        },
        {
            "external_id": "seed-salary-001",
            "occurred_at": now,
            "amount": 1500.0,
            "memo": "Salary",
            "category_slug": "salary",
        },
        {
            "external_id": "seed-coffee-001",
            "occurred_at": now,
            "amount": -4.50,
            "memo": "Coffee",
            "category_slug": "coffee",
        },
    ]

    account = (
        accounts.get("Primary Checking")
        or accounts.get("Everyday Checking")
        or next(iter(accounts.values()), None)
    )
    if account is None:
        return

    for spec in transaction_specs:
        existing = session.exec(
            select(Transaction).where(
                Transaction.external_id == spec["external_id"], Transaction.user_id == user_id
            )
        ).one_or_none()
        category_id = categories[spec["category_slug"]].id
        if category_id is None or account.id is None:
            continue
        if existing is None:
            existing = Transaction(
                user_id=user_id,
                external_id=spec["external_id"],
                occurred_at=spec["occurred_at"],
                amount=spec["amount"],
                memo=spec["memo"],
                category_id=category_id,
                account_id=account.id,
                currency=account.currency,
            )
            session.add(existing)
        else:
            existing.occurred_at = spec["occurred_at"]
            existing.amount = spec["amount"]
            existing.memo = spec["memo"]
            existing.category_id = category_id
            existing.account_id = account.id
            existing.currency = account.currency
            existing.user_id = user_id


def _heavy_transactions_seed(session: Session, user_id: int, accounts: dict[str, Account]) -> None:
    """Generate a randomized but realistic transaction dataset for testing (5 years)."""

    YEARS_BACK = 5

    # Get categories for this user
    categories = {
        cat.slug: cat for cat in session.exec(
            select(Category).where(Category.user_id == user_id)
        ).all()
    }

    # Primary accounts for different transaction types
    checking = accounts.get("Primary Checking") or accounts.get("Everyday Checking") or next(iter(accounts.values()), None)
    savings = accounts.get("Emergency Fund") or accounts.get("Rainy Day Savings")
    credit_card = accounts.get("Chase Sapphire") or accounts.get("Travel Card")

    today = date.today()
    start_date = today.replace(year=today.year - YEARS_BACK, month=1, day=1)

    transactions_to_add = []

    # RECURRING MONTHLY TRANSACTIONS
    # These happen every month on specific days
    recurring_monthly = [
        {"day": 1, "category": "rent", "amount_range": (-1850, -2100), "memo": "Monthly Rent", "account": checking},
        {"day": 1, "category": "mortgage", "amount_range": (-1950, -1950), "memo": "Mortgage Payment", "account": checking},
        {"day": 5, "category": "utilities", "amount_range": (-95, -180), "memo": "Electric Bill", "account": checking},
        {"day": 8, "category": "internet", "amount_range": (-79, -89), "memo": "Internet Service", "account": checking},
        {"day": 10, "category": "phone", "amount_range": (-85, -125), "memo": "Phone Bill", "account": checking},
        {"day": 12, "category": "insurance", "amount_range": (-145, -165), "memo": "Auto Insurance", "account": checking},
        {"day": 15, "category": "subscriptions", "amount_range": (-15, -15), "memo": "Netflix", "account": credit_card},
        {"day": 18, "category": "subscriptions", "amount_range": (-11, -11), "memo": "Spotify", "account": credit_card},
        {"day": 20, "category": "subscriptions", "amount_range": (-14, -14), "memo": "iCloud Storage", "account": credit_card},
        {"day": 22, "category": "utilities", "amount_range": (-45, -85), "memo": "Water Bill", "account": checking},
    ]

    # BI-WEEKLY INCOME (1st and 15th, or every other Friday)
    # Salary arrives twice a month
    income_patterns = [
        {"days": [1, 15], "category": "salary", "amount_range": (2800, 3500), "memo": "Paycheck - Direct Deposit", "account": checking},
    ]

    # WEEKLY PATTERNS (approximate - not exactly every week)
    weekly_patterns = [
        {"category": "groceries", "times_per_month": (4, 5), "amount_range": (-85, -220), "memo_options": ["Grocery Run", "Weekly Groceries", "Food Shopping", "Costco Run", "Trader Joe's"], "prefer_weekend": True},
        {"category": "gas", "times_per_month": (2, 4), "amount_range": (-35, -65), "memo_options": ["Gas Station", "Fill Up", "Shell", "Chevron", "Costco Gas"], "prefer_weekend": False},
    ]

    # VARIABLE FREQUENCY PATTERNS
    variable_patterns = [
        {"category": "dining-out", "times_per_month": (6, 12), "amount_range": (-15, -85), "memo_options": ["Lunch", "Dinner Out", "Restaurant", "Takeout", "Food Delivery", "Coffee Shop", "Brunch"], "prefer_weekend": True},
        {"category": "coffee", "times_per_month": (8, 20), "amount_range": (-4, -8), "memo_options": ["Starbucks", "Coffee", "Morning Coffee", "Dunkin", "Local Cafe"], "prefer_weekend": False},
        {"category": "entertainment", "times_per_month": (2, 5), "amount_range": (-12, -75), "memo_options": ["Movie Tickets", "Concert", "Streaming Rental", "Event Tickets", "Arcade"], "prefer_weekend": True},
        {"category": "transit", "times_per_month": (4, 12), "amount_range": (-3, -25), "memo_options": ["Uber", "Lyft", "Metro Card", "Parking", "Toll"], "prefer_weekend": False},
        {"category": "household", "times_per_month": (1, 3), "amount_range": (-25, -150), "memo_options": ["Target", "Amazon", "Home Depot", "Cleaning Supplies", "Home Goods"], "prefer_weekend": True},
        {"category": "clothing", "times_per_month": (0, 2), "amount_range": (-35, -200), "memo_options": ["Clothes Shopping", "Shoes", "Amazon Fashion", "Nordstrom", "TJ Maxx"], "prefer_weekend": True},
        {"category": "medical", "times_per_month": (0, 1), "amount_range": (-25, -250), "memo_options": ["Pharmacy", "Doctor Copay", "Prescription", "CVS", "Urgent Care"], "prefer_weekend": False},
        {"category": "pets", "times_per_month": (1, 2), "amount_range": (-30, -120), "memo_options": ["Pet Food", "Vet Visit", "Pet Supplies", "Chewy.com"], "prefer_weekend": False},
        {"category": "gifts", "times_per_month": (0, 1), "amount_range": (-25, -150), "memo_options": ["Birthday Gift", "Present", "Gift Card", "Amazon Gift"], "prefer_weekend": True},
        {"category": "wellness", "times_per_month": (2, 4), "amount_range": (-15, -50), "memo_options": ["Gym", "Yoga Class", "Fitness App", "Vitamins"], "prefer_weekend": False},
    ]

    # OCCASIONAL/SEASONAL (not every month)
    occasional_patterns = [
        {"category": "travel", "times_per_year": (2, 5), "amount_range": (-200, -1500), "memo_options": ["Flight", "Hotel", "Airbnb", "Vacation", "Road Trip"], "months": [3, 6, 7, 8, 11, 12]},
        {"category": "education", "times_per_year": (1, 4), "amount_range": (-50, -500), "memo_options": ["Online Course", "Books", "Udemy", "Certification"], "months": [1, 2, 9, 10]},
        {"category": "charity", "times_per_year": (2, 6), "amount_range": (-25, -200), "memo_options": ["Donation", "Charity", "GoFundMe", "Non-profit"], "months": [4, 11, 12]},
    ]

    # OCCASIONAL INCOME (not every month)
    occasional_income = [
        {"category": "bonus", "times_per_year": (1, 2), "amount_range": (1000, 5000), "memo_options": ["Annual Bonus", "Performance Bonus", "Holiday Bonus"], "months": [3, 12]},
        {"category": "dividends", "times_per_year": (4, 4), "amount_range": (50, 350), "memo_options": ["Dividend Payment", "Quarterly Dividend"], "months": [3, 6, 9, 12]},
        {"category": "interest", "times_per_year": (12, 12), "amount_range": (5, 45), "memo_options": ["Savings Interest", "Interest Payment"], "months": list(range(1, 13))},
        {"category": "refund", "times_per_year": (2, 5), "amount_range": (15, 500), "memo_options": ["Tax Refund", "Return Refund", "Rebate", "Reimbursement"], "months": [2, 3, 4, 5]},
        {"category": "side-hustle", "times_per_year": (3, 10), "amount_range": (100, 800), "memo_options": ["Freelance Work", "Side Project", "Consulting", "Gig Income"], "months": list(range(1, 13))},
    ]

    def get_random_day(year: int, month: int, prefer_weekend: bool = False) -> int:
        """Get a random day in the month, optionally preferring weekends."""
        last_day = monthrange(year, month)[1]

        if prefer_weekend:
            # 60% chance of weekend, 40% chance of weekday
            if random.random() < 0.6:
                # Find weekend days in this month
                weekend_days = []
                for day in range(1, last_day + 1):
                    if date(year, month, day).weekday() >= 5:  # Saturday=5, Sunday=6
                        weekend_days.append(day)
                if weekend_days:
                    return random.choice(weekend_days)

        return random.randint(1, last_day)

    def add_transaction(occurred_at: datetime, amount: float, memo: str, category_slug: str, account: Account):
        """Helper to create a transaction dict."""
        cat = categories.get(category_slug)
        if not cat or not account:
            return

        external_id = f"seed-{category_slug}-{occurred_at.isoformat()}-{random.randint(1000, 9999)}"

        transactions_to_add.append({
            "user_id": user_id,
            "external_id": external_id,
            "occurred_at": occurred_at,
            "amount": round(amount, 2),
            "memo": memo,
            "category_id": cat.id,
            "account_id": account.id,
            "currency": account.currency or "USD",
        })

    # Generate transactions for each month
    current = start_date
    while current <= today:
        year, month = current.year, current.month
        last_day = monthrange(year, month)[1]

        # 1. RECURRING MONTHLY
        for pattern in recurring_monthly:
            day = min(pattern["day"], last_day)
            occurred = datetime(year, month, day, random.randint(8, 20), random.randint(0, 59))
            amount = random.uniform(*pattern["amount_range"]) if pattern["amount_range"][0] != pattern["amount_range"][1] else pattern["amount_range"][0]
            if pattern.get("account"):
                add_transaction(occurred, amount, pattern["memo"], pattern["category"], pattern["account"])

        # 2. BI-WEEKLY INCOME
        for pattern in income_patterns:
            for day in pattern["days"]:
                if day <= last_day:
                    occurred = datetime(year, month, day, 6, 0)  # Early morning deposit
                    amount = random.uniform(*pattern["amount_range"])
                    add_transaction(occurred, amount, pattern["memo"], pattern["category"], pattern["account"])

        # 3. WEEKLY PATTERNS
        for pattern in weekly_patterns:
            times = random.randint(*pattern["times_per_month"])
            used_days = set()
            for _ in range(times):
                day = get_random_day(year, month, pattern.get("prefer_weekend", False))
                # Avoid duplicate days for same category
                attempts = 0
                while day in used_days and attempts < 10:
                    day = get_random_day(year, month, pattern.get("prefer_weekend", False))
                    attempts += 1
                used_days.add(day)

                occurred = datetime(year, month, day, random.randint(9, 21), random.randint(0, 59))
                amount = random.uniform(*pattern["amount_range"])
                memo = random.choice(pattern["memo_options"])
                account = credit_card if random.random() < 0.4 else checking
                add_transaction(occurred, amount, memo, pattern["category"], account or checking)

        # 4. VARIABLE PATTERNS
        for pattern in variable_patterns:
            times = random.randint(*pattern["times_per_month"])
            for _ in range(times):
                day = get_random_day(year, month, pattern.get("prefer_weekend", False))
                occurred = datetime(year, month, day, random.randint(7, 22), random.randint(0, 59))
                amount = random.uniform(*pattern["amount_range"])
                memo = random.choice(pattern["memo_options"])
                # Mix of credit card and checking
                account = credit_card if random.random() < 0.5 else checking
                add_transaction(occurred, amount, memo, pattern["category"], account or checking)

        # 5. OCCASIONAL/SEASONAL
        for pattern in occasional_patterns:
            if month in pattern.get("months", []):
                # Random chance based on times per year
                chance = pattern["times_per_year"][1] / len(pattern["months"])
                if random.random() < chance:
                    day = get_random_day(year, month, True)
                    occurred = datetime(year, month, day, random.randint(10, 18), random.randint(0, 59))
                    amount = random.uniform(*pattern["amount_range"])
                    memo = random.choice(pattern["memo_options"])
                    add_transaction(occurred, amount, memo, pattern["category"], credit_card or checking)

        # 6. OCCASIONAL INCOME
        for pattern in occasional_income:
            if month in pattern.get("months", []):
                chance = pattern["times_per_year"][1] / len(pattern["months"])
                if random.random() < chance:
                    day = random.randint(1, min(15, last_day))
                    occurred = datetime(year, month, day, random.randint(8, 12), random.randint(0, 59))
                    amount = random.uniform(*pattern["amount_range"])
                    memo = random.choice(pattern["memo_options"])
                    add_transaction(occurred, amount, memo, pattern["category"], checking or next(iter(accounts.values()), None))

        # Move to next month
        if month == 12:
            current = date(year + 1, 1, 1)
        else:
            current = date(year, month + 1, 1)

    # Batch insert all transactions
    for tx_data in transactions_to_add:
        # Check for existing by external_id
        existing = session.exec(
            select(Transaction).where(
                Transaction.external_id == tx_data["external_id"],
                Transaction.user_id == user_id,
            )
        ).first()

        if existing is None:
            session.add(Transaction(**tx_data))

    session.flush()


def _seed_habits(session: Session, user_id: int) -> None:
    """Seed sample habits for testing."""

    habit_specs = [
        {"name": "Morning Exercise", "description": "30 minutes of cardio or strength training", "cadence": "daily"},
        {"name": "Read 30 Minutes", "description": "Read books, articles, or educational content", "cadence": "daily"},
        {"name": "Meditate", "description": "10-15 minutes of mindfulness meditation", "cadence": "daily"},
        {"name": "Drink 8 Glasses Water", "description": "Stay hydrated throughout the day", "cadence": "daily"},
        {"name": "Review Budget", "description": "Check spending against budget categories", "cadence": "weekly"},
        {"name": "Meal Prep", "description": "Prepare meals for the upcoming week", "cadence": "weekly"},
        {"name": "Call Family", "description": "Stay connected with family members", "cadence": "weekly"},
        {"name": "Deep Clean", "description": "Thorough cleaning of one room/area", "cadence": "weekly"},
        {"name": "Review Investments", "description": "Check portfolio performance and rebalance if needed", "cadence": "monthly"},
        {"name": "Pay Credit Cards", "description": "Pay off credit card balances in full", "cadence": "monthly"},
    ]

    for spec in habit_specs:
        existing = session.exec(
            select(Habit).where(Habit.name == spec["name"], Habit.user_id == user_id)
        ).first()
        if existing is None:
            session.add(Habit(user_id=user_id, **spec))

    session.flush()


def _seed_liabilities(session: Session, user_id: int) -> list[Liability]:
    """Seed realistic debt/liability records."""

    liability_specs = [
        # Credit cards
        {"name": "Chase Sapphire Balance", "balance": 2340.67, "apr": 24.99, "minimum_payment": 75.0, "due_day": 15},
        {"name": "Amazon Card Balance", "balance": 567.89, "apr": 26.99, "minimum_payment": 25.0, "due_day": 22},
        {"name": "Capital One Balance", "balance": 125.00, "apr": 22.99, "minimum_payment": 25.0, "due_day": 8},

        # Loans
        {"name": "Honda Auto Loan", "balance": 18750.00, "apr": 5.49, "minimum_payment": 385.0, "due_day": 1},
        {"name": "Personal Loan", "balance": 4500.00, "apr": 9.99, "minimum_payment": 150.0, "due_day": 10},

        # Medical (0% APR common for medical payment plans)
        {"name": "Medical Bill Payment Plan", "balance": 1200.00, "apr": 0.0, "minimum_payment": 100.0, "due_day": 20},

        # Student loan (if applicable)
        {"name": "Student Loan", "balance": 22500.00, "apr": 4.99, "minimum_payment": 275.0, "due_day": 28},
    ]

    liabilities: list[Liability] = []
    for spec in liability_specs:
        existing = session.exec(
            select(Liability).where(Liability.name == spec["name"], Liability.user_id == user_id)
        ).one_or_none()
        if existing is None:
            existing = Liability(user_id=user_id, **spec)
            session.add(existing)
        else:
            existing.balance = spec["balance"]
            existing.apr = spec["apr"]
            existing.minimum_payment = spec["minimum_payment"]
            existing.due_day = spec["due_day"]
        liabilities.append(existing)
    session.flush()
    return liabilities


def _seed_liability_transactions(
    session: Session,
    liabilities: list[Liability],
    accounts: dict[str, Account],
    categories: dict[str, Category],
    user_id: int,
) -> None:
    """Link liabilities to the ledger by inserting/updating payment transactions."""

    if not liabilities:
        return

    primary_account = (
        accounts.get("Primary Checking")
        or accounts.get("Joint Checking")
        or accounts.get("Everyday Checking")
        or accounts.get("Rainy Day Savings")
        or next((acct for acct in accounts.values() if acct.id), None)
    )
    if primary_account is None or primary_account.id is None:
        return

    payment_category = categories.get("payment") or categories.get("transfer-out")
    today = date.today()
    last_day = monthrange(today.year, today.month)[1]

    for liability in liabilities:
        if liability.id is None:
            continue
        due_day = getattr(liability, "due_day", 1) or 1
        due_date = date(today.year, today.month, min(due_day, last_day))
        occurred_at = datetime.combine(due_date, datetime.min.time())
        external_id = f"liability-payment-{liability.name}-{due_date.isoformat()}"
        existing = session.exec(
            select(Transaction).where(
                Transaction.external_id == external_id,
                Transaction.user_id == user_id,
            )
        ).one_or_none()

        amount = -abs(getattr(liability, "minimum_payment", 0.0) or 0.0)
        category_id = getattr(payment_category, "id", None)
        payload = {
            "occurred_at": occurred_at,
            "amount": amount,
            "memo": f"{liability.name} payment",
            "category_id": category_id,
            "account_id": primary_account.id,
            "currency": primary_account.currency,
            "liability_id": liability.id,
            "user_id": user_id,
        }

        if existing is None:
            session.add(
                Transaction(
                    external_id=external_id,
                    **payload,
                )
            )
        else:
            existing.occurred_at = occurred_at
            existing.amount = amount
            existing.memo = payload["memo"]
            existing.category_id = category_id
            existing.account_id = primary_account.id
            existing.currency = primary_account.currency
            existing.liability_id = liability.id
            existing.user_id = user_id
    session.flush()


def _seed_holdings(session: Session, accounts: dict[str, Account], user_id: int) -> None:
    """Seed a diversified portfolio with holdings across multiple accounts."""
    brokerage = accounts.get("Fidelity Brokerage") or accounts.get("Brokerage")
    retirement = accounts.get("Vanguard IRA") or accounts.get("Company 401(k)")
    robinhood = accounts.get("Robinhood")
    coinbase = accounts.get("Coinbase")

    # Create default brokerage if none exists
    if brokerage is None:
        brokerage = Account(
            user_id=user_id, name="Brokerage", account_type="brokerage", currency="USD", balance=45000
        )
        session.add(brokerage)
        session.flush()
        accounts["Brokerage"] = brokerage

    holdings_by_account = {
        # Main brokerage - diversified ETFs and stocks
        brokerage: [
            {"symbol": "VTI", "quantity": 45, "avg_price": 215.00, "market_price": 242.50},    # Total Stock Market
            {"symbol": "VXUS", "quantity": 30, "avg_price": 55.00, "market_price": 58.75},     # International
            {"symbol": "BND", "quantity": 25, "avg_price": 78.00, "market_price": 73.25},      # Bonds
            {"symbol": "AAPL", "quantity": 15, "avg_price": 145.00, "market_price": 178.50},   # Individual stock
            {"symbol": "MSFT", "quantity": 10, "avg_price": 285.00, "market_price": 378.00},   # Individual stock
            {"symbol": "GOOGL", "quantity": 8, "avg_price": 125.00, "market_price": 142.00},   # Individual stock
        ],
        # Retirement account - target date and index funds
        retirement: [
            {"symbol": "VFFVX", "quantity": 150, "avg_price": 42.00, "market_price": 48.50},   # Target Date 2055
            {"symbol": "VFIAX", "quantity": 35, "avg_price": 410.00, "market_price": 445.00},  # S&P 500 Index
        ] if retirement else [],
        # Robinhood - individual stocks
        robinhood: [
            {"symbol": "TSLA", "quantity": 5, "avg_price": 210.00, "market_price": 248.00},
            {"symbol": "NVDA", "quantity": 8, "avg_price": 450.00, "market_price": 875.00},
            {"symbol": "AMD", "quantity": 20, "avg_price": 95.00, "market_price": 125.00},
        ] if robinhood else [],
        # Crypto account
        coinbase: [
            {"symbol": "BTC", "quantity": 0.15, "avg_price": 35000.00, "market_price": 42000.00},
            {"symbol": "ETH", "quantity": 2.5, "avg_price": 2200.00, "market_price": 2650.00},
            {"symbol": "SOL", "quantity": 25, "avg_price": 85.00, "market_price": 125.00},
        ] if coinbase else [],
    }

    for account, holdings in holdings_by_account.items():
        if account is None:
            continue
        for payload in holdings:
            symbol = payload["symbol"]
            existing = session.exec(
                select(Holding).where(
                    Holding.symbol == symbol,
                    Holding.account_id == account.id,
                    Holding.user_id == user_id
                )
            ).first()
            if existing:
                existing.quantity = payload["quantity"]
                existing.avg_price = payload["avg_price"]
                existing.market_price = payload["market_price"]
            else:
                session.add(
                    Holding(
                        user_id=user_id,
                        account_id=account.id,
                        symbol=symbol,
                        quantity=payload["quantity"],
                        avg_price=payload["avg_price"],
                        market_price=payload["market_price"],
                        currency="USD",
                    )
                )


def _seed_budget(session: Session, categories: dict[str, Category], user_id: int) -> None:
    today = date.today()
    first_of_month = today.replace(day=1)
    last_day = monthrange(today.year, today.month)[1]
    end_of_month = today.replace(day=last_day)

    existing_budget = session.exec(
        select(Budget).where(
            Budget.user_id == user_id,
            Budget.period_start == first_of_month,
            Budget.period_end == end_of_month,
        )
    ).one_or_none()

    if existing_budget is None:
        existing_budget = Budget(
            user_id=user_id,
            period_start=first_of_month,
            period_end=end_of_month,
            label=f"{today.strftime('%B %Y')} Budget",
        )
        session.add(existing_budget)
        session.flush()

    expense_slugs = ["rent", "utilities", "groceries", "dining-out", "transit", "coffee"]
    lines = session.exec(
        select(BudgetLine).where(BudgetLine.budget_id == existing_budget.id, BudgetLine.user_id == user_id)
    ).all()
    if not lines:
        payloads: list[BudgetLine] = []
        for slug in expense_slugs:
            cat = categories.get(slug)
            if cat is None:
                continue
            payloads.append(
                BudgetLine(
                    user_id=user_id,
                    budget_id=existing_budget.id,
                    category_id=cat.id,
                    planned_amount=200.0 if slug != "rent" else 1200.0,
                    rollover_enabled=False,
                )
            )
        session.add_all(payloads)
def reset_demo_database(
    user_id: int, session_factory: Optional[SessionFactory] = None, reseed: bool = True
) -> SeedSummary:
    """Reset demo data for a specific user."""

    # Guard against accidental cross-user resets
    with _get_session(session_factory) as session:
        models = (
            Transaction,
            BudgetLine,
            Budget,
            HabitEntry,
            Habit,
            Liability,
            Holding,
            Account,
            Category,
        )
        for model in models:
            rows = session.exec(select(model).where(getattr(model, "user_id") == user_id)).all()  # type: ignore[attr-defined]
            for row in rows:
                session.delete(row)
        session.commit()
    if reseed:
        return run_demo_seed(session_factory=session_factory, user_id=user_id, force=True)
    return SeedSummary(transactions=0, categories=0, accounts=0, habits=0, liabilities=0, budgets=0)


def run_demo_seed(
    session_factory: Optional[SessionFactory] = None,
    *,
    user_id: int,
    force: bool = False,
) -> SeedSummary:
    """Seed demo data idempotently for desktop workflows and return counts."""

    with _get_session(session_factory) as session:
        if not force:
            # Skip heavy re-seeding when data already present for this user.
            existing_tx = session.exec(
                select(Transaction.id).where(Transaction.user_id == user_id)
            ).first()
            if existing_tx is not None:
                return _build_seed_summary(session, user_id=user_id)

        categories = _seed_categories(session, user_id=user_id)
        accounts = _seed_accounts(session, user_id=user_id)
        _seed_transactions(session, categories, accounts, user_id=user_id)
        # Ensure baseline transactions exist
        tx_exists = session.exec(select(Transaction.id).where(Transaction.user_id == user_id)).first()
        if tx_exists is None:
            primary_account = (
                accounts.get("Primary Checking")
                or accounts.get("Joint Checking")
                or accounts.get("Everyday Checking")
                or next(iter(accounts.values()), None)
            )
            sample = [
                Transaction(
                    user_id=user_id,
                    occurred_at=datetime(2025, 1, 1),
                    amount=1500.0,
                    memo="Seed Paycheck",
                    category_id=categories.get("salary").id if categories.get("salary") else None,  # type: ignore[union-attr]
                    account_id=primary_account.id if primary_account else None,  # type: ignore[union-attr]
                    currency="USD",
                ),
                Transaction(
                    user_id=user_id,
                    occurred_at=datetime(2025, 1, 2),
                    amount=-120.0,
                    memo="Seed Groceries",
                    category_id=categories.get("groceries").id if categories.get("groceries") else None,  # type: ignore[union-attr]
                    account_id=primary_account.id if primary_account else None,  # type: ignore[union-attr]
                    currency="USD",
                ),
            ]
            session.add_all(sample)
        _seed_habits(session, user_id=user_id)
        liabilities = _seed_liabilities(session, user_id=user_id)
        _seed_budget(session, categories, user_id=user_id)
        _seed_holdings(session, accounts, user_id=user_id)
        _seed_liability_transactions(
            session, liabilities, accounts, categories, user_id=user_id
        )
        session.commit()
        return _build_seed_summary(session, user_id=user_id)


def _build_seed_summary(session: Session, *, user_id: int) -> SeedSummary:
    """Compile counts for tables populated by the demo seed."""

    tx_count = session.exec(
        select(func.count(Transaction.id)).where(Transaction.user_id == user_id)
    ).one()
    category_count = session.exec(
        select(func.count(Category.id)).where(Category.user_id == user_id)
    ).one()
    account_count = session.exec(
        select(func.count(Account.id)).where(Account.user_id == user_id)
    ).one()
    habit_count = session.exec(select(func.count(Habit.id)).where(Habit.user_id == user_id)).one()
    liability_count = session.exec(
        select(func.count(Liability.id)).where(Liability.user_id == user_id)
    ).one()
    budget_count = session.exec(
        select(func.count(Budget.id)).where(Budget.user_id == user_id)
    ).one()
    return SeedSummary(
        transactions=tx_count,
        categories=category_count,
        accounts=account_count,
        habits=habit_count,
        liabilities=liability_count,
        budgets=budget_count,
    )


EXPORT_RETENTION = 5


def _ensure_secure_directory(directory: Path) -> None:
    """Create the directory and set restrictive permissions when possible."""

    directory.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(directory, 0o700)
    except (NotImplementedError, PermissionError):  # pragma: no cover - platform specific
        pass


def _prune_old_exports(directory: Path, keep: int = EXPORT_RETENTION) -> None:
    """Remove export archives beyond the retention count."""

    archives = sorted(
        directory.glob("pocketsage_export_*.zip"),
        key=lambda file: file.stat().st_mtime,
        reverse=True,
    )
    for old in archives[keep:]:
        try:
            old.unlink()
        except OSError:  # pragma: no cover - best-effort cleanup
            pass


def run_export(
    output_dir: Path | None = None,
    session_factory: Optional[SessionFactory] = None,
    user_id: Optional[int] = None,
    retention: int = EXPORT_RETENTION,
) -> Path:
    """Generate export bundle for download and return path to zip file."""

    write_to_instance = output_dir is not None
    out_dir: Path | None = None
    if write_to_instance:
        out_dir = Path(output_dir) if not isinstance(output_dir, Path) else output_dir
        _ensure_secure_directory(out_dir)

    with TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        safe_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        csv_path = tmp / f"transactions-{safe_stamp}.csv"
        png_path = tmp / f"spending-{safe_stamp}.png"

        with _get_session(session_factory) as session:
            try:
                stmt = select(Transaction)
                if user_id is not None:
                    stmt = stmt.where(Transaction.user_id == user_id)
                txs = session.exec(stmt).all()
            except OperationalError:
                txs = []

            try:
                export_transactions_csv(transactions=txs, output_path=csv_path)
            except Exception:
                csv_path.write_text("id,occurred_at,amount,memo\n")

            try:
                export_spending_png(transactions=txs, output_path=png_path, renderer=None)  # type: ignore[arg-type]
            except Exception:
                png_path.write_bytes(b"")

        zip_name = f"pocketsage_export_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.zip"
        zip_path = (Path.cwd() / zip_name) if not out_dir else out_dir / zip_name

        with ZipFile(zip_path, "w") as archive:
            if csv_path.exists():
                archive.write(csv_path, arcname=csv_path.name)
            if png_path.exists():
                archive.write(png_path, arcname=png_path.name)

        if write_to_instance and out_dir is not None:
            _prune_old_exports(out_dir, keep=retention)

        return zip_path


def backup_database(
    output_dir: Path | None = None, config: Optional[BaseConfig] = None
) -> Path:
    """Copy the current database file (all users) to a backup location."""

    config = config or BaseConfig()
    db_path = config.DATA_DIR / config.DB_FILENAME
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")

    destination_root = output_dir if output_dir is not None else config.DATA_DIR / "backups"
    dest_dir = destination_root if isinstance(destination_root, Path) else Path(destination_root)
    _ensure_secure_directory(dest_dir)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    backup_path = dest_dir / f"pocketsage_backup_{stamp}.db"
    with db_path.open("rb") as src, backup_path.open("wb") as dst:
        dst.write(src.read())
    return backup_path


def restore_database(
    backup_file: Path, *, config: Optional[BaseConfig] = None, overwrite: bool = True
) -> Path:
    """Restore the database from a provided backup file."""

    config = config or BaseConfig()
    source = backup_file if isinstance(backup_file, Path) else Path(backup_file)
    if not source.exists():
        raise FileNotFoundError(f"Backup file not found: {source}")
    target = config.DATA_DIR / config.DB_FILENAME
    if not overwrite and target.exists():
        raise FileExistsError(f"Target database already exists at {target}")

    _ensure_secure_directory(config.DATA_DIR)
    with source.open("rb") as src, target.open("wb") as dst:
        dst.write(src.read())
    # Hint: caller should trigger app restart to reload connections.
    return target


__all__ = [
    "reset_demo_database",
    "run_demo_seed",
    "run_export",
    "EXPORT_RETENTION",
    "backup_database",
    "restore_database",
]
