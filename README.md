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

## Packaging
- The PyInstaller build mirrors `run.py`, which calls `create_app()` and then `app.run(debug=True)` for a development-friendly binary entry point.
- `make package` → run PyInstaller using `PocketSage.spec` (outputs to `dist/`).
- Launch the bundled app the same way as the script (`./dist/PocketSage/PocketSage` on macOS/Linux, `dist\\PocketSage\\PocketSage.exe` on Windows) to confirm parity with local execution.

### Make Targets
- `make setup` → install deps, enable pre-commit
- `make dev` → run Flask dev server
- `make test` → pytest (currently skipped TODOs)
- `make lint` → ruff + black check
- `make package` → PyInstaller stub build
- `make demo-seed` → populate the local database with curated demo data

## Configuration Flags
- `.env` values prefixed with `POCKETSAGE_`
- `POCKETSAGE_DATA_DIR=./instance` ships as the default entry in `.env.example`; leave it in place if you want PocketSage to manage the bundled `instance/` folder out of the box.
- `POCKETSAGE_USE_SQLCIPHER=true` switches DB URL builder (SQLCipher driver TODO)
- `POCKETSAGE_DATABASE_URL` overrides computed path if needed
- `_resolve_data_dir` respects `POCKETSAGE_DATA_DIR` and defaults to `instance/`; the directory is created during app factory
  initialization so the resolved path exists immediately afterwards. Use this location for SQLite files, local backup jobs,
  or cleanup scripts that prune historical exports.

`BaseConfig._resolve_data_dir()` expands the configured data path, creates the directory with `parents=True, exist_ok=True`, and then caches the resolved `Path` during startup. This means the `instance/` folder—and any custom directory you point to—will be created automatically before the database URL is built.【F:pocketsage/config.py†L25-L45】

To store data somewhere else, override `POCKETSAGE_DATA_DIR` in your `.env` file with an absolute or relative path. Ensure the PocketSage process can read from and write to that location (for example, set directory permissions appropriately on Unix with `chmod`/`chown`, or run the app under a user that owns the target folder on Windows) so SQLite/SQLCipher files can be created successfully.【F:pocketsage/config.py†L35-L45】

## Privacy & Offline Notes
- All data stored locally under `instance/`
- No external APIs or telemetry
- SQLCipher support planned; see TODOs in `config.py` for key exchange

## Folder Highlights
- `pocketsage/` – app factory, config, extensions, models, services, blueprints, templates, static
- `scripts/` – demo seeding + CSV samples
- `docs/` – architecture, code review, demo runbook, troubleshooting matrix
- `tests/` – pytest scaffolding with skips awaiting implementations

## Next Steps for Teammates
- Replace repository protocols with SQLModel CRUD implementations
- Implement Matplotlib chart rendering + CSV import idempotency
- Wire watchdog optional observer when extra installed
- Fill Admin tasks, seeding, and export flows

See `TODO.md` for the full itemization with owners.

## Demo Data Seeding

Run the demo seeding script whenever you need a representative dataset for manual
testing:

- `make demo-seed`
- or `python scripts/seed_demo.py`

The script applies upserts instead of blind inserts so it can be executed
multiple times without duplicating rows. Categories are keyed by slug,
transactions by their synthetic `external_id`, habits by name (including habit
entries by date), and liabilities by name. This ensures the seed remains
idempotent while still refreshing values such as balances, descriptions, or
transaction memos on subsequent runs.
