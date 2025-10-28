"""Liability form stubs."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Self


@dataclass(slots=True)
class LiabilityForm:
    """Placeholder for liability creation/editing form."""

    name: str = ""
    balance: Decimal | None = None
    apr: Decimal | None = None
    minimum_payment: Decimal | None = None
    
    def validate(self) -> bool:
        """Validate liability inputs."""
        # Check if required fields are not None and are positive numbers
        if self.balance is None or self.balance <= Decimal("0"):
            return False
        if self.apr is None or self.apr < Decimal("0"):
            return False
        if self.minimum_payment is None or self.minimum_payment < Decimal("0"):
            return False

        if self.minimum_payment > self.balance:
            return False

        return True
