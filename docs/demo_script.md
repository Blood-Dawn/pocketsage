# PocketSage Demo Runbook (WIP)

## Preconditions
- Python 3.11 installed
- `pip install -e ".[dev]"`
- Optional: install `watchdog` extra for auto-import demo (`pip install -e ".[watcher]"`).

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

## Test & QA Reminders
- The `make test` target is a thin wrapper that executes plain `pytest` with no extra arguments.
- You can also invoke tests directly by running `pytest` from the repository root to mirror CI behaviour.
- Several test modules are currently marked with `@pytest.mark.skip` placeholders; seeing `s`/`SKIPPED` entries in the output is expected until the related TODOs are implemented.

## TODO Risks for Demo
- Seeder not implemented; manual DB state may be required.
- Charts and CSV imports pending.
- Tests currently skipped; mention roadmap for coverage.
