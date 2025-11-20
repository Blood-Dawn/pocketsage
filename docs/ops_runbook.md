# Operations Checklist & Runbook

## Desktop Admin Actions

### Seed Demo Data
- **Command:** `make demo-seed` (or `python scripts/seed_demo.py`)
- **Purpose:** Seeds demo data by invoking `pocketsage.services.admin_tasks.run_demo_seed` when the database is empty.
- **Expected Output:** Script completes silently; desktop UI will reflect seeded ledger/habits/liabilities/budget entries on next launch.
- **Side Effects:** Safe no-op if transactions already exist.

### Export Artifacts
- **Command:** `python - <<'PY'\nfrom pathlib import Path\nfrom pocketsage.services.admin_tasks import run_export\nfrom pocketsage.config import BaseConfig\nfrom pocketsage.infra.database import create_db_engine, init_database, session_scope\n\nconfig = BaseConfig()\nengine = create_db_engine(config)\ninit_database(engine)\npath = run_export(Path(config.DATA_DIR) / \"exports\", session_factory=lambda: session_scope(engine))\nprint(path)\nPY`
- **Purpose:** Builds an export archive (CSV + PNG placeholder) to a target directory. Equivalent actions exist in the desktop Settings/Reports views.
- **Expected Output:** Filesystem path to the generated ZIP file.
- **Side Effects:** Creates/updates the `exports/` directory under the configured data dir and prunes older archives beyond retention.
