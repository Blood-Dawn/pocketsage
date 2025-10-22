# PocketSage System Overview

## Purpose
PocketSage is an offline-first personal finance and habits tracker built on Flask and SQLModel. The repository provides a complete scaffold for registering domain blueprints, building services, ingesting CSV data, and packaging the desktop application with PyInstaller.

## High-Level Architecture
- **Flask application factory** (`pocketsage/__init__.py`) wires configuration, blueprints, and persistence.
- **Configuration layer** (`pocketsage/config.py`) reads environment variables, resolves storage paths, and prepares SQLAlchemy engine options (including SQLCipher toggles).
- **Extensions** (`pocketsage/extensions.py`) initialize the SQLModel engine, manage per-request sessions, and expose shared session helpers.
- **Domain models** (`pocketsage/models/`) declare SQLModel tables for ledger, budgeting, liabilities, habits, and settings.
- **Services** (`pocketsage/services/`) provide domain logic boundaries (budgeting, debts, CSV import, reporting, watcher orchestration).
- **Presentation layer** (`pocketsage/blueprints/`) groups routes, forms, and repository contracts for each UI area (ledger, habits, liabilities, portfolio, admin).
- **Assets and templates** live under `pocketsage/static/` and `pocketsage/templates/`, respectively, and are consumed by blueprints.
- **Tooling & packaging** includes `pyproject.toml`, `Makefile`, `PocketSage.spec`, tests under `tests/`, and documentation in `docs/`.

The sections below describe each component in more detail.

---

## Application Entry Points

| File | Purpose |
| --- | --- |
| `run.py` | Small runner that imports `create_app` and starts Flask's development server. |
| `PocketSage.spec` | PyInstaller specification that bundles `run.py` (calls `create_app()` then `app.run(debug=True)`) and the extra data needed for a desktop binary. |
| `Makefile` | Convenience shortcuts for linting, testing, packaging, and cleanup. |

`run.py` delegates all setup to the application factory, ensuring configuration and blueprints stay consistent between development, production, and bundled binaries.

---

## Configuration (`pocketsage/config.py`)
- Loads `.env` values automatically via `python-dotenv`.
- Resolves a writable data directory (defaults to `instance/`).
- Constructs a SQLite URL; when `POCKETSAGE_USE_SQLCIPHER` is enabled, prepares a SQLCipher-compatible URI placeholder.
- Provides `sqlalchemy_engine_options()` to pass connect arguments (thread-safety, future SQLCipher handshake).
- `DevConfig` extends `BaseConfig` for local-friendly settings.

Key environment variables:
- `POCKETSAGE_SECRET_KEY`: Flask session signing.
- `POCKETSAGE_DATA_DIR`: override storage location.
- `POCKETSAGE_DATABASE_URL`: use a custom database path or external engine.
- `POCKETSAGE_USE_SQLCIPHER` / `POCKETSAGE_SQLCIPHER_KEY`: enable encrypted storage (TODO in code).

---

## Application Factory (`pocketsage/__init__.py`)
- Resolves a configuration class based on the `ENV` name or explicit argument.
- Stores the config object on `app.config["POCKETSAGE_CONFIG"]` for extension code.
- Registers each blueprint declared in `_blueprint_paths()`.
- Calls `init_db()` to set up the SQLModel engine and session lifecycle.
- TODO hooks cover CLI registration, logging, and background services.

Blueprint discovery is explicit: updating `_blueprint_paths()` is the central place to add new domains.

---

## Persistence Layer (`pocketsage/extensions.py`)
- Creates a global SQLModel engine using the config-provided URL and options.
- Sets up `before_request` / `teardown_appcontext` handlers to attach and close scoped sessions stored on Flask's `g` object.
- Runs `SQLModel.metadata.create_all` at startup to materialize tables (future migrations TODO).
- Offers `get_engine()` and `session_scope()` helpers for scripts or services outside request contexts.

---

## Models (`pocketsage/models/`)
Each module defines SQLModel tables used across the app:
- `transaction.py`: Transactions, many-to-one to categories, optional tag link table.
- `category.py`: Budget/reporting categories with convenience metadata (slug, color, type).
- `budget.py`: Budget envelopes and line allocations per period.
- `liability.py`: Debts/liabilities for payoff calculators.
- `habit.py`: Habits and habit entries for streak tracking.
- `settings.py`: Simple key/value application settings.
- `__init__.py`: Re-exports models for easy imports.

Fields use typing annotations, relationships, and TODOs highlight future constraints (currency, uniqueness, etc.).

---

## Services (`pocketsage/services/`)
These modules define business logic boundaries. Most still contain TODO placeholders for teams to implement:
- `budgeting.py`: Compute variance reports and rolling cashflow series.
- `debts.py`: Debt snowball/avalanche payoff schedules, writer integration.
- `import_csv.py`: Normalize CSVs, transform rows into `Transaction` objects, perform idempotent upserts.
- `reports.py`: Future metrics/report aggregation (currently stubbed).
- `watcher.py`: Optional filesystem watcher that reacts to new CSV files (see *Watcher Extra* below).
- `__init__.py`: Explicit public API for service modules.

Protocols describe the expected interfaces that repositories or writers must satisfy, making it easier to swap implementations or unit-test behavior with fakes.

---

## Blueprints (`pocketsage/blueprints/`)
Each blueprint package contains:
- `__init__.py`: Instantiates the Flask `Blueprint`.
- `forms.py`: Dataclass or WTForms-like placeholders describing expected input fields.
- `repository.py`: Protocol describing the data access layer for that domain.
- `routes.py`: View functions responding to HTTP requests.
- Optional `tasks.py`: Background jobs (currently in `admin/`).

Templates for each domain live under `pocketsage/templates/<blueprint>/`, and routes render them with Flash messages or placeholder context. TODOs mark where form validation, pagination, repository queries, and business logic should be implemented.

---

## Static Assets & Templates
- `pocketsage/static/css/main.css`: Shared styles.
- `pocketsage/static/js/main.js`: Placeholder for interactive behavior.
- `pocketsage/templates/base.html`: Global layout, navigation, flash messages.
- Partial templates `_nav.html`, `_flash.html` support layout reuse.
- Domain templates (e.g., `ledger/index.html`, `habits/list.html`) display stub content ready for data bindings.

---

## Scripts (`scripts/`)
- `seed_demo.py`: Entry point for populating demo data (currently raises `NotImplementedError`).
- `csv_samples/`: Example ledger and portfolio CSVs for import flows.

The scripts directory is intended for CLI utilities that leverage the app's services via `session_scope()` or their own dependency resolution.

---

## Tests (`tests/`)
- `test_smoke.py`: Ensures the Flask app factory builds and blueprints register (currently skipped until features are complete).
- `test_routes_smoke.py`: Future endpoint contract coverage (skipped).
- `test_budgeting.py`, `test_debts.py`: Targeted unit tests for service logic (skipped until implementations land).

Skipped markers document the intended coverage once the corresponding features are implemented.

---

## Documentation & Guides (`docs/`)
- `architecture.md`: High-level design decisions and component responsibilities.
- `demo_script.md`: Proposed walkthrough for showcasing features once implemented.
- `code_review.md`: Audit of the legacy scaffold and migration notes.
- `system_overview.md` (this file): Comprehensive tour of files, strategies, and rationale.

`README.md`, `CONTRIBUTING.md`, and `TODO.md` supplement these documents with onboarding steps and outstanding work items.

---

## Build & Tooling Strategy
- `pyproject.toml` defines runtime dependencies, optional extras (`watcher`, `dev`), code style (Black), linting (Ruff), and pytest defaults.
- `requirements.txt` mirrors runtime dependencies for environments that prefer pip requirements.
- `.pre-commit-config.yaml` (if enabled) runs formatting/lint hooks on commit.
- `Makefile` targets: `install`, `lint`, `test`, `package`, etc.
- PyInstaller spec orchestrates building a standalone executable.

---

## Watcher Extra
Installing the extra (`pip install .[watcher]`) adds the `watchdog` package, enabling `pocketsage.services.watcher.start_watcher` to monitor a directory for new CSV files and dispatch them to the CSV import service. Without the extra, calling `start_watcher` raises a runtime error pointing to the missing dependency.

`start_watcher` workflow:
1. Lazily imports `watchdog` modules (keeps default install lightweight).
2. Creates an observer and handler to watch a folder.
3. On file creation, invokes the provided importer callable with the new file path.
4. Returns the observer so callers can control lifecycle (stop/join).

Integration TODOs remain for batching events, surfacing shutdown hooks, and wiring this into the Flask app or CLI utilities.

---

## Next Steps & TODO Themes
- Implement service functions that currently raise `NotImplementedError`.
- Flesh out blueprint repositories and form handling.
- Complete SQLCipher key handshake and production safeguards.
- Add automated tests for variance calculations, debt strategies, watcher flows, and blueprint smoke coverage.
- Wire CLI commands, logging, and background services into the application factory.
- Replace `create_all` with Alembic migrations once the schema stabilizes.

This document should help new contributors understand how the pieces fit together and where to focus future development.
