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

## TODO Risks for Demo
- Seeder not implemented; manual DB state may be required.
- Charts and CSV imports pending.
- Tests currently skipped; mention roadmap for coverage.

## README Focus Follow-Up Tasks

### Replace repository protocols with SQLModel CRUD implementations
- **Owner:** @ledger-squad, @habits-squad, @debts-squad
- **Status:** Not started – repositories for ledger transactions and liabilities remain unchecked in `TODO.md`; habit persistence landed but additional CRUD wiring is still pending.
- **Next Action:** Implement the SQLModel repositories listed under the "Ledger", "Habits", and "Liabilities & Debts" sections of the backlog so services stop depending on protocol stubs.

### Implement Matplotlib chart rendering + CSV import idempotency
- **Owner:** @ledger-squad, @reports, @imports, @qa-team
- **Status:** In progress – chart hooks and CSV idempotent upserts are still open, though QA already has regression coverage marked complete.
- **Next Action:** Finish `build_spending_chart`/`export_spending_png` work and the import persistence/idempotent upsert tasks in "Services & Integrations" so ledger charts reflect reliable ingest results.

### Wire watchdog optional observer when extra installed
- **Owner:** @watcher
- **Status:** Not started – both watcher bootstrap and debounce/retry TODOs remain unchecked in the integrations backlog.
- **Next Action:** Implement the filesystem observer startup and stabilization tasks gated behind the `[watcher]` extra to complete the automation story highlighted in the README.

### Fill Admin tasks, seeding, and export flows
- **Owner:** @admin-squad, @framework-owner, @ops-team
- **Status:** Complete – the entire "Admin & Operations" section of `TODO.md` is checked off following seed/export automation and scheduler wiring.
- **Next Action:** Monitor for polish opportunities post-launch; no immediate backlog work is required beyond demo rehearsal.
