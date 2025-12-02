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

### Fresh Install / Clean Slate
When testing major changes or encountering caching issues, do a complete clean install:

1. **Close the app** completely (ensure no processes are running)
2. **Remove the instance directory**:
   ```powershell
   Remove-Item -Recurse -Force instance
   ```
3. **If using a packaged build**, also delete the `dist/` folder and rebuild:
   ```powershell
   Remove-Item -Recurse -Force dist
   scripts\build_desktop.bat
   ```
4. **Launch fresh**: Run `python run_desktop.py` (or your packaged executable)
5. **Re-seed demo data**: Go to Admin mode (user icon in app bar) → "Run Demo Seed" to populate with sample transactions across multiple months

This ensures:
- Clean database schema (no old migrations or cached data)
- Fresh configuration files
- All directories recreated properly
- No stale Python bytecode (`.pyc` files) if running from source

**Quick PowerShell one-liner for full dev reset:**
```powershell
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue instance, dist, src\pocketsage.egg-info, **\__pycache__
```

### Partial Reset (Database Only)
For minor resets during development:
- Close the app, then delete the SQLite files under `POCKETSAGE_DATA_DIR` (default `instance/`), e.g., `pocketsage.db` plus any `-wal`/`-shm` files. On next launch, schema is recreated; rerun demo seed if you need sample data.
- PowerShell 7 example: `Remove-Item -Force -ErrorAction SilentlyContinue instance\\pocketsage.db, instance\\pocketsage.db-wal, instance\\pocketsage.db-shm`
- Full clean reset: `Remove-Item -Recurse -Force instance` to allow schema + dirs to be recreated on next launch.

### Dependency hygiene
- Check a package/version in your venv: `.\.venv\Scripts\python -m pip show apscheduler` (swap the name as needed). `pip list` gives the full table.
- If you add/change dependencies in `pyproject.toml`, reinstall dev extras: `pip install -e ".[dev]"` (add `--upgrade` if an existing pin needs a bump).
- When the venv feels stale or Pylance cannot resolve new imports, recreate it: `Remove-Item -Recurse -Force .venv; python -m venv .venv; .\.venv\Scripts\pip install -e ".[dev]"`.

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
- Startup debugging: run `python run_desktop.py` from a terminal to see errors; check `instance/logs/*.log` for startup issues if the UI spinner hangs.
- Admin mode checklist:
  - Toggle Admin mode in the app bar (User vs Admin mode is login-free).
  - Actions: Run Demo Seed, Reset Demo Data, Export, Backup/Restore (see `src/pocketsage/desktop/views/admin.py`).
  - Guards added so `_notify/_with_spinner` no-op if page/controls aren't attached; prevents blank/gray admin screen.
- DB bootstrap: use `bootstrap_database()` (infra/database.py) for a consistent engine + session factory with schema init in tests or scripts; keeps expire_on_commit=False and mirrors desktop startup options.
- Quick add flow: Dashboard "Add Transaction" sets `ctx.pending_new_transaction`; ledger auto-opens the add dialog on load.
- Button wiring tests: `tests/test_button_actions.py` covers add/edit/delete across Ledger/Habits/Debts/Portfolio/Budgets and Admin seed/reset buttons. Re-run with `.\.venv\Scripts\python -m pytest tests/test_button_actions.py -q`.

## What changed recently (per area)
- **Foundations & shell**: Login removed; startup goes straight into a guest-bound `AppContext`. Theme preference is persisted and updates live from Settings. All FK writes now use the ensured guest/local user id.
- **Ledger**: Register rebuilt with validated CRUD dialog; category dropdown seeds defaults and the "All" filter no longer crashes. Monthly summary + budget progress recompute after saves. Spending chart refreshes on change. CSV import/export is idempotent via `external_id`/hash and shows snackbars on success/failure.
- **Budgets**: Monthly budgets stored with per-category lines; progress bars surface overrun; copy-previous-month flow in place. (Line creation still swallows errors—see TODO.)
- **Habits**: CRUD plus archive/reactivate; daily toggle writes entries and recalculates streaks immediately; streak/heatmap service logic lives in `services/habits` (reminder handling is still a placeholder).
- **Debts**: Liabilities CRUD, payment recording, and snowball/avalanche payoff calculations with rollover guard; payoff chart + projected debt-free date wired into the Debts view.
- **Portfolio**: Holding model fixed; CRUD + CSV import/export with dedupe; allocation donut updates on data change; totals honor accounts.
- **Admin & backup**: Demo seed/reset/export/backup/restore wired with spinners and retention; secure dirs under `instance/`. Admin snackbars and status updates no-op safely if controls aren’t attached.
- **Reports/Dashboard**: Dashboard shows current month income/expense/net, debts, habits done today, recent txns, and quick actions; reports aggregate charts and export bundle is reusable.
- **Data/Infra**: All models declare `__tablename__`; shared session factory; CSV imports share dedupe helper; job runner available for longer ops.
- **QA/Tooling**: Ruff/pytest green; UI regression covers add dialogs; perf guardrails allow large (multi-thousand row) imports and pagination scans; packaging scripts are non-interactive and documented.
