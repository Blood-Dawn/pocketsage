# PocketSage - Offline Desktop Finance + Habits

PocketSage is a **desktop-only**, offline personal finance and habit tracker. Launch the app and start tracking immediately—no login, no network, and your data stays local.

## What You Can Do
- **Ledger**: Add/edit transactions with categories, filters, CSV import/export, monthly summaries, budgets, and spending charts.
- **Habits**: Track daily habits with streaks, heatmap history, optional reminders, and archive/reactivate controls.
- **Debts**: Manage liabilities, record payments, and view snowball/avalanche payoff schedules with payoff charts and projected interest.
- **Portfolio**: Manage holdings, import/export CSV, and see allocation plus gain/loss.
- **Reports**: View aggregated charts (spending, budget usage, habits, debt payoff, portfolio allocation) and download bundles.
- **Settings/Admin**: Theme toggle, data directory info, demo seed/reset, backup/export/restore with retention.

## Quickstart
1) Install Python 3.11 and create a virtualenv.  
2) `pip install -e ".[dev]"`  
3) `python run_desktop.py` (shortcuts: `Ctrl+N` new transaction, `Ctrl+Shift+H` new habit, `Ctrl+1..7` navigation).  
4) Optional: seed demo data from Settings/Admin.

## Data & Privacy
- Offline-first: no telemetry or external APIs. Data lives under `POCKETSAGE_DATA_DIR` (default `instance/`).
- Backups/exports under `instance/exports`; restore from Settings/Admin. Retention keeps the last five archives.
- Encryption readiness: SQLCipher flags exist for future use; current builds use SQLite by default.

## CSV Formats
- **Ledger import**: `date,amount,memo,category,account,currency,transaction_id` (idempotent by `transaction_id` or hash).  
- **Portfolio import**: `symbol,shares,price,account,market_price,as_of,currency` (upsert by symbol+account).  
Exports mirror these schemas for easy round-trips.

## More Info
Developer setup, packaging, and architecture notes live in `DEV_NOTES.md`.
