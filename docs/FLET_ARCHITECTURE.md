# PocketSage Flet Desktop Architecture

## Current Desktop Architecture

### Domain Layer
SQLModel entities in `src/pocketsage/models/`:
- Transaction, Account, Category, Budget/BudgetLine, Habit/HabitEntry, Liability, Holding, AppSetting

### Service Layer
Business logic in `src/pocketsage/services/` (mix of implemented and TODO):
- `debts.py` snowball/avalanche calculators
- `budgeting.py` variance/rolling cashflow stubs
- `import_csv.py` CSV parsing and upsert helpers
- `export_csv.py` transaction export
- `admin_tasks.py` demo seed + export ZIP generation
- `reports.py` reporting stubs

### Infrastructure Layer
Database/config in `src/pocketsage/`:
- `config.py` environment-driven settings with SQLite/SQLCipher toggle
- `infra/database.py` engine/session helpers + schema initialization
- `infra/repositories/` concrete SQLModel repositories

### Presentation Layer (Flet)
- Router + page setup in `desktop/app.py` and `desktop/navigation.py`
- Shared components in `desktop/components/`
- Views per area in `desktop/views/` (dashboard, ledger, budgets, habits, debts, portfolio, reports, settings)
- `desktop/context.py` builds `AppContext` with repositories and UI state

---

## Proposed/Target Structure

```
src/pocketsage/
├─ domain/            # Pure business logic (protocols, entities) - future refactor
├─ infra/             # Database + repositories
│  ├─ database.py
│  └─ repositories/
├─ desktop/           # Flet UI
│  ├─ app.py
│  ├─ context.py
│  ├─ navigation.py
│  ├─ components/
│  └─ views/
├─ models/            # SQLModel tables
└─ services/          # Cross-cutting services (debts, budgeting, CSV, admin tasks)
```

---

## AppContext Pattern

`desktop/context.py` builds a single container used across views:

```python
@dataclass
class AppContext:
    config: BaseConfig
    session_factory: Callable[[], Session]
    transaction_repo: SQLModelTransactionRepository
    account_repo: SQLModelAccountRepository
    category_repo: SQLModelCategoryRepository
    budget_repo: SQLModelBudgetRepository
    habit_repo: SQLModelHabitRepository
    liability_repo: SQLModelLiabilityRepository
    holding_repo: SQLModelHoldingRepository
    theme_mode: ft.ThemeMode
    current_account_id: Optional[int]
    current_month: date
    page: Optional[ft.Page] = None
```

`AppContext` is created once at startup, shares the session factory with services/admin tasks, and is passed into every view builder.

---

## Routing

- `desktop/navigation.Router` maps paths to view-builder functions.
- `desktop/app.py` registers routes (`/dashboard`, `/ledger`, `/budgets`, `/habits`, `/debts`, `/portfolio`, `/reports`, `/settings`) and wires keyboard shortcuts (`Ctrl+N`, `Ctrl+Shift+H`, `Ctrl+1..7`).
- Navigation rail in `desktop/components/layout.py` drives page transitions.

---

## Data & Session Handling

- `infra/database.create_db_engine` builds an engine from `BaseConfig` (SQLite/SQLCipher-ready).
- `infra/database.session_scope(engine)` provides a commit/rollback context manager.
- `create_session_factory(engine)` returns a factory compatible with repositories and `services/admin_tasks`.

---

## Admin Tasks (Desktop)

- `services/admin_tasks.run_demo_seed(session_factory)` seeds categories, accounts, six sample transactions, habits (with entries), liabilities, and a current-month budget idempotently.
- `services/admin_tasks.run_export(output_dir, session_factory)` generates a ZIP with CSV + PNG, retaining the latest five archives (`EXPORT_RETENTION`).
- Desktop Settings/Reports views call these helpers directly; no Flask CLI remains.

---

## Open Issues / TODOs

- Fix Holding <-> Account mapper error; move money handling away from floats.
- Implement budgeting calculations, debt payoff correctness, habit streak fixes.
- Add CSV import/export flows in the Flet UI and wire watcher extra.
- Replace `SQLModel.metadata.create_all` with Alembic once schema stabilizes.
- Expand desktop CRUD/filtering, charts, and admin/backup UX.
