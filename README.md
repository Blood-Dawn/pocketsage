# PocketSage · Offline Finance + Habits Scaffold

Framework Owner checkpoint for the PocketSage desktop-first Flask app. Focus areas:
- 💸 Ledger + budgeting (SQLModel)
- 🔁 Habit tracking with daily toggles
- 🧾 Liabilities payoff snowball/avalanche
- 📈 Portfolio CSV import (optional)
- 🛠️ Admin seed/reset/export workflows

> **Pattern** – Methods, services, and docs include explicit `# TODO(@assignee)` markers. Teammates own implementations in follow-up PRs.

## Stack Snapshot
- Python 3.11, Flask app-factory + Blueprints
- SQLModel over SQLite with SQLCipher toggle
- Matplotlib PNG chart generation (server-rendered)
- pytest + ruff + black + pre-commit
- PyInstaller onefile packaging

## Quickstart (Local)
1. `python -m venv .venv && .venv\Scripts\activate` *(Windows)*
   - macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -e ".[dev]"`
3. `cp .env.example .env`
4. `python run.py`
5. Visit http://127.0.0.1:5000 to view the landing page and navigate to scaffolded blueprints

### Make Targets
- `make setup` → install deps, enable pre-commit
- `make dev` → run Flask dev server
- `make test` → pytest (currently skipped TODOs)
- `make lint` → ruff + black check
- `make package` → PyInstaller stub build
- `make demo-seed` → placeholder seeding script (raises TODO)

## Configuration Flags
- `.env` values prefixed with `POCKETSAGE_`
- `POCKETSAGE_DATA_DIR=./instance` ships as the default entry in `.env.example`; leave it in place if you want PocketSage to manage the bundled `instance/` folder out of the box.
- `POCKETSAGE_USE_SQLCIPHER=true` switches DB URL builder (SQLCipher driver TODO)
- `POCKETSAGE_DATABASE_URL` overrides computed path if needed

`BaseConfig._resolve_data_dir()` expands the configured data path, creates the directory with `parents=True, exist_ok=True`, and then caches the resolved `Path` during startup. This means the `instance/` folder—and any custom directory you point to—will be created automatically before the database URL is built.【F:pocketsage/config.py†L25-L45】

To store data somewhere else, override `POCKETSAGE_DATA_DIR` in your `.env` file with an absolute or relative path. Ensure the PocketSage process can read from and write to that location (for example, set directory permissions appropriately on Unix with `chmod`/`chown`, or run the app under a user that owns the target folder on Windows) so SQLite/SQLCipher files can be created successfully.【F:pocketsage/config.py†L35-L45】

## Privacy & Offline Notes
- All data stored locally under `instance/`
- No external APIs or telemetry
- SQLCipher support planned; see TODOs in `config.py` for key exchange

## Folder Highlights
- `pocketsage/` – app factory, config, extensions, models, services, blueprints, templates, static
- `scripts/` – demo seeding + CSV samples
- `docs/` – architecture, code review, demo runbook
- `tests/` – pytest scaffolding with skips awaiting implementations

## Next Steps for Teammates
- Replace repository protocols with SQLModel CRUD implementations
- Implement Matplotlib chart rendering + CSV import idempotency
- Wire watchdog optional observer when extra installed
- Fill Admin tasks, seeding, and export flows

See `TODO.md` for the full itemization with owners.
