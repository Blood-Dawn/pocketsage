"""Data loaders for the overview dashboard."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable

from sqlmodel import select

from ...extensions import session_scope
from ...models import Habit, HabitEntry, Liability, Transaction
from ..portfolio.repository import SqlModelPortfolioRepository


@dataclass(slots=True)
class HoldingHighlight:
    symbol: str
    value: float
    allocation_pct: float


def _compute_current_streak(entries: Iterable[HabitEntry], *, today: date) -> int:
    """Return the length of the current streak for the provided entries."""

    streak = 0
    # Sort newest to oldest to calculate consecutive days from today backward.
    for entry in sorted(entries, key=lambda item: item.occurred_on, reverse=True):
        expected = today - timedelta(days=streak)
        if entry.occurred_on == expected:
            streak += 1
            continue
        if entry.occurred_on > expected:
            # Entries newer than the expected day (e.g., duplicate completions) are skipped.
            continue
        break
    return streak


def load_overview_summary() -> dict:
    """Gather summary statistics used by the overview dashboard."""

    with session_scope() as session:
        # Ledger / balances --------------------------------------------------
        transactions = session.exec(select(Transaction)).all()
        total_inflow = sum(float(tx.amount) for tx in transactions if tx.amount > 0)
        total_outflow = sum(-float(tx.amount) for tx in transactions if tx.amount < 0)
        net_balance = total_inflow - total_outflow

        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_spending = sum(
            -float(tx.amount)
            for tx in transactions
            if tx.amount < 0 and tx.occurred_at >= thirty_days_ago
        )

        # Habits -------------------------------------------------------------
        habits = session.exec(select(Habit)).all()
        active_habit_count = sum(1 for habit in habits if habit.is_active)
        entries = session.exec(select(HabitEntry)).all()
        today = date.today()
        week_start = today - timedelta(days=6)
        completions_today = sum(1 for entry in entries if entry.occurred_on == today)
        weekly_completions = sum(1 for entry in entries if entry.occurred_on >= week_start)

        entries_by_habit: dict[int, list[HabitEntry]] = defaultdict(list)
        for entry in entries:
            entries_by_habit[entry.habit_id].append(entry)
        best_streak = max(
            (
                _compute_current_streak(habit_entries, today=today)
                for habit_entries in entries_by_habit.values()
            ),
            default=0,
        )

        # Liabilities -------------------------------------------------------
        liabilities = session.exec(select(Liability)).all()
        total_liability_balance = sum(float(item.balance or 0.0) for item in liabilities)
        average_apr = (
            sum(float(item.apr or 0.0) for item in liabilities) / len(liabilities)
            if liabilities
            else 0.0
        )

        # Portfolio ---------------------------------------------------------
        repo = SqlModelPortfolioRepository(session)
        holdings = list(repo.list_holdings())
        allocation_summary = repo.allocation_summary()
        total_portfolio_value = float(allocation_summary.get("total_value", 0.0) or 0.0)
        allocation_map = allocation_summary.get("allocation", {})

        holding_highlights: list[HoldingHighlight] = []
        for holding in holdings:
            quantity = float(holding.quantity or 0.0)
            avg_price = float(holding.avg_price or 0.0)
            value = quantity * avg_price
            if value <= 0:
                continue
            allocation_pct = float(allocation_map.get(holding.symbol, 0.0) * 100)
            holding_highlights.append(
                HoldingHighlight(symbol=holding.symbol, value=value, allocation_pct=allocation_pct)
            )

    holding_highlights.sort(key=lambda h: h.value, reverse=True)

    return {
        "balances": {
            "net": net_balance,
            "inflow": total_inflow,
            "outflow": total_outflow,
            "recent_spending": recent_spending,
        },
        "habits": {
            "active": active_habit_count,
            "total": len(habits),
            "completions_today": completions_today,
            "weekly_completions": weekly_completions,
            "best_streak": best_streak,
        },
        "liabilities": {
            "count": len(liabilities),
            "total_balance": total_liability_balance,
            "average_apr": average_apr,
        },
        "portfolio": {
            "holdings": len(holdings),
            "total_value": total_portfolio_value,
            "top_holdings": holding_highlights[:3],
        },
    }
