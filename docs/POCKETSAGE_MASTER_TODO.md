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

## Follow-ups: Admin Mode UX & Button Wiring
- [x] Admin view blank state: ensure actions card renders (see `src/pocketsage/desktop/views/admin.py`) and avoid control `.update()` calls before attaching to a page (`status_ref`/`Text.update` guards).
- [x] Button handlers: confirm seed/reset/export/backup buttons surface feedback and refresh user-facing views; adjust `_with_spinner/_notify` to no-op updates when `page` is absent.
- [x] Verify dashboard "Add Transaction" quick action opens ledger dialog automatically (uses `ctx.pending_new_transaction` in `ledger.build_ledger_view`).
- [x] Re-run new button action tests (`tests/test_button_actions.py`) to validate add/edit/delete flows across Ledger/Habits/Debts/Portfolio/Budgets and Admin seed/reset wiring.

---

## 11. Code Quality & Completeness Issues (Audit Nov 2025)

### 11.1 NotImplementedError Stubs & Incomplete Services

**Budgeting Service (`src/pocketsage/services/budgeting.py`)**
- [ ] Implement `BudgetRepository.planned_amounts()` - Currently returns `...` (Protocol stub)
- [ ] Implement `BudgetRepository.actual_spend()` - Currently returns `...` (Protocol stub)
- [ ] Complete `compute_variances()` function - Partially implemented but needs full testing
- [ ] Add comprehensive unit tests for budget variance calculations
- **Priority:** High - Core budgeting feature incomplete
- **Impact:** Budgets view cannot show accurate variance data
- **Location:** Lines 14-24

**Reports Service (`src/pocketsage/services/reports.py`)**
- [ ] Add unit tests for `build_spending_chart()` - Chart generation untested
- [ ] Add tests for `export_transactions_csv()` wrapper
- [ ] Add tests for `export_spending_png()` - PNG export untested
- [ ] Mock matplotlib to test chart rendering without file I/O
- **Priority:** Medium - Functionality works but lacks test coverage
- **Location:** Lines 18-89

### 11.2 Placeholder & Incomplete Implementations

**Habit Reminders (`src/pocketsage/services/habits.py`)**
- [ ] Replace `reminder_placeholder()` with real local notification system
- [ ] Integrate with OS notification APIs (Windows, macOS, Linux)
- [ ] OR document this as a future feature and update UI copy accordingly
- [ ] Remove "no-op placeholder" messaging from user-facing strings
- **Priority:** Medium - Feature exists but does nothing
- **Impact:** Users expect reminders to work but they're non-functional
- **Location:** Lines 41-47

**File Watcher (`src/pocketsage/services/watcher.py`)**
- [ ] Implement debouncing for rapid duplicate file events
- [ ] Add batch processing for multiple CSV files
- [ ] Surface observer lifecycle hooks in app factory
- [ ] Add proper shutdown/cleanup for observer threads
- [ ] Write integration tests for watcher behavior
- **Priority:** Low - Optional feature, watchdog dependency already handled
- **Impact:** Watcher could process duplicate events or leak threads
- **Location:** Lines 43, 50

**Authentication View (`src/pocketsage/desktop/views/auth.py`)**
- [ ] Document this placeholder as intentional for login-free desktop mode
- [ ] Remove or clearly mark as deprecated if multi-user mode returns
- [ ] Consider removing the redirect and just showing dashboard directly
- **Priority:** Low - Works as intended for current single-user mode
- **Location:** Entire file is a placeholder redirect

**CSV Import Validation (`src/pocketsage/services/import_csv.py`)**
- [ ] Add validation for duplicate CSV headers
- [ ] Add validation for inconsistent delimiters
- [ ] Enhance error messages for malformed CSV files
- [ ] Add unit tests for edge cases (empty files, wrong encoding)
- **Priority:** Medium - Could prevent import errors
- **Location:** Line 33

**Ledger Import Idempotency (`src/pocketsage/services/importers.py`)**
- [ ] Guarantee true idempotent import by external_id
- [ ] Write comprehensive tests for duplicate detection
- [ ] Handle hash collision scenarios gracefully
- [ ] Document import behavior in user-facing help
- **Priority:** High - Data integrity concern
- **Location:** Line 2 (TODO comment)

### 11.3 Budget Creation Error Handling

**Budget Line Creation (`src/pocketsage/desktop/views/budgets.py`)**
- [ ] Replace silent `pass` in budget line creation error handler (line ~85)
- [ ] Add proper validation before attempting to create budget line
- [ ] Show clear error snackbar when line creation fails
- [ ] Validate amount field is numeric before casting
- [ ] Validate category selection exists before creating line
- **Priority:** High - Silent failures confuse users
- **Impact:** Users don't know why budget lines aren't created
- **Location:** Lines 80-95 in `save_budget()` function

### 11.4 Data Model TODOs

**Transaction Model (`src/pocketsage/models/transaction.py`)**
- [ ] Enforce account linkage once multi-account support lands
- [ ] Enforce currency validation
- [ ] Replace tag_id FK with dedicated Tag table once taxonomy defined
- **Priority:** Medium - Future enhancements
- **Location:** Lines 52, 62

**Habit Model (`src/pocketsage/models/habit.py`)**
- [ ] Add owner foreign key when multi-user support arrives
- [ ] Enforce timezone-aware capture for cross-region tracking
- **Priority:** Low - Multi-user feature not yet active
- **Location:** Lines 37, 57

**Budget Model (`src/pocketsage/models/budget.py`)**
- [ ] Enforce non-overlapping budget windows per user
- [ ] Track actual spend + available with materialized views
- **Priority:** Medium - Data integrity & performance
- **Location:** Lines 33, 54

**Category Model (`src/pocketsage/models/category.py`)**
- [ ] Enforce color palette uniqueness
- [ ] Implement icon set once design assets land
- **Priority:** Low - UX enhancement
- **Location:** Line 34

**Settings Model (`src/pocketsage/models/settings.py`)**
- [ ] Add updated_at timestamp for audit trail
- [ ] Add audit trail for setting changes
- **Priority:** Low - Admin/ops enhancement
- **Location:** Line 19

### 11.5 Configuration & Security

**SQLCipher Implementation (`src/pocketsage/config.py`)**
- [ ] Replace SQLCipher driver URL placeholder with actual implementation
- [ ] Add SQLCipher pragma key handshake using env key material
- [ ] Test encryption/decryption with real SQLCipher installation
- [ ] Document SQLCipher setup steps for users
- [ ] Hide encryption toggle in Settings until feature is complete
- **Priority:** High - Security feature advertised but not working
- **Impact:** Users expect database encryption but it's not functional
- **Location:** Lines 54, 67

**Secret Key Validation (`src/pocketsage/config.py`)**
- [ ] Fail fast when SECRET_KEY is default in production modes
- [ ] Add validation for minimum key entropy
- [ ] Generate random key on first run if not provided
- **Priority:** Medium - Security best practice
- **Location:** Line 39

### 11.6 Settings View Issues

**Database Encryption Toggle (`src/pocketsage/desktop/views/settings.py`)**
- [ ] Remove or hide "SQLCipher toggle placeholder" until feature implemented
- [ ] Update UI copy to reflect that encryption is "coming soon"
- [ ] OR implement the full SQLCipher handshake
- **Priority:** High - Misleading to users
- **Location:** Line 269

**Import/Export Feedback (`src/pocketsage/desktop/views/settings.py`)**
- [ ] Force live data reload after CSV import completion
- [ ] Show detailed mapping errors from import process
- [ ] Add progress indicator for large imports
- [ ] Surface row counts (imported/skipped/failed) in snackbar
- **Priority:** Medium - UX improvement
- **Location:** Controllers `start_ledger_import`, `start_portfolio_import`

### 11.7 Admin Operations

**Admin Tasks (`src/pocketsage/services/admin_tasks.py`)**
- [ ] Add safety checks before destructive reset operations
- [ ] Support light vs heavy seed profiles
- [ ] Measure and log seed performance metrics
- [ ] Add confirmation dialogs for irreversible operations
- [ ] Document admin task behavior in ops guide
- **Priority:** High - Prevent accidental data loss
- **Location:** Lines 2, 3, 5

**Export Retention (`src/pocketsage/services/admin_tasks.py`)**
- [ ] Make EXPORT_RETENTION configurable via environment variable
- [ ] Add option to skip retention cleanup
- [ ] Log retention actions for audit trail
- **Priority:** Low - Current default (5) is reasonable
- **Location:** Export retention logic

### 11.8 Debts & Liabilities

**Debt Payment History (`src/pocketsage/desktop/views/debts.py`)**
- [ ] Record debt payments as ledger transactions
- [ ] Link debt payment UI to transaction creation
- [ ] Show payment history for each liability
- [ ] Integrate strategy modes (aggressive/balanced/lazy) into projections
- **Priority:** Medium - Feature gap
- **Location:** Lines 2, 4, 253

**Liability Service (`src/pocketsage/services/liabilities.py`)**
- [ ] Create dedicated liability service module
- [ ] Implement `build_payment_transaction()` helper
- [ ] Add validation for payment amounts vs minimum
- **Priority:** Medium - Referenced but not fully implemented
- **Location:** Referenced in debts.py line 22

### 11.9 Portfolio Enhancements

**Portfolio Filters (`src/pocketsage/desktop/views/portfolio.py`)**
- [ ] Add sector/asset-class breakdown visualization
- [ ] Add time-series portfolio value tracking
- [ ] Implement filtering by account, sector, or symbol
- [ ] Add market value calculations (current price * quantity)
- **Priority:** Low - Nice-to-have features
- **Location:** Lines 2, 4

### 11.10 Reports & Charts

**Report Service Centralization (`src/pocketsage/desktop/views/reports.py`)**
- [ ] Move report generation logic from views to service layer
- [ ] Create dedicated reports service module
- [ ] Keep views thin (presentation only)
- [ ] Add caching for expensive chart computations
- **Priority:** Medium - Architecture improvement
- **Location:** Line 2

### 11.11 Testing Gaps

**Test Coverage Priorities:**
- [ ] Budget variance calculations - `services/budgeting.py` has stubs
- [ ] CSV export tests - Format validation, injection prevention
- [ ] Chart generation tests - Matplotlib PNG mocking
- [ ] Watcher integration tests - Requires watchdog dependency
- [ ] Desktop view navigation tests - Routing, error handling
- [ ] Settings action tests - Import/export/backup flows
- [ ] Admin task error scenarios - Permission errors, disk full
- **Priority:** High - Core functionality needs coverage
- **Source:** `docs/TESTING_INFRASTRUCTURE.md`, `tests/README.md`

**Protocol Implementations (Domain Repositories):**
All domain repository protocols use `...` as method bodies (interface definitions).
These are INTENTIONAL and should NOT be implemented - they define contracts for
infra layer implementations. No action needed.
- `src/pocketsage/domain/repositories/*.py` - All use `...` correctly

### 11.12 Help & Documentation

**Help View (`src/pocketsage/desktop/views/help.py`)**
- [ ] Add quick-start checklist for first-time users
- [ ] Expand CSV import help with field mapping examples
- [ ] Add troubleshooting section for common issues
- **Priority:** Low - UX enhancement
- **Location:** Line 2

**Ledger View (`src/pocketsage/desktop/views/ledger.py`)**
- [ ] Implement three-tier layout (filters, summary cards, two-column)
- [ ] Add advanced filtering (date ranges, amounts, tags)
- [ ] Add bulk edit/delete operations
- **Priority:** Low - UX enhancement
- **Location:** Line 2

---

## 12. Test Stub Cleanup (Low Priority)

The following are legitimate test helpers and should remain as-is:
- `tests/test_view_reachability.py` - `_PageStub` class (line 12)
- `tests/test_ledger_view.py` - `_PageStub` class (line 14)
- `tests/test_ledger_filters.py` - `_PageStub` class (line 16)
- `tests/test_desktop_smoke.py` - `_IconsStub`, `_ColorsStub` (lines 16-28)
- `tests/test_admin_backup_restore.py` - `_PageStub` class (line 15)
- All test `pass` statements are intentional exception handlers or no-ops

---

## Summary Statistics

**Total Issues Found:** 60+
**High Priority:** 12 items (data integrity, security, user confusion)
**Medium Priority:** 18 items (UX improvements, architecture)
**Low Priority:** 30+ items (future enhancements, nice-to-haves)

**Categories:**
- Incomplete implementations: 8
- Missing tests: 15
- Data model enhancements: 8
- Security/config: 3
- UX/error handling: 12
- Documentation: 3
- Architecture improvements: 5
- Future features: 10+
