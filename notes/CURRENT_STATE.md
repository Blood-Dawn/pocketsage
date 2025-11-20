# PocketSage Current State - 2025-11-19

## Architecture Snapshot
- Layers: Flask app factory with blueprints (overview, home, ledger, habits, liabilities, portfolio, admin) using SQLModel/SQLite via `config.py` and `extensions.py`. Domain protocols live in `src/pocketsage/domain/repositories/`; concrete SQLModel repositories and DB helpers live in `src/pocketsage/infra/`.
- Desktop: Flet shell (`run_desktop.py` -> `desktop/app.py`) with navigation rail and stub views (dashboard, ledger, budgets, habits, debts, portfolio, settings). Desktop owns a separate DB bootstrap (`infra/database.py`) and wires repositories directly.
- Models: SQLModel tables for Account, Category, Budget/BudgetLine, Transaction, Habit/HabitEntry, Liability, Holding, AppSetting. Money is stored as `float`. Only Transaction and Liability declare `__tablename__`. Holding uses `account: "Account | None"` which currently breaks mapper setup.
- Services: CSV import/export scaffolding, debts payoff calculators, liabilities payment scheduler, simple in-memory job runner. Budgeting service (`compute_variances`, `rolling_cash_flow`) is NotImplemented; reports/watchers remain placeholders.

## Feature Status (complete / partial / missing)
- **Ledger:** SQLModel repo supports CRUD and filters; Flask blueprint renders forms/tables with minimal validation and no pagination. Desktop ledger supports basic add/delete and lists recent transactions; no filters, CSV import/export, or inline edit. No idempotent upsert path.
- **Budgets:** CRUD models/repos exist; budgeting calculations are unimplemented. Desktop budgets view is read-only for current month (no create/edit/copy, no progress visuals).
- **Habits:** Repo supports CRUD plus entry upsert and streak helpers, but streak logic fails tests. Desktop view shows habits and today toggle only; no heatmap, metrics, or archive/reactivate flow.
- **Debts/Liabilities:** Repo CRUD plus summary helpers; payoff service mishandles freed minimum rollover and very small minimum payments. Desktop debts view is static list/summary with no strategy toggle, payments, or projections.
- **Portfolio:** Holding repo exists and Flask import/export routes are stubbed; Desktop view lists holdings and totals only (no allocations, filters, CSV import/export). Holding mapper issue prevents most DB-backed flows from starting.
- **Admin/Settings:** Admin tasks (demo seed/export) call job runner but currently fail; download endpoint redirects instead of streaming the archive. Settings UI exposes theme toggle and backup/import placeholders only.

## Tests & Known Failures
- Command used: `.venv\\Scripts\\python -m pytest -q` (system Python lacks pytest; venv works but tests fail).
- Major blockers:
  - SQLModel mapper error: `InvalidRequestError` because Holding relationship annotation `"Account | None"` cannot be resolved. Cascades through repository tests, ledger routes, admin jobs, integration flows, and money representation tests.
  - Debt payoff schedules: snowball does not roll freed minimums forward; very small minimum payments can loop (`tests/test_debt_calculations.py`).
  - Habits: streak calculations and entry upsert expectations fail (`tests/test_habit_streaks.py`).
  - Admin jobs: demo seed/export jobs return `failed` or 302 redirect instead of success (`tests/test_admin_jobs.py`).
  - Budgeting service still NotImplemented, contributing to integration failures.

## How to Run (current)
- Flask web app: `python run.py` (uses `.env` and `instance/pocketsage.db`).
- Desktop app: `python run_desktop.py`.
- Tests: `.venv\\Scripts\\python -m pytest` (currently red as noted).

## Risks/Gaps
- Broken ORM mapping for Holding<->Account prevents most DB-backed flows.
- Budgeting, debt payoff correctness, and habit streak logic need proper implementations.
- Desktop UI lacks CRUD depth, charts, CSV import/export, and admin/backup flows; depends on stable domain/services.
- No single shared DB/session bootstrap across Flask, desktop, and tests; float-based money handling carries precision risk.
