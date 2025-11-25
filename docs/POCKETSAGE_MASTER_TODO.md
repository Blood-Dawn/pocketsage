# PocketSage Master TODO (Desktop Overhaul)

Working backlog aligned to PocketSage requirements docs (`PocketSage-Requirements-Doc.pdf`, `PocketSage_Project_CEN4010.pdf`) and current app gaps. Track sprint progress here; inline TODOs in code reference matching owners.

## 1. MVP for CEN4010 Demo
- [x] Single local user flow with profile auto-loaded (no password).
- [x] Normal user view: ledger, habits, debts, portfolio, reports.
- [x] Admin mode toggle (no password) with seed/reset/export/backup.
- [x] Demo shows admin changes reflecting immediately in user views.

## 2. Core Ledger & Budgets
- [x] Add transaction from Dashboard and Ledger.
- [x] Edit transaction.
- [x] Delete transaction.
- [x] Import CSV (idempotent) and verify duplicate handling.
- [x] Export CSV with success snackbar and file path confirmation.
- [x] Fix category filter “All” handling and add regression tests.
- [x] Budgets: create/update budget and monthly paged view.

## 3. Seed Data & Admin Tools
- [x] Reset Demo Data fully clears DB while keeping schema intact.
- [x] Run Demo Seed populates ledger, habits, debts, portfolio.
- [x] Support heavy seed (10-year, ~10 tx/day) plus lightweight fixtures for tests.
- [x] Seed runs only via Admin actions (no forced seeding on first run).
- [x] Guest/admin/demo behavior consistent after simplified login removal.

## 4. Habits
- [x] Habits page reachable via nav and shortcuts without crashes.
- [x] Create/edit/archive habits.
- [x] Toggle daily completion.
- [x] Recompute streaks correctly.
- [x] Show simple heatmap or streak visualization.
- [x] Surface basic habit data in Reports (later).

## 5. Debts / Liabilities
- [x] Enter liabilities (principal, APR, min payment).
- [x] Snowball and avalanche strategies wired to UI buttons.
- [x] Compute and display payoff schedule with projected debt-free date.
- [x] Strategy modes: aggressive / balanced / lazy alter assumptions.
- [x] User-friendly explanation text for strategy differences.
- [x] Show summary chart or table (timeline / remaining balance).

## 6. Portfolio (Demo-Focused)
- [x] Add holding manually or via CSV import.
- [x] Parse symbol, quantity, price, category/sector columns.
- [x] Allocation donut chart by symbol or category.
- [x] Export portfolio CSV with confirmation snackbar.
- [x] Add second chart (allocation by category or gain/loss bar).

## 7. Reports & Analytics
- [x] Reports page reachable without crashes.
- [x] Charts visible without exporting: spending vs income, category breakdown, debt payoff summary, habit streak snippet.
- [x] CSV/PNG export for key reports under `instance/reports/` with confirmation path.
- [x] Add month filters per page (not only topbar).

## 8. Settings & Admin View
- [x] Dark/Light toggle stays working.
- [x] Admin toggle or tab clearly exposed (User vs Admin mode).
- [x] Admin actions wired: Run Demo Seed, Reset Demo Data, Import/Export, Backup/Restore.
- [x] Backup zips DB + CSV/PNGs under `instance/backups/` with timestamp snackbar.
- [x] Show app version and instance path for demos.

## 9. Navigation, Topbar, and UX
- [x] Stable tab switching (no jitter, instant transitions).
- [x] Each page owns month filters; topbar provides shortcuts only.
- [x] CSV Help and Help page reachable from Settings/Reports/Portfolio/topbar.
- [x] Copy is concise and friendly.

## 10. Testing & Docs
- [x] Expand tests: ledger filters/add/delete (“All” category), admin seed/reset, debts calculations, habits streak logic.
- [x] New doc pointers for verbose pytest and ruff commands (no skips).
- [x] Reference this master TODO from README and keep milestones updated.
