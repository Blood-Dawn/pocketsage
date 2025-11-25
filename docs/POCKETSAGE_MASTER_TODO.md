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
- [ ] Habits page reachable via nav and shortcuts without crashes.
- [ ] Create/edit/archive habits.
- [ ] Toggle daily completion.
- [ ] Recompute streaks correctly.
- [ ] Show simple heatmap or streak visualization.
- [ ] Surface basic habit data in Reports (later).

## 5. Debts / Liabilities
- [ ] Enter liabilities (principal, APR, min payment).
- [ ] Snowball and avalanche strategies wired to UI buttons.
- [ ] Compute and display payoff schedule with projected debt-free date.
- [ ] Strategy modes: aggressive / balanced / lazy alter assumptions.
- [ ] User-friendly explanation text for strategy differences.
- [ ] Show summary chart or table (timeline / remaining balance).

## 6. Portfolio (Demo-Focused)
- [ ] Add holding manually or via CSV import.
- [ ] Parse symbol, quantity, price, category/sector columns.
- [ ] Allocation donut chart by symbol or category.
- [ ] Export portfolio CSV with confirmation snackbar.
- [ ] Add second chart (allocation by category or gain/loss bar).

## 7. Reports & Analytics
- [ ] Reports page reachable without crashes.
- [ ] Charts visible without exporting: spending vs income, category breakdown, debt payoff summary, habit streak snippet.
- [ ] CSV/PNG export for key reports under `instance/reports/` with confirmation path.
- [ ] Add month filters per page (not only topbar).

## 8. Settings & Admin View
- [ ] Dark/Light toggle stays working.
- [ ] Admin toggle or tab clearly exposed (User vs Admin mode).
- [ ] Admin actions wired: Run Demo Seed, Reset Demo Data, Import/Export, Backup/Restore.
- [ ] Backup zips DB + CSV/PNGs under `instance/backups/` with timestamp snackbar.
- [ ] Show app version and instance path for demos.

## 9. Navigation, Topbar, and UX
- [ ] Stable tab switching (no jitter, instant transitions).
- [ ] Each page owns month filters; topbar provides shortcuts only.
- [ ] CSV Help and Help page reachable from Settings/Reports/Portfolio/topbar.
- [ ] Copy is concise and friendly.

## 10. Testing & Docs
- [ ] Expand tests: ledger filters/add/delete (“All” category), admin seed/reset, debts calculations, habits streak logic.
- [ ] New doc pointers for verbose pytest and ruff commands (no skips).
- [ ] Reference this master TODO from README and keep milestones updated.
