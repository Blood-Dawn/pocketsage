"""Liabilities projection utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(slots=True)
class LiabilitySnapshot:
    """Simple container describing a liability for projections."""

    id: int
    name: str
    balance: float
    apr: float
    minimum_payment: float
    payoff_strategy: str


_SAMPLE_LIABILITIES: tuple[LiabilitySnapshot, ...] = (
    LiabilitySnapshot(
        id=1,
        name="Visa Rewards",
        balance=5400.0,
        apr=19.99,
        minimum_payment=125.0,
        payoff_strategy="snowball",
    ),
    LiabilitySnapshot(
        id=2,
        name="Auto Loan",
        balance=16200.0,
        apr=4.9,
        minimum_payment=320.0,
        payoff_strategy="avalanche",
    ),
    LiabilitySnapshot(
        id=3,
        name="Student Loan",
        balance=23800.0,
        apr=5.4,
        minimum_payment=275.0,
        payoff_strategy="snowball",
    ),
)


def _monthly_rate(apr: float) -> float:
    return max(apr, 0.0) / 100.0 / 12.0


def amortize_liability(liability: LiabilitySnapshot) -> list[dict]:
    """Generate a simple amortization schedule for a liability."""

    balance = float(liability.balance)
    monthly_rate = _monthly_rate(liability.apr)
    schedule: list[dict] = []
    month = 1
    max_months = 600  # prevent runaway schedules

    while balance > 0.01 and month <= max_months:
        interest = balance * monthly_rate if monthly_rate else 0.0
        minimum_due = max(liability.minimum_payment, balance * 0.04)
        payment = min(minimum_due, balance + interest)
        principal = payment - interest

        # Guard against scenarios where interest eclipses payment.
        if principal <= 0:
            principal = min(balance, max(balance * 0.01, 1.0))
            payment = interest + principal

        balance = max(0.0, balance - principal)

        schedule.append(
            {
                "month": month,
                "payment": round(payment, 2),
                "principal": round(principal, 2),
                "interest": round(interest, 2),
                "ending_balance": round(balance, 2),
            }
        )
        month += 1

    return schedule


def compute_overview(*, liabilities: Sequence[LiabilitySnapshot] | None = None) -> dict:
    """Produce payoff projections and chart-ready aggregates."""

    liability_inputs: Sequence[LiabilitySnapshot] = liabilities or _SAMPLE_LIABILITIES

    projections: list[dict] = []
    total_start_balance = 0.0

    for snapshot in liability_inputs:
        schedule = amortize_liability(snapshot)
        total_interest = round(sum(row["interest"] for row in schedule), 2)
        total_payment = round(sum(row["payment"] for row in schedule), 2)
        months_to_payoff = len(schedule)

        projections.append(
            {
                "id": snapshot.id,
                "name": snapshot.name,
                "balance": round(snapshot.balance, 2),
                "apr": round(snapshot.apr, 2),
                "minimum_payment": round(snapshot.minimum_payment, 2),
                "payoff_strategy": snapshot.payoff_strategy,
                "schedule": schedule,
                "total_interest": total_interest,
                "total_payment": total_payment,
                "months_to_payoff": months_to_payoff,
            }
        )
        total_start_balance += snapshot.balance

    max_months = max((projection["months_to_payoff"] for projection in projections), default=0)

    balance_timeline: list[dict] = [
        {
            "month": 0,
            "label": "Start",
            "total_balance": round(total_start_balance, 2),
        }
    ]

    for month_index in range(1, max_months + 1):
        total_balance = 0.0
        for projection in projections:
            schedule = projection["schedule"]
            if month_index <= len(schedule):
                total_balance += schedule[month_index - 1]["ending_balance"]
        balance_timeline.append(
            {
                "month": month_index,
                "label": f"Month {month_index}",
                "total_balance": round(total_balance, 2),
            }
        )

    strategy_keys = sorted({projection["payoff_strategy"] for projection in projections})
    payments_by_strategy: list[dict] = []
    for month_index in range(1, max_months + 1):
        month_totals = {key: 0.0 for key in strategy_keys}
        for projection in projections:
            schedule = projection["schedule"]
            if month_index <= len(schedule):
                month_totals[projection["payoff_strategy"]] += schedule[month_index - 1]["payment"]
        payments_by_strategy.append(
            {
                "month": month_index,
                "label": f"Month {month_index}",
                "strategies": {key: round(value, 2) for key, value in month_totals.items()},
            }
        )

    start_balance = balance_timeline[0]["total_balance"] if balance_timeline else 0.0
    end_balance = balance_timeline[-1]["total_balance"] if balance_timeline else 0.0
    months = max(len(balance_timeline) - 1, 0)

    balance_description = (
        "Projected total balances stay flat."
        if months == 0 or abs(start_balance - end_balance) < 0.01
        else "Projected total balance declines from $"
        + f"{start_balance:,.0f} to ${end_balance:,.0f} over {months} month"
        + ("s" if months != 1 else "")
    )

    strategy_totals = {
        key: round(
            sum(row["strategies"].get(key, 0.0) for row in payments_by_strategy),
            2,
        )
        for key in strategy_keys
    }

    if strategy_totals:
        parts = [
            f"{key.title()} payments total ${value:,.0f}"
            for key, value in strategy_totals.items()
        ]
        strategy_description = ", ".join(parts) + "."
    else:
        strategy_description = "No scheduled payments recorded yet."

    return {
        "liabilities": [
            {key: value for key, value in projection.items() if key != "schedule"}
            for projection in projections
        ],
        "schedules": {
            projection["id"]: projection["schedule"] for projection in projections
        },
        "balance_timeline": balance_timeline,
        "strategy_payments": payments_by_strategy,
        "strategy_keys": strategy_keys,
        "balance_description": balance_description,
        "strategy_description": strategy_description,
        "totals": {
            "starting_balance": round(total_start_balance, 2),
            "projected_interest": round(
                sum(projection["total_interest"] for projection in projections),
                2,
            ),
        },
    }


__all__ = ["LiabilitySnapshot", "amortize_liability", "compute_overview"]
