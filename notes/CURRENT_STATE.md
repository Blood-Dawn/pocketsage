# PocketSage Current State - 2025-11-24

## Architecture Snapshot
- Desktop-only Flet shell (`run_desktop.py` → `desktop/app.py`) with guest-mode startup, navigation rail, and full views (dashboard, ledger, budgets, habits, debts, portfolio, reports, settings, admin).
- Data layer: SQLModel/SQLite tables for Account, Category, Budget/BudgetLine, Transaction, Habit/HabitEntry, Liability, Holding, AppSetting. All models declare `__tablename__`; session factory reuse and DB bootstrap live in `infra/database.py` and `desktop/context.py`.
- Services: CSV import/export, debts payoff calculators (snowball/avalanche with loop guards), admin tasks (seed/export/backup/restore with retention), job runner, reports/charts, watcher placeholder. Budgeting service still has stubs beyond UI usage.

## Feature Status
- **Ledger:** CRUD with validation, filters (date/category/type), pagination, monthly summaries, budget progress/alerts, spending chart, category CRUD/defaults, CSV import/export with idempotent external_id/hash.
- **Budgets:** Desktop view shows month budgets with lines, progress bars, totals, copy/add/edit/delete; overall rollups present. Advanced variance/rolling calc still deferred to budgeting service stubs.
- **Habits:** CRUD with optional reminder time, archive/reactivate, daily toggle with instant streak recalculation, 7–180 day heatmap, streak logic centralized in `services/habits`.
- **Debts:** Liability CRUD, payment recording (optional ledger reconcile), snowball/avalanche payoff schedules with rollover fix and tiny-payment guard, projected payoff date/interest, timeline chart, strategy toggle.
- **Portfolio:** Holding model fixed; CRUD, CSV import/export with merge/duplicate hash, gain/loss + allocation chart, account filter-aware totals.
- **Reports/Dashboard:** Dashboard shows income/expense/net, debts, habits done today, recent txns, quick actions, cashflow/spending charts. Reports page aggregates spending/budget/habit/debt/portfolio charts and offers export bundles (PNG/CSV/ZIP).
- **Admin/Backup:** Demo seed/reset, backup/export/restore with retention and secure dirs; confirmation/spinner UI; idempotent seeding.
- **Settings:** Theme toggle persistence, data directory display, SQLCipher readiness placeholder toggle, backups/exports/restore wiring, shared file picker.

## Tests & Quality
- Full pytest suite currently green (unit, integration, UI regression, performance). Performance guardrails allow ~5k-row import and pagination sweep. UI regression exercises primary dialogs/buttons headlessly.
- Linting tools (ruff/black) configured; not auto-run here but expected to pass.
- Money stored as float; tolerances handled in tests, but precision risk remains for future FX/multi-currency work.

## Data & Ops
- Default data root `instance/`; backups/exports under `instance/backups` and `instance/exports` with retention=5.
- Guest mode is the only auth flow; all user FKs point to the guest user by default. SQLCipher flags are placeholders; current builds use SQLite.
- Packaging via `make package` or `scripts\\build_desktop.bat` (non-interactive, `--delete-build`) produces `dist/` binaries.

## Open Risks / Future Work
- Budgeting service functions (`compute_variances`, `rolling_cash_flow`) still stubbed; advanced budget alerts/rollover logic beyond current UI progress bars remains.
- Advisor/notifications and scheduled backups are not yet implemented.
- Multi-currency/account FX handling and optimistic locking are planned stretch items.
- Time-series portfolio tracking and richer analytics are future-phase work.
