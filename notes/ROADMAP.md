# PocketSage Roadmap

## Phase 0 - Discovery
- [x] Inventory repo structure, docs, and dependencies.
- [x] Capture current architecture/status in `notes/CURRENT_STATE.md`.
- [x] Establish initial roadmap.

## Phase 1 - Unblock ORM & Data Model
- [ ] Fix Holding<->Account relationship mapping and add explicit `__tablename__` where missing.
- [ ] Standardize DB bootstrap (shared engine/session options) for Flask, desktop, and tests.
- [ ] Clarify money field behavior/tolerances; document float usage.
- [ ] Remove or align legacy/duplicate models and wiring.

## Phase 2 - Domain & Services Correctness
- [ ] Implement budgeting `compute_variances` and `rolling_cash_flow` with unit tests.
- [ ] Fix debt payoff (freed minimum rollover, tiny payments, deterministic timeline) with tests.
- [ ] Fix habit streak/entry logic to satisfy streak and upsert scenarios.
- [ ] Add cashflow/category summaries and idempotent transaction/CSV upsert path.

## Phase 3 - Repos, Import/Export, Seeding
- [ ] Harden repositories (pagination, filters, idempotent upsert) to align with tests.
- [ ] Build CSV import/export persistence path for transactions/holdings with idempotency.
- [ ] Create shared fixtures/seed data for web/desktop/tests across budgets/habits/debts/portfolio.
- [ ] Make demo seed idempotent and map to updated schema.

## Phase 4 - Admin & Backups
- [ ] Make export/backup jobs succeed (zip, retention, download) with regression tests.
- [ ] Add restore path and safe filesystem handling under `instance/`.
- [ ] Wire CLI/Flask endpoints and desktop settings actions to backup/seed/restore with error handling.

## Phase 5 - Desktop Shell & Plumbing
- [ ] Strengthen `AppContext` (shared session factory, error handling, theming, selectors).
- [ ] Add navigation polish (stateful routing, toasts/dialogs, loading states).
- [ ] Ensure desktop mode can bootstrap demo data consistently.

## Phase 6 - Desktop Feature Screens
- [x] Dashboard: net worth/spend/debt widgets plus category and income/expense charts; habit/debt summary.
- [x] Ledger: filters, quick-add with validation, inline edit/delete, CSV import/export.
- [ ] Budgets: month selector, copy previous month, CRUD, overspend highlighting, alerts.
- [x] Habits: create/edit/archive/reactivate, streak metrics, calendar/heatmap view, completion toggle.
- [x] Debts: strategy toggle, payment recording, payoff timeline/projection with charts.
- [ ] Portfolio: holdings CRUD/import/export, allocation visualization, filters.
- [ ] Settings/Admin: theme toggle, DB path, seed/backup/restore wired with dialogs.

## Phase 7 - Tests, CI, and Handoff
- [ ] Turn test suite green; expand domain and integration coverage (including desktop view smoke tests).
- [ ] Ensure CI workflow runs lint and tests on clean clone; refresh README/dev workflow with desktop steps.
- [ ] Publish CHANGELOG and final handoff notes.
