# PocketSage TODO (solo owner)

## App polish & UX
- [x] Budgets: add create flow for budgets and budget lines (current month); respect selected month; copy previous month; line edit/delete.
- [x] Habits: add create/archive UI.  
- [ ] Add reminders/notifications; extend heatmap/calendar range.
- [ ] Debts: persist payment history and reconcile to ledger transaction; consider amortization detail/table export.
- [ ] Portfolio: add filters (account/asset type) and optional market value inputs; refresh allocation chart accordingly.
- [ ] Dashboard: add richer KPIs (overspend warnings, last-month vs this-month) and tidy any placeholder text.
- [ ] Theme toggle: verify dark/light switch works across views and persists preference.

## Admin & data safety
- [x] Admin: add user delete; confirmation guard.
- [x] Admin: add password reset flow with confirmation.
- [x] Admin: offer full-database export/restore (all users) and data-directory selector UI.
- [ ] Demo/reset: ensure post-reset UI refreshes; add guardrails for guest purge and multi-user isolation (integration test).

## Reports & exports
- [x] Add more reports: category trend over time, cashflow by account, and combined ZIP with PDFs/PNGs.
- [ ] Let users pick export destination (file picker) for ledger/portfolio/reports.
- [x] Add retention toggle/config for exports and surface export folder opener.

## Imports & watcher
- [ ] Add auto-detect/mapping suggestions for CSV imports; idempotent upsert for transactions by external_id.
- [ ] Wire optional watcher (debounce/retry) to auto-import from watched folder.

## Quality & tests
- [ ] UI automation/regression for new dialogs (budgets, habits, debts payments, portfolio CRUD) and reports exports.
- [ ] Performance test path for large imports/ledger pagination.
- [ ] Coverage for admin full-export/restore and guest purge isolation.

## Packaging & docs
- [ ] Make packaging non-interactive (skip prompts) and document `scripts\\build_desktop.bat` usage/results.
- [ ] Update Help/README after manual QA with any UX notes and CSV guidance.
