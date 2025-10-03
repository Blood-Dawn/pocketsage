"""Debt payoff calculators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol


@dataclass(slots=True)
class DebtAccount:
    """Represents a liability input for payoff projections."""

    id: int
    balance: float
    apr: float
    minimum_payment: float

    # TODO(@debts-squad): include statement_due_day and extra_payment fields.


class AmortizationWriter(Protocol):
    """Persists payoff projections for later retrieval."""

    def write_schedule(
        self, *, debt_id: int, rows: list[dict]
    ) -> None:  # pragma: no cover - interface
        ...


def snowball_schedule(*, debts: Iterable[DebtAccount], surplus: float) -> list[dict]:
    """Return payoff schedule prioritizing smallest balances first."""

    # TODO(@teammate): implement balance sorting + amortization math per finance spec.
    raise NotImplementedError


def avalanche_schedule(*, debts: Iterable[DebtAccount], surplus: float) -> list[dict]:
    """Return payoff schedule prioritizing highest APR first."""

    # TODO(@teammate): implement APR sort, tie-breakers, and minimum payment handling.
    raise NotImplementedError


def persist_projection(
    *, writer: AmortizationWriter, debts: Iterable[DebtAccount], strategy: str, surplus: float
) -> None:
    """Compute schedule for desired strategy and hand to persistence layer."""

    # TODO(@teammate): dispatch to strategy, call writer, and assert on payload shape.
    raise NotImplementedError
