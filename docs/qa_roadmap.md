# QA Roadmap

## Navigation Coverage

**Goal:** Add a `test_desktop_routes` smoke test once the Flet views stabilize so navigation regressions are caught automatically.

**Acceptance Criteria:**
- Each desktop route (`/dashboard`, `/ledger`, `/budgets`, `/habits`, `/debts`, `/portfolio`, `/reports`, `/settings`) builds without raising exceptions.
- Navigation rail selections update the current view and route.
- Settings/Reports actions (demo seed/export) handle success/failure without crashing.
- Skip markers for desktop smoke tests removed and test added back into the continuous integration workflow.

**Next Steps:**
- Coordinate with the desktop squad to stabilize headings/copy before updating assertions.
- Add lightweight assertions (e.g., presence of key headings/controls) once views are fleshed out to increase coverage without introducing fragility.
