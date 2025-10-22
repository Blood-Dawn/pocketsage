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
   - If `make` is unavailable, run the lint commands directly:

     ```sh
     ruff check .
     black --check .
     ```

     Both commands exit with `0` when the codebase satisfies the configured rules.
     `ruff check .` returns a non-zero exit code when it finds lint violations; run
     `ruff check . --fix` to apply automatic fixes or address the reported issues
     manually. `black --check .` exits with `1` when files need formatting; resolve
     by running `black .` to rewrite the files, then re-run the check.
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
