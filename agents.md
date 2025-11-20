# PocketSage Agents Brief

Desktop-only guide for PocketSage. Use this as the working source for architecture, operations, testing, design, roadmap, and release management now that the Flask/web stack has been removed.

## Product & Purpose
- Offline-first personal finance and habit tracker with ledger, budgets, habits, debts, portfolio, and admin/backup tooling.
- Built on Python 3.11, Flet for the desktop UI, SQLModel over SQLite with an optional SQLCipher toggle, Matplotlib for charts/exports.
- No external APIs or telemetry; all data lives locally under `instance/` by default, with SQLCipher enablement planned via environment flags.

## Architecture Snapshot
- Desktop entrypoint: `run_desktop.py` -> `desktop/app.py` with navigation rail and views for dashboard, ledger, budgets, habits, debts, portfolio, reports, settings. `desktop/context.py` wires repositories via `infra/database.py` and `infra/repositories` into an `AppContext` used by the Router + views.
- Persistence: SQLModel tables for Account, Category, Budget/BudgetLine, Transaction, Habit/HabitEntry, Liability, Holding, AppSetting. Relationships include Transaction -> Category, Budget -> BudgetLine, Habit -> HabitEntry. Holding <-> Account mapping is still broken and needs correction.
- Services: budgeting (NotImplemented stubs), debts payoff calculators, CSV import/export scaffolding, reporting/chart generation placeholders, optional filesystem watcher, simple in-memory job runner, and desktop-friendly admin tasks in `services/admin_tasks.py` (demo seed/export/retention).
- Layering: domain protocols and services, infra repositories + database/session factory, `AppContext` dependency container, router-based views (`/dashboard`, `/ledger`, `/budgets`, `/habits`, `/debts`, `/portfolio`, `/reports`, `/settings`), reusable components (dialogs, charts, widgets).

## Project Structure & Entry Points
- Root entrypoint: `run_desktop.py`. Make targets: `setup`, `dev`, `test`, `lint`, `package`, `demo-seed`. Helper scripts live under `scripts/` (desktop builds, demo seed, CSV samples).
- Key directories: `src/pocketsage/` (config, models, services including `admin_tasks`, desktop UI, domain, infra repos), `docs/` (architecture/runbooks/QA/testing/design), `tests/` (pytest suite), `notes/` (roadmap, current state), `scripts/` (seed/build helpers).

## Run Mode & Quickstart
- Desktop (Flet): create venv, `pip install -e ".[dev]"`, copy `.env`, run `python run_desktop.py`. Shortcuts: `Ctrl+N` new transaction, `Ctrl+Shift+H` new habit, `Ctrl+1..7` navigation, quick actions in the app bar.
- Demo seed: `make demo-seed` or `python scripts/seed_demo.py` (idempotent upserts for categories, accounts, transactions, habits, liabilities, and a simple budget) powered by `services/admin_tasks.py`.
- Packaging: `make package` runs `flet pack run_desktop.py`; platform scripts `bash scripts/build_desktop.sh` (Linux/macOS) or `scripts\\build_desktop.bat` (Windows) emit binaries to `dist/`.

## Configuration & Data Handling
- Environment prefix `POCKETSAGE_`. Key flags: `POCKETSAGE_DATA_DIR` (defaults `instance/`, auto-created), `POCKETSAGE_DATABASE_URL` (override), `POCKETSAGE_USE_SQLCIPHER` / `POCKETSAGE_SQLCIPHER_KEY` (future SQLCipher handshake), `POCKETSAGE_SECRET_KEY` retained for forward compatibility.
- `BaseConfig._build_sqlite_url` switches to SQLCipher-style URI when enabled; `sqlalchemy_engine_options` always disables `check_same_thread` and toggles `uri=True` + placeholder `execution_options` for SQLCipher mode.
- `_resolve_data_dir` eagerly creates the resolved path; use this location for DB files, backups, and exports. Respect permissions when overriding the path.
- Privacy/offline: no network calls; data local unless exports are shared manually.

## Admin, Ops & Security Guardrails
- Admin tasks live in `services/admin_tasks.py`: `run_demo_seed(session_factory)` and `run_export(output_dir, session_factory)` with `EXPORT_RETENTION = 5`. Desktop Settings/Reports screens call these helpers directly.
- Export retention: keeps five most recent archives; adjust constant if longer history needed, mindful of disk usage.
- Secure directories: `_ensure_secure_directory` creates staging/output paths and best-effort `chmod 0700`; on Windows/unsupported FS, permission changes are skipped; use native ACLs. Troubleshoot by validating ownership/permissions, parents, recreating directories, and reviewing logs.

## Runbooks & Extras
- Installation extras: `dev` extra installs formatting/linting/testing/pre-commit; `watcher` extra installs `watchdog` for filesystem observer workflows.
- Demo script focus: highlight offline-first design, SQLCipher toggle readiness, ledger/habits/liabilities/portfolio/admin flows from the desktop shell, and packaged binary parity.

## Testing & QA
- Tooling: pytest, ruff, black, bandit, safety; CI runs tests (Py3.11/3.12), lint, security, build check, coverage upload (target 40%+; module goals higher), with pip caching and parallel pytest via xdist.
- Commands: `pytest`, `pytest --cov=src/pocketsage --cov-report=term-missing`, `pytest -n auto`, `pytest -m "not slow"`, pattern filters via `-k`. Coverage HTML via `--cov-report=html`.
- Fixtures (from `tests/README.md`/`conftest.py`): `db_engine`, `db_session`, `session_factory`, factories for categories/accounts/transactions/liabilities/habits/budgets/holdings, seed data fixtures, `assert_float_equal` for money tolerance.
- Best practices: use factories over manual construction, test one behavior per test, descriptive names, mark slow/integration, use tolerance for floats.
- Coverage targets: domain logic 80%+, repositories 75%+, CSV import/export 70%+, overall 60%+ baseline; gaps include budgeting service stubs, CSV export/charts, watcher integration, route smoke tests removed with web stack, and fuller desktop feature coverage.
- Manual QA: verify desktop navigation shortcuts and placeholders; portfolio/debts visuals remain stubbed.
- Testing infrastructure summary: extensive suites for debts (snowball/avalanche, freed minimum rollover), habits (streaks, upsert), CSV import (mapping, validation, UTF-8, idempotency), money representation (float vs Decimal), integration workflows, repository CRUD/filtering. CI workflow defined in `.github/workflows/ci.yml` with lint/security/build steps. Remaining work: budgeting variance, CSV export PNGs, watcher flows, desktop route smoke polish once views mature.

## Contributor Workflow & Standards
- Ground rules: target Python 3.11; keep business logic behind services/repos; preserve `# TODO(@assignee)` markers; install dev tooling and `pre-commit`.
- Workflow: branch naming `feature|fix|docs/<slug>`; run `make lint` and `make test` (or `ruff check .`, `black --check .`) before push; update README/docs/TODO when scope changes; PRs should reference TODOs, include verification notes/screenshots, keep diffs <= 300 LOC when possible.
- Commit style: concise conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`); squash merges allowed while retaining context.
- Security/privacy: no external APIs without approval; secrets stay in `.env`; document SQLCipher handling in any related PRs.

## Demo & Narrative Aids
- Preconditions: Python 3.11, `pip install -e ".[dev]"`; watcher extra optional via `pip install -e ".[watcher]"`.
- Story beats: launch desktop app (`make dev` or packaged binary), highlight offline/SQLCipher readiness; tour ledger placeholders and planned Matplotlib charts; habit toggle actions; debt snowball/avalanche plans and timeline chart TODO; portfolio CSV sample at `scripts/csv_samples/portfolio.csv`; admin seed/export buttons tied to `services/admin_tasks` helpers.
- Follow-ups: finish repo implementations, chart rendering + CSV idempotency, watcher bootstrap/debounce, admin polish monitoring.

## Roadmap, Status & Backlog
- Current state (2025-11-19): Holding <-> Account mapper error blocks DB-backed flows/tests; budgeting service unimplemented; debt payoff mishandles freed minimum rollover and tiny payments; habit streak logic failing; admin/export flows now desktop-only but still need UX polish; desktop views are mostly static with limited CRUD/filters; float money risk.
- Feature status: ledger repos CRUD/filters but limited validation/pagination and no desktop CSV/import UI; budgets CRUD but no calculations; habits streak helpers fail tests; debts summary helpers exist but strategy logic flawed; portfolio repos exist but mapping bug blocks flows; admin seed/export available via services; desktop lacks filters/CSV/charts/admin wiring.
- TODO backlog with owners (see `TODO.md`): ops config hardening (secret key fail-fast, SQLCipher handshake, Alembic, logging, scheduler); ledger validation/pagination/charts; habits forms/heatmaps/reminders/archival; debts repos/calculators/charts/payments; imports idempotent upserts and watcher debounce; reports spending charts; analytics rolling cashflow; QA DB-backed import tests; desktop budgets/portfolio/settings wiring; testing to remove skips.
- Roadmap phases (notes/ROADMAP): Phase 1 fix ORM/shared DB/money handling; Phase 2 implement budgeting/debt/habit correctness; Phase 3 harden repos/import/export/seeds; Phase 4 admin/backups; Phase 5 desktop shell polish; Phase 6 desktop feature screens; Phase 7 tests/CI/handoff.
- Milestones: (1) Production-ready core (config, migrations, logging, scheduler); (2) Ledger improvements (pagination, validation, categories, charts, imports); (3) Habits & debts engagement (streaks, heatmaps/reminders, payoff projections); (4) Import & analytics reliability (idempotent upserts, mapping suggestions, watcher debounce, rolling cashflow, portfolio/ledger persistence + QA); (5) Admin/ops enhancements (post-core polish).

## Release Management
- Release notes template: version/tag, date, packaging status, highlights, known issues/TODOs, next steps, stakeholder actions; example entry provided in `docs/release_notes.md`.
- Release checklist: ensure clean tree, install deps, run `make package` (flet pack), verify executable under `dist/` launches, confirm data dir handling, update release notes, communicate via agreed channels.

## UI & Design Direction
- Inspiration brief references Mint (legacy dashboard/nav/alert ribbon), Monarch Money (gradient hero, trial CTA, testimonials, serif+sans pairing), Lunch Money (dense ledger, nav rail, hover interactions), Tiller (spreadsheet preview, dual CTA stack, integration badges).
- Design principles: information hierarchy first (large numeric typography + whitespace), restrained palette with focused accent, card-based summaries with drill-down paths, sticky CTAs with secondary links, trust via transparency (badges, alerts, testimonials).
- Asset policy: keep repo lean - store annotated visuals in design tools, document links/callouts in `docs/ui_inspiration.md`; prefer SVG/Markdown if lightweight assets are needed.
- Team share questions to align: confirm hierarchy principle, choose cooler vs warmer accent palette (or dual modes), gather any additional interaction patterns before locking navigation wireframes.

## Troubleshooting Cheatsheet
- SQLCipher URL issues: verify `POCKETSAGE_USE_SQLCIPHER=true`, inspect engine options for `uri=True`, supply key via `POCKETSAGE_SQLCIPHER_KEY` once handshake lands.
- Test hiccups: ensure dev deps installed, run from repo root, use parallel pytest for speed, mark/skip slow tests as needed, confirm `pythonpath` config in `pyproject.toml`.
- Export permission failures: validate directory ownership/permissions, recreate directories to reapply secure defaults, check parent traversal rights, review logs for `PermissionError`/`OSError`.

## Data Seeding, Admin Tasks, and Retention
- Demo seed and export wired through `services/admin_tasks.py`; exports bundle CSV + PNG artifacts, retained to five latest archives. Ensure target directories writable and secured; adjust retention constant if policy changes.

## Documentation Pointers (source coverage)
- README: stack snapshot, quickstart (desktop), packaging commands, make targets, desktop shortcuts/features/architecture/benefits, configuration flags, privacy, folder map, next steps, demo seeding.
- CONTRIBUTING: ground rules, workflow, lint/test commands, commit style, testing requirements/coverage expectations, security/privacy reminders.
- TODO: backlog by squad for configuration, ledger, habits, debts, portfolio, services/imports/reports, admin/ops, desktop UI, testing.
- tests/README: test suite overview, commands, fixtures, examples, coverage goals, CI, troubleshooting.
- notes/CURRENT_STATE + notes/ROADMAP: current health, risks, planned phases.
- docs (architecture, system_overview, FLET_ARCHITECTURE, packaging, configuration, troubleshooting, ops_guide, ops_runbook, admin_operations, runbook, demo_script, milestones, manual_test_plan, QA roadmap, testing_infrastructure, release_notes, release_checklist, ui_inspiration, communication/ui_brief_share, assets README): content integrated above.
