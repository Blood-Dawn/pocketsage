# PocketSage TODOs

## Milestone Checklist
- [ ] Harden production configuration & secrets (Due: 2024-06-14) — owners: Ops Team — [#101](https://github.com/pocketsage/pocketsage/issues/101)
- [ ] Deliver ledger transaction MVP (Due: 2024-06-21) — owners: Ledger Squad — [#112](https://github.com/pocketsage/pocketsage/issues/112)
- [ ] Launch habit tracker streak improvements (Due: 2024-06-28) — owners: Habits Squad — [#121](https://github.com/pocketsage/pocketsage/issues/121)
- [ ] Publish debt payoff modeling toolkit (Due: 2024-07-12) — owners: Debts Squad — [#135](https://github.com/pocketsage/pocketsage/issues/135)

## Near Term (0–4 Weeks)
| Task | Owner | Target Date | Status | Tracker |
| --- | --- | --- | --- | --- |
| Harden `BaseConfig` so the app fails when `POCKETSAGE_SECRET_KEY` uses the default value | Ops Team | 2024-06-14 | Not Started | [#101](https://github.com/pocketsage/pocketsage/issues/101) |
| Implement SQLCipher key handshake (`PRAGMA key`) driven by `POCKETSAGE_SQLCIPHER_KEY` | Ops Team | 2024-06-17 | In Progress | [#102](https://github.com/pocketsage/pocketsage/issues/102) |
| Provide Alembic migration bootstrap scripts and document the workflow | Ops Team | 2024-06-19 | Not Started | [#103](https://github.com/pocketsage/pocketsage/issues/103) |
| Add structured logging config (JSON output + rotating file handler) | Ops Team | 2024-06-21 | Not Started | [#104](https://github.com/pocketsage/pocketsage/issues/104) |
| Wire a background job scheduler (e.g., APScheduler) for nightly tasks | Ops Team | 2024-06-24 | Not Started | [#105](https://github.com/pocketsage/pocketsage/issues/105) |
| Implement SQLModel repository for transactions with filtering and pagination | Ledger Squad | 2024-06-21 | In Progress | [#112](https://github.com/pocketsage/pocketsage/issues/112) |
| Build `LedgerEntryForm` validation using WTForms or Pydantic | Ledger Squad | 2024-06-24 | Not Started | [#113](https://github.com/pocketsage/pocketsage/issues/113) |
| Persist `HabitEntry` creation with streak recalculation via repository layer | Habits Squad | 2024-06-28 | Not Started | [#121](https://github.com/pocketsage/pocketsage/issues/121) |

## Mid Term (1–2 Months)
| Task | Owner | Target Date | Status | Tracker |
| --- | --- | --- | --- | --- |
| Add category management UI and CRUD endpoints for ledger entries | Ledger Squad | 2024-07-05 | Not Started | [#114](https://github.com/pocketsage/pocketsage/issues/114) |
| Implement ledger rollup summaries (income vs. expense, net cashflow) | Ledger Squad | 2024-07-05 | Not Started | [#115](https://github.com/pocketsage/pocketsage/issues/115) |
| Hook Matplotlib spending chart into ledger template | Ledger Squad | 2024-07-08 | Blocked (awaiting rollup API) | [#116](https://github.com/pocketsage/pocketsage/issues/116) |
| Ensure optimistic locking on transaction updates | Ledger Squad | 2024-07-12 | Not Started | [#117](https://github.com/pocketsage/pocketsage/issues/117) |
| Add weekly/monthly habit heatmap visualization | Habits Squad | 2024-07-12 | Not Started | [#123](https://github.com/pocketsage/pocketsage/issues/123) |
| Introduce habit reminders (local notification or email toggle) | Habits Squad | 2024-07-19 | Not Started | [#124](https://github.com/pocketsage/pocketsage/issues/124) |
| Support habit archival and reactivation flows | Habits Squad | 2024-07-26 | Not Started | [#125](https://github.com/pocketsage/pocketsage/issues/125) |
| Implement liabilities repository with CRUD and payoff schedule storage | Debts Squad | 2024-07-05 | In Progress | [#131](https://github.com/pocketsage/pocketsage/issues/131) |
| Finish snowball and avalanche payoff calculators with deterministic ordering | Debts Squad | 2024-07-12 | Not Started | [#132](https://github.com/pocketsage/pocketsage/issues/132) |
| Generate payoff timeline chart PNG via `services.reports` | Debts Squad | 2024-07-19 | Not Started | [#133](https://github.com/pocketsage/pocketsage/issues/133) |
| Record actual payments and reconcile balances | Debts Squad | 2024-07-26 | Not Started | [#134](https://github.com/pocketsage/pocketsage/issues/134) |
| Surface debt-free date projections in UI | Debts Squad | 2024-07-31 | Not Started | [#135](https://github.com/pocketsage/pocketsage/issues/135) |

## Backlog (2+ Months / Nice-to-Have)
| Task | Owner | Target Date | Status | Tracker |
| --- | --- | --- | --- | --- |
| Implement idempotent `upsert_transactions` with `external_id` matching | Imports Team | 2024-08-09 | Not Started | [#141](https://github.com/pocketsage/pocketsage/issues/141) |
| Add column auto-detection and mapping suggestions in import flow | Imports Team | 2024-08-16 | Not Started | [#142](https://github.com/pocketsage/pocketsage/issues/142) |
| Start watchdog observer on app boot when watched folder configured | Watcher Team | 2024-08-16 | Not Started | [#143](https://github.com/pocketsage/pocketsage/issues/143) |
| Add debounce and retry logic for duplicate filesystem events | Watcher Team | 2024-08-23 | Not Started | [#144](https://github.com/pocketsage/pocketsage/issues/144) |
| Implement `build_spending_chart` with category color palette | Reports Team | 2024-08-23 | Not Started | [#145](https://github.com/pocketsage/pocketsage/issues/145) |
| Implement `export_spending_png` to persist charts via renderer protocol | Reports Team | 2024-08-30 | Not Started | [#146](https://github.com/pocketsage/pocketsage/issues/146) |
| Add rolling cash flow computation in `services.budgeting` | Analytics Team | 2024-09-06 | Not Started | [#147](https://github.com/pocketsage/pocketsage/issues/147) |
| Persist parsed imports through repository/session scope | Imports Team | 2024-09-13 | Not Started | [#148](https://github.com/pocketsage/pocketsage/issues/148) |
| Add DB-backed tests for import persistence and idempotency | QA Team | 2024-09-13 | Not Started | [#149](https://github.com/pocketsage/pocketsage/issues/149) |
| Wire upload form to accept CSV and call `import_csv.import_csv_file` | Portfolio Squad | 2024-05-17 | Done | [#201](https://github.com/pocketsage/pocketsage/issues/201) |
| Implement repository to persist holdings and allocation snapshots | Portfolio Squad | 2024-05-17 | Done | [#202](https://github.com/pocketsage/pocketsage/issues/202) |
| Render allocation donut chart via Matplotlib | Portfolio Squad | 2024-05-17 | Done | [#203](https://github.com/pocketsage/pocketsage/issues/203) |
| Add gain/loss table with cost basis calculations | Portfolio Squad | 2024-05-17 | Done | [#204](https://github.com/pocketsage/pocketsage/issues/204) |
| Provide export of holdings to CSV | Portfolio Squad | 2024-05-17 | Done | [#205](https://github.com/pocketsage/pocketsage/issues/205) |
| Support account and currency columns in CSV imports with mapping suggestions | Imports Team | 2024-05-24 | Done | [#206](https://github.com/pocketsage/pocketsage/issues/206) |
| Persist portfolio-imported transactions into the ledger repository | Ledger Squad | 2024-05-24 | Done | [#207](https://github.com/pocketsage/pocketsage/issues/207) |
| Update portfolio templates to show upload progress, validation messaging, and export/download links | Frontend Team | 2024-05-24 | Done | [#208](https://github.com/pocketsage/pocketsage/issues/208) |
| Add idempotency and end-to-end tests for portfolio CSV import through allocation snapshot | QA Team | 2024-05-24 | Done | [#209](https://github.com/pocketsage/pocketsage/issues/209) |
| Implement `run_demo_seed` to populate all tables with sample data | Admin Squad | 2024-05-03 | Done | [#211](https://github.com/pocketsage/pocketsage/issues/211) |
| Implement `run_export` to bundle CSV and PNG artifacts into a zip | Admin Squad | 2024-05-03 | Done | [#212](https://github.com/pocketsage/pocketsage/issues/212) |
| Add admin UI feedback (progress indicators, error handling) | Admin Squad | 2024-05-10 | Done | [#213](https://github.com/pocketsage/pocketsage/issues/213) |
| Create CLI commands (e.g., `flask pocketsage seed`) | Admin Squad | 2024-05-10 | Done | [#214](https://github.com/pocketsage/pocketsage/issues/214) |
| Update admin templates to show export progress, messaging, and download links | Frontend Team | 2024-05-10 | Done | [#215](https://github.com/pocketsage/pocketsage/issues/215) |
| Implement exports retention/rotation and permissions for `instance/exports` | Ops Team | 2024-05-17 | Done | [#216](https://github.com/pocketsage/pocketsage/issues/216) |
| Register background worker/scheduler and expose job-status API | Framework Owner | 2024-05-17 | Done | [#217](https://github.com/pocketsage/pocketsage/issues/217) |
| Add integration tests for admin export, seed confirmation, and background tasks | QA Team | 2024-05-17 | Done | [#218](https://github.com/pocketsage/pocketsage/issues/218) |
| Replace skipped tests with golden datasets for budgeting/debts services | QA Team | 2024-04-26 | Done | [#221](https://github.com/pocketsage/pocketsage/issues/221) |
| Add route smoke tests verifying template context variables | QA Team | 2024-04-26 | Done | [#222](https://github.com/pocketsage/pocketsage/issues/222) |
| Add CSV import idempotency regression tests using fixtures | QA Team | 2024-04-26 | Done | [#223](https://github.com/pocketsage/pocketsage/issues/223) |
| Configure CI workflow running lint, tests, and packaging dry run | QA Team | 2024-04-26 | Done | [#224](https://github.com/pocketsage/pocketsage/issues/224) |

## Weekly Review Log
> Update every Friday with current status, risks, and notable wins to keep momentum visible.

| Review Date | Highlights | Risks / Blockers | Next Steps |
| --- | --- | --- | --- |
| 2024-05-31 | Kick-off review. Configuration hardening queued; ledger repository work underway. | Matplotlib spending chart blocked on rollup API. | Confirm Ops timelines; unblock chart once summaries API lands. |

## Notes
- Owners correspond to cross-functional squads; adjust to specific individuals as assignments firm up.
- Target dates reflect current planning assumptions and should be revisited during the weekly review.
- Status options: Not Started, In Progress, Blocked, Done (include completion date in Highlights when relevant).
