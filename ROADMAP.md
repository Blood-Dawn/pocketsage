# PocketSage Desktop Roadmap

Owner-friendly checklist of what now works and what remains to reach the planned desktop milestone.

## Ledger
- Done: Add/Delete wired and export now writes to `instance/exports` with user feedback; filters handle "All" safely; pagination/summaries intact.
- TODO: Category CRUD UI and richer validations/pagination controls; CSV export file-picker; roll-up summaries and charting polish.

## Budgets
- Done: Month selector refreshes Budgets when changed.
- TODO(@budget-squad): Budget creation/editing flow and copy-forward; alerts/notifications; deeper variance views.

## Habits
- Done: Active list, streaks, toggles remain functional.
- TODO(@habits-squad): Habit creation/edit/archive UI; reminders/notifications; extended heatmap/calendar.

## Debts
- Done: Liability Add/Edit/Delete + payment adjustment; payoff schedule preview + chart; snowball/avalanche helper text; projections refresh on changes.
- TODO(@debts-squad): Persisted payment history, amortization download per-liability, and transaction linkage for reconciled payments.

## Portfolio
- Done: Holding CRUD with account selection; CSV import surfaced; CSV export; allocation chart refreshes after changes.
- TODO(@portfolio-squad): Live price/manual market value inputs; filters; performance metrics; improved holding/account integrity tests.

## Reports/Exports
- Done: Full data export retained; monthly spending PNG; YTD CSV; debt payoff CSV + chart; clearer export locations.
- TODO(@reports-squad): Additional trend reports (category over time, cashflow by account), PDF bundling, and export destination picker.

## Admin/Settings
- Done: Seed/reset per user; guest purge on login; seed auto-runs for new/guest users; role updates remain live in admin view.
- TODO(@admin-squad): Full-db export/restore, user delete/password reset, configurable data dir/SQLCipher handshake UX.

## QA/Testing
- Done: Added payoff chart test; existing suites still primary guardrails.
- TODO(@qa-team): UI automation for new dialogs (debts/portfolio), report-export exercises, and month-selector route refresh coverage.

## Docs
- Done: Roadmap created/updated; export/report flows summarized in code.
- TODO: README/Help examples for new buttons, plus packaging sanity checklist when features stabilize.
