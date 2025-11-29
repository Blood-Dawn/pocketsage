PocketSage Completion Plan (desktop-only, offline-first)
=========================================

Source of truth for what to do next. Written against Python 3.11 + Flet desktop, SQLModel/SQLite, no web stack. Aligns with AGENTS.md, IMPLEMENTATION_STATUS.md, ROADMAP, and UR/FR mapping from the brief you provided.

Snapshot: Where we stand vs requirements
----------------------------------------

- ✅ Core shell: Flet app, nav rail, routing, AppContext, repos, local login wired. Data under `instance/` by default.
- ✅ Ledger: CRUD + filters + CSV import/export exist; month selector refreshes budgets/reports. Bug: category filter “All” still raises `int('All')`.
- ⚠️ Budgets: UI wired but creation/editing/progress polish incomplete; budgets read-only vibe.
- ⚠️ Habits: CRUD/toggle/streak logic largely there; reminders + richer visuals missing.
- ⚠️ Debts: Snowball/avalanche math in place; timeline chart + richer projection UX missing.
- ⚠️ Portfolio: CSV import works; allocation chart/P&L summaries/exports missing.
- ⚠️ Reports: Export bundle partially done; unified report builder + inline charts missing.
- ⚠️ Admin/Ops: Seed/reset/demo/export partially wired; backup/restore/CLI surface and retention polish needed.
- ⚠️ Ops/QA: Logging/testing coverage OK baseline but needs refresh; packaging via flet pack exists; watcher/scheduler not enabled.

Guiding principles (keep in mind while editing)
-----------------------------------------------

- Offline-first; no external APIs/telemetry. Respect `POCKETSAGE_*` flags, data under `instance/` (or override).
- Reuse AppContext + repos; keep business logic in services, UI in views. Prefer idempotent imports/exports.
- Favor friendly error dialogs + logging over silent failures. Keep buttons doing something predictable.
- Charts/exports live under `instance/charts` and `instance/exports`; honor retention limits.
- Tests: prefer factories/fixtures from `tests/conftest.py`; aim for coverage targets noted in AGENTS.md.

Execution plan (phased; tackle in order)
---------------------------------------

Phase 0 – Baseline & smoke

- Read: `agents.md`, `IMPLEMENTATION_STATUS.md`, `notes/CURRENT_STATE`, `notes/ROADMAP`, `docs/QA/manual_test_plan.md`.
- Run quick checks: `pytest -q` (expect current status), `python run_desktop.py` to click through nav. Note dead buttons/log errors.
- Inventory logs under `instance/logs/`; ensure log writer is working for later debugging.
- Progress: session log shows nav/seed/reset flows; targeted pytest slices green (`tests/test_ledger_filters.py::test_category_filter_all_value_does_not_crash`, `tests/test_ledger_view.py`, `tests/test_csv_imports.py`).

Phase 1 – Stabilize auth/context

- Files: `src/pocketsage/services/auth.py`, `desktop/app.py`, `desktop/context.py`, `infra/database.py`, `infra/repositories/user.py`, `desktop/views/auth.py` (if present).
- Confirm admin login (`admin/admin123`) works; Argon2 hashing; password reset path functions.
- Ensure AppContext exposes all repos (category/budget/budget_line/transaction/habit/habit_entry/liability/holding/settings/user) with shared engine/session factory; no duplicate engines.
- Persist admin toggle state in session/context; nav should hide `/admin` when not admin.
- Add structured logging on login success/failure and seed/reset actions.

Phase 2 – Ledger polish + budget link (UR-1/2/3, FR-7–13, FR-30/35/49/50)

- Fix “All” filter bug: in `desktop/views/ledger.py` `apply_filters`, parse dropdowns via helper `parse_int_or_none`; treat “All”/None safely.
- Validation: in save/edit transaction, require date/description/type/amount; guard income vs expense sign; show friendly dialog on errors.
- User scoping: ensure all repo calls pass `user_id=self.ctx.require_user_id()`.
- CSV import/export: use importer/exporter services; make import idempotent via `external_id`/hash; export to `instance/exports/ledger_YYYYMMDD.csv` and snackbar path.
- Month summaries: income/expense/net for selected month; color-coded labels. Update on CRUD/import.
- Spending chart: add helper (Matplotlib) to render monthly category breakdown PNG under `instance/charts/`; embed image; refresh on data change.
- Progress: ledger view now initializes quick range on load (aligned with dropdowns) and still defaults to all-time so imported rows surface immediately; “All” handling backed by `normalize_category_value`; regression tests green.

Phase 3 – Budgets completion (UR-3, FR-13)

- Files: `desktop/views/budgets.py`, `infra/repositories/budget.py`, `infra/repositories/budget_line.py`, `models/budget.py`, `models/budget_line.py`.
- Implement create/edit dialog (one input per category) tied to current month; upsert `Budget` + `BudgetLine` rows.
- Hook month selector to budgets view; copy-from-previous-month convenience if present.
- Compute actual spend per category for month using transactions; render progress bars with overspend highlighting.
- Ensure data scoped to user; handle empty budgets gracefully.

Phase 4 – Habits completion (UR-4/11–14, FR-14–18)

- Files: `desktop/views/habits.py`, `services/habits.py`, `infra/repositories/habit.py`, `infra/repositories/habit_entry.py`, `models/habit.py`, `models/habit_entry.py`.
- Verify Add/Edit/Archive/Reactivate wires to repos and refresh list. Toggle writes entry for today and recalculates streaks.
- Heatmap/streak visuals: build simple Matplotlib or grid heatmap for recent 30–60 days; show current/longest streak numbers inline.
- Reminders MVP: add reminder fields on habit; log scheduled reminders (console/log) or optional APScheduler ping; document limitation.

Phase 5 – Debts/Liabilities (UR-5/15–18, FR-19–24)

- Files: `desktop/views/debts.py`, `services/debts.py`, `infra/repositories/liability.py`, `models/liability.py`.
- Validate snowball (balance asc) vs avalanche (APR desc) ordering; payoff schedule calculations with interest/principal per period; unit tests for both strategies.
- Timeline chart: Matplotlib line of total balance vs month; highlight debt-free date; embed in view.
- Record payment flow: writes Payment row and optional ledger transaction; recalculates remaining balance; displays updated payoff date.
- UX messaging: show chosen strategy and projected debt-free date in text above chart.

Phase 6 – Portfolio (UR-19–21, FR-25–29)

- Files: `desktop/views/portfolio.py`, `infra/repositories/holding.py`, `models/holding.py`, CSV sample in `scripts/csv_samples/portfolio.csv`.
- Ensure CSV import maps headers → Holding fields; idempotent on rerun; success snackbar with row count.
- Compute per-symbol P/L, total value, total gain/loss; render table with totals row.
- Allocation donut chart + export PNG; export holdings snapshot to CSV in `instance/exports/portfolio_*.csv`.
- Confirm Account/Holding relationship mapping is correct and user-scoped.

Phase 7 – Reports (UR-7/22/23, FR-34/38/41/42)

- Files: `desktop/views/reports.py`, `services/reports.py` (create if missing), `services/admin_tasks.py` for export bundle.
- Build unified report service: spending (month), YTD summary, debt payoff, habit streaks, portfolio allocation. Each returns data + chart PNG path + CSV path.
- Reports UI: dropdown for report type + date/month selectors; “Generate” shows inline chart + download buttons (CSV, ZIP bundle).
- Export-all bundle: zip CSVs/PNGs into `instance/exports/reports_*.zip` with retention (reuse EXPORT_RETENTION=5).

Phase 8 – Admin/Settings/Ops (UR-24–27, FR-37–40)

- Files: `desktop/views/admin.py`, `desktop/views/settings.py`, `services/admin_tasks.py`, `infra/repositories/settings.py`.
- Admin actions: create user, reset password, toggle admin; ensure protected by admin flag. Persist theme + data dir display.
- Seed/reset demo data: call `admin_tasks.run_demo_seed` or equivalent; add confirmation for reset; refresh all views post-run.
- Backup/restore: create ZIP with DB + exports + charts under `instance/backups/`; restore flow with confirmation; log actions.
- CLI surface (if CLI hooks exist): expose seed/export commands that call same services; document in README.

Phase 9 – Ops / Logging / Scheduler / Watcher (SR/ops goals)

- Logging: structured JSON (or consistent text) with rotating handler under `instance/logs/`; log login, seed, import, export, errors, reminder pings.
- Config: enforce non-default secret key in config init; respect `POCKETSAGE_USE_SQLCIPHER` toggle (even if stub) and document key flow.
- Scheduler: optional APScheduler job to refresh cached summaries nightly; ensure safe to disable.
- File watcher: optional `instance/imports/` watcher to auto-import CSVs (idempotent); guard with `watcher` extra.

Phase 10 – Navigation + UX consistency

- Verify routes `/dashboard`, `/ledger`, `/budgets`, `/habits`, `/debts`, `/portfolio`, `/reports`, `/settings`, `/admin`, `/help`, `/login` all wired.
- Keyboard shortcuts: `Ctrl+1..7` nav, `Ctrl+N` new transaction, `Ctrl+Shift+H` new habit; ensure they dispatch to live handlers.
- Sweep for dead buttons / TODO placeholders in `desktop/views/**`; either wire or remove.
- Standardize notifications (`snack_bar` helper) and `show_error_dialog` usage.

Phase 11 – Testing & QA

- Automated: update/add tests for ledger filters/import/export, budgets upsert, habit streak calc/toggle, debt strategy ordering/payoff, portfolio P&L, report generation, admin seed/reset. Use fixtures/factories; keep coverage goals (domain >=80%, repos >=75%, CSV >=70%, overall >=60%).
- Commands: `pytest`, `pytest --cov=src/pocketsage --cov-report=term-missing`, `ruff check .`, `black --check .`. Parallel `pytest -n auto` if needed.
- Manual QA (per AGENTS.md): full desktop smoke (nav + shortcuts); ledger add/delete/export/import; debts CRUD/payments + chart; portfolio CRUD/import/export + chart; reports exports; admin seed/reset; month selector refresh budgets/reports; theme toggle; backups.

Phase 12 – Packaging & release hygiene

- Ensure `make package` / `flet pack run_desktop.py` works; PyInstaller spec uses `instance/` relative paths for DB/logs/charts/exports.
- Verify packaged binary launches and respects config flags; data dir auto-creates with secure permissions helper.
- Update release notes template in `docs/release_notes.md` if changes; follow release checklist in docs.

Phase 13 – Documentation & traceability

- Update README with current feature matrix (implemented vs optional), quickstart, shortcuts, config flags, data paths.
- Update `notes/ROADMAP` or `IMPLEMENTATION_STATUS.md` and this TODO as milestones complete.
- Add traceability table: UR/FR/SR → code modules/services/views.
- Keep assets light; if charts examples needed, prefer PNG generated locally under `instance/` (not committed).

Working notes while implementing
--------------------------------

- Use helper directories: exports → `instance/exports`, charts → `instance/charts`, backups → `instance/backups`, imports → `instance/imports` (watched).
- Respect permissions helper `_ensure_secure_directory`; log when chmod skipped (Windows OK).
- Reuse services instead of duplicating logic in views; keep user scoping consistent.
- Avoid introducing new external dependencies unless necessary and documented.
- Commit cadence (if relevant): small, logical commits per phase; keep diffs manageable (<300 LOC when possible).

Quick checkpoints (mark as you go)
----------------------------------

- [ ] Phase 0 baseline complete (smoke + notes read)
- [ ] Phase 1 auth/context stable
- [ ] Phase 2 ledger bugfix + summaries + chart + import/export polish
- [ ] Phase 3 budgets create/edit/progress
- [ ] Phase 4 habits visuals/reminders
- [ ] Phase 5 debts chart/payment flow
- [ ] Phase 6 portfolio chart/export
- [ ] Phase 7 reports unified builder/UI
- [ ] Phase 8 admin/backup/restore
- [ ] Phase 9 ops logging/scheduler/watcher
- [ ] Phase 10 nav/UX consistency
- [ ] Phase 11 tests/coverage
- [ ] Phase 12 packaging pass
- [ ] Phase 13 docs/traceability
