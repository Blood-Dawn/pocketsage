# PocketSage System Overview

## Purpose
PocketSage is an offline-first personal finance and habits tracker built for desktop. The repository provides a complete scaffold for a Flet-based UI, SQLModel persistence, services for CSV/reporting tasks, and packaging with `flet pack`.

## High-Level Architecture
- **Desktop shell** (`run_desktop.py` -> `desktop/app.py`) wires routing, keyboard shortcuts, and navigation into Flet views.
- **Configuration layer** (`pocketsage/config.py`) reads environment variables, resolves storage paths, and prepares SQLAlchemy engine options (including SQLCipher toggles).
- **Database bootstrap** (`pocketsage/infra/database.py`) builds/initializes the SQLModel engine and exposes session helpers for repositories and services.
- **Domain models** (`pocketsage/models/`) declare SQLModel tables for ledger, budgeting, liabilities, habits, holdings, and settings.
- **Services** (`pocketsage/services/`) provide domain logic boundaries (budgeting, debts, CSV import, reporting, admin tasks, watcher stubs).
- **Desktop UI** (`pocketsage/desktop/`) houses the router, shared components, and views for dashboard, ledger, budgets, habits, debts, portfolio, reports, and settings.
- **Tooling** includes `pyproject.toml`, `Makefile`, tests under `tests/`, and documentation in `docs/`.

## Application Entry Points

| File | Purpose |
| --- | --- |
| `run_desktop.py` | Launches the Flet application (uses `desktop/app.py`). |
| `Makefile` | Convenience shortcuts for linting, testing, packaging, and demo seeding. |
| `scripts/build_desktop.*` | Platform-specific wrappers around `flet pack` to emit binaries under `dist/`. |

`run_desktop.py` delegates initialization to the Flet app, which constructs `AppContext` and registers routes.

## Configuration (`pocketsage/config.py`)
- Loads `.env` values automatically via `python-dotenv`.
- Resolves a writable data directory (defaults to `instance/`).
- Constructs a SQLite URL; when `POCKETSAGE_USE_SQLCIPHER` is enabled, prepares a SQLCipher-compatible URI placeholder.
- Provides `sqlalchemy_engine_options()` to pass connect arguments (thread-safety, future SQLCipher handshake).

Key environment variables:
- `POCKETSAGE_DATA_DIR`: override storage location.
- `POCKETSAGE_DATABASE_URL`: use a custom database path or external engine.
- `POCKETSAGE_USE_SQLCIPHER` / `POCKETSAGE_SQLCIPHER_KEY`: enable encrypted storage (TODO in code).

## Persistence Layer (`pocketsage/infra/database.py`)
- Creates a SQLModel engine using the config-provided URL and options.
- Initializes tables via `SQLModel.metadata.create_all` (future migrations TODO).
- Exposes `create_session_factory` and `session_scope(engine)` helpers for repositories, services, and admin tasks.

## Models (`pocketsage/models/`)
Tables cover ledger, budgeting, liabilities, habits, holdings, and settings. Fields use typing annotations and relationships, with TODOs for money precision and mapper corrections (Holding <-> Account remains broken).

## Services (`pocketsage/services/`)
Business logic modules with TODO markers:
- `budgeting.py`: Compute variance reports and rolling cashflow series.
- `debts.py`: Debt snowball/avalanche payoff schedules.
- `import_csv.py`: Normalize CSVs, transform rows into `Transaction` objects, perform idempotent upserts.
- `reports.py`: Future metrics/report aggregation (currently stubbed).
- `watcher.py`: Optional filesystem watcher (extra dependency).
- `admin_tasks.py`: Desktop-friendly demo seed and export ZIP generation with retention.

## Desktop UI (`pocketsage/desktop/`)
- `app.py` configures the page, builds `AppContext`, registers routes, and wires keyboard shortcuts.
- `navigation.py` handles routing/view stack.
- `components/` holds reusable UI pieces (layout, dialogs, charts).
- `views/` implements screens for dashboard, ledger, budgets, habits, debts, portfolio, reports, and settings; admin/export actions call `services/admin_tasks.py`.

## Scripts (`scripts/`)
- `seed_demo.py`: Seeds demo data using `services/admin_tasks.run_demo_seed` (idempotent).
- `csv_samples/`: Example ledger and portfolio CSVs for import flows.
- `build_desktop.*`: Wrappers around `flet pack` plus test execution.

## Tests (`tests/`)
- Repository and service coverage (habits, debts, budgeting stubs, CSV import, money representation, admin tasks, desktop smoke test).
- Fixtures in `tests/conftest.py` provide temporary SQLite databases and factories.
- Command examples: `pytest`, `pytest -n auto`, `pytest --cov=src/pocketsage --cov-report=term-missing`.

## Build & Tooling Strategy
- `pyproject.toml` defines runtime deps, optional extras (`watcher`, `dev`), code style (Black), linting (Ruff), pytest defaults, and coverage config.
- `.pre-commit-config.yaml` can run formatting/lint hooks on commit (`make setup` installs them).
- `Makefile` targets: `setup`, `dev`, `test`, `lint`, `package`, `demo-seed`.
- Packaging uses `flet pack` (no PyInstaller spec required post-web removal).

## Next Steps & TODO Themes
- Fix ORM mapping issues (Holding <-> Account) and money precision risks.
- Implement budgeting calculations, debt payoff correctness, and streak fixes.
- Add imports idempotency/CSV UI, watcher flows, charts/report exports.
- Expand desktop CRUD, filters, and admin/backup UX; replace `create_all` with Alembic once schema stabilizes.
