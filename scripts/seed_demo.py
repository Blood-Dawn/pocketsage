"""Demo data seeding script."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlmodel import select

from pocketsage import create_app
from pocketsage.extensions import session_scope
from pocketsage.models import (
    Account,
    Category,
    Habit,
    HabitEntry,
    Liability,
    Transaction,
)


def seed_demo() -> None:
    """Populate the database with demo content."""

    app = create_app("development")
    with app.app_context():
        with session_scope() as session:
            category_specs = [
                {
                    "name": "Groceries",
                    "slug": "groceries",
                    "category_type": "expense",
                    "color": "#4CAF50",
                },
                {
                    "name": "Dining Out",
                    "slug": "dining-out",
                    "category_type": "expense",
                    "color": "#FF9800",
                },
                {
                    "name": "Utilities",
                    "slug": "utilities",
                    "category_type": "expense",
                    "color": "#03A9F4",
                },
                {
                    "name": "Salary",
                    "slug": "salary",
                    "category_type": "income",
                    "color": "#8BC34A",
                },
            ]

            category_map: dict[str, Category] = {}
            for spec in category_specs:
                existing = session.exec(
                    select(Category).where(Category.slug == spec["slug"])
                ).one_or_none()
                if existing is None:
                    existing = Category(**spec)
                    session.add(existing)
                    session.flush()
                else:
                    existing.name = spec["name"]
                    existing.category_type = spec["category_type"]
                    existing.color = spec["color"]
                category_map[spec["slug"]] = existing

            account = session.exec(
                select(Account).where(Account.name == "Demo Checking")
            ).one_or_none()
            if account is None:
                account = Account(name="Demo Checking", currency="USD")
                session.add(account)
                session.flush()

            transaction_specs = [
                {
                    "external_id": "demo-tx-001",
                    "occurred_at": datetime(2024, 1, 5, 13, 30, tzinfo=timezone.utc),
                    "amount": -58.23,
                    "memo": "Grocery Run",
                    "category_slug": "groceries",
                },
                {
                    "external_id": "demo-tx-002",
                    "occurred_at": datetime(2024, 1, 8, 19, 45, tzinfo=timezone.utc),
                    "amount": -32.5,
                    "memo": "Dinner with friends",
                    "category_slug": "dining-out",
                },
                {
                    "external_id": "demo-tx-003",
                    "occurred_at": datetime(2024, 1, 10, 8, 0, tzinfo=timezone.utc),
                    "amount": -90.0,
                    "memo": "Electric bill",
                    "category_slug": "utilities",
                },
                {
                    "external_id": "demo-tx-004",
                    "occurred_at": datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc),
                    "amount": 2800.0,
                    "memo": "Monthly salary",
                    "category_slug": "salary",
                },
            ]

            for spec in transaction_specs:
                existing = session.exec(
                    select(Transaction).where(Transaction.external_id == spec["external_id"])
                ).one_or_none()
                if existing is None:
                    existing = Transaction(external_id=spec["external_id"])
                    session.add(existing)
                existing.occurred_at = spec["occurred_at"]
                existing.amount = spec["amount"]
                existing.memo = spec["memo"]
                existing.category_id = category_map[spec["category_slug"]].id
                existing.account_id = account.id
                existing.currency = account.currency

            habit_specs = [
                {
                    "name": "Morning Run",
                    "description": "Run at least 2 miles before work.",
                    "cadence": "daily",
                    "entries": [
                        (date(2024, 1, 6), 1),
                        (date(2024, 1, 7), 0),
                        (date(2024, 1, 8), 1),
                    ],
                },
                {
                    "name": "Review Budget",
                    "description": "Check spending against the monthly plan.",
                    "cadence": "weekly",
                    "entries": [
                        (date(2024, 1, 5), 1),
                        (date(2024, 1, 12), 1),
                    ],
                },
            ]

            for spec in habit_specs:
                existing = session.exec(
                    select(Habit).where(Habit.name == spec["name"])
                ).one_or_none()
                if existing is None:
                    existing = Habit(
                        name=spec["name"],
                        description=spec["description"],
                        cadence=spec["cadence"],
                    )
                    session.add(existing)
                    session.flush()
                else:
                    existing.description = spec["description"]
                    existing.cadence = spec["cadence"]
                    if not existing.is_active:
                        existing.is_active = True

                entries = {
                    entry.occurred_on: entry
                    for entry in session.exec(
                        select(HabitEntry).where(HabitEntry.habit_id == existing.id)
                    ).all()
                }
                for occurred_on, value in spec["entries"]:
                    entry = entries.get(occurred_on)
                    if entry is None:
                        session.add(
                            HabitEntry(
                                habit_id=existing.id,
                                occurred_on=occurred_on,
                                value=value,
                            )
                        )
                    else:
                        entry.value = value

            liability_specs = [
                {
                    "name": "Student Loan",
                    "balance": 12500.0,
                    "apr": 4.5,
                    "minimum_payment": 150.0,
                    "due_day": 15,
                },
                {
                    "name": "Credit Card",
                    "balance": 2300.0,
                    "apr": 19.99,
                    "minimum_payment": 65.0,
                    "due_day": 10,
                },
            ]

            for spec in liability_specs:
                existing = session.exec(
                    select(Liability).where(Liability.name == spec["name"])
                ).one_or_none()
                if existing is None:
                    session.add(Liability(**spec))
                else:
                    existing.balance = spec["balance"]
                    existing.apr = spec["apr"]
                    existing.minimum_payment = spec["minimum_payment"]
                    existing.due_day = spec["due_day"]


if __name__ == "__main__":
    seed_demo()
