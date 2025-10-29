# QA Roadmap

## Route Rendering Coverage

**Goal:** Restore the `test_routes_render` smoke test once the UI templates are available so navigation regressions are caught automatically.

**Acceptance Criteria for Re-enabling `test_routes_render`:**
- Shared base layout and section-specific templates exist for each tracked route (`/`, `/ledger/`, `/ledger/new`, `/habits/`, `/habits/new`, `/liabilities/`, `/liabilities/new`, `/portfolio/`, `/portfolio/upload`, `/admin/`).
- Flask view functions render the correct template without raising `TemplateNotFound` or other server errors.
- Smoke test responses return HTTP 200 with non-empty HTML bodies that include a `<title>` element describing the page.
- Navigation links in the rendered templates allow users to reach the listed routes without manual URL entry (verified via template inspection or integration test).
- Skip marker in `tests/test_routes_smoke.py` removed and test added back into the continuous integration workflow.

**Next Steps:**
- Coordinate with the frontend squad delivering the templates to ensure selectors and copy are stable before updating assertions.
- Add lightweight assertions (e.g., `contains` checks on key headings) once templates are available to increase coverage without introducing fragility.
