"""Portfolio form stubs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class PortfolioImportForm:
    """Placeholder for portfolio CSV upload."""

    file_path: str = ""

    def validate(self) -> bool:
        """Validate uploaded file metadata."""
        p = Path(self.file_path)
        if not p.exists():
            return False
        if p.suffix.lower() not in {".csv", ".txt"}:
            return False
        try:
            # Ensure the file has at least one header line
            with p.open("r", encoding="utf-8") as fh:
                header = fh.readline().strip()
                if "," not in header:
                    return False
        except Exception:
            return False
        return True
