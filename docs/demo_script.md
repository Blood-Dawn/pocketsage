# PocketSage Demo Runbook (WIP)

## Quick 5-Min CEN4010 Demo
1. Launch: `python run_desktop.py` (local profile auto-loads).
2. Toggle **Admin mode** in the top bar → Run Demo Seed → confirm snackbar.
3. Ledger: add a transaction, filter by category, export CSV (note path in snackbar).
4. Habits: add habit, toggle completion once.
5. Debts: open projections (snowball/avalanche) for seeded liabilities.
6. Portfolio: view allocation chart; import CSV if desired.
7. Reports: open spending/debt summaries; trigger a Download.
8. Settings/Admin: Backup database; confirm path shown.

## Preconditions
- Python 3.11 installed
- `pip install -e ".[dev]"`

### Optional Tooling
- **Watcher extra** – install with `pip install -e ".[watcher]"` to enable filesystem observers that support future watchdog-based background import workflows outlined in the README.

## Smoke / Sanity Checklist
- Launch the desktop app (`make dev` or `python run_desktop.py`) and open the Habits view from the navigation rail.
  - Confirm placeholder copy or streak UI renders without errors.
  - If the UI has progressed past placeholders, record the new behavior in the team log so this checklist and related docs stay accurate.
- Skim other desktop views (Ledger, Debts, Portfolio, Settings, Reports) to ensure they load without crashes.

## Suggested Narrative
1. **App Launch**
   - Run `make dev` (or `python run_desktop.py`).
   - To showcase the packaged build, first run `make package`, then execute the binary from `dist/` (`PocketSage.exe` on Windows, `PocketSage.app` on macOS, or `dist/PocketSage/PocketSage` on Linux).
   - Mention offline-first architecture and SQLCipher toggle.
2. **Ledger Tour**
   - Show ledger list placeholder; describe upcoming rollups and Matplotlib charts.
   - Capture a screenshot or note any placeholder changes signaling upcoming work.
3. **Habits Tracker**
   - Highlight streak logic TODOs and planned toggle actions.
4. **Liabilities Payoff**
   - Discuss snowball/avalanche services and planned timeline chart.
5. **Portfolio Upload**
   - Reference `scripts/csv_samples/portfolio.csv`; describe CSV mapping helper.
6. **Admin Actions**
   - Show Settings/Reports actions that call `services/admin_tasks.py` seed/export helpers.

## Follow-up Talking Points
- Emphasize SQLCipher optional mode (`POCKETSAGE_USE_SQLCIPHER=true`).
- Highlight pre-commit, tests, and `flet pack` packaging targets.
- Reinforce Campus Board TODO assignments for teammates.

## Test & QA Reminders
- The `make test` target is a thin wrapper that executes plain `pytest` with no extra arguments.
- You can also invoke tests directly by running `pytest` from the repository root to mirror CI behaviour.
- Several test modules are currently marked with `@pytest.mark.skip` placeholders; seeing `s`/`SKIPPED` entries in the output is expected until the related TODOs are implemented.

## TODO Risks for Demo
- Seeder exists but still depends on SQLModel mappings (Holding bug blocks portfolio flows).
- Charts and CSV imports pending.
- Some tests remain skipped or red; mention roadmap for coverage.

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
