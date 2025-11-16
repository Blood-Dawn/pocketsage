# PocketSage Demo Runbook (WIP)

## Preconditions
- Python 3.11 installed
- `pip install -e ".[dev]"`
- Optional: install `watchdog` extra for auto-import demo (`pip install -e ".[watcher]"`).

## Suggested Narrative
1. **App Launch**
   - Run `make dev` (Windows: `python run.py`).
   - To showcase the packaged build, first run `make package`, then execute the binary from `dist/PocketSage/` (`./PocketSage` on macOS/Linux or `PocketSage.exe` on Windows) which mirrors the `run.py` entry point.
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

## Portfolio Context Verification
- **Template compatibility:** `list_portfolio` supplies `holdings`, `total_value`, `allocation`, `upload_url`, and `export_url`, matching the variables referenced in `templates/portfolio/index.html`. No discrepancies were found between the view context keys and the template expectations.
- **Data population:** Holdings rows include the display-friendly fields (`quantity_display`, `avg_price_display`, `value_display`, `allocation_display`, `account`, `currency`) that the template renders. Allocation entries provide `symbol` and `percentage`, which back both the chart rows and the percentage labels. Upload and export buttons are wired to `portfolio.upload_portfolio` and `portfolio.export_holdings`, respectively.
- **Follow-up:** No remediation needed at this time. Revisit if the template or view contracts change so that feature teams can react quickly to any newly introduced mismatches.
