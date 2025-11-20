# PocketSage Test Suite

Comprehensive automated testing infrastructure for PocketSage domain logic, repositories, services, and data pipelines.

## Overview

This test suite is designed to verify all domain logic **without requiring the UI**. Tests run against an isolated in-memory SQLite database and cover:

- **Financial calculations** (debt payoff, budget tracking, cash flow)
- **Repository operations** (CRUD, queries, filters, upsert logic)
- **CSV import/export** (parsing, validation, idempotency)
- **Habit tracking** (streaks, completions)
- **Money representation** (float precision, rounding)
- **Integration scenarios** (multi-model workflows)

## Quick Start

### Run All Tests

```bash
# From project root
pytest

# With coverage report
pytest --cov=src/pocketsage --cov-report=term-missing

# Parallel execution (faster)
pytest -n auto

# Verbose output
pytest -v
```

### Run Specific Test Modules

```bash
# Debt calculations only
pytest tests/test_debt_calculations.py

# Habit streaks only
pytest tests/test_habit_streaks.py

# CSV import only
pytest tests/test_csv_import_comprehensive.py

# Money representation (float validation)
pytest tests/test_money_representation.py
```

### Run Tests by Pattern

```bash
# All tests matching "snowball"
pytest -k snowball

# All tests for repositories
pytest tests/test_repositories.py tests/test_*_repository.py

# All integration tests
pytest -m integration
```

## Test Structure

```
tests/
├── conftest.py                         # Shared fixtures, DB setup, factories
├── test_debt_calculations.py           # Snowball/avalanche payoff tests
├── test_habit_streaks.py               # Habit completion and streak tests
├── test_csv_import_comprehensive.py    # CSV parsing and import tests
├── test_money_representation.py        # Float precision and rounding tests
├── test_repositories.py                # Repository CRUD and query tests
├── test_ledger_*.py                    # Legacy ledger tests
├── test_budgeting.py                   # Budget variance tests
├── test_admin_jobs.py                  # Admin task tests
└── README.md                           # This file
```

## Fixtures Reference

All fixtures are defined in `conftest.py` and available to all tests.

### Database Fixtures

| Fixture | Scope | Description |
|---------|-------|-------------|
| `db_engine` | function | Isolated SQLite engine per test |
| `db_session` | function | Session with automatic rollback |
| `session_factory` | function | Factory for repository-compatible sessions |

### Test Data Factories

| Factory | Returns | Example Usage |
|---------|---------|---------------|
| `category_factory` | Category | `category_factory(name="Groceries", slug="groceries")` |
| `account_factory` | Account | `account_factory(name="Checking", currency="USD")` |
| `transaction_factory` | Transaction | `transaction_factory(amount=-50.00, memo="Groceries")` |
| `liability_factory` | Liability | `liability_factory(balance=5000.00, apr=18.0)` |
| `habit_factory` | Habit | `habit_factory(name="Exercise", is_active=True)` |
| `budget_factory` | Budget | `budget_factory(label="January", lines=[...])` |
| `holding_factory` | Holding | `holding_factory(symbol="AAPL", quantity=10.0)` |

### Seed Data Fixtures

| Fixture | Returns | Description |
|---------|---------|-------------|
| `seed_categories` | dict | Standard categories (groceries, salary, rent, utilities) |
| `seed_accounts` | dict | Standard accounts (checking, savings) |

## Writing New Tests

### Example: Testing a New Service Function

```python
from src.pocketsage.services.my_service import calculate_net_worth

def test_calculate_net_worth_basic(transaction_factory, liability_factory):
    """Net worth should be assets minus liabilities."""
    # Arrange: Create test data
    transaction_factory(amount=1000.00, memo="Asset")
    liability_factory(balance=500.00, name="Debt")

    # Act: Call service function
    net_worth = calculate_net_worth()

    # Assert: Verify result
    assert net_worth == 500.00
```

### Example: Testing Repository CRUD

```python
from src.pocketsage.infra.repositories.transaction import SQLModelTransactionRepository

def test_transaction_repository_filters_by_date(session_factory, transaction_factory):
    """Repository should filter transactions by date range."""
    repo = SQLModelTransactionRepository(session_factory)

    # Create transactions on different dates
    today = datetime.now()
    yesterday = today - timedelta(days=1)

    transaction_factory(amount=-50.00, occurred_at=today)
    transaction_factory(amount=-25.00, occurred_at=yesterday)

    # Filter for today only
    start = today.replace(hour=0, minute=0, second=0, microsecond=0)
    end = today.replace(hour=23, minute=59, second=59, microsecond=999999)

    results = repo.filter_by_date_range(start, end)

    assert len(results) == 1
    assert results[0].amount == -50.00
```

### Example: Testing CSV Import

```python
import tempfile
from pathlib import Path
from src.pocketsage.services.import_csv import import_csv_file, ColumnMapping

def test_csv_import_skips_invalid_rows():
    """CSV import should skip rows with invalid data."""
    # Create temporary CSV file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("date,amount,memo\\n")
        f.write("2024-01-01,100.00,Valid\\n")
        f.write("2024-01-02,invalid,Invalid amount\\n")  # Should skip
        f.write("2024-01-03,50.00,Valid\\n")
        csv_path = Path(f.name)

    try:
        mapping = ColumnMapping(
            amount="amount",
            occurred_at="date",
            memo="memo",
        )

        count = import_csv_file(csv_path=csv_path, mapping=mapping)

        # Should only count valid rows
        assert count == 2
    finally:
        csv_path.unlink()
```

## Testing Best Practices

### 1. **Use Factories, Not Manual Construction**

✅ **Good:**
```python
def test_something(transaction_factory):
    tx = transaction_factory(amount=-50.00)
```

❌ **Avoid:**
```python
def test_something(db_session):
    tx = Transaction(amount=-50.00, occurred_at=datetime.now(), memo="")
    db_session.add(tx)
    db_session.commit()
```

### 2. **Test One Thing Per Test**

✅ **Good:**
```python
def test_snowball_orders_by_smallest_balance():
    # Test only snowball ordering logic
    pass

def test_snowball_calculates_interest_correctly():
    # Test only interest calculation
    pass
```

❌ **Avoid:**
```python
def test_snowball_everything():
    # Tests ordering, interest, payments, etc. all in one
    pass
```

### 3. **Use Descriptive Test Names**

Test names should describe the behavior being tested:

```python
def test_current_streak_returns_zero_when_no_entries():
    # Clear what's being tested from the name
    pass

def test_csv_import_handles_utf8_special_characters():
    # Specific scenario is obvious
    pass
```

### 4. **Use `assert_float_equal` for Money**

Since the codebase uses float for money (not Decimal), always use tolerance:

```python
from tests.conftest import assert_float_equal

def test_interest_calculation():
    interest = calculate_interest(principal=1000.00, apr=12.0)
    assert_float_equal(interest, 10.00, tolerance=0.01)
```

### 5. **Mark Slow or Integration Tests**

```python
import pytest

@pytest.mark.slow
def test_import_huge_csv_file():
    # This test takes a long time
    pass

@pytest.mark.integration
def test_full_budget_workflow():
    # Tests multiple components together
    pass
```

Run fast tests only:
```bash
pytest -m "not slow"
```

## Coverage Guidelines

### Current Coverage Goals

- **Domain logic** (services, calculations): **80%+**
- **Repositories** (CRUD operations): **75%+**
- **CSV import/export**: **70%+**
- **Overall codebase**: **60%+**

### Viewing Coverage Reports

```bash
# Terminal report with missing lines
pytest --cov=src/pocketsage --cov-report=term-missing

# HTML report (opens in browser)
pytest --cov=src/pocketsage --cov-report=html
open htmlcov/index.html

# XML report (for CI tools)
pytest --cov=src/pocketsage --cov-report=xml
```

### Coverage Gaps to Address

As of the current test suite, the following areas need more coverage:

1. **Budget variance calculations** - `services/budgeting.py` has NotImplementedError stubs
2. **Desktop admin flows** - Settings/Reports actions and admin task triggers need lightweight smoke coverage
3. **Export CSV** - CSV export formatting and security (CSV injection prevention)
4. **Chart generation** - Matplotlib PNG generation (if applicable)
5. **Watchdog integration** - File watcher automation logic

## Continuous Integration (CI)

### GitHub Actions Workflow

Tests run automatically on:
- Push to `main` or `develop` branches
- Pull requests targeting `main` or `develop`

The CI workflow includes:

1. **Tests** (Python 3.11 and 3.12)
   - Run full test suite with coverage
   - Upload coverage to Codecov
   - Check coverage threshold (40% minimum, increasing over time)

2. **Linting**
   - `ruff` for code quality
   - `black --check` for formatting

3. **Security**
   - `bandit` for security vulnerabilities
   - `safety` for dependency vulnerabilities

4. **Build Check**
   - Verify package builds correctly
   - Run `twine check` on dist

### Local CI Simulation

Run the same checks locally before pushing:

```bash
# Run tests with coverage
pytest --cov=src/pocketsage --cov-report=term-missing

# Run linting
ruff check src/ tests/
black --check src/ tests/

# Run security scan
bandit -r src/pocketsage

# Build package
python -m build
```

## Troubleshooting

### Tests Fail with "No module named 'src'"

Ensure `pythonpath = ["."]` is in `pyproject.toml` under `[tool.pytest.ini_options]`.

Or run pytest from project root:

```bash
cd /path/to/pocketsage
pytest
```

### Tests Fail with Database Errors

Check that the test is using fixtures correctly:

```python
# ✅ Correct
def test_something(session_factory):
    repo = SQLModelTransactionRepository(session_factory)

# ❌ Wrong - no session provided
def test_something():
    repo = SQLModelTransactionRepository()  # Error!
```

### Tests Are Slow

Use parallel execution:

```bash
pytest -n auto  # Uses all CPU cores
pytest -n 4     # Uses 4 workers
```

Or mark slow tests and skip them during development:

```bash
pytest -m "not slow"
```

### Import Errors in Tests

Make sure you've installed the dev dependencies:

```bash
pip install -e ".[dev]"
```

## Test Maintenance

### When Adding a New Model

1. Add factory fixture to `conftest.py`
2. Create basic CRUD tests in `test_repositories.py`
3. Add integration tests for business logic

### When Adding a New Service Function

1. Create a new test file or add to existing module
2. Test happy path and edge cases
3. Test with mock dependencies (if applicable)
4. Verify money calculations with `assert_float_equal`

### When Fixing a Bug

1. Write a failing test that reproduces the bug
2. Fix the bug
3. Verify test passes
4. Commit test + fix together

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [SQLModel testing guide](https://sqlmodel.tiangolo.com/tutorial/testing/)
- [Coverage.py documentation](https://coverage.readthedocs.io/)
- [GitHub Actions Python guide](https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python)

## Questions?

If you have questions about testing or need help writing tests, please:

1. Check this README first
2. Look at existing tests for examples
3. Open an issue or ask in the team channel
