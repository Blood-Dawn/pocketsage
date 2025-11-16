# PocketSage Architecture Guide

## Overview
- Flask 3.0 app-factory pattern (`pocketsage.create_app`).
- Blueprints per domain (`ledger`, `habits`, `liabilities`, `portfolio`, `admin`).
- Persistence via SQLModel on SQLite/SQLCipher toggle.
- Services layer encapsulates business logic contracts with TODO markers for teammates.

## Application Flow
1. `create_app` loads configuration, registers blueprints, and initializes the database engine.
2. `extensions.init_db` wires SQLModel session handling and creates tables (pending migrations TODO).
3. Blueprints use repository protocols to decouple views from persistence.
4. Services provide math/reporting helpers (budgeting, debts, CSV import, watcher, reporting).

## Configuration Strategy
- `.env` variables prefixed with `POCKETSAGE_` feed `BaseConfig`.
- `USE_SQLCIPHER` flip changes database URL builder (TODO: implement pragma handshake).
- Development defaults to local SQLite file under `instance/`.

## Data Relationships (Initial Draft)
- `Transaction` -> optional `Category` (many-to-one).
- `Budget` -> `BudgetLine` (one-to-many).
- `Habit` -> `HabitEntry` (one-to-many keyed by date).
- `Liability` standalone table (future joins to scheduled payments, TODO).
- `AppSetting` key/value store for runtime preferences.

## Rendering & UI
- Templates share `base.html` with `_nav` and `_flash` partials.
- Each blueprint folder holds its own view templates with TODO scaffolding.
- Static assets live under `pocketsage/static/` (CSS/JS placeholder).
- Charts planned via Matplotlib generating PNGs (TODO in `services/reports`).

## Packaging
- PyInstaller spec (`PocketSage.spec`) bundles CLI app, templates, and static assets.
- `make package` runs `pyinstaller PocketSage.spec --clean` (TODO: refine hidden imports & bundling).

### Packaging checklist
- [ ] Confirm `PocketSage.spec` exists at the repository root before packaging.
  - If the file is missing, restore it from version control or regenerate with `pyinstaller run.py --name PocketSage --specpath .`.
- [ ] Run `make package` to build the binary with PyInstaller.

## TODO Highlights
- Replace repository protocols with SQLModel implementations.
- Wire forms using WTForms or alternative validation.
- Implement CSV idempotent upsert and optional watchdog observer.
- Add migrations, CLI commands, and error handling middleware.
