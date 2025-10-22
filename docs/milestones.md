# PocketSage Milestones

This roadmap distills the outstanding work in [`TODO.md`](../TODO.md) into a sequence of deliverable-oriented milestones. Each milestone is organized around the functional areas already called out in the backlog so squads can plan in parallel while still converging on a coherent release timeline.

## Milestone 1: Production-Ready Core

**Objective:** Ship a hardened foundation that can safely run in a managed production environment.

**Key Deliverables**
- Fail-fast configuration defaults for `BaseConfig` and encrypted SQLCipher handshakes.
- Documented migration workflow with Alembic bootstrap guidance.
- Structured logging (JSON) with rotation to support operations visibility.
- Background job scheduler wired for nightly or administrative jobs.

**Relevant TODO Items**
- `Configuration & Infrastructure` backlog items owned by `@ops-team`.
- Scheduler integration tasks under `Services & Integrations` (watcher bootstrap).

**Dependencies & Notes**
- Requires coordination with operations for secret management.
- Logging format should be agreed upon with analytics/observability stakeholders before implementation.

## Milestone 2: Ledger Experience Improvements

**Objective:** Deliver end-to-end ledger functionality suitable for day-to-day budgeting and spend tracking.

**Key Deliverables**
- SQLModel repository with pagination and filtering for transactions.
- Ledger entry form validation and optimistic locking on updates.
- Category management CRUD UI and rollup summaries (income, expense, cashflow).
- Matplotlib spending chart and integration into the ledger template.

**Relevant TODO Items**
- Entire `Ledger - Jennifer Ginther` section.
- Reporting tasks (`build_spending_chart`, `export_spending_png`).
- Import persistence to ensure ledger reflects CSV ingestion outputs.

**Dependencies & Notes**
- Requires portfolio import persistence to surface imported transactions.
- Coordinate color palette and chart exports with design/analytics teams.

## Milestone 3: Habits & Debts Engagement

**Objective:** Expand habit tracking and debt payoff tooling to drive user retention.

**Key Deliverables**
- Habit repository with streak recalculation and validated form flows.
- Visualization of weekly/monthly habit completion (heatmaps) and reminder options.
- Liabilities repository with payoff schedules plus snowball/avalanche calculators.
- Payoff timeline chart, payment reconciliation, and debt-free date projections in the UI (current `/liabilities/` view still shows a TODO placeholder).

**Relevant TODO Items**
- `Habits - Dossell Sinclair` backlog items.
- `Liabilities & Debts - Vedell Jones` backlog items.

**Dependencies & Notes**
- Heatmap visualizations may reuse charting infrastructure from ledger work.
- Reminder delivery requires coordination with notifications/integrations.

## Milestone 4: Import & Analytics Reliability

**Objective:** Ensure data ingestion, reports, and background automation run reliably at scale.

**Key Deliverables**
- Idempotent transaction upserts with external ID matching.
- Column auto-detection and mapping suggestions for CSV imports.
- Watchdog observer with debounce/retry for filesystem events.
- Rolling cash flow computation in budgeting services.
- Persistence path and QA coverage for CSV imports into portfolio and ledger.

**Relevant TODO Items**
- `Services & Integrations` backlog items (imports, watcher, analytics, QA).

**Dependencies & Notes**
- Must be sequenced after Milestone 2 to validate ledger integration scenarios.
- Requires QA fixtures and temporary DB setup for automated testing.

## Milestone 5: Admin & Operations Enhancements *(Optional Follow-up)*

**Objective:** After core releases, continue refining admin flows and operational tooling based on feedback.

**Key Deliverables**
- Re-assess completed admin tasks for polish opportunities.
- Extend scheduler-backed jobs to cover new maintenance routines.
- Evaluate additional monitoring hooks or alerts.

**Relevant TODO Items**
- All `Admin & Operations` items are marked complete; revisit as needed once new functionality ships.

**Dependencies & Notes**
- Only commence after the preceding milestones to prevent resource contention with core feature work.

---

Each milestone should result in a deployable increment. Squads can break down the backlog within the milestone into sprint-sized deliverables while tracking cross-team dependencies noted above.
