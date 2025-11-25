# PocketSage TODO (Login-Free Desktop MVP)


## Codebase Audit Findings (Nov 2025)

### Models - Incomplete / Future Enhancements
- [ ] **AppSetting model**: Add updated_at timestamp + audit trail for setting changes (`src/pocketsage/models/settings.py:19`).
- [ ] **Category model**: Enforce palette uniqueness + icon set once design assets land (`src/pocketsage/models/category.py:34`).
- [ ] **Transaction model**: Enforce account linkage + currency once multi-account support lands (`src/pocketsage/models/transaction.py:52`).
- [ ] **TransactionTagLink model**: Replace tag_id FK with dedicated Tag table once taxonomy defined (`src/pocketsage/models/transaction.py:62`).
- [ ] **Budget model**: Enforce non-overlapping windows per user (`src/pocketsage/models/budget.py:33`).
- [ ] **BudgetLine model**: Track actual spend + available with materialized views (`src/pocketsage/models/budget.py:54`).
- [ ] **Habit model**: Add owner foreign key when multi-user support arrives (`src/pocketsage/models/habit.py:37`).
- [ ] **HabitEntry model**: Enforce timezone-aware capture for cross-region tracking (`src/pocketsage/models/habit.py:57`).

### Services - Placeholders / Incomplete Logic
- [ ] **Auth service**: Reintroduce real multi-user auth in a future phase if needed (`src/pocketsage/services/auth.py:2`).
- [ ] **Auth purge_guest_user**: Exception handling uses bare `pass` for best-effort cleanup - consider logging (`src/pocketsage/services/auth.py:176`).
- [ ] **Habits service**: `reminder_placeholder` is a no-op function returning placeholder text; replace with real local notifications or adjust UI copy (`src/pocketsage/services/habits.py:41-46`).
- [ ] **Watcher service**: Debounce rapid duplicate events and batch processing (`src/pocketsage/services/watcher.py:43`).
- [ ] **Watcher service**: Surface observer lifecycle hooks + shutdown in app factory (`src/pocketsage/services/watcher.py:50`).
- [ ] **Admin tasks**: Support light vs heavy seed profiles and measure seed performance (`src/pocketsage/services/admin_tasks.py:2`).
- [ ] **Admin tasks**: Add safety checks before destructive reset operations (`src/pocketsage/services/admin_tasks.py:3`).
- [ ] **CSV import service**: Add validation for duplicate headers and inconsistent delimiters (`src/pocketsage/services/import_csv.py:33`).
- [ ] **Importers service**: Guarantee idempotent import by external_id and write tests (`src/pocketsage/services/importers.py:2`).

### Desktop Views - Placeholders / Unwired Features
- [ ] **Auth view**: Placeholder redirect; implement/document proper login flow if multi-user mode returns (`src/pocketsage/desktop/views/auth.py:1`).
- [ ] **Auth view**: Exception in ensure_local_user uses bare `pass` - consider logging or user feedback (`src/pocketsage/desktop/views/auth.py:24`).
- [ ] **Admin view**: Guard redirects away when `admin_mode` is false, leaving gray/blank page; add deterministic admin toggle and fallback content (`src/pocketsage/desktop/views/admin.py:36-40`).
- [ ] **Admin view**: Multiple bare `pass` statements in _notify and _with_spinner for AssertionError handling - consider logging (`src/pocketsage/desktop/views/admin.py:66,70,103,111`).
- [ ] **Settings view**: Surface seed/reset progress and final row counts to the user (`src/pocketsage/desktop/views/settings.py:2`).
- [ ] **Settings view**: Expose instance path and backup status in the UI (`src/pocketsage/desktop/views/settings.py:3`).
- [ ] **Settings view**: SQLCipher encryption toggle is a placeholder (line 269: "SQLCipher toggle placeholder"); implement SQLCipher handshake or hide until supported (`src/pocketsage/desktop/views/settings.py:53,269`).
- [ ] **Settings view**: Watcher stop uses bare `pass` for exception handling (`src/pocketsage/desktop/views/settings.py:132`).
- [ ] **Habits view**: Enhance visualizations (heatmaps, weekly summaries) and tie into Reports (`src/pocketsage/desktop/views/habits.py:2`).
- [ ] **Habits view**: Habit linking to spending notes (future stretch goal) (`src/pocketsage/desktop/views/habits.py:9`).
- [ ] **Habits view**: Optional reminders field exists but notification scheduling is future (`src/pocketsage/desktop/views/habits.py:10`).
- [ ] **Debts view**: Integrate strategy modes (aggressive/balanced/lazy) into projections (`src/pocketsage/desktop/views/debts.py:2`).
- [ ] **Debts view**: Edge case handling (tiny payments, infinite loops) needs verification (`src/pocketsage/desktop/views/debts.py:10`).
- [ ] **Debts view**: Record payment TODO partially addressed but needs transaction linkage refinement (`src/pocketsage/desktop/views/debts.py:253-258`).
- [ ] **Portfolio view**: Add sector/asset-class breakdown and time-series portfolio value (`src/pocketsage/desktop/views/portfolio.py:2`).
- [ ] **Portfolio view**: Optional price update mechanism (manual input or CSV) not fully wired (`src/pocketsage/desktop/views/portfolio.py:10`).
- [ ] **Portfolio view**: Time series tracking (future: track portfolio value over time) (`src/pocketsage/desktop/views/portfolio.py:11`).
- [ ] **Ledger view**: Implement three-tier layout (filters, summary cards, two-column) - partially done (`src/pocketsage/desktop/views/ledger.py:2`).
- [ ] **Ledger view**: Replace old table layout with register-style table + actions column - partially done (`src/pocketsage/desktop/views/ledger.py:3`).
- [ ] **Ledger view**: Centralize transaction creation/update in a helper/service (`src/pocketsage/desktop/views/ledger.py:5`).
- [ ] **Reports view**: Centralize report generation to a service layer and keep views thin (`src/pocketsage/desktop/views/reports.py:2`).
- [ ] **Help view**: Add quick-start checklist for first-time users (`src/pocketsage/desktop/views/help.py:2`).

### Desktop Controllers - Incomplete Wiring
- [ ] **Controllers logout**: Exception handling uses bare `pass` - consider logging (`src/pocketsage/desktop/controllers.py:240`).
- [ ] **Ledger/portfolio CSV imports**: Surface snackbars but do not force a live data reload; hook import completion to refresh registers/insights and surface mapping errors clearly (`src/pocketsage/desktop/controllers.py` start_ledger_import/start_portfolio_import).

### Configuration / Security
- [ ] **Config**: Fail fast when SECRET_KEY is default in production modes (`src/pocketsage/config.py:39`).
- [ ] **Config**: Replace SQLCipher driver URL and pragma injection once SQLCipher driver is wired into dependencies (`src/pocketsage/config.py:54`).
- [ ] **Config**: Add SQLCipher pragma key handshake using env key material (`src/pocketsage/config.py:67`).
- [ ] **Config**: Consider enabling toolbar once UI is wired (`src/pocketsage/config.py:76`).


## Stretch Goals (Post-MVP)
- [ ] Advanced budgets & recurrence
  - Per-category budgets with rollover rules and alert thresholds; display remaining/overrun and allow rollover toggles per line.
  - Recurring transactions (scheduler stub) with templates for bills/income; allow skip/modify per occurrence.
  - Multi-currency/account support with FX override inputs and per-account currency display; document money tolerance/rounding.
  - Optimistic locking/versioning columns on key tables to prep for future sync/multi-user scenarios.
- [ ] Engagement & advisor
  - Habit reminders/notifications: allow per-habit reminder time, enqueue local notifications; surface missed reminders.
  - Scheduled backups (opt-in) using job runner; retention and status UI.
  - Advisor insights: detect overspend trends, top categories, and highlight habit impact (e.g., "no coffee" streak vs coffee spend); show actionable nudges in dashboard/reports.
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


## Previously observed placeholders / incomplete wiring (Dec 2025)
- [ ] Admin view guard currently redirects away when `admin_mode` is false, leaving a gray/blank page; add a deterministic admin toggle and fallback content instead of redirect-only flow (src/pocketsage/desktop/views/admin.py).
- [ ] Ledger/portfolio CSV imports surface snackbars but do not force a live data reload; hook import completion to refresh registers/insights and surface mapping errors clearly (src/pocketsage/desktop/controllers.py start_ledger_import/start_portfolio_import).
- [ ] Budget creation silently swallows line-add errors (`pass` in save_budget) leaving users without feedback; add validation/snackbars for failed line creation (src/pocketsage/desktop/views/budgets.py).
- [ ] Settings encryption toggle is a placeholder; implement SQLCipher handshake or hide the toggle until supported (src/pocketsage/desktop/views/settings.py database section).
- [ ] Habit reminder logic is a placeholder `reminder_placeholder` no-op; replace with real local notifications or adjust UI copy (src/pocketsage/services/habits.py).
- [ ] Auth view is a placeholder redirect; implement/document proper login flow if multi-user mode returns (src/pocketsage/desktop/views/auth.py).
