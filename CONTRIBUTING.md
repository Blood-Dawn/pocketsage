# Contributing

PocketSage uses the Campus Board pattern: Framework Owner seeds scaffolding + TODO markers, teammates land implementations.

## Ground Rules
- Target Python **3.11**.
- Keep business logic behind service/repository abstractions.
- Preserve `# TODO(@assignee)` comments; update acceptance criteria if scope changes.
- New routes require matching tests (skip allowed until backend ready).
- Install tooling: `pip install -e ".[dev]"` then `pre-commit install`.

## Workflow
1. Branch naming: `feature/<slug>`, `fix/<slug>`, or `docs/<slug>`.
2. Run `make lint` and `make test` before pushing.
   - If `make` is unavailable, run the lint commands directly:

     ```sh
     ruff check .
     black --check .
     ```

     Both commands exit with `0` when the codebase satisfies the configured rules.
     `ruff check .` returns a non-zero exit code when it finds lint violations; run
     `ruff check . --fix` to apply automatic fixes or address the reported issues
     manually. `black --check .` exits with `1` when files need formatting; resolve
     by running `black .` to rewrite the files, then re-run the check.
3. Update docs (`README.md`, `docs/`, `TODO.md`) whenever functionality shifts.
4. Pull Request checklist:
	- Reference addressed TODO items.
	- Describe manual/automated verification (screenshots for UI changes).
	- Keep diff <= 300 LOC when possible; split otherwise.

## Commit Style
- Use concise conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
- Squash merges allowed; ensure final message keeps context.

## Testing Requirements

### Running Tests Locally

Before submitting a PR, run the full test suite:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src/pocketsage --cov-report=term-missing

# Run tests in parallel (faster)
pytest -n auto

# Run only fast tests (skip slow integration tests)
pytest -m "not slow"
```

### When to Write Tests

**Always write tests when:**
- Adding new domain logic (services, calculations, business rules)
- Adding new repository methods (CRUD, queries, filters)
- Fixing a bug (write failing test first, then fix)
- Adding CSV import/export functionality
- Adding financial calculations (debts, budgets, cash flow)

**Tests are optional (but encouraged) for:**
- UI-only changes (templates, styling)
- Documentation updates
- Configuration changes

### Test Coverage Expectations

- **Domain logic** (services, calculations): **80%+**
- **Repositories** (CRUD operations): **75%+**
- **CSV import/export**: **70%+**
- **New features**: Must include tests before PR approval

### How to Write Tests

All test fixtures and helpers are in `tests/conftest.py`. Use factories instead of manual object construction:

```python
# ✅ Good: Use factory fixtures
def test_transaction_creation(transaction_factory):
    tx = transaction_factory(amount=-50.00, memo="Groceries")
    assert tx.amount == -50.00

# ❌ Avoid: Manual construction
def test_transaction_creation(db_session):
    tx = Transaction(amount=-50.00, memo="Groceries", occurred_at=datetime.now())
    db_session.add(tx)
    db_session.commit()
```

### Test Structure

Follow the **Arrange-Act-Assert** pattern:

```python
def test_snowball_orders_by_smallest_balance():
    # Arrange: Set up test data
    debt1 = DebtAccount(id=1, balance=5000.00, apr=15.0, minimum_payment=100.00, statement_due_day=15)
    debt2 = DebtAccount(id=2, balance=500.00, apr=20.0, minimum_payment=25.00, statement_due_day=15)

    # Act: Call function under test
    schedule = snowball_schedule(debts=[debt1, debt2], surplus=200.00)

    # Assert: Verify behavior
    assert schedule[0]["payments"]["debt_2"]["payment_amount"] == 225.00
```

### Testing Money Calculations

Use `assert_float_equal` from `conftest.py` for money comparisons:

```python
from tests.conftest import assert_float_equal

def test_interest_calculation():
    principal = 1000.00
    apr = 12.0
    monthly_interest = principal * apr / 1200

    # Don't use exact equality with floats
    assert_float_equal(monthly_interest, 10.00, tolerance=0.01)
```

### Continuous Integration

All PRs must pass CI checks:

1. **Tests** - pytest on Python 3.11 and 3.12
2. **Coverage** - Minimum 40% (increasing over time)
3. **Linting** - ruff and black
4. **Security** - bandit security scan
5. **Build** - Package builds successfully

View CI results in GitHub Actions tab. Fix failures before requesting review.

### Test Documentation

See `tests/README.md` for:
- Complete fixture reference
- Testing best practices
- Examples for each test type
- Troubleshooting guide

## Security & Privacy
- No external API calls without Framework Owner approval.
- Keep secrets in `.env`; never commit actual keys.
- Document SQLCipher key handling steps in any PR enabling encryption.
