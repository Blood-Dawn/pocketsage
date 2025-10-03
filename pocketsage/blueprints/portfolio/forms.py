"""Portfolio form stubs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PortfolioImportForm:
    """Placeholder for portfolio CSV upload."""

    file_path: str = ""

    def validate(self) -> bool:
        """Validate uploaded file metadata."""

        # TODO(@portfolio-squad): ensure CSV extension, size limits, and content sniffing.
        raise NotImplementedError
