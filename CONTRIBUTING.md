# Contributing

PocketSage uses the Campus Board pattern: Framework Owner seeds scaffolding + TODO markers, teammates land implementations.

## Ground Rules
- Target Python **3.11**.
- Keep business logic behind service/repository abstractions.
- Preserve `# TODO(@assignee)` comments; update acceptance criteria if scope changes.
- New routes require matching tests (skip allowed until backend ready).
- Install tooling: `pip install -e ".[dev]"` then `pre-commit install`.

## Workflow
1. Branch naming: `feature/<slug>`, `fix/<slug>`, or `docs/<slug>`.
2. Run `make lint` and `make test` before pushing.
3. Update docs (`README.md`, `docs/`, `TODO.md`) whenever functionality shifts.
4. Pull Request checklist:
	- Reference addressed TODO items.
	- Describe manual/automated verification (screenshots for UI changes).
	- Keep diff <= 300 LOC when possible; split otherwise.

## Commit Style
- Use concise conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
- Squash merges allowed; ensure final message keeps context.

## Security & Privacy
- No external API calls without Framework Owner approval.
- Keep secrets in `.env`; never commit actual keys.
- Document SQLCipher key handling steps in any PR enabling encryption.
