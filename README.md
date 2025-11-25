# PocketSage - Offline Desktop Finance + Habits Tracker

[![CI](https://github.com/Blood-Dawn/pocketsage/actions/workflows/ci.yml/badge.svg)](https://github.com/Blood-Dawn/pocketsage/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**PocketSage** is a privacy-focused, offline-first personal finance and habit tracking application. No cloud, no login, no telemetry—your data stays on your machine.

## ✨ Features

### 💰 Ledger & Transactions
- **Complete CRUD**: Add, edit, delete transactions with categories and accounts
- **Smart Filtering**: Filter by date range, category, type (income/expense), or text search
- **CSV Import/Export**: Idempotent imports prevent duplicates, round-trip compatible
- **Monthly Summaries**: Automatic income/expense/net calculations
- **Budget Integration**: Real-time budget progress and overspend warnings
- **Spending Charts**: Visual breakdown by category with colorblind-friendly palette

### 📊 Budgets
- **Monthly Planning**: Create budgets per category with copy-from-previous-month
- **Rollover Support**: Underspend rolls forward, overspend reduces next month's budget
- **Progress Tracking**: Visual progress bars with red highlights for exceeded categories
- **Overall View**: Total budget vs. actual spending with variance calculations

### ✅ Habit Tracking
- **Daily Toggle**: One-click to mark habit completion for today
- **Streak Calculation**: Current streak and longest streak automatically computed
- **Visual Heatmap**: 30-day grid showing completion history
- **Archive/Reactivate**: Hide completed habits without losing history
- **Optional Reminders**: Set reminder times (notification infrastructure ready)

### 💳 Debt Management
- **Liability Tracking**: Track loans, credit cards with APR and minimum payments
- **Payoff Strategies**: Snowball (smallest first) and Avalanche (highest APR first)
- **Payment Recording**: Log payments and watch balance decrease
- **Payoff Timeline**: Visual chart showing path to debt-free with projected dates
- **Interest Calculations**: See total interest saved with different strategies

### 📈 Portfolio (Investment Tracking)
- **Holdings Management**: Track stocks, ETFs, crypto with quantity and prices
- **CSV Import/Export**: Batch import holdings from broker statements
- **Gain/Loss Tracking**: Automatic cost basis and market value calculations
- **Allocation Chart**: Donut chart showing portfolio distribution
- **Multi-Account**: Separate holdings by brokerage account

### 📑 Reports & Analytics
- **Comprehensive Charts**: Spending, cashflow trends, budget usage, debt payoff
- **Habit Insights**: Completion heatmaps and streak summaries
- **Export Bundles**: Download all data + charts as ZIP for backup
- **Month-over-Month**: Compare current vs. previous month performance

### ⚙️ Settings & Admin
- **Theme Toggle**: Light/dark mode with persistence
- **Demo Data**: One-click seed realistic demo transactions, habits, debts, portfolio
- **Backup/Restore**: ZIP archives with 5-file retention, easy restore
- **Data Directory**: View and access your local data folder

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/Blood-Dawn/pocketsage.git
cd pocketsage

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Optional: Install scheduler for auto-backup
pip install -e ".[scheduler]"

# Optional: Install watcher for auto-import
pip install -e ".[watcher]"
```

### Running the App

```bash
python run_desktop.py
```

The app launches directly to the Dashboard—no login required!

### First Steps

1. **Explore Demo Data**: Go to Settings → "Seed Demo Data" to populate with sample transactions, habits, and debts
2. **Add a Transaction**: Press `Ctrl+N` or click "Add transaction" in Ledger
3. **Create a Budget**: Navigate to Budgets → "Create new budget" → Set amounts per category
4. **Track a Habit**: Press `Ctrl+Shift+H` or go to Habits → "Add habit" → Toggle daily completion

## Roadmap & Sprint TODO
- Master backlog: see `docs/POCKETSAGE_MASTER_TODO.md` for the current overhaul plan.
- Run locally via `python run_desktop.py` from the repo root (no login required).
- Exports/backups live under `instance/exports/` and `instance/backups/`; Settings/Admin buttons trigger them.

### User/Admin Modes
- The desktop app auto-loads a local profile (no password).
- Toggle **Admin mode** from the app bar switch to access seed/reset/export/backup.
- Switch back to user mode to continue normal ledger/habits/debts/portfolio/reports flows; changes reflect immediately.

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+1` | Dashboard |
| `Ctrl+2` | Ledger |
| `Ctrl+3` | Budgets |
| `Ctrl+4` | Habits |
| `Ctrl+5` | Debts |
| `Ctrl+6` | Portfolio |
| `Ctrl+7` | Settings |
| `Ctrl+N` | New Transaction |
| `Ctrl+Shift+H` | New Habit |

## 📁 Data & Privacy

### Local Storage
- All data stored in `instance/` directory (configurable via `POCKETSAGE_DATA_DIR`)
- SQLite database: `instance/pocketsage.db`
- Logs: `instance/logs/` (JSON format with rotation)
- Backups: `instance/backups/` and `instance/exports/`

### No Telemetry
- **Zero external network calls** - completely offline
- No analytics, tracking, or data collection
- Your financial data never leaves your machine

### Encryption (Optional)
SQLCipher support ready via environment variable:
```bash
export POCKETSAGE_DB_ENCRYPTION=true
export POCKETSAGE_DB_KEY="your-strong-passphrase"
```

## 📊 CSV Import/Export Formats

### Ledger Transactions
```csv
date,amount,memo,category,account,currency,transaction_id
2025-01-15,-45.50,Groceries,Food,Checking,USD,tx-001
2025-01-16,1500.00,Salary,Income,Checking,USD,tx-002
```

### Portfolio Holdings
```csv
symbol,shares,price,market_price,account,currency
AAPL,10,150.00,175.50,Brokerage,USD
BTC,0.5,40000.00,42000.00,Crypto,USD
```

**Note**: Imports are idempotent—re-importing the same file won't create duplicates.

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POCKETSAGE_DATA_DIR` | `instance/` | Data directory path |
| `POCKETSAGE_ENV` | `development` | Environment (development/testing/production) |
| `POCKETSAGE_SECRET_KEY` | `dev-secret-key` | Flask session secret |
| `POCKETSAGE_DB_ENCRYPTION` | `false` | Enable SQLCipher |
| `POCKETSAGE_DB_KEY` | - | Encryption passphrase |

### Settings (In-App)
- **Theme**: Light/dark mode toggle
- **Auto-Backup**: Enable nightly backups at 3:00 AM (requires scheduler extra)
- **Data Directory**: View path to your data folder

## 🏗️ Development

### Running Tests
```bash
# All tests
pytest

# Fast tests only (skip slow/performance)
pytest -m "not slow and not performance"

# With coverage
pytest --cov=src/pocketsage --cov-report=html
```

### Code Quality
```bash
# Linting
ruff check src/ tests/

# Formatting
black src/ tests/

# Security scan
bandit -r src/pocketsage
```

### Building Desktop Executable
```bash
# Linux/macOS
./scripts/build_desktop.sh

# Windows
scripts\build_desktop.bat
```

Output: `dist/PocketSage/PocketSage.exe` (or `.app` on macOS)

## 🛠️ Optional Dependencies

Install extras for additional features:

```bash
# Auto-backup scheduler
pip install -e ".[scheduler]"

# CSV auto-import watcher
pip install -e ".[watcher]"

# All extras
pip install -e ".[dev,scheduler,watcher]"
```

## 📖 Architecture

- **Frontend**: Flet (Flutter-based Python UI framework)
- **Database**: SQLite (SQLModel ORM, SQLAlchemy 2.0)
- **Charts**: Matplotlib with accessible color palettes
- **Data**: Pandas for CSV processing
- **Security**: Argon2 password hashing, optional SQLCipher encryption
- **Logging**: Structured JSON logs with rotation (10MB max, 5 backups)

### Project Structure
```
pocketsage/
├── src/pocketsage/
│   ├── models/          # SQLModel ORM definitions
│   ├── services/        # Business logic
│   ├── infra/           # Repositories (data access)
│   ├── desktop/         # Flet UI views
│   ├── config.py        # Configuration
│   ├── logging_config.py # Structured logging
│   └── scheduler.py     # Background tasks
├── tests/               # Pytest test suite
├── scripts/             # Build and utility scripts
└── instance/            # Local data directory (gitignored)
```

## 🐛 Troubleshooting

### Common Issues

**Import Error: ModuleNotFoundError**
```bash
# Ensure package is installed in development mode
pip install -e .
```

**Database Locked Error**
```bash
# Stop any running instances
pkill -f run_desktop.py

# Or delete lock file
rm instance/pocketsage.db-wal instance/pocketsage.db-shm
```

**Charts Not Displaying**
- Ensure matplotlib is installed: `pip install matplotlib`
- Check `instance/logs/pocketsage.log` for errors

**Scheduler Not Working**
```bash
# Install scheduler extra
pip install -e ".[scheduler]"

# Enable in Settings: "auto_backup_enabled" = true
```

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest`)
4. Format code (`black .` and `ruff check --fix .`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Flet](https://flet.dev/) for cross-platform UI
- Inspired by HomeBank, GnuCash, Mint, and YNAB
- Colorblind-friendly palettes from Paul Tol's designs

## 📬 Support

- **Issues**: [GitHub Issues](https://github.com/Blood-Dawn/pocketsage/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Blood-Dawn/pocketsage/discussions)
- **Docs**: See `DEV_NOTES.md` for developer documentation

---

**Made with ❤️ for privacy-conscious personal finance tracking**
