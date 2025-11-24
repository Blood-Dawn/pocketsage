# PocketSage TODO (Login-Free Desktop MVP)

## Foundations & Guest Mode
- [x] Remove/bypass authentication flows; default all operations to a single Guest user and ensure any user FK uses that ID.
- [x] Refactor desktop startup to skip login, initialize shared `AppContext`/DB session once, and load main shell directly.
- [x] Persist and load theme preference (light/dark) at startup; wire Settings toggle to update live.

## Ledger (Transactions, Categories, Budgets)
- [x] Implement transaction CRUD UI (date, description, category dropdown, amount, income/expense type) with validation and inline error feedback.
- [x] Add category management (seed common categories, add/edit/delete UI) and ensure transactions link to category FK.
- [x] Fix category filter: include "All" option without casting; support filter by category/date and pagination/limit for lists (FR-7).
- [x] Compute monthly summaries (income, expense, net) and show budget progress (overall or per-category) with progress bar/alert when exceeding budget (FR-10, FR-13).
- [x] Add spending chart (pie/bar of expenses by category) using accessible palette; refresh when data changes (FR-11, NFR-18).
- [x] CSV import/export for transactions with idempotent upsert by `external_id`/hash; surface toast/dialog success/failure (FR-30, NFR-11).
- [x] Budget logic: store monthly budget(s), calculate remaining/overrun per category; return alert flag on save attempts.

## Habits
- [x] Habit CRUD UI (name, optional notes/reminder time) with validation; default to active and support archive/reactivate.
- [x] Daily toggle creates/removes today's `HabitEntry`; recalc and display current/longest streak immediately (FR-14, UR-11).
- [x] Habit history visualization (last ~30 days grid/mini-calendar) updates on toggle (FR-16).
- [x] Service logic: streak calculation algorithm; placeholder for reminders (no-op for now).

## Debts (Liabilities & Payoff Planner)
- [x] Liability model/repo CRUD (name, balance, APR, min/extra payment); list with total remaining balance.
- [x] Payoff strategy toggle (snowball vs avalanche) and calculation service returning payoff time, total interest, and schedule data (FR-20/21).
- [x] Guard against infinite loops on tiny payments; ensure rollover of freed minimums is correct.
- [x] Payment recording action updates balance, recalculates schedule, and marks paid-off when cleared (FR-23).
- [x] Payoff timeline chart (line/bar of balance over time) for selected strategy; show projected debt-free date (FR-22, UR-18).

## Portfolio (Optional)
- [x] Define/repair `Holding` SQLModel (`__tablename__`, relationships) to avoid forward-ref mapping issues; link to account if needed.
- [x] CSV import for holdings (symbol, qty, cost/current price) with merge/skip duplicates; success feedback (FR-25).
- [x] Manual add/edit/delete holding; compute total value and gain/loss per holding.
- [x] Allocation chart (pie/donut) showing % of total per holding; refresh on data change (FR-27/28).
- [x] Export holdings to CSV (FR-29).

## Admin & Backup
- [x] Demo seed routine (categories, sample transactions, habits+entries, debts, holdings) idempotent on rerun (FR-37).
- [x] UI buttons: Seed Demo, Backup/Export (zip of CSVs + charts optional), Restore from backup with confirmation prompts (FR-38/50).
- [x] Export retention (keep last 5 archives) and secure directories (best-effort chmod 0700) respected.
- [x] Error handling/logging for seed/export/restore; surface status to UI.

## Reports & Dashboard
- [x] Dashboard summary (current month income/expense/net, habits done today, debts remaining) as landing view.
- [x] Reports page aggregates charts: spending breakdown, budget usage, habit completion, debt payoff, portfolio allocation (if enabled).
- [x] Allow saving charts/exports as PNG/CSV bundle; reuse unified export pipeline (FR-41/42, UR-23).
- [x] Basic insights text (e.g., top 3 spending categories, biggest month-over-month change) as advisor-lite.

## Settings & Shared UI Shell
- [x] Top navigation bar/rail with sections: Ledger, Habits, Debts, Portfolio (optional), Reports, Settings; highlight active view.
- [x] No-login flow adjustments: remove/hide login view, show "Guest" indicator, keep placeholder for future auth.
- [x] Display data directory path and encryption status info; placeholder toggle for SQLCipher readiness.
- [x] Accessibility pass: labels for controls, color contrast, keyboard navigation; responsive layout with scrollable lists.

## Data, ORM, and Infrastructure
- [x] Ensure all SQLModel tables have `__tablename__`; verify session factory reuse and thread safety flags.
- [x] Idempotent CSV import helpers shared across ledger/portfolio; hash/external_id utility for deduping.
- [x] Job runner/background task hooks ready for long exports (spinner/progress UI), but keep offline/no-network.

## QA, Tests, and Tooling
- [x] Unit tests: ledger import idempotency, budget overrun flag, habit streak edge cases, debt payoff math (snowball/avalanche), holding import merge.
- [x] Integration tests: backup/export/restore round-trip, demo seed result coverage, admin buttons guarded with confirmations.
- [x] UI automation/regression for dialogs (transaction add/edit, habit toggle/add, debt add/payment, portfolio import/export) and report/chart buttons.
- [x] Performance test path for large CSV imports and ledger pagination.
- [x] Keep ruff/black/pytest green; target coverage >60% overall, higher on services.

## Packaging & Docs
- [x] Make packaging script non-interactive; document `scripts\\build_desktop.bat`/`make package` outputs and data directory handling.
- [x] Update README/Help with new no-login flow, CSV formats, shortcuts, and backup/restore steps.
- [x] Note SQLCipher toggle readiness and offline-only stance in docs.

## Stretch Goals (Post-MVP)
- [ ] Advanced budgets & recurrence: per-category budgets with rollover/alerts, recurring transactions, multi-currency/accounts support, and optimistic locking/versioning prep for future sync.
- [ ] Engagement & advisor: habit reminders/notifications, scheduled backups, and advisor insights that connect habits/budgets/spending (e.g., overspend warnings, habit impact callouts).
- [ ] Portfolio analytics & extensibility: time-series portfolio tracking, richer analytics (returns, allocation by class), and plugin-friendly optional modules.
