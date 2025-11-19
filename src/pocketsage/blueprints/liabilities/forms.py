"""Liability form definitions and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Dict, Iterable, List

StrategyChoices = Dict[str, str]


DEFAULT_STRATEGIES: StrategyChoices = {
    "avalanche": "Avalanche · prioritize highest APR first",
    "snowball": "Snowball · knock out the smallest balance",
    "hybrid": "Hybrid · mix avalanche with manual targeting",
}


@dataclass(slots=True)
class LiabilityForm:
    """Represents liability inputs and associated validation errors."""

    name: str = ""
    balance: Decimal | str | None = None
    apr: Decimal | str | None = None
    minimum_payment: Decimal | str | None = None
    target_strategy: str = "avalanche"
    errors: Dict[str, List[str]] = field(default_factory=dict, init=False)

    def validate(self, *, strategies: StrategyChoices | None = None) -> bool:
        """Validate liability inputs returning True when all values are acceptable."""

        self.errors.clear()

        if not self.name or not self.name.strip():
            self.errors.setdefault("name", []).append("Enter the creditor or account name.")
        else:
            self.name = self.name.strip()

        strategies = strategies or DEFAULT_STRATEGIES

        self.balance = self._parse_currency("balance", self.balance, minimum=Decimal("0.01"))
        self.apr = self._parse_currency("apr", self.apr, minimum=Decimal("0"))
        self.minimum_payment = self._parse_currency(
            "minimum_payment", self.minimum_payment, minimum=Decimal("0.01")
        )

        if isinstance(self.apr, Decimal) and (self.apr < 0 or self.apr > Decimal("100")):
            self.errors.setdefault("apr", []).append("APR must be between 0 and 100 percent.")

        if isinstance(self.minimum_payment, Decimal) and isinstance(self.balance, Decimal):
            if self.minimum_payment > self.balance:
                self.errors.setdefault("minimum_payment", []).append(
                    "Minimum payment cannot be greater than the balance."
                )

        if not self.target_strategy or self.target_strategy not in strategies:
            self.errors.setdefault("target_strategy", []).append("Choose a payoff strategy.")

        return not self.errors

    def _parse_currency(
        self,
        field: str,
        value: Decimal | str | None,
        *,
        minimum: Decimal,
    ) -> Decimal | None:
        """Parse and validate numeric input, storing errors when parsing fails."""

        if value is None or value == "":
            self.errors.setdefault(field, []).append("This field is required.")
            return None

        if not isinstance(value, Decimal):
            try:
                value = Decimal(str(value))
            except (InvalidOperation, TypeError, ValueError):
                self.errors.setdefault(field, []).append("Enter a valid number.")
                return None

        if value < minimum:
            message = (
                "Amount must be greater than zero."
                if minimum > 0
                else "Amount must be at least zero."
            )
            self.errors.setdefault(field, []).append(message)
        return value

    @property
    def error_messages(self) -> Iterable[str]:
        """Flattened iterable of error strings for summaries."""

        for messages in self.errors.values():
            yield from messages
