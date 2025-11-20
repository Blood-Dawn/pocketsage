# PocketSage — Offline Desktop Finance + Habits

PocketSage is now a **desktop-only** personal finance and habit tracker. It uses Flet for the UI, SQLModel over SQLite for storage (SQLCipher-ready), and keeps every byte of data on your machine.

> All web/Flask code has been removed. The desktop shell is the single supported experience going forward.

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

## Packaging
- `make package` builds a desktop executable with `flet pack run_desktop.py` (outputs to `dist/`).
- Platform scripts: `bash scripts/build_desktop.sh` (Linux/macOS) or `scripts\build_desktop.bat` (Windows).
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

## Folder Highlights
- `src/pocketsage/` – config, models, services (including `services/admin_tasks.py` for seeding/exports), domain protocols, infra repositories, desktop UI.
- `scripts/` – demo seeding and desktop build helpers.
- `docs/` – architecture, testing, packaging, and Flet notes.
- `tests/` – pytest suite for repositories, services, and desktop smoke tests.

## Desktop Features
- **Dashboard** – placeholder metrics and quick actions
- **Ledger** – transaction list, add/delete actions, import/export scaffolding
- **Budgets** – monthly summaries (read-only for now)
- **Habits** – daily toggle and streak helpers
- **Debts** – liability list and payoff calculators
- **Portfolio** – holdings list and allocations scaffolding
- **Reports/Settings** – data export, demo seed, theme toggle, and data location info

## Demo Data Seeding
The seeding path is fully desktop-aware and idempotent:
- `make demo-seed` (or `python scripts/seed_demo.py`) seeds categories, accounts, six sample transactions, habits with entries, liabilities, and a simple monthly budget.
- The seeder uses `pocketsage.services.admin_tasks.run_demo_seed` and respects `POCKETSAGE_DATABASE_URL` / `POCKETSAGE_DATA_DIR`. Re-running the seed will not duplicate rows.
