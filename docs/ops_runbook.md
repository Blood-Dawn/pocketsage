# Operations Checklist & Runbook

## CLI Commands

### Seed Demo Data
- **Command:** `flask pocketsage-seed --demo`
- **Purpose:** Seeds demo transactions by invoking `pocketsage.blueprints.admin.tasks.run_demo_seed` when the database is empty.
- **Expected Output:**
  - `Scheduling demo seed...`
  - `Demo seed completed (or scheduled).`
- **Side Effects:** Triggers the demo seed workflow and schedules/executes the insert of sample transactions (safe no-op if data already exists).

### Export Artifacts
- **Command:** `flask pocketsage-export`
- **Purpose:** Calls `pocketsage.blueprints.admin.tasks.run_export` to build the export archive containing CSV and PNG artifacts.
- **Expected Output:**
  - `Starting export...`
  - `Export written: <path>`
- **Side Effects:** Creates a ZIP archive in the current working directory (unless an output directory is provided via the task) and prints the filesystem path to the generated file.
