"""Liability form stubs."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class LiabilityForm:
    """Placeholder for liability creation/editing form."""

    name: str = ""
    balance: Decimal | None = None
    apr: Decimal | None = None
    minimum_payment: Decimal | None = None

    def validate(self) -> bool:
        """Validate liability inputs."""

        # TODO(@debts-squad): enforce APR/balance/minimum payment ranges and units.
        raise NotImplementedError
