# PocketSage Framework Owner Audit

## Architecture
- **Strengths**
  - Flask app factory already exists with minimal configuration.
  - Simple blueprint registration pattern keeps routing centralized.
- **Gaps / Replacements**
  - Single `routes.py` blueprint prevents modular feature ownership.
  - Configuration loading is ad-hoc; no environment layering or secrets handling.
  - App package name `app` conflicts with expected campus board structure; will be replaced with `pocketsage/` package.

## Data Model
- **Strengths**
  - SQLModel already in use for basic tables.
- **Gaps / Replacements**
  - Models lack relationships, indices, and validation.
  - Missing key domain entities (budgets, categories, habit entries, settings).
  - Seed script tightly coupled to legacy schema; will be superseded.

## Security
- **Strengths**
  - Uses `.env` convention for secrets.
- **Gaps / Replacements**
  - No cipher toggle or key management guidance.
  - No session or CSRF hardening.
  - Static secret fallback shipped in code; will be replaced with config enforcement.

## Performance
- **Strengths**
  - Lightweight dependencies only.
- **Gaps / Replacements**
  - No indexing or batching strategies.
  - Portfolio and ledger computations done inline without caching or background jobs.

## Developer Experience (DX)
- **Strengths**
  - Requirements file present with pinned versions.
- **Gaps / Replacements**
  - No task runner, formatting hooks, or contributor docs.
  - No project-wide README scaffolding or architecture notes.
  - `run.py` imports legacy app package; will be updated.

## Testability
- **Strengths**
  - Pytest dependency in place.
- **Gaps / Replacements**
  - Single smoke test only; lacks fixtures and module-level coverage.
  - No strategy for deterministic data seeding in tests.

## Packaging
- **Strengths**
  - None identified beyond simple run script.
- **Gaps / Replacements**
  - No PyInstaller spec, packaging docs, or release process.
  - No offline assets bundling guidance.

## TODO Risks & Follow-ups
- Replace legacy `app/` module with structured `pocketsage/` package aligned to campus board conventions.
- Rebuild templates and static assets to reflect new blueprint boundaries.
- Migrate seed/demo scripts to new models.
- Establish SQLCipher toggle and document operations.
- Expand testing surface to budgeting, debts, CSV import, and route smoke coverage.
