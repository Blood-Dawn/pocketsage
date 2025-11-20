# PocketSage Architecture Guide

## Overview
- Desktop-only Flet shell (`run_desktop.py` -> `desktop/app.py`) with a router and `AppContext` for dependencies.
- Persistence via SQLModel on SQLite with a SQLCipher-ready toggle exposed by `BaseConfig`.
- Services layer encapsulates business logic and admin utilities (`services/admin_tasks.py` for seeding/exports) with TODO markers for teammates.

## Application Flow
1. `desktop/context.py` builds configuration, database engine (`infra/database.py`), initializes tables, and creates a session factory.
2. The `AppContext` wires SQLModel repositories from `infra/repositories` and shares UI state (theme, selected account/month) with Flet views.
3. Views in `desktop/views` consume repositories/services directly; admin/export actions call `services/admin_tasks.py` helpers.

## Configuration Strategy
- `.env` variables prefixed with `POCKETSAGE_` feed `BaseConfig` (data dir, DB URL override, SQLCipher flags).
- `USE_SQLCIPHER` flip changes database URL builder (TODO: implement pragma handshake).
- Development defaults to local SQLite file under `instance/`.

## Data Relationships (Initial Draft)
- `Transaction` -> optional `Category` (many-to-one).
- `Budget` -> `BudgetLine` (one-to-many).
- `Habit` -> `HabitEntry` (one-to-many keyed by date).
- `Liability` standalone table (future joins to scheduled payments, TODO).
- `AppSetting` key/value store for runtime preferences.

## UI Layer
- Flet views per area (dashboard, ledger, budgets, habits, debts, portfolio, reports, settings) with shared components in `desktop/components` and navigation in `desktop/navigation.py`.
- Charts planned via Matplotlib generating PNGs (TODO in `services/reports`).

## Packaging
- Desktop binaries are produced with `flet pack run_desktop.py` (see Makefile `package` target or `scripts/build_desktop.*`).
- Outputs land in `dist/` (`PocketSage.exe` on Windows, `.app` on macOS, binary on Linux).

## TODO Highlights
- Fix Holding <-> Account mapper error and money precision risks.
- Fill budgeting service/calculations and debt payoff correctness.
- Implement CSV idempotent upsert and optional watchdog observer.
- Add richer desktop CRUD flows, charts, and report exports.
