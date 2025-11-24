# PocketSage Developer Notes (Login-Free Desktop MVP)

This app is now a desktop-only, offline-first finance + habits tracker built with Flet, SQLModel/SQLite, and Matplotlib. It runs in guest mode by default (no login) and keeps all data under `POCKETSAGE_DATA_DIR` (defaults to `instance/`). Key outcomes and how to work with the current codebase:

## What's Implemented
- **Guest-mode shell**: Login is bypassed; `AppContext` seeds a guest user and all routes load directly. Settings show data dir and SQLCipher placeholder; theme preference persists.
- **Ledger**: Transaction CRUD with validation, category filter (All-safe), pagination, monthly summaries, budget progress checks, spending chart, CSV import/export with idempotent external_id/hash. Category CRUD + defaults, budget overrun warnings, and progress bars included.
- **Habits**: CRUD with optional reminder time, archive/reactivate, daily toggle updates streaks instantly, 7–180 day heatmap, streak calculations centralized in `services/habits`.
- **Debts**: Liability CRUD, payments, snowball/avalanche schedules with loop guard and rollover fix, payoff chart + metrics (date, total interest), strategy toggle, projected interest card.
- **Portfolio**: Holding model wired; CRUD + CSV import/export with dedupe hash; gain/loss and allocation chart; account filter-aware totals.
- **Reports/Dashboard**: Dashboard shows current month income/expense/net, debts, habits done today, recent txns, quick actions. Reports page aggregates charts (spending, budget usage, habits, debt payoff, allocation) and keeps export bundles (PNG/CSV/ZIP).
- **Admin/Backup**: Demo seed/reset, backup/export/restore with retention and secure dirs; spinners for long ops; idempotent seed data.
- **Infra**: All models have `__tablename__`; session factory reuse; CSV imports use digest fallback; job runner available. Performance tests cover large CSV import and pagination.
- **Tests**: Full pytest suite green (unit, integration, UI regression, perf). UI regression builds views headlessly and exercises primary dialogs; perf guardrails allow 5k imports.
- **Packaging/Docs**: README updated (guest flow, CSV formats, backup/restore, SQLCipher readiness, packaging outputs). Windows build script is non-interactive with `--delete-build`.

## Developer Setup & Commands
- Python 3.11; install with `pip install -e ".[dev]"`.
- Run app: `python run_desktop.py` (or `make dev`). Shortcuts: `Ctrl+N` new transaction, `Ctrl+Shift+H` new habit, `Ctrl+1..7` navigation. Set `POCKETSAGE_DEV_MODE=true` for verbose logging/banners/snackbars.
- Lint/tests: `ruff check .`, `black --check .`, `python -m pytest` (perf tests under `-m performance`).
- Packaging: `make package` or `scripts\\build_desktop.bat` (non-interactive with `--delete-build`) -> `dist/`.
- Data dir: controlled by `POCKETSAGE_DATA_DIR` (default `instance/`); backups/exports live under `instance/exports` and `instance/backups`.
- CSV formats: ledger imports expect `date,amount,memo,category,account,currency,transaction_id` (idempotent by external_id/hash); portfolio imports expect `symbol,shares,price,account,market_price,as_of,currency` (upsert by symbol+account).

## Next Up (Stretch Targets)
1) **Advanced Budgets & Recurrence**
   - Per-category budgets with rollover rules and alerts, recurring transactions scheduling, multi-currency/account handling, and optimistic locking/versioning hooks for future sync.
2) **Engagement & Advisor**
   - Habit reminders/notifications (scheduler), scheduled backups, and simple advisor insights that relate habits to spending/budgets (e.g., detect overspend trends + habit impact).
3) **Portfolio Analytics & Extensibility**
   - Time-series portfolio tracking (periodic snapshots + charts), richer analytics (returns, allocation by class), and a plugin-friendly module structure for optional features.

## How to Work Locally
- Run `python run_desktop.py` (or `make dev`) after `pip install -e ".[dev]"`. Guest mode starts immediately.
- Data lives under `instance/` by default. Exports/backups under `instance/exports` and `instance/backups`.
- Tests: `python -m pytest` (perf tests under `-m performance`). Lint: `ruff check .` and `black --check .`.
- Packaging: `make package` or `scripts\\build_desktop.bat` (non-interactive) -> `dist/`.
