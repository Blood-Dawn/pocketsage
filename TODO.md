# PocketSage TODOs

## Configuration & Infrastructure
- [ ] # TODO(@ops-team) Harden `BaseConfig`: fail application start when `POCKETSAGE_SECRET_KEY` equals default.
- [ ] # TODO(@ops-team) Implement SQLCipher key handshake (PRAGMA key) using `POCKETSAGE_SQLCIPHER_KEY`.
- [ ] # TODO(@ops-team) Provide Alembic migration bootstrap and document workflow.
- [ ] # TODO(@ops-team) Add structured logging config (JSON + rotating file handler).
- [ ] # TODO(@ops-team) Wire background job scheduler (e.g., APScheduler) for nightly tasks.

## Ledger - Jennifer Ginther
- [ ] # TODO(@ledger-squad) Implement SQLModel repository for transactions with filtering + pagination.
- [ ] # TODO(@ledger-squad) Build LedgerEntryForm validation using WTForms or Pydantic.
- [ ] # TODO(@ledger-squad) Add category management UI + CRUD endpoints.
- [ ] # TODO(@ledger-squad) Implement rollup summaries (income vs. expense, net cashflow).
- [ ] # TODO(@ledger-squad) Hook Matplotlib spending chart into ledger template.
- [ ] # TODO(@ledger-squad) Ensure optimistic locking on transaction updates.

## Habits - Dossell Sinclair
- [ ] # TODO(@habits-squad) Persist HabitEntry creation via repository with streak recalculation.
- [ ] # TODO(@habits-squad) Implement HabitForm validation + error messaging.
- [ ] # TODO(@habits-squad) Add weekly/monthly heatmap visualization for habit completion.
- [ ] # TODO(@habits-squad) Introduce reminders (local notification or email toggle).
- [ ] # TODO(@habits-squad) Support habit archival and reactivation flows.

## Liabilities & Debts - Vedell Jones
- [ ] # TODO(@debts-squad) Implement liabilities repository with create/read/update and payoff schedule storage.
- [ ] # TODO(@debts-squad) Finish snowball and avalanche calculators with deterministic ordering.
- [ ] # TODO(@debts-squad) Generate payoff timeline chart PNG via `services.reports`.
- [ ] # TODO(@debts-squad) Add ability to record actual payments and reconcile balances.
- [ ] # TODO(@debts-squad) Surface debt-free date projections in UI.

## Portfolio (Optional)(KD)
- [x] # TODO(@portfolio-squad) Wire upload form to accept CSV and call `import_csv.import_csv_file`.
- [x] # TODO(@portfolio-squad) Implement repository to persist holdings + allocation snapshots.
- [x] # TODO(@portfolio-squad) Render allocation donut chart via Matplotlib.
- [x] # TODO(@portfolio-squad) Add gain/loss table with cost basis calculations.
- [x] # TODO(@portfolio-squad) Provide export of holdings to CSV.
 - [x] # TODO(@imports) Add account and currency column support in CSV imports and mapping suggestions so portfolio uploads can record account_id + currency.
 - [x] # TODO(@ledger-squad) Persist parsed portfolio-imported transactions into the ledger repository (ensure account_id and currency are stored and respected by reporting).
 - [x] # TODO(@frontend) Update portfolio templates to show upload progress, validation messaging, and export/download links.
 - [x] # TODO(@qa-team) Add idempotency & end-to-end tests for portfolio CSV import -> persist -> allocation snapshot.

## Services & Integrations
- [ ] # TODO(@imports) Implement idempotent `upsert_transactions` with external_id matching.
- [ ] # TODO(@imports) Add column auto-detection + mapping suggestions.
- [ ] # TODO(@watcher) Start watchdog observer on app boot when watched folder configured.
- [ ] # TODO(@watcher) Add debounce + retry logic for duplicate filesystem events.
- [ ] # TODO(@reports) Implement `build_spending_chart` with category color palette.
- [ ] # TODO(@reports) Implement `export_spending_png` to persist chart via renderer protocol.
- [ ] # TODO(@analytics) Add rolling cash flow computation in `services.budgeting`.
 - [ ] # TODO(@imports) Implement the persistence path: take parsed dicts from `import_csv` and insert/update ORM models via repository/session_scope (portfolio and transactions).
 - [ ] # TODO(@qa-team) Add DB-backed tests for import persistence and idempotency (use a temporary SQLite DB fixture).

## Admin & Operations(KD)
- [x] # TODO(@admin-squad) Implement `run_demo_seed` to populate all tables with sample data.
- [x] # TODO(@admin-squad) Implement `run_export` to bundle CSV + PNG artifacts into zip.
- [x] # TODO(@admin-squad) Add admin UI feedback (progress indicators, error handling).
- [x] # TODO(@admin-squad) Create CLI commands (`flask pocketsage seed`, etc.).
- [x] # TODO(@frontend) Update admin templates to show export/download button, seed confirmation UI, and progress/status indicators wired to endpoints.
- [x] # TODO(@ops-team) Implement exports retention/rotation and filesystem permissions for `instance/exports` (ensure secure access and cleanup policy).
- [x] # TODO(@framework-owner) Register background worker or scheduler (e.g., APScheduler/Celery) and wire `run_demo_seed` / `run_export` into it; provide a job-status API.
- [x] # TODO(@qa-team) Add route and integration tests for `/admin/export/download`, seed confirmation flow, and background task behavior (mocking worker runtimes).

## Testing & QA(KD)
- [x] # TODO(@qa-team) Replace skipped tests with golden datasets for budgeting/debts services.
- [x] # TODO(@qa-team) Add route smoke tests verifying template context variables.
- [x] # TODO(@qa-team) Add CSV import idempotency regression tests using fixtures.
- [x] # TODO(@qa-team) Configure CI workflow (GitHub Actions) running lint + tests + packaging dry run.
