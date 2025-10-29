# PocketSage Demo Runbook (WIP)

## Preconditions
- Python 3.11 installed
- `pip install -e ".[dev]"`

### Optional Tooling
- **Watcher extra** – install with `pip install -e ".[watcher]"` to enable filesystem observers that support future watchdog-based background import workflows outlined in the README.

## Suggested Narrative
1. **App Launch**
   - Run `make dev` (Windows: `python run.py`).
   - Mention offline-first architecture and SQLCipher toggle.
2. **Ledger Tour**
   - Show placeholder ledger list; describe upcoming rollups and Matplotlib charts.
3. **Habits Tracker**
   - Toggle action posts to `/habits/<id>/toggle`; highlight streak logic TODOs.
4. **Liabilities Payoff**
   - Discuss snowball/avalanche services and planned timeline chart.
5. **Portfolio Upload**
   - Reference `scripts/csv_samples/portfolio.csv`; describe CSV mapping helper.
6. **Admin Actions**
   - Show seed/export buttons calling `tasks.py` stubs.

## Follow-up Talking Points
- Emphasize SQLCipher optional mode (`POCKETSAGE_USE_SQLCIPHER=true`).
- Highlight pre-commit, tests, and PyInstaller packaging targets.
- Reinforce Campus Board TODO assignments for teammates.

## TODO Risks for Demo
- Seeder not implemented; manual DB state may be required.
- Charts and CSV imports pending.
- Tests currently skipped; mention roadmap for coverage.
