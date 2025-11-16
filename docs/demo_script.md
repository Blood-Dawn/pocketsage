# PocketSage Demo Runbook (WIP)

## Preconditions
- Python 3.11 installed
- `pip install -e ".[dev]"`
- Optional: install `watchdog` extra for auto-import demo (`pip install -e ".[watcher]"`).

## Smoke / Sanity Checklist
- Launch the dev server (`make dev` or `python run.py`) and load the Habits index at `http://127.0.0.1:5000/habits/`.
  - Confirm the placeholder copy "TODO(@habits-squad): render habits list with streak badges and toggle buttons." still renders.
  - If the UI has progressed past the placeholder, record the new behavior in the team log so this checklist and related docs stay accurate.
- Skim other blueprint index pages to ensure they load without template errors.

## Suggested Narrative
1. **App Launch**
   - Run `make dev` (Windows: `python run.py`).
   - To showcase the packaged build, first run `make package`, then execute the binary from `dist/PocketSage/` (`./PocketSage` on macOS/Linux or `PocketSage.exe` on Windows) which mirrors the `run.py` entry point.
   - Mention offline-first architecture and SQLCipher toggle.
2. **Ledger Tour**
   - Show placeholder ledger list; describe upcoming rollups and Matplotlib charts.
   - Load `/ledger/` to confirm the TODO banner remains visible; capture a screenshot or note any placeholder changes signaling upcoming work.
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

## Blueprint Routing Overview

PocketSage exposes its major feature areas via Flask blueprints. Use the following
reference when hitting routes during manual testing:

- **Home (`pocketsage.blueprints.home`)**
  - **Base path:** `/` (no blueprint `url_prefix`). Visiting `/` serves the landing
    page; Flask redirects `/` requests that omit the trailing slash as needed.
  - **Key routes:** `GET /`.
- **Admin (`pocketsage.blueprints.admin`)**
  - **Base path:** `/admin/` (`url_prefix="/admin"`; Flask enforces the trailing
    slash on the dashboard route defined as `@bp.get("/")`).
  - **Key routes:** `GET /admin/`, `POST /admin/seed-demo`, `POST /admin/export`,
    `GET /admin/export/download`, `GET /admin/jobs/<job_id>`.
- **Habits (`pocketsage.blueprints.habits`)**
  - **Base path:** `/habits/` (`url_prefix="/habits"`; expect trailing-slash
    redirects for the index route).
  - **Key routes:** `GET /habits/`, `GET /habits/new`,
    `POST /habits/<habit_id>/toggle`.
- **Ledger (`pocketsage.blueprints.ledger`)**
  - **Base path:** `/ledger/` (`url_prefix="/ledger"`; trailing slash enforced on
    the index route).
  - **Key routes:** `GET /ledger/`, `GET /ledger/new`, `POST /ledger/`,
    `GET /ledger/<transaction_id>/edit`, `POST /ledger/<transaction_id>`.
- **Liabilities (`pocketsage.blueprints.liabilities`)**
  - **Base path:** `/liabilities/` (`url_prefix="/liabilities"`; trailing slash
    enforced on the index route).
  - **Key routes:** `GET /liabilities/`, `GET /liabilities/new`,
    `POST /liabilities/<liability_id>/recalculate`.
- **Portfolio (`pocketsage.blueprints.portfolio`)**
  - **Base path:** `/portfolio/` (`url_prefix="/portfolio"`; trailing slash
    enforced on the holdings index).
  - **Key routes:** `GET /portfolio/`, `POST /portfolio/import`,
    `GET /portfolio/upload`, `GET /portfolio/export`.

All route decorators use Flask's default strict-slash behavior: define index
routes with `"/"` so Flask issues redirects for missing trailing slashes, while
subroutes such as `/export` or `/new` do not carry trailing slashes.
