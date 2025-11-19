# PocketSage Flet Desktop Architecture

## Current Flask Architecture Summary

### Domain Layer
**Models** (SQLModel entities in `src/pocketsage/models/`):
- `Transaction` - Ledger entries with amounts, memos, categories, accounts
- `Account` - Multi-account support with currency tracking
- `Category` - Expense/income categorization with color coding
- `Budget` + `BudgetLine` - Time-boxed budget envelopes
- `Habit` + `HabitEntry` - Daily habit tracking with streaks
- `Liability` - Debt tracking with APR and payment strategies
- `Holding` - Portfolio holdings with cost basis
- `AppSetting` - Application configuration

### Service Layer
**Pure business logic** (in `src/pocketsage/services/`):
- `debts.py` - Snowball/avalanche amortization calculators
- `budgeting.py` - Budget variance computation (partial)
- `import_csv.py` - CSV parsing with column mapping
- `export_csv.py` - Transaction export to CSV
- `reports.py` - Analytics and reporting helpers

### Infrastructure Layer
**Database & Config** (in `src/pocketsage/`):
- `extensions.py` - SQLModel engine initialization, session management
- `config.py` - Environment-based config with SQLite/SQLCipher support
- Database URL: `instance/pocketsage.db` (configurable via env)
- Session lifecycle: Flask request-scoped via `g.sqlmodel_session`

### Presentation Layer (Flask)
**Blueprints** (in `src/pocketsage/blueprints/`):
- `overview` - Dashboard with summary stats
- `ledger` - Transaction CRUD with filters
- `habits` - Habit tracking UI
- `liabilities` - Debt management
- `portfolio` - Holdings management
- `admin` - System administration

**Templates**: Jinja2 templates in `src/pocketsage/templates/`

---

## Proposed Flet Architecture

### 1. Layered Structure

```
src/pocketsage/
├── domain/              # Pure business logic (NEW)
│   ├── entities/        # Domain models (moved from models/)
│   ├── services/        # Pure services (refactored from services/)
│   └── repositories/    # Repository protocols (NEW)
│
├── infra/               # Infrastructure concerns (NEW)
│   ├── database.py      # Engine, session factory
│   ├── repositories/    # Concrete SQLModel repos
│   ├── csv_io.py        # Import/export adapters
│   └── config.py        # Config management
│
├── desktop/             # Flet UI layer (NEW)
│   ├── app.py           # Main Flet entrypoint
│   ├── context.py       # AppContext for DI
│   ├── navigation.py    # Routing & view registry
│   ├── components/      # Reusable UI components
│   │   ├── charts.py    # Chart wrappers
│   │   ├── dialogs.py   # Error/confirm dialogs
│   │   └── widgets.py   # Common controls
│   └── views/           # Screen implementations
│       ├── dashboard.py
│       ├── ledger.py
│       ├── budgets.py
│       ├── habits.py
│       ├── debts.py
│       ├── portfolio.py
│       └── settings.py
│
├── models/              # Keep existing SQLModel definitions
└── services/            # Keep existing services temporarily
```

### 2. AppContext Pattern

Centralized dependency container created once at app startup:

```python
@dataclass
class AppContext:
    """Shared application services and repositories."""

    # Infrastructure
    config: BaseConfig
    session_factory: Callable[[], Session]

    # Repositories
    transaction_repo: TransactionRepository
    account_repo: AccountRepository
    category_repo: CategoryRepository
    budget_repo: BudgetRepository
    habit_repo: HabitRepository
    liability_repo: LiabilityRepository
    holding_repo: HoldingRepository

    # Services
    debt_service: DebtService
    budget_service: BudgetService
    import_service: ImportService
    export_service: ExportService

    # UI State
    theme_mode: ft.ThemeMode
    current_account_id: Optional[int]
    current_month: date
```

### 3. Flet Entrypoint & Routing

**Main entry** (`src/pocketsage/desktop/app.py`):
```python
def main(page: ft.Page):
    # Configure page
    page.title = "PocketSage"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 1200
    page.window_height = 800

    # Initialize context
    ctx = create_app_context()

    # Set up routing
    router = Router(page, ctx)
    page.on_route_change = router.route_change

    # Navigate to default route
    page.go("/dashboard")

if __name__ == "__main__":
    ft.app(target=main)
```

**Routes**:
- `/dashboard` - Overview with net worth, spending, habits
- `/ledger` - Transaction table with filters
- `/budgets` - Budget vs actual
- `/habits` - Habit tracking grid
- `/debts` - Liability list and payoff projections
- `/portfolio` - Holdings and allocation
- `/settings` - App configuration and admin tools

### 4. Repository Pattern

**Protocol** (in `domain/repositories/`):
```python
class TransactionRepository(Protocol):
    def get_by_id(self, id: int) -> Optional[Transaction]: ...
    def list_all(self, limit: int = 100) -> list[Transaction]: ...
    def filter_by_date_range(self, start: date, end: date) -> list[Transaction]: ...
    def create(self, transaction: Transaction) -> Transaction: ...
    def update(self, transaction: Transaction) -> Transaction: ...
    def delete(self, id: int) -> None: ...
```

**Implementation** (in `infra/repositories/`):
```python
class SQLModelTransactionRepository:
    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory

    def get_by_id(self, id: int) -> Optional[Transaction]:
        with self.session_factory() as session:
            return session.get(Transaction, id)
```

### 5. View Pattern

Each view is a function that builds a `ft.View`:

```python
def build_dashboard_view(ctx: AppContext, page: ft.Page) -> ft.View:
    # Fetch data
    summary = load_summary(ctx)

    # Build UI
    return ft.View(
        route="/dashboard",
        controls=[
            build_app_bar(ctx, "Dashboard"),
            build_summary_cards(summary),
            build_charts(summary),
        ],
    )
```

---

## Migration Strategy

### Phase 1: Foundation (Domain & Infra)
1. Keep existing `models/` intact
2. Create repository protocols in `domain/repositories/`
3. Implement SQLModel repositories in `infra/repositories/`
4. Refactor services to depend on repository protocols
5. Create `infra/database.py` with standalone session factory
6. Create `AppContext` in `desktop/context.py`

### Phase 2: Flet Shell
1. Add Flet to dependencies
2. Create `desktop/app.py` with main entrypoint
3. Build routing system in `desktop/navigation.py`
4. Create base layout with NavigationRail
5. Implement error dialog component
6. Add month/account selector in app bar

### Phase 3: Core Views
1. Dashboard - Summary cards + basic charts
2. Ledger - Transaction table with add/edit/delete
3. Budgets - Budget lines with progress bars
4. Habits - Habit list with daily toggles

### Phase 4: Advanced Views
1. Debts - Liability table + payoff chart
2. Portfolio - Holdings table + allocation pie
3. Settings - Theme toggle, DB path, admin tools

### Phase 5: Charts & Polish
1. Integrate Matplotlib PNGs via `ft.Image`
2. Add native Flet charts for interactivity
3. Implement responsive layouts
4. Add animations and transitions

### Phase 6: Packaging
1. Configure `flet pack` command
2. Create build scripts
3. Test Windows desktop binary
4. Update README with desktop mode docs

---

## Key Design Decisions

1. **Keep Flask & Flet coexisting** - The Flask app remains for web/server mode; Flet is a parallel desktop UI
2. **Share all domain logic** - No duplication of business rules
3. **Repository abstraction** - Services depend on protocols, not SQLModel directly
4. **Offline-first** - No external API calls; all data local
5. **Type annotations everywhere** - Full mypy compatibility
6. **Minimal dependencies** - Add Flet; keep matplotlib, pandas, sqlmodel

---

## Testing Strategy

1. **Unit tests for services** - Pure functions with mock repositories
2. **Integration tests for repos** - Real SQLite DB in tmpdir
3. **UI smoke tests** - Launch Flet app, verify no crashes
4. **Manual smoke test checklist**:
   - Start app → Dashboard loads
   - Add transaction → Appears in ledger
   - Toggle habit → Updates streak
   - Add liability → Shows in debts
   - Import CSV → Creates transactions
   - Export CSV → File created
   - Theme toggle → UI updates

---

## Open Questions & TODOs

1. **Multi-user support** - Future: Add User model, auth layer
2. **Recurring transactions** - Add RecurringTransaction model
3. **Budget envelopes** - Rollover logic for unused funds
4. **Savings goals** - Add Goal model with target amounts
5. **Reports** - PDF export, custom date ranges
6. **Data sync** - Optional cloud backup via encrypted exports
7. **Mobile** - Flet supports mobile; consider iOS/Android builds

---

## References

- Flet docs: https://flet.dev/docs/
- SQLModel docs: https://sqlmodel.tiangolo.com/
- Current Flask app: `src/pocketsage/__init__.py`
- Existing models: `src/pocketsage/models/`
