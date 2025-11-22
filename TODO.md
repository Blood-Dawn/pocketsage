# PocketSage TODO

## App polish & UX
- [x] Budgets: add create flow for budgets and budget lines (current month); respect selected month; copy previous month; line edit/delete.
- [x] Habits: add create/archive UI.  
- [x] Extend heatmap/calendar range with selectable window; reminder toggle placeholder added (notifications still pending).
- [x] Debts: persist payment history and reconcile to ledger transaction; consider amortization detail/table export.
- [x] Portfolio: add filters (account) and optional market value inputs; refresh allocation chart accordingly.
- [x] Dashboard: add richer KPIs (overspend warnings, last-month vs this-month) and tidy any placeholder text.
- [x] Theme toggle: verify dark/light switch works across views and persists preference.

## Admin & data safety
- [x] Admin: add user delete; confirmation guard.
- [x] Admin: add password reset flow with confirmation.
- [x] Admin: offer full-database export/restore (all users) and data-directory selector UI.
- [x] Demo/reset: ensure post-reset UI refreshes; add guardrails for guest purge and multi-user isolation (integration test).

## Reports & exports
- [x] Add more reports: category trend over time, cashflow by account, and combined ZIP with PDFs/PNGs.
- [x] Let users pick export destination (file picker) for ledger/portfolio/reports.
- [x] Add retention toggle/config for exports and surface export folder opener.

## Imports & watcher
- [x] Add auto-detect/mapping suggestions for CSV imports; idempotent upsert for transactions by external_id.
- [x] Wire optional watcher (debounce/retry) to auto-import from watched folder.

## Quality & tests
- [ ] UI automation/regression for new dialogs (budgets, habits, debts payments, portfolio CRUD) and reports exports.
- [ ] Performance test path for large imports/ledger pagination.
- [ ] Coverage for admin full-export/restore and guest purge isolation.
- [ ] Add regression coverage for dashboard quick action buttons (new transaction/habit shortcuts).
- [ ] Exercise Settings import/export/watcher buttons end-to-end (backup, export, restore, auto-import).
- [ ] Admin screen button flows (seed/reset/create/delete users) with multi-user isolation checks.
- [ ] Reports export buttons (spending, YTD, debt payoff) success/failure surfacing tests.
- [ ] Budgets buttons: copy previous month, create budget, and add-line actions covered in tests.

## Packaging & docs
- [ ] Make packaging non-interactive (skip prompts) and document `scripts\\build_desktop.bat` usage/results.
- [ ] Update Help/README after manual QA with any UX notes and CSV guidance.
