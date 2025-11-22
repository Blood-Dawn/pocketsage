# PocketSage — Offline Desktop Finance + Habits

PocketSage is now a **desktop-only** personal finance and habit tracker. It uses Flet for the UI, SQLModel over SQLite for storage (SQLCipher-ready), and keeps every byte of data on your machine.

> All web/Flask code has been removed. The desktop shell is the single supported experience going forward.

## Login-Free MVP

PocketSage now operates in **guest mode by default** for simplified single-user operation:
- **No login required** - The app starts directly in the dashboard
- **Persistent data** - All your data is saved locally and persists across sessions
- **Offline-first** - Everything works without an internet connection
- **Privacy-focused** - Your data never leaves your machine

This design is ideal for personal finance tracking where you are the only user. Multi-user authentication can be re-enabled in the future if needed.

## Stack Snapshot
- Python 3.11, Flet desktop UI
- SQLModel + SQLite (SQLCipher toggle planned), Matplotlib for charts/exports
- pytest + ruff + black + pre-commit
- Packaging via `flet pack` (desktop executables)

## Quickstart
1. `python -m venv .venv && .venv\Scripts\activate` (macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`)
2. `pip install -e ".[dev]"`
3. `cp .env.example .env`
4. `python run_desktop.py` to launch the app (shortcuts: `Ctrl+N` new transaction, `Ctrl+Shift+H` new habit, `Ctrl+1..7` navigation)
5. Optional: `make demo-seed` or `python scripts/seed_demo.py` to preload sample data.

**Note:** The app now starts directly in **guest mode** without requiring login. All your data is saved locally and persists between sessions. This is perfect for single-user, offline-first operation.

### Run in developer mode
Enable verbose console diagnostics, dev banner, and extra error snackbars (imports/exports/watcher) by setting `POCKETSAGE_DEV_MODE=true` when starting the app:
- Windows PowerShell: `$env:POCKETSAGE_DEV_MODE='true'; python run_desktop.py`
- macOS/Linux: `POCKETSAGE_DEV_MODE=true python run_desktop.py`
Watch the terminal for `[DEV] ...` messages and tracebacks when actions fail.

### Reset local database (recreate schema)
If the schema changes or you get stuck at login, you can delete the local SQLite file and let the app recreate it (all data will be lost):
1. Close the app.
2. Backup then remove the DB files: `instance/pocketsage.db` (and any `pocketsage.db-wal` / `pocketsage.db-shm` files).
   - PowerShell: `Remove-Item -Force -ErrorAction SilentlyContinue instance\pocketsage.db, instance\pocketsage.db-wal, instance\pocketsage.db-shm`
   - macOS/Linux: `rm -f instance/pocketsage.db instance/pocketsage.db-wal instance/pocketsage.db-shm`
3. Relaunch: `python run_desktop.py` (or `make dev`). The schema will be recreated automatically.
4. Optional: re-seed demo data with `make demo-seed` or `python scripts/seed_demo.py`.
5. If you see schema mismatches (e.g., after adding new columns), delete the DB as above and rerun; a fresh file will be created with the latest schema.

## Packaging
- `make package` builds a desktop executable with `flet pack run_desktop.py` (outputs to `dist/`).
- Platform scripts: `bash scripts/build_desktop.sh` (Linux/macOS) or `scripts\build_desktop.bat` (Windows, now non-interactive with `--delete-build`).
- Output paths: Windows `dist\PocketSage\PocketSage.exe`, macOS `dist/PocketSage.app`, Linux `dist/PocketSage/PocketSage`.

### Clean Rebuild (Windows PowerShell)
Use these commands when you need to purge everything and regenerate the desktop binary:

```powershell
# Stop lingering python.exe processes if files are locked
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force"

# Remove virtualenv and build artifacts
powershell -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'C:\Users\kheiven\Documents\GitHub\pocketsage'; if (Test-Path .venv) { Remove-Item -Recurse -Force .venv }; if (Test-Path dist) { Remove-Item -Recurse -Force dist }; if (Test-Path build) { Remove-Item -Recurse -Force build }"

# Recreate environment and install deps + PyInstaller
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".[dev]" pyinstaller

# Build the packaged desktop app
.\.venv\Scripts\flet pack run_desktop.py
```

## Make Targets
- `make setup` – install deps + register pre-commit
- `make dev` – run the desktop app
- `make test` – pytest
- `make lint` – ruff + black checks
- `make package` – flet pack desktop build
- `make demo-seed` – seed local DB with demo data

## Configuration Flags
- `.env` values prefixed with `POCKETSAGE_`
- `POCKETSAGE_DATA_DIR` (defaults to `instance/`) controls where SQLite/SQLCipher files and exports are written.
- `POCKETSAGE_DATABASE_URL` overrides the computed SQLite URL.
- `POCKETSAGE_USE_SQLCIPHER` / `POCKETSAGE_SQLCIPHER_KEY` reserved for future SQLCipher support.
- `POCKETSAGE_SECRET_KEY` remains for forward compatibility; no Flask usage in desktop mode.
- `POCKETSAGE_DEV_MODE=true` surfaces console diagnostics and error snackbars for imports/exports/navigation.

## Folder Highlights
- `src/pocketsage/` – config, models, services (including `services/admin_tasks.py` for seeding/exports), domain protocols, infra repositories, desktop UI.
- `scripts/` – demo seeding and desktop build helpers.
- `docs/` – architecture, testing, packaging, and Flet notes.
- `tests/` – pytest suite for repositories, services, and desktop smoke tests.

## Desktop Features
- **Dashboard** - quick stats, recent transactions, and shortcuts
- **Ledger** - transaction list with add/delete, filters, CSV import/export
- **Budgets** - month-aware summaries (creation/editing coming soon)
- **Habits** - daily toggle and streak helpers
- **Debts** - liability CRUD, payments, payoff projections (snowball/avalanche), chart + schedule
- **Portfolio** - holdings CRUD with account selection, CSV import/export, allocation chart
- **Reports/Settings** - full data export plus monthly spending, YTD, debt payoff reports; demo seed/reset; theme toggle; data location info

## Demo Data Seeding
The seeding path is fully desktop-aware and idempotent:
- Desktop UI/Admin uses a heavy randomized seed for testing richer datasets (10-year synthetic ledger) via the “Seed demo data” button.
- CLI helpers remain light/deterministic: `make demo-seed` (or `python scripts/seed_demo.py`) seeds categories, accounts, six sample transactions, habits with entries, liabilities, and a simple monthly budget.
- Light seeder uses `pocketsage.services.admin_tasks.run_demo_seed` and respects `POCKETSAGE_DATABASE_URL` / `POCKETSAGE_DATA_DIR`. Re-running the light seed will not duplicate rows.

## Tests
- Run `pytest` (or `pytest -m "not performance"` to skip perf guardrails).
- Performance marker: `pytest -m performance` runs the ledger import guardrail test.
