"""Optional watchdog-based CSV folder ingestion."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Protocol


class CSVImporter(Protocol):
    """Protocol describing the CSV import orchestration function."""

    def __call__(self, *, csv_path: Path) -> int:  # pragma: no cover - interface
        ...


def start_watcher(*, folder: Path, importer: CSVImporter, allowed_filename: str | None = None):
    """Start a watchdog observer for the provided folder.

    When allowed_filename is provided, only matching files will be processed.
    """

    try:
        events_mod = importlib.import_module("watchdog.events")
        observers_mod = importlib.import_module("watchdog.observers")
        FileSystemEventHandler = getattr(events_mod, "FileSystemEventHandler")
        Observer = getattr(observers_mod, "Observer")
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "watchdog not installed; install extras to enable watched folder"
        ) from exc

    class _Handler(FileSystemEventHandler):  # type: ignore[misc]
        def __init__(self, *, importer: CSVImporter) -> None:
            self.importer = importer

        def on_created(self, event) -> None:  # pragma: no cover - integration path
            if getattr(event, "is_directory", False):
                return
            candidate = Path(event.src_path)
            if allowed_filename and candidate.name != allowed_filename:
                return
            # TODO(@teammate): debounce rapid duplicate events and batch processing.
            self.importer(csv_path=candidate)

    observer = Observer()
    handler = _Handler(importer=importer)
    observer.schedule(handler, path=str(folder), recursive=False)
    observer.start()
    # TODO(@ops-team): surface observer lifecycle hooks + shutdown in app factory.
    return observer
