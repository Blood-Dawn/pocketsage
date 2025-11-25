# PocketSage TODO (Login-Free Desktop MVP)



## Stretch Goals (Post-MVP)
- [ ] Advanced budgets & recurrence
  - Per-category budgets with rollover rules and alert thresholds; display remaining/overrun and allow rollover toggles per line.
  - Recurring transactions (scheduler stub) with templates for bills/income; allow skip/modify per occurrence.
  - Multi-currency/account support with FX override inputs and per-account currency display; document money tolerance/rounding.
  - Optimistic locking/versioning columns on key tables to prep for future sync/multi-user scenarios.
- [ ] Engagement & advisor
  - Habit reminders/notifications: allow per-habit reminder time, enqueue local notifications; surface missed reminders.
  - Scheduled backups (opt-in) using job runner; retention and status UI.
  - Advisor insights: detect overspend trends, top categories, and highlight habit impact (e.g., “no coffee” streak vs coffee spend); show actionable nudges in dashboard/reports.
- [ ] Portfolio analytics & extensibility
  - Time-series tracking: store periodic portfolio snapshots; render value-over-time charts and allocation history.
  - Richer analytics: unrealized/realized return calculations, allocation by asset class/sector, simple risk concentration alerts.
  - Plugin-friendly modules: feature flags to enable/disable optional screens; hook points for future data sources without breaking offline-first mode.

## Roadmap Workstreams (from notes/ROADMAP.md)
- **Phase 1: ORM & Data Model**
  - [x] Fix Holding<->Account mapping and confirm all models declare `__tablename__` (captured in DEV_NOTES).
  - [x] Standardize DB bootstrap (shared engine/session options) for desktop/tests; document money field tolerances and float usage (new `bootstrap_database()` helper in infra/database.py + notes in DEV_NOTES and TESTING_INFRASTRUCTURE).
  - [ ] Remove or align legacy/duplicate models/wiring (needs audit for unused schemas/old web-era code).
- **Phase 2: Domain & Services Correctness**
  - Implement budgeting `compute_variances` and `rolling_cash_flow` with unit tests.
  - Harden debt payoff math (freed minimum rollover, tiny payments, deterministic timelines) with tests.
  - Ensure habit streak/entry logic covers all upsert scenarios.
  - Add cashflow/category summaries and idempotent transaction/CSV upsert path.
- **Phase 3: Repos, Import/Export, Seeding**
  - Harden repositories (pagination, filters, idempotent upsert) to align with tests.
  - Build CSV import/export persistence for transactions/holdings with idempotency.
  - Create shared fixtures/seed data for budgets/habits/debts/portfolio; make demo seed idempotent for updated schema.
- **Phase 4: Admin & Backups**
  - Ensure export/backup jobs succeed (zip, retention, download) with regression tests.
  - Add restore path and safe filesystem handling under `instance/`.
  - Wire desktop settings actions and CLI/script helpers to backup/seed/restore with clear error handling.
- **Phase 5: Desktop Shell & Plumbing**
  - Strengthen `AppContext` (shared session factory, error handling, theming, selectors).
  - Add navigation polish (stateful routing, toasts/dialogs, loading states).
  - Ensure desktop mode can bootstrap demo data consistently.
- **Phase 6: Desktop Feature Screens**
  - Budgets: month selector, copy previous month, CRUD, overspend highlighting, alerts.
  - Portfolio: holdings CRUD/import/export, allocation visualization, filters.
  - Settings/Admin: theme toggle, DB path, seed/backup/restore wired with dialogs.
- **Phase 7: Tests, CI, Handoff**
  - Keep test suite green; expand domain and integration coverage (desktop view smoke tests included).
  - Ensure CI runs lint/tests on clean clone; refresh docs with desktop steps; publish changelog/handoff notes.


## Newly observed placeholders / incomplete wiring (Dec 2025)
- [ ] Admin view guard currently redirects away when `admin_mode` is false, leaving a gray/blank page; add a deterministic admin toggle and fallback content instead of redirect-only flow (src/pocketsage/desktop/views/admin.py).
- [ ] Ledger/portfolio CSV imports surface snackbars but do not force a live data reload; hook import completion to refresh registers/insights and surface mapping errors clearly (src/pocketsage/desktop/controllers.py start_ledger_import/start_portfolio_import).
- [ ] Budget creation silently swallows line-add errors (`pass` in save_budget) leaving users without feedback; add validation/snackbars for failed line creation (src/pocketsage/desktop/views/budgets.py).
- [ ] Settings encryption toggle is a placeholder; implement SQLCipher handshake or hide the toggle until supported (src/pocketsage/desktop/views/settings.py database section).
- [ ] Habit reminder logic is a placeholder `reminder_placeholder` no-op; replace with real local notifications or adjust UI copy (src/pocketsage/services/habits.py).
- [ ] Auth view is a placeholder redirect; implement/document proper login flow if multi-user mode returns (src/pocketsage/desktop/views/auth.py).
