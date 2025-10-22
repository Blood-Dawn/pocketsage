# PocketSage Runbook

## Installation Extras

PocketSage defines two optional extras in `pyproject.toml` that tailor the development experience:

### Development toolchain (`dev` extra)
- **Install:** `pip install -e ".[dev]"`
- **When to use:** Install this extra for day-to-day development. It includes the formatting, linting, and testing tools (`black`, `ruff`, `pytest`, and `pre-commit`) required to work on the codebase and run CI-equivalent checks locally.

### Background file watcher (`watcher` extra)
- **Install:** `pip install -e ".[watcher]"`
- **When to use:** Install this extra when you need filesystem event monitoring for background import/testing workflows. It provides the `watchdog` dependency that powers optional observer integrations referenced in the README TODO items.
