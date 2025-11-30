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
import time
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

# Seed randomness initialization
def _initialize_random_seed() -> int:
    """Initialize random with true randomness from multiple entropy sources."""
    # Combine time, process ID, and object ID for entropy
    entropy = int(time.time() * 1000000) ^ os.getpid() ^ id(object())
    random.seed(entropy)
    return entropy


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

    # Initialize with fresh randomness each run
    seed_value = _initialize_random_seed()

    # Get category map
    categories = session.exec(
        select(Category).where(Category.user_id == user_id)
    ).all()
    category_map = {c.slug: c for c in categories}

    # Find primary accounts
    checking = (
        accounts.get("Primary Checking")
        or accounts.get("Joint Checking")
        or accounts.get("Everyday Checking")
        or next((a for a in accounts.values() if "check" in a.name.lower()), None)
    )
    credit_card = (
        accounts.get("Travel Rewards Card")
        or accounts.get("Cashback Card")
        or next((a for a in accounts.values() if "card" in a.name.lower() or "credit" in a.name.lower()), None)
    )
    savings = (
        accounts.get("Emergency Savings")
        or accounts.get("High-Yield Savings")
        or next((a for a in accounts.values() if "saving" in a.name.lower()), None)
    )

    if not checking:
        checking = next(iter(accounts.values()), None)
    if not checking:
        return

    # Date range: 5 years back to today
    today = date.today()
    start_date = date(today.year - 5, 1, 1)

    # =========================================
    # SPENDING PATTERNS (Amount ranges and frequencies)
    # =========================================

    SPENDING_PATTERNS = {
        # Essential expenses (negative amounts)
        "groceries": {"min": 25, "max": 250, "typical": 85, "per_month": (8, 12)},
        "rent": {"min": 1200, "max": 2800, "typical": 1950, "per_month": (1, 1)},
        "utilities": {"min": 80, "max": 350, "typical": 175, "per_month": (1, 1)},
        "gas": {"min": 30, "max": 75, "typical": 48, "per_month": (4, 8)},
        "insurance": {"min": 100, "max": 400, "typical": 225, "per_month": (1, 1)},

        # Lifestyle expenses
        "dining-out": {"min": 12, "max": 120, "typical": 42, "per_month": (6, 15)},
        "coffee": {"min": 4, "max": 15, "typical": 7, "per_month": (8, 20)},
        "entertainment": {"min": 10, "max": 150, "typical": 45, "per_month": (3, 8)},
        "shopping": {"min": 15, "max": 300, "typical": 65, "per_month": (2, 6)},
        "subscriptions": {"min": 8, "max": 50, "typical": 18, "per_month": (3, 6)},

        # Periodic expenses
        "medical": {"min": 25, "max": 500, "typical": 120, "per_month": (0, 2)},
        "travel": {"min": 150, "max": 2500, "typical": 650, "per_month": (0, 1)},
        "education": {"min": 30, "max": 500, "typical": 125, "per_month": (0, 2)},
        "personal-care": {"min": 15, "max": 150, "typical": 55, "per_month": (1, 3)},
        "gifts": {"min": 25, "max": 300, "typical": 75, "per_month": (0, 2)},
        "home-maintenance": {"min": 50, "max": 800, "typical": 200, "per_month": (0, 1)},
        "clothing": {"min": 30, "max": 250, "typical": 80, "per_month": (1, 3)},
        "pets": {"min": 20, "max": 200, "typical": 65, "per_month": (1, 2)},
        "fitness": {"min": 30, "max": 120, "typical": 55, "per_month": (1, 1)},

        # Income (positive amounts)
        "salary": {"min": 3500, "max": 8500, "typical": 5200, "per_month": (2, 2)},
        "bonus": {"min": 1000, "max": 15000, "typical": 4500, "per_month": (0, 0)},  # Handled separately
        "interest": {"min": 5, "max": 150, "typical": 35, "per_month": (1, 1)},
        "dividends": {"min": 25, "max": 800, "typical": 150, "per_month": (0, 1)},
        "freelance": {"min": 200, "max": 3000, "typical": 800, "per_month": (0, 2)},
        "refund": {"min": 15, "max": 500, "typical": 85, "per_month": (0, 1)},

        # Transfers
        "transfer-in": {"min": 100, "max": 2000, "typical": 500, "per_month": (1, 3)},
        "transfer-out": {"min": 100, "max": 2000, "typical": 500, "per_month": (1, 3)},
    }

    # Memo templates for realism
    MEMO_TEMPLATES = {
        "groceries": ["Grocery Run", "Weekly Groceries", "Costco", "Trader Joe's", "Whole Foods", "Publix", "Kroger", "Aldi", "Safeway", "Target Groceries"],
        "rent": ["Monthly Rent", "Rent Payment", "Apartment Rent"],
        "utilities": ["Electric Bill", "Gas Bill", "Water & Sewer", "Utilities Payment", "Power Company"],
        "gas": ["Gas Station", "Shell", "Chevron", "BP", "Exxon", "Fuel", "Gas Fill-up"],
        "dining-out": ["Restaurant", "Dinner Out", "Lunch", "Brunch", "Pizza Night", "Thai Food", "Sushi", "Mexican Restaurant", "Italian Dinner", "Burger Joint"],
        "coffee": ["Coffee Shop", "Starbucks", "Dunkin", "Local Cafe", "Morning Coffee", "Espresso"],
        "entertainment": ["Movie Night", "Concert Tickets", "Streaming", "Gaming", "Netflix", "Spotify", "Event Tickets", "Bowling", "Mini Golf"],
        "shopping": ["Amazon", "Target", "Walmart", "Online Shopping", "Home Goods", "Electronics", "General Shopping"],
        "subscriptions": ["Netflix", "Spotify", "Amazon Prime", "Gym Membership", "News Subscription", "Software License", "Cloud Storage"],
        "medical": ["Doctor Visit", "Pharmacy", "Medical Copay", "Prescription", "Dental Checkup", "Vision Care", "Lab Work"],
        "travel": ["Flight Booking", "Hotel Stay", "Vacation", "Road Trip", "Airbnb", "Rental Car", "Travel Expenses"],
        "salary": ["Paycheck", "Salary Deposit", "Direct Deposit", "Bi-weekly Pay"],
        "bonus": ["Annual Bonus", "Performance Bonus", "Holiday Bonus", "Quarterly Bonus"],
        "interest": ["Savings Interest", "Bank Interest", "Interest Earned"],
        "dividends": ["Dividend Payment", "Stock Dividends", "Investment Income"],
        "insurance": ["Car Insurance", "Health Insurance", "Renters Insurance", "Life Insurance"],
        "personal-care": ["Haircut", "Salon", "Spa", "Beauty Products", "Skincare"],
        "gifts": ["Birthday Gift", "Holiday Gift", "Wedding Gift", "Gift Purchase"],
        "home-maintenance": ["Home Repair", "Plumbing", "Electrical", "HVAC Service", "Lawn Care", "Cleaning Supplies"],
        "education": ["Online Course", "Books", "Tuition", "Workshop", "Training"],
        "clothing": ["Clothes Shopping", "New Shoes", "Work Clothes", "Seasonal Clothes"],
        "pets": ["Pet Food", "Vet Visit", "Pet Supplies", "Grooming"],
        "fitness": ["Gym Membership", "Fitness Class", "Sports Equipment"],
        "transfer-in": ["Transfer from Savings", "Account Transfer", "Funds Transfer"],
        "transfer-out": ["Transfer to Savings", "Investment Transfer", "Account Transfer"],
        "freelance": ["Freelance Payment", "Side Gig Income", "Contract Work"],
        "refund": ["Return Refund", "Reimbursement", "Cashback", "Refund Received"],
    }

    def generate_amount(slug: str, is_expense: bool) -> float:
        """Generate realistic amount using triangular distribution."""
        pattern = SPENDING_PATTERNS.get(slug, {"min": 10, "max": 100, "typical": 50})

        # Triangular distribution clusters around typical value
        amount = random.triangular(
            pattern["min"],
            pattern["max"],
            pattern["typical"]
        )

        # Add slight noise for variety
        noise = random.uniform(0.92, 1.08)
        amount = amount * noise

        # Round to realistic cents
        amount = round(amount, 2)

        return -amount if is_expense else amount

    def get_random_day(year: int, month: int, prefer_end: bool = False) -> int:
        """Get a random day in the given month."""
        last_day = monthrange(year, month)[1]
        if prefer_end:
            # Prefer later in month (bills, rent)
            return random.randint(max(1, last_day - 7), last_day)
        return random.randint(1, last_day)

    def get_memo(slug: str) -> str:
        """Get a random memo for the category."""
        templates = MEMO_TEMPLATES.get(slug, [slug.replace("-", " ").title()])
        return random.choice(templates)

    # =========================================
    # GENERATE TRANSACTIONS
    # =========================================

    transactions_to_add: list[dict] = []
    external_id_counter = 0

    def add_transaction(occurred: datetime, amount: float, memo: str, category_slug: str, account: Account | None):
        nonlocal external_id_counter
        external_id_counter += 1

        category = category_map.get(category_slug)
        if category is None:
            return

        transactions_to_add.append({
            "user_id": user_id,
            "external_id": f"seed-heavy-{seed_value}-{external_id_counter:06d}",
            "occurred_at": occurred,
            "amount": round(amount, 2),
            "memo": memo,
            "category_id": category.id,
            "account_id": account.id if account else checking.id,
            "currency": account.currency if account else "USD",
        })

    current = start_date

    while current <= today:
        year = current.year
        month = current.month
        last_day = monthrange(year, month)[1]

        # =========================
        # FIXED MONTHLY EXPENSES
        # =========================

        # Rent (1st-5th of month)
        if "rent" in category_map:
            rent_day = random.randint(1, 5)
            rent_amount = generate_amount("rent", is_expense=True)
            add_transaction(
                datetime(year, month, rent_day, 9, 0),
                rent_amount,
                get_memo("rent"),
                "rent",
                checking
            )

        # Utilities (varies by month - higher in summer/winter)
        if "utilities" in category_map:
            util_day = random.randint(10, 20)
            base_util = generate_amount("utilities", is_expense=True)
            # Seasonal adjustment
            if month in [1, 2, 7, 8, 12]:  # Hot/cold months
                base_util *= random.uniform(1.2, 1.5)
            add_transaction(
                datetime(year, month, util_day, 14, 0),
                round(base_util, 2),
                get_memo("utilities"),
                "utilities",
                checking
            )

        # Insurance (monthly)
        if "insurance" in category_map:
            ins_day = random.randint(1, 10)
            add_transaction(
                datetime(year, month, ins_day, 10, 0),
                generate_amount("insurance", is_expense=True),
                get_memo("insurance"),
                "insurance",
                checking
            )

        # =========================
        # INCOME (Salary bi-weekly)
        # =========================

        if "salary" in category_map:
            # Two paychecks per month (around 15th and end of month)
            salary_amount = generate_amount("salary", is_expense=False)

            # First paycheck
            pay_day_1 = random.randint(13, 16)
            add_transaction(
                datetime(year, month, pay_day_1, 8, 0),
                salary_amount,
                get_memo("salary"),
                "salary",
                checking
            )

            # Second paycheck
            pay_day_2 = random.randint(max(28, last_day - 3), last_day)
            add_transaction(
                datetime(year, month, pay_day_2, 8, 0),
                salary_amount * random.uniform(0.98, 1.02),  # Slight variation
                get_memo("salary"),
                "salary",
                checking
            )

        # Interest income (monthly on savings)
        if "interest" in category_map and savings:
            interest_day = random.randint(last_day - 3, last_day)
            add_transaction(
                datetime(year, month, interest_day, 23, 59),
                generate_amount("interest", is_expense=False),
                get_memo("interest"),
                "interest",
                savings
            )

        # =========================
        # VARIABLE FREQUENCY EXPENSES
        # =========================

        for slug, pattern in SPENDING_PATTERNS.items():
            if slug in ["rent", "utilities", "insurance", "salary", "interest", "bonus"]:
                continue  # Already handled above

            category = category_map.get(slug)
            if not category:
                continue

            # Determine if expense or income
            is_expense = category.category_type == "expense" or slug not in ["dividends", "freelance", "refund", "transfer-in"]

            # Get frequency range
            min_freq, max_freq = pattern.get("per_month", (1, 3))
            num_transactions = random.randint(min_freq, max_freq)

            # Generate transactions for this category this month
            for _ in range(num_transactions):
                # Random day
                prefer_weekend = slug in ["dining-out", "entertainment", "shopping", "travel"]
                tx_day = get_random_day(year, month, prefer_end=False)

                # Adjust for weekends for certain categories
                if prefer_weekend:
                    # Push towards Friday-Sunday
                    day_date = date(year, month, tx_day)
                    if day_date.weekday() < 4 and random.random() < 0.6:
                        # Move to weekend
                        days_to_friday = 4 - day_date.weekday()
                        tx_day = min(tx_day + days_to_friday + random.randint(0, 2), last_day)

                # Random time
                hour = random.randint(7, 22)
                minute = random.randint(0, 59)

                # Generate amount
                amount = generate_amount(slug, is_expense)

                # Choose account
                if is_expense and credit_card and random.random() < 0.6:
                    account = credit_card
                elif slug.startswith("transfer"):
                    account = savings if random.random() < 0.5 else checking
                else:
                    account = checking

                add_transaction(
                    datetime(year, month, tx_day, hour, minute),
                    amount,
                    get_memo(slug),
                    slug,
                    account
                )

        # =========================
        # SPECIAL: Annual Bonus (December or June)
        # =========================

        if "bonus" in category_map and month in [6, 12]:
            if random.random() < 0.8:  # 80% chance each eligible month
                bonus_day = random.randint(10, 20)
                add_transaction(
                    datetime(year, month, bonus_day, 9, 0),
                    generate_amount("bonus", is_expense=False),
                    get_memo("bonus"),
                    "bonus",
                    checking
                )

        # =========================
        # SPECIAL: Dividends (Quarterly)
        # =========================

        if "dividends" in category_map and month in [3, 6, 9, 12]:
            if random.random() < 0.7:
                div_day = random.randint(15, last_day)
                add_transaction(
                    datetime(year, month, div_day, 10, 0),
                    generate_amount("dividends", is_expense=False),
                    get_memo("dividends"),
                    "dividends",
                    checking
                )

        # =========================
        # SPECIAL: Travel (Seasonal peaks)
        # =========================

        if "travel" in category_map and month in [3, 6, 7, 8, 11, 12]:
            if random.random() < 0.35:  # 35% chance in travel months
                for _ in range(random.randint(1, 4)):  # Multiple travel expenses
                    travel_day = random.randint(1, last_day)
                    add_transaction(
                        datetime(year, month, travel_day, random.randint(6, 22), random.randint(0, 59)),
                        generate_amount("travel", is_expense=True),
                        get_memo("travel"),
                        "travel",
                        credit_card or checking
                    )

        # Move to next month
        if month == 12:
            current = date(year + 1, 1, 1)
        else:
            current = date(year, month + 1, 1)

    # =========================================
    # BATCH INSERT ALL TRANSACTIONS
    # =========================================

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


def _seed_habit_entries(session: Session, user_id: int, days_back: int = 365 * 2) -> None:
    """Seed realistic habit completion patterns over 2 years."""

    conditions = [Habit.user_id == user_id]
    archived_column = getattr(Habit, "archived", None)
    if archived_column is not None:
        conditions.append(archived_column == False)  # type: ignore[operator]
    elif hasattr(Habit, "is_active"):
        conditions.append(Habit.is_active == True)  # noqa: E712

    habits = session.exec(select(Habit).where(*conditions)).all()

    if not habits:
        return

    today = date.today()

    for habit in habits:
        # Each habit has different consistency (40-85%)
        base_consistency = random.uniform(0.40, 0.85)

        # Some habits have weekly patterns (workout MWF, etc.)
        has_weekly_pattern = random.random() < 0.4
        if has_weekly_pattern:
            weekly_days = set(random.sample(range(7), k=random.randint(3, 5)))
        else:
            weekly_days = None

        streak_bonus = 0.0  # Increases when on a streak

        for day_offset in range(days_back, -1, -1):
            check_date = today - timedelta(days=day_offset)

            # Skip if entry exists
            existing = session.exec(
                select(HabitEntry).where(
                    HabitEntry.habit_id == habit.id,
                    HabitEntry.occurred_on == check_date,
                )
            ).first()
            if existing:
                if existing.value > 0:
                    streak_bonus = min(streak_bonus + 0.05, 0.25)  # Build streak momentum
                else:
                    streak_bonus = 0
                continue

            # Determine if completed
            effective_consistency = base_consistency + streak_bonus

            if weekly_days is not None:
                # Weekly pattern - higher consistency on designated days
                if check_date.weekday() in weekly_days:
                    completed = random.random() < (effective_consistency + 0.15)
                else:
                    completed = random.random() < (effective_consistency * 0.3)  # Much lower on off-days
            else:
                completed = random.random() < effective_consistency

            if completed:
                entry = HabitEntry(
                    habit_id=habit.id,
                    occurred_on=check_date,
                    value=1,
                    user_id=user_id,
                )
                session.add(entry)
                streak_bonus = min(streak_bonus + 0.05, 0.25)
            else:
                streak_bonus = 0

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
    """Seed a diverse, realistic investment portfolio."""

    # Initialize randomness
    _initialize_random_seed()

    # Define realistic portfolio with various asset classes
    HOLDINGS_TEMPLATE = [
        # US Total Market / Large Cap ETFs (35%)
        {"symbol": "VTI", "name": "Vanguard Total Stock Market ETF", "target_pct": 0.18, "price_range": (220, 290)},
        {"symbol": "VOO", "name": "Vanguard S&P 500 ETF", "target_pct": 0.10, "price_range": (420, 520)},
        {"symbol": "QQQ", "name": "Invesco QQQ Trust", "target_pct": 0.07, "price_range": (380, 480)},

        # Individual Stocks (15%)
        {"symbol": "AAPL", "name": "Apple Inc.", "target_pct": 0.04, "price_range": (165, 210)},
        {"symbol": "MSFT", "name": "Microsoft Corp.", "target_pct": 0.04, "price_range": (380, 450)},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "target_pct": 0.03, "price_range": (140, 185)},
        {"symbol": "NVDA", "name": "NVIDIA Corp.", "target_pct": 0.02, "price_range": (450, 950)},
        {"symbol": "AMZN", "name": "Amazon.com Inc.", "target_pct": 0.02, "price_range": (160, 210)},

        # International (12%)
        {"symbol": "VXUS", "name": "Vanguard Total International", "target_pct": 0.08, "price_range": (56, 68)},
        {"symbol": "VEA", "name": "Vanguard FTSE Developed Markets", "target_pct": 0.04, "price_range": (46, 54)},

        # Bonds (18%)
        {"symbol": "BND", "name": "Vanguard Total Bond Market", "target_pct": 0.12, "price_range": (72, 82)},
        {"symbol": "VTIP", "name": "Vanguard Short-Term Inflation-Protected", "target_pct": 0.03, "price_range": (48, 53)},
        {"symbol": "TLT", "name": "iShares 20+ Year Treasury Bond", "target_pct": 0.03, "price_range": (88, 110)},

        # Real Estate (8%)
        {"symbol": "VNQ", "name": "Vanguard Real Estate ETF", "target_pct": 0.05, "price_range": (82, 105)},
        {"symbol": "O", "name": "Realty Income Corp.", "target_pct": 0.03, "price_range": (52, 68)},

        # Crypto (5%)
        {"symbol": "BTC", "name": "Bitcoin", "target_pct": 0.03, "price_range": (42000, 75000)},
        {"symbol": "ETH", "name": "Ethereum", "target_pct": 0.02, "price_range": (2200, 4200)},

        # Commodities / Other (7%)
        {"symbol": "GLD", "name": "SPDR Gold Shares", "target_pct": 0.04, "price_range": (175, 220)},
        {"symbol": "VIG", "name": "Vanguard Dividend Appreciation", "target_pct": 0.03, "price_range": (165, 195)},
    ]

    # Random total portfolio value ($75k - $750k range)
    total_portfolio = random.uniform(75000, 750000)

    # Find or create investment accounts
    investment_accounts = [
        acc for name, acc in accounts.items()
        if any(t in name.lower() for t in ["brokerage", "ira", "401", "investment", "robinhood", "fidelity", "schwab", "vanguard"])
    ]

    if not investment_accounts:
        # Use first available account
        investment_accounts = list(accounts.values())[:1]

    if not investment_accounts:
        return

    for template in HOLDINGS_TEMPLATE:
        # Randomly skip some holdings (not everyone owns everything)
        if random.random() < 0.15:  # 15% chance to skip
            continue

        # Random account assignment
        account = random.choice(investment_accounts)

        # Calculate target value with variance (+/- 30%)
        target_value = total_portfolio * template["target_pct"]
        target_value *= random.uniform(0.7, 1.3)

        # Skip if value too small
        if target_value < 100:
            continue

        # Generate prices with gain/loss variance
        avg_price = random.uniform(*template["price_range"])

        # Market price: can be -25% to +40% from avg (simulating gains/losses)
        gain_loss = random.uniform(0.75, 1.40)
        market_price = avg_price * gain_loss

        # Calculate shares
        shares = target_value / avg_price

        # Round shares appropriately
        if template["symbol"] in ["BTC", "ETH"]:
            shares = round(shares, 6)  # Crypto allows fractional
        elif shares < 1:
            shares = round(shares, 4)  # Fractional shares
        else:
            shares = round(shares, 2)

        # Random acquisition date (30 days to 5 years ago)
        days_ago = random.randint(30, 5 * 365)
        acquired_at = datetime.now() - timedelta(days=days_ago)

        # Check for existing holding
        existing = session.exec(
            select(Holding).where(
                Holding.user_id == user_id,
                Holding.symbol == template["symbol"],
                Holding.account_id == account.id,
            )
        ).first()

        if existing:
            # Update existing
            existing.quantity = shares
            existing.avg_price = round(avg_price, 2)
            existing.market_price = round(market_price, 2)
            existing.acquired_at = acquired_at
        else:
            # Create new
            holding = Holding(
                user_id=user_id,
                symbol=template["symbol"],
                quantity=shares,
                avg_price=round(avg_price, 2),
                market_price=round(market_price, 2),
                account_id=account.id,
                acquired_at=acquired_at,
                currency="USD",
            )
            session.add(holding)

    session.flush()


def _seed_budget(session: Session, categories: dict[str, Category], user_id: int) -> None:
    """Generate realistic budgets based on actual transaction patterns over 5 years."""

    today = date.today()
    start_year = today.year - 4  # 5 years of budgets

    # Categories that tend to go over budget sometimes
    OVERSPEND_PRONE = ["entertainment", "dining-out", "shopping", "travel", "coffee", "gifts"]

    for year in range(start_year, today.year + 1):
        for month in range(1, 13):
            # Don't create future budgets
            if year == today.year and month > today.month:
                break

            period_start = date(year, month, 1)
            period_end = date(year, month, monthrange(year, month)[1])

            # Skip if budget already exists
            existing = session.exec(
                select(Budget).where(
                    Budget.period_start == period_start,
                    Budget.user_id == user_id,
                )
            ).first()
            if existing:
                continue

            # Calculate actual spending by category for this month
            month_start = datetime.combine(period_start, datetime.min.time())
            month_end = datetime.combine(period_end, datetime.max.time())

            category_spending: dict[int, float] = {}

            for category in categories.values():
                if category.category_type != "expense":
                    continue
                if category.id is None:
                    continue

                txns = session.exec(
                    select(Transaction).where(
                        Transaction.user_id == user_id,
                        Transaction.category_id == category.id,
                        Transaction.occurred_at >= month_start,
                        Transaction.occurred_at <= month_end,
                        Transaction.amount < 0,
                    )
                ).all()

                total_spent = sum(abs(t.amount) for t in txns)
                if total_spent > 0:
                    category_spending[category.id] = total_spent

            if not category_spending:
                continue

            # Create budget
            budget = Budget(
                period_start=period_start,
                period_end=period_end,
                label=f"{period_start.strftime('%B %Y')} Budget",
                user_id=user_id,
            )
            session.add(budget)
            session.flush()

            # Create budget lines with realistic variance
            for category_id, actual_spent in category_spending.items():
                category = session.get(Category, category_id)

                # Determine budget amount relative to actual spending
                if category and category.slug in OVERSPEND_PRONE:
                    # These categories often go over budget
                    if random.random() < 0.35:  # 35% chance of overspending
                        # Budget less than actual (will show as over budget)
                        variance = random.uniform(0.65, 0.90)
                    else:
                        variance = random.uniform(0.95, 1.15)
                else:
                    # Regular categories - usually on or under budget
                    variance = random.uniform(0.90, 1.20)

                planned = round(actual_spent * variance, 2)

                # Minimum budget amounts for realism
                planned = max(planned, 25.0)

                line = BudgetLine(
                    budget_id=budget.id,
                    category_id=category_id,
                    planned_amount=planned,
                    rollover_enabled=random.random() < 0.25,  # 25% have rollover
                    user_id=user_id,
                )
                session.add(line)

            session.flush()


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
        _seed_habit_entries(session, user_id=user_id)
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
