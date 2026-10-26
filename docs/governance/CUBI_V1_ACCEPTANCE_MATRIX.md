# CUBI V1 Acceptance Matrix

- **Effective:** 2026-10-26
- **Repository:** `cubi-platform`
- **Branch / head at authoring:** `fix/resource-dependent-nondriving-leveling` @ `41564743` plus the uncommitted preview, Web E2E, workspace-fact and acceptance-matrix work described in [PROJECT_STATE_LEDGER.md](PROJECT_STATE_LEDGER.md)
- **Open PR / issue:** #1582 / #1517
- **Status vocabulary:** `implemented-and-verified`, `implemented-not-verified`, `partial`, `missing`, `blocked-external`

This matrix is an evidence index for the approved product scope, not a completion percentage. A name, class, menu or test file by itself does not justify **implemented-and-verified**. That status requires an identifiable current-tree code path, a test or runtime evidence attached to this branch, and a usable surface (UI and/or API) where the requirement is user-facing.

## Sources used

- [PRODUCT_SCOPE.md](../requirements/PRODUCT_SCOPE.md)
- [PRODUCT_COMPLETION_CONTROL.md](../PRODUCT_COMPLETION_CONTROL.md)
- [CUBI_MULTILINGUAL_AND_AI_PERMISSION_REQUIREMENTS.md](../requirements/CUBI_MULTILINGUAL_AND_AI_PERMISSION_REQUIREMENTS.md)
- [V1_MASTER_AUDIT_MATRIX.md](../V1_MASTER_AUDIT_MATRIX.md) (historical 2026-10-01 snapshot, used only as an evidence index)
- [PROJECT_STATE_LEDGER.md](PROJECT_STATE_LEDGER.md)
- Issue #1517, PR #1582
- Current-tree module, route, test and browser-E2E inspection on 2026-10-26

## External evidence limits (not invented)

- **`cubisite.xlsx` is not present** in the repository or accessible workspace. Official CUBISITE weights, scores and completion percentages are therefore unavailable. No weight, percentage or “Jalal 5” value is invented or inferred. This matrix is qualitative.
- **No external preview deployment exists.** The repository was checked and has no GitHub Pages site (`has_pages = false`), and no production or external preview deployment was performed. The real runnable preview is local (`apps/web` + WSGI + SQLite), documented in [FULL_STACK_PREVIEW.md](../preview/FULL_STACK_PREVIEW.md).
- **No production deployment, secret change or sensitive admin change** has been performed.
- PostgreSQL integration is exercised by the repository's PostgreSQL test modules and CI workflow; local execution of those tests requires the configured service and is recorded separately from SQLite results.

## Verification log

| Date | Evidence | Result |
|---|---|---|
| 2026-10-26 | `PYTHONPATH=src py -3 -m pytest -q` (full Python suite on the review-split branch, after typed capacity, calendar/project-creation, formula-authority, typed Jalali, layout-history and layout-concurrency fixes) | **2781 passed, 126 skipped, 2 warnings** (RD/AI-specific tests remain on PR #1582; the PostgreSQL layout-history twin skips without `P6_TEST_POSTGRES_DSN` and CI runs it) |
| 2026-10-26 | `cd apps/web && npm test` / `npm run typecheck` / `npm run build` | **323 TypeScript tests + 7 preview-resolver tests passed**; typecheck and build passed |
| 2026-10-26 | `cd apps/web && npm run test:e2e:preview` (isolated temporary SQLite + random port) | **35 checks, 24 screenshots passed**; real WSGI/SQLite/Shared-Core read-back, including layout undo/redo, explicit revision restore, stale-write conflict reload with a competing server revision, formula validation, interchange export/import UI, typed capacity, typed Jalali entry with fail-closed invalid dates, viewer denial and admin project creation |
| 2026-10-26 | `PYTHONPATH=src py -3 -m pytest -q tests/test_p6_layout_definition_postgres.py tests/test_p6_layout_definition_repository.py tests/test_p6_layout_definition_api.py tests/test_project_lifecycle_http_routes.py` | **100 passed, 1 skipped** for append-only layout history (repository/API/HTTP/PostgreSQL twin), scope and read-permission checks, newest-first ordering, revision/limit validation, idempotent retry, stale-base 409 conflict and immutable published revisions |
| 2026-10-26 | `PYTHONPATH=src py -3 -m pytest -q tests/test_preview_runtime.py` | **7 passed** (includes registered-capacity read/restart and admin project creation/restart) |
| 2026-10-26 | `PYTHONPATH=src py -3 -m pytest -q tests/test_p6_formula_authority_api.py tests/test_p6_formula_field_adapter.py tests/test_project_lifecycle_http_routes.py` | **108 passed**; includes unsupported-registry-field isolation, structured duration diagnostic and self-reference precedence |
| 2026-10-26 | `PYTHONPATH=src py -3 -m pytest -q tests/resources/test_max_units_time.py tests/test_p6_resource_capacity_repository.py tests/test_preview_runtime.py` | 18 passed for the typed capacity slice |
| 2026-10-26 | Exact-head CI for the review-split branch | Pending; update only after all four workflows complete on the final head |

**Full-suite result:** 2781 passed, 126 skipped, 2 warnings on the review-split branch. Earlier defects found by full runs were fixed rather than skipped, including formula audit events with tied timestamps that could be returned in random UUID order: SQLite now uses insertion order (`rowid`) and PostgreSQL uses an `event_seq` sequence, with a regression test for identical timestamps. A review finding in the append-only layout store (a retry compared a two-field slice with the three-field stored row, so identical replays were rejected and stale writers were mislabeled) is fixed in `4b140c89`, with repository, HTTP and browser regression coverage.

**Web result:** `npm test` passed 323 TypeScript tests plus 7 preview-resolver tests; `npm run typecheck` and `npm run build` passed. The browser E2E is the runtime evidence for the workspace slice. (Counts are from the latest local run; exact-head CI is tracked separately in OPS-04.)

## A. Foundation, architecture and security

| ID | Requirement | Code path | UI / API path | Test / evidence | Status |
|---|---|---|---|---|---|
| FND-01 | Shared Domain/Calculation Core is the only scheduling, calendar, formula and resource-calculation authority; Web/Desktop/Mobile do not re-implement CPM. | `src/construction_pm/scheduling/`, `resources/`, `p6_formula_*`, `apps/web/src/shared-scheduling-adapter.ts` | UI consumes server FACT/cells | `tests/scheduling/`, `tests/architecture/`, `apps/web/src/shared-scheduling-adapter.test.ts`, `p6-formula-grid-binding.test.ts` | implemented-and-verified |
| FND-02 | API / application / repository separation with typed contracts. | `src/construction_pm/application/`, `http/`, `backend_p0/` | HTTP WSGI routes | `tests/test_project_lifecycle_api.py`, `tests/test_p6_*_repository.py`, `tests/contracts/` | implemented-and-verified |
| FND-03 | Tenant/project/revision scope isolation; cross-scope access rejected. | `application/authorization.py`, `backend_p0/models.py` | `X-Tenant-Id`, `X-Project-Id`, `X-Project-Revision` | `tests/test_application_authorization_context.py`, `tests/test_project_lifecycle_http_routes.py`, scope tests across resources/interchange/claims | implemented-and-verified |
| FND-04 | Optimistic concurrency: stale revision is rejected, never silently overwritten; an identical retry is idempotent. | `p6_layout_definition_repository.py`, `backend_p0/idempotency.py`, `schedule_input_snapshot_repository.py` | Layout POST/PUT (409 `REVISION_CONFLICT`/`IMMUTABLE_LAYOUT_REVISION`), schedule snapshot, claims, procurement | `tests/test_p6_layout_definition_repository.py` (identical retry appends nothing, stale base conflicts, published revision immutable), layout HTTP 409 test, PostgreSQL twin, preview E2E competing-writer conflict reload | implemented-and-verified |
| FND-05 | Atomic writes, idempotency and replay protection for mutation boundaries. | `backend_p0/idempotency.py`, `transactions.py`, `resources/idempotency.py` | Project/activity/resource mutation routes | `tests/test_sqlite_atomic_transaction.py`, `tests/test_postgres_idempotency_lock.py`, `tests/test_atomic_sync_idempotency_*.py` | implemented-and-verified |
| FND-06 | Durable audit trail for controlled mutations. | `change_claims.py`, `procurement.py`, AI runtime audit | Claims/procurement/AI APIs | `tests/test_change_claims.py`, `tests/test_procurement.py`, `tests/test_ai_action_runtime.py` | implemented-and-verified |
| FND-07 | Trusted server identity, exact-scope AI grants, approval bound to actor/proposal/revision, two-phase execution. | `ai_action_boundary.py`, `ai_action_runtime.py`, `ai_action_activity_tools.py` | `/api/projects/{p}/ai/proposals/*` | `tests/test_ai_action_boundary.py`, `tests/test_ai_action_runtime.py`, `tests/test_ai_action_http_routes.py` | implemented-and-verified |
| FND-08 | No user-visible Oracle/Primavera/P6 branding, URLs or source references. | Web labels/localization | Workspace, landing, preview | `apps/web/src/*.test.ts`; visible-string inspection (only internal identifiers/console keys contain “P6”) | implemented-and-verified |
| FND-09 | Production deploy, secrets and sensitive admin settings are not changed without separate explicit permission. | n/a | n/a | No deployment or secret/admin change performed in this branch | implemented-and-verified (constraint observed) |

## B. Lifecycle, session, permissions and projects

| ID | Requirement | Code path | UI / API path | Test / evidence | Status |
|---|---|---|---|---|---|
| LIF-01 | Authenticated session and project-context bootstrap. | `application/project_lifecycle.py`, `project_lifecycle_api.py`, `http/project_lifecycle_routes.py` | `/api/session`, `/api/projects`, Web bootstrap | `tests/test_project_lifecycle.py`, `tests/test_project_lifecycle_http_routes.py`, preview E2E login/bootstrap | implemented-and-verified |
| LIF-02 | Project selection by permission; only visible projects are listed and opened. | `application/project_lifecycle.py` | Project selector in Web workspace | Preview E2E planner selects `preview-rps-01`; viewer list/permission test | implemented-and-verified |
| LIF-03 | Project creation (admin role) through a real surface. | `ProjectLifecycleService.create_project`, `http/project_lifecycle_routes.py` | `/api/projects`; Web project-selection create form | `tests/test_project_lifecycle_api.py`; `test_preview_runtime.py::test_preview_project_creation...`; preview E2E admin creation + persisted project list | implemented-and-verified (preview identity; production identity remains LIF-06) |
| LIF-04 | Role enforcement: viewer read-only; planner writes; admin also creates projects. | `application/authorization.py` | All project routes; Web viewer state | Preview E2E viewer gets 403 on writes and explicit failed-calculation state; route tests | implemented-and-verified |
| LIF-05 | Logout, session expiry and guarded workspace entry. | Preview `server.py` session store | `/preview/login`, `/preview/logout`, guarded `/app` | `test_preview_server_guards_login_banner_static_files_and_logout`; E2E logout/guard | implemented-and-verified (preview identity only) |
| LIF-06 | Production identity/login surface. | No production login route in `http/` | missing in production composition | Deployment must supply identity; preview has fixture personas only | missing |
| LIF-07 | Multiple projects remain isolated and switchable without leaking state. | Lifecycle + scope models | Project selector | Preview health reports two fixture projects; scope tests; Web reload | implemented-and-verified |
| LIF-08 | New-project initialization creates a consistent calendar, schedule settings, scope and revision baseline. | `ProjectLifecycleService` + `preview/runtime.py` initializer | `/api/projects`; Web create form | `test_preview_project_creation_initializes_real_workspace_and_persists` (layout revision 1, 20-column catalogue, empty activities, empty capacities, restart); preview E2E empty grid + curated layout | implemented-and-verified (preview composition) |

## C. Scheduling and progress core

| ID | Requirement | Code path | UI / API path | Test / evidence | Status |
|---|---|---|---|---|---|
| SCH-01 | CPM forward pass with calendar-aware durations. | `scheduling/schedule.py`, `time_schedule.py`, `calendar_context.py` | Schedule run API; Gantt consumes FACT | `tests/scheduling/test_forward_pass.py`, `test_time_forward_pass.py`, `test_authoritative_schedule.py` | implemented-and-verified |
| SCH-02 | CPM backward pass, early/late dates, total/free float, critical path. | `scheduling/schedule.py`, `calculate_floats`, `time_backward_pass` | Schedule result/FACT | `tests/scheduling/test_schedule.py`, `test_multi_project_float.py`, `tests/test_authoritative_schedule_query.py` | implemented-and-verified |
| SCH-03 | FS/SS/FF/SF relationships. | `scheduling/relationships.py`, dependency graph | Schedule run; relationship APIs | `tests/scheduling/test_relationships.py`, `test_project_relationships.py`, `test_dependency_graph.py` | implemented-and-verified |
| SCH-04 | Relationship lag, including calendar-aware lag. | `scheduling/schedule.py`, lag resolvers | Schedule options/run | `tests/scheduling/test_schedule.py` lag scenarios | implemented-and-verified |
| SCH-05 | Working-day and time-aware calendars, holidays, calendar exceptions. | `scheduling/calendar.py`, `calendar_context.py`, `calendar_*_repository.py` | Calendar settings API; preview settings panel | `tests/scheduling/test_calendar*.py`, `tests/test_calendar_*_repository.py`, preview E2E settings save | implemented-and-verified |
| SCH-06 | Constraints and open-ended activities. | `scheduling/constraints.py` | Schedule settings/activity data | `tests/scheduling/test_constraints.py`, `test_backward_constraints.py`, `test_oos_policy.py` | implemented-and-verified for implemented constraint types; full parity is a separate audit item |
| SCH-07 | Schedule options, data date and out-of-sequence policy. | `scheduling/schedule_options.py`, `authoritative_schedule_batch.py` | Settings API and reference catalogue | `tests/scheduling/test_schedule_options*.py`, `test_out_of_sequence*.py`; parity catalogue still marks unmapped options | partial |
| SCH-08 | Progress override, retained logic and progress-aware scheduling. | `scheduling/progress_state.py`, `remaining_work.py`, batch composer | Progress surfaces are preview-only | `tests/scheduling/test_progress_state.py`, `test_remaining_work.py`, `test_out_of_sequence.py` | implemented-not-verified (no complete Web workflow) |
| SCH-09 | Multiple float paths. | `scheduling/schedule.py` result structures | Schedule result | Tests cover float paths; full P6 option parity remains open | partial |
| SCH-10 | WBS Summary rollup dates and assignments. | Resolver/scheduler WBS Summary handling | Project/WBS surface is partial | `tests/scheduling/test_activity_calendar_resource_leveling.py`, resolver tests; no hierarchy editor | partial |
| SCH-11 | Level of Effort is fail-closed where resource semantics are unsupported. | `p6_persisted_resource_leveling_resolver.py` (`RESOURCE_LEVELING_LEVEL_OF_EFFORT_UNSUPPORTED`) | Schedule query returns explicit error | `tests/test_authoritative_schedule_snapshot_composer.py` LOE error test, resolver test | implemented-and-verified (fail-closed, not full LOE support) |
| SCH-12 | Earned Schedule and progress/EVM metrics from authoritative data. | `scheduling/earned_schedule.py`, `evm_bridge.py` | Progress/cost preview surfaces | `tests/scheduling/test_earned_schedule.py`, `tests/resources/test_evm_bridge.py` | implemented-not-verified in Web |
| SCH-13 | Baselines vs current schedule/actuals. | `p6_baseline_repository.py`, `p6_baseline_api.py` | Progress & baselines submenu is reference-only; no baseline editor | `tests/test_p6_baseline_repository.py`, `test_p6_baseline_api.py` | partial |
| SCH-14 | No schedule/FACT calculation inside the Web UI. | `apps/web/src/shared-scheduling-adapter.ts`, `workspace-gantt.ts` | Table/Gantt render server facts | Web tests; preview E2E compares displayed dates to API read-back | implemented-and-verified |
| SCH-15 | Schedule run writes an immutable snapshot and returns a fresh authoritative read-back. | `schedule_input_snapshot_repository.py`, `p6_schedule_snapshot_publication_api.py`, `backend_p0/authoritative_schedule_query.py` | Web Run Schedule panel | Preview E2E snapshot POST + query + fresh reload; `test_p6_activity_master_http_routes.py`; preview runtime test | implemented-and-verified |

## D. Resources, capacity, leveling and cost

| ID | Requirement | Code path | UI / API path | Test / evidence | Status |
|---|---|---|---|---|---|
| RES-01 | Typed resource/assignment read and write boundaries. | `p6_resource_read_api.py`, `p6_resource_write_api.py`, `p6_resource_assignment_repository.py` | Resource APIs; Web resource surface is preview | `tests/test_p6_resource_read_api.py`, `test_p6_resource_write_api.py`, `test_p6_resource_assignment_repository.py` | implemented-and-verified (API); Web surface partial |
| RES-02 | Resource calendar is the authoritative capacity source, with version, snapshot hash and strict period slices. | `resources/calendar.py`, `p6_resource_capacity_contract.py` | Schedule/leveling input | `tests/scheduling/test_resource_capacity_contract.py`, `test_versioned_resource_calendar_resolver.py` | implemented-and-verified |
| RES-03 | **Typed effective-dated Resource Max Units/Time** with unit basis, conversion, effective interval, source and immutable hash/identity, separate from assignment `units_per_time`; authenticated effective changes close an open-ended prior segment append-only. | `resources/max_units_time.py`, `p6_resource_capacity_repository.py`, `p6_resource_capacity_read_api.py`, `p6_resource_capacity_write_api.py` | `GET/POST /api/projects/{p}/p6/resource-capacities`, `POST .../{resource_id}/resolve`; Resources → Max units / time Web panel; seeded preview fixtures | `tests/resources/test_max_units_time.py`, `tests/test_p6_resource_capacity_repository.py`, `tests/test_p6_postgres_resource_capacity.py`, `tests/test_preview_runtime.py` capacity write/restart test; Web `p6-capacity-api.test.ts`, `p6-capacity-panel.test.ts`; preview E2E capacity edit/supersession/resolve/reload/permission + fail-closed unknown resource | implemented-and-verified |
| RES-04 | Assignment `units_per_time` is never treated as the resource ceiling. | Separate typed ceiling (`resources/max_units_time.py`) vs assignment demand (`P6ResourceAssignment.units_per_time`) and resource-calendar slices | Capacity read API returns only registered ceiling segments | Domain docstring and tests assert the separation; capacity API has no assignment-demand input; preview fixtures seeded explicitly | implemented-and-verified (separation); assignment UI remains RES-01 partial |
| RES-05 | Forward/backward resource leveling in Shared Core. | `scheduling/leveling_scheduler.py`, `resources/leveling.py`, `leveling_boundary.py` | Schedule run | `tests/scheduling/test_leveling_scheduler.py`, `test_resource_leveling*.py`, `test_leveling_boundary.py`, `test_public_forward_backward_leveling.py` | implemented-and-verified |
| RES-06 | Resource Dependent driving/non-driving placement with assignment diagnostics and priority rules. | `scheduling/resource_dependent.py`, `p6_persisted_resource_leveling_resolver.py` | Schedule run/query | `tests/scheduling/test_resource_dependent*.py`, `tests/test_persisted_resource_leveling_resolver.py`; PR #1582 remains open | partial (PR not merged; acceptance gaps below) |
| RES-07 | Assignment-level early/late dates. | Leveling result currently emphasizes activity placement; assignment-level early/late contract is not exposed end-to-end | Not exposed | Placement tests cover assignment start/finish; no complete assignment early/late result contract found | partial |
| RES-08 | Assignment-level backward placement. | `backward_leveling_exact_constraints`, backward leveling tests | Schedule run | `tests/scheduling/test_resource_leveling_backward.py` covers backward activity leveling; assignment-level backward contract not proven | partial |
| RES-09 | Resource histogram, curves and utilization from authoritative data. | `resources/histogram.py`, `curves.py`, `control.py` | Resources preview surface only | `tests/resources/test_histogram.py`, `test_curves.py`, `test_control.py` | implemented-not-verified in Web |
| RES-10 | Effective-dated resource rates and cost basis. | `resources/models.py` (`ResourceRate`), `resources/calculator.py` | Cost API; cost UI preview | `tests/resources/test_capacity.py`, `test_resource_calculator.py` | implemented-not-verified in Web |
| RES-11 | Capacity/leveling failures are explicit, never silently assumed. | Resolver diagnostics, preview query errors | Schedule run error panel; failed-calculation state | `tests/scheduling/test_resource_dependent.py` fail-closed cases; preview E2E viewer failed-calculation state with no fabricated rows | partial (activity-level diagnostics verified; independent nondriving placement diagnostics remain on PR #1582) |
| RES-12 | Resource Max Units/Time conversion across time bases (hour/day/week) with immutable identity. | `ResourceMaxUnitsTime.convert_to`, `compute_capacity_identity`, `ResourceMaxUnitsTimeProfile` | Capacity resolve API `capacity_on` with explicit basis/hours; Web resolve form performs no arithmetic | `tests/resources/test_max_units_time.py` (identity, conversion, overlap, missing factor), `test_p6_resource_capacity_repository.py`, `test_preview_runtime.py`, Web capacity API/panel tests, preview E2E day→week conversions (60 and 50) with explicit 40 h/week | implemented-and-verified (explicit factors only; no implicit 24-hour day or 5-day week) |

## E. Cost, EVM, cash flow and commercial control

| ID | Requirement | Code path | UI / API path | Test / evidence | Status |
|---|---|---|---|---|---|
| CST-01 | Cost accounts, expenses, financial periods and typed cost values. | `p6_cost_account_*`, `p6_expense_*`, `p6_financial_period_*` | Cost APIs; Cost menu preview | `tests/test_p6_cost_account_*.py`, `test_p6_expense_*.py`, `test_p6_financial_period_*.py` | implemented-and-verified (API); Web partial |
| CST-02 | EVM metrics and earned value bridge. | `resources/evm_bridge.py`, `resources/performance.py` | Cost/Progress preview | `tests/resources/test_evm_bridge.py`, `test_performance.py` | implemented-not-verified in Web |
| CST-03 | Cash flow / time-phased cost. | Cost/period models and reporting | No complete Web surface | Resource/cost tests; no explicit cash-flow acceptance scenario found | partial |
| CST-04 | Change notices, change cases and claims with schedule/cost impact. | `control_intelligence/change_claim.py`, `change_claims.py`, `change_claim_api.py` | Control → Changes & Claims surface | `tests/test_change_claims.py`, `test_change_claim_api.py`, `apps/web/src/workspace-change-claim.test.ts` | implemented-and-verified (backend + partial UI) |
| CST-05 | Payment application/certification and notices. | Commercial/ERP modules | Control/report surfaces partial | `tests/test_erp_accounting.py`; no complete payment-certification workflow found | partial |
| CST-06 | Reports and print with typed datasets. | `reporting.py`, `p6_report_profile_repository.py` | Report menu preview; print selection component | `tests/test_reporting.py`, `apps/web/src/p6-report-print-field-selection.test.ts` | partial |
| CST-07 | ERP/accounting integration boundary. | `erp_accounting.py` | API contract | `tests/test_erp_accounting.py`, `test_bi_integration.py` | implemented-and-verified (contract only) |

## F. Web workspace and UX

| ID | Requirement | Code path | UI / API path | Test / evidence | Status |
|---|---|---|---|---|---|
| WEB-01 | Real session/bootstrap/workspace read against WSGI, not static fixtures. | `apps/web/src/main.ts`, `project-bootstrap.ts`, `workspace-read-api.ts` | `/app`, `/api/session`, workspace read | Preview E2E 27 checks; `test_preview_runtime.py`; `workspace-read-api.test.ts` | implemented-and-verified |
| WEB-02 | Main menus and submenus with honest status labels. | `workspace-navigation.ts`, `workspace-view.ts` | Project/Schedule/Progress/Resources/Cost/Documents/Reports/Control/Settings | Preview E2E menu/submenu navigation; `workspace-navigation.test.ts`, `workspace-view-submenu-navigation.test.ts` | implemented-and-verified |
| WEB-03 | Permission-aware dashboard/workspace entry. | `main.ts`, lifecycle API | Viewer/planner/admin states | Preview E2E viewer read-only + denied writes | implemented-and-verified |
| WEB-04 | WBS hierarchy display/editing. | `workspace-model.ts` exposes distinct `wbs_id` rows only | Project/WBS surface lists flat WBS IDs | No hierarchy repository/editor; navigation marks Project “Partial” | partial |
| WEB-05 | Activity table with authoritative cells, CRUD and selection. | `workspace-view.ts`, `main.ts`, activity read model | Activity Grid | Preview E2E grid/selection; activity API tests | implemented-and-verified (read/selection); CRUD UI partial |
| WEB-06 | Table–Gantt linked selection. | `workspace-gantt.ts`, `workspace-view.ts` | Activity row + Gantt bar | Preview E2E selection; `workspace-gantt.test.ts` | implemented-and-verified |
| WEB-07 | Gantt bars, progress, critical styling from FACT only. | `workspace-gantt.ts` | Gantt Chart panel | Preview E2E; workspace model tests | implemented-and-verified |
| WEB-08 | Column add/remove/hide/reorder/resize/align/pin/freeze with persisted layout. | `workspace-model.ts`, `p6-field-chooser.ts`, `p6-api.ts`, layout repository | Field Chooser + grid headers | Preview E2E column operations + reload; `tests/test_p6_layout_definition_*`; Web tests | implemented-and-verified |
| WEB-09 | Filter and sort activities. | `workspace-filter-sort.ts` | Activity Grid filter/sort controls | Preview E2E filter/sort; `workspace-filter-sort.test.ts` | implemented-and-verified |
| WEB-10 | Layout persists across reload and server restart. | `p6_layout_definition_repository.py` | Layout GET/POST | Preview E2E reload; `test_preview_layout_survives_runtime_restart...`; layout tests | implemented-and-verified |
| WEB-11 | Schedule settings load/save with revision handling. | `schedule-cycle.ts`, schedule settings repository | Schedule Options panel | Preview E2E save + status; settings tests | implemented-and-verified |
| WEB-12 | Run Schedule through API, snapshot, query and fresh read-back. | `schedule-cycle.ts`, snapshot/query APIs | Run Schedule panel | Preview E2E run + results; Python preview test | implemented-and-verified |
| WEB-13 | Formula editor wired to authoritative validation/dependency/type results. | `apps/web/src/p6-formula-panel.ts`, `p6-formula-api.ts`, `p6-formula-editor.ts`, `src/construction_pm/p6_formula_authority_api.py` | `Schedule → Formula editor`; `POST /api/projects/{p}/p6/formulas/{registry_version}` | `p6-formula-panel.test.ts`, `p6-formula-api.test.ts`, `p6-formula-editor*.test.ts`; `tests/test_p6_formula_authority_api.py`; preview E2E valid, self-reference and unsupported-duration states | implemented-and-verified |
| WEB-14 | AI assistant chat → missing-input detection → proposal → approval → execution → verification panel. | `ai-assistant-chat.ts`, `ai-action-panel.ts`, `main.ts` | Workspace AI panels | Earlier Web E2E for AI proposal/verification; backend tests; requires configured provider/grants | implemented-and-verified (laboratory path) |
| WEB-15 | Explicit loading, empty, error, unavailable, rejected and permission states; no success on denial. | `main.ts`, `workspace-view.ts`, `schedule-cycle.ts` | All panels | Preview E2E guards, empty filter, viewer failure; error tests | implemented-and-verified |
| WEB-16 | English/Persian and LTR/RTL. | `workspace-localization.ts`, `main.ts`, `styles.css` | Language/settings; full workspace | Preview E2E Persian RTL; localization tests | implemented-and-verified (EN/FA) |
| WEB-17 | Jalali date display/input in the workspace. | `workspace-calendar-display.ts`, `workspace-jalali-entry.ts`, `schedule-cycle.ts`, `workspace-view.ts`, `main.ts` | Calendar-mode toggle in the workspace status bar; date cells; Schedule settings start/finish fields when the calendar system is Jalali (DATE_BASED) | `workspace-calendar-display.test.ts`, `workspace-jalali-entry.test.ts` (conversion, leap-day, Persian/Arabic digits, fail-closed invalid dates); preview E2E display toggle plus typed `۱۴۰۵/۰۶/۳۰` → stored `2026-09-21`, invalid `1405/13/01` rejected with no persistence, and Gregorian restore | implemented-and-verified (DATE_BASED schedule settings; time-aware mode remains an ISO datetime-local control) |
| WEB-18 | Usable smaller/compact layout. | `styles.css`, responsive workspace | 1024 px layout | Preview E2E compact layout screenshot/assertion | implemented-and-verified |
| WEB-19 | No raw action/proposal JSON or fake calculated dates shown to users. | `ai-action-panel.ts`, `workspace-view.ts` | AI and workspace panels | Web tests; preview E2E | implemented-and-verified |
| WEB-20 | Import/export panel in the Web UI with server-codec export, mapped import review and explicit errors. | `apps/web/src/p6-interchange-panel.ts`, `p6-interchange-api.ts`, `main.ts`, `workspace-view.ts`; `src/construction_pm/p6_interchange_api.py` | `Project → Import / Export`; `POST /api/projects/{p}/p6/interchange/{format}/export` and `.../import` | `p6-interchange-panel.test.ts`, `p6-interchange-api.test.ts`; preview E2E 14-activity export→download→import round-trip, invalid-document error and viewer denial | implemented-and-verified |
| WEB-21 | Recovery, undo/redo and restore UI. | Append-only layout history: `p6_layout_definition_repository.py` (`list_revisions`), `p6_layout_definition_api.py`, `http/project_lifecycle_routes.py`; Web `p6-api.ts` (`loadP6LayoutRevisions`), `main.ts`, `workspace-view.ts` | Field Chooser Undo/Redo and a revision picker that restores any older revision as a new head; `GET /api/projects/{p}/p6/layouts/{scope}/{view}/revisions`; undo/redo/restore append new revisions | `test_p6_layout_definition_repository.py` (newest-first/scoped/limit), `test_p6_layout_definition_api.py` (read permission/scope), `test_project_lifecycle_http_routes.py` (history route), `p6-api.test.ts` (loader/invalid envelope), `workspace-view.test.ts` (localized controls/delegation/restore selection), preview E2E undo, redo, restore of an older revision and undo-after-reload | partial (layout presentation only; no activity/settings/commercial undo or project-wide backup/restore UI) |
| WEB-22 | Project creation UI. | `main.ts` project-create form, `bootstrap-labels.ts` | Project selection create form | Preview E2E admin creates project, opens empty workspace, sees curated layout and persisted project name | implemented-and-verified |
| WEB-23 | Resources, Cost, Progress, Reports and Control product surfaces. | Navigation marks them Preview/Partial; view renders partial sections | Menus exist, deeper workflows not complete | Preview E2E checks navigation only | partial |
| WEB-24 | Documents, field operations and procurement surfaces. | `workspace-document.ts`, `workspace-field-*.ts`, `workspace-procurement.ts` | Documents/Control panels | Unit tests; no full E2E workflow | partial |
| WEB-25 | Desktop/mobile responsive Web parity for the tested slice. | Web CSS/layout | Same workspace | 1024 px check only | partial |

## G. AI assistant and smart guide

| ID | Requirement | Code path | UI / API path | Test / evidence | Status |
|---|---|---|---|---|---|
| AI-01 | Natural-language request becomes a typed proposal, not a silent mutation. | `ai_assistant_orchestration.py`, `ai_action_runtime.py` | `/ai/proposals`, Web chat/panel | `tests/test_ai_assistant_orchestration.py`, `test_ai_action_runtime.py` | implemented-and-verified |
| AI-02 | Missing-input detection and clarification. | Orchestration/activity tools | Chat panel | Orchestration tests | implemented-and-verified |
| AI-03 | Approval is bound to actor, proposal and current revision. | `ai_action_runtime.py` | Decision route | Runtime/boundary tests | implemented-and-verified |
| AI-04 | Authorized execution with exact-scope grants; default deny. | `ai_action_boundary.py`, activity tools | Execute route | Boundary/tool tests | implemented-and-verified |
| AI-05 | Real persistence, Shared-Core recalculation and fresh-connection read-back. | AI runtime + activity repository + schedule query | Execute → verified result | `tests/test_ai_action_activity_tools.py`, HTTP/runtime tests, prior browser E2E | implemented-and-verified |
| AI-06 | Duplicate/idempotent execution protection. | Runtime idempotency | Execute route | Runtime tests | implemented-and-verified |
| AI-07 | Durable verification record returned on proposal reads. | `ai_action_execution_verification*`, repository | Proposal read | Tests for durable round-trip/restart | implemented-and-verified |
| AI-08 | Real Web assistant path (not a mock). | `main.ts`, chat/action panels | Workspace AI panels | Prior browser E2E with real routes | implemented-and-verified (requires provider configuration) |
| AI-09 | Model/provider orchestration, file/voice intake. | Orchestration seam; voice adapters exist | No complete operator-configured provider workflow | `voice-adapters.test.ts`, `web-speech-provider.test.ts`; provider setup external | partial |
| AI-10 | Learning/research/review/publish workflow and multilingual AI coverage. | `ai_learning_memory*`, `i18n/ai.py` | None complete | Tests for memory; no admin workflow | partial |

## H. Interchange, portability and data recovery

| ID | Requirement | Code path | UI / API path | Test / evidence | Status |
|---|---|---|---|---|---|
| INT-01 | Typed mapping registry for source/canonical fields with status. | `p6_mapping_registry.py`, `p6_mapping_api.py` | Mapping API | `tests/test_p6_mapping_registry*.py` | implemented-and-verified |
| INT-02 | XML/XER/MPX/XLSX codecs and typed conversion. | `p6_primavera_xml_codec.py`, `p6_xer_codec.py`, `p6_mpx_codec.py`, `p6_xlsx_codec.py` | Interchange API | `tests/test_p6_*_codec.py`, `test_p6_interchange_typed_conversion.py` | implemented-and-verified (codec level) |
| INT-03 | Export requires explicit object extension and preserves Decimal/typed values. | `p6_interchange_api.py`, codec validation | Export API | Codec/interchange tests; preview E2E export/import | implemented-and-verified |
| INT-04 | Import round-trip maps canonical values back without warnings. | `p6_interchange_api.py` | Import API | Preview E2E XML round trip; `test_preview_interchange_round_trip...` | implemented-and-verified (API); no Web wizard |
| INT-05 | Scope/revision validation and viewer denial on interchange writes. | Interchange application service | Import/export routes | Scope tests; preview viewer import 403 | implemented-and-verified |
| INT-06 | HTTP routes for import/export in production composition. | `production_composition.py`, `project_lifecycle_routes.py` | `/api/projects/{p}/p6/interchange/{format}/import` and `.../export` | Route tests; preview runtime test | implemented-and-verified |
| INT-07 | Web import/export UI with mapping review and error states. | `apps/web/src/p6-interchange-panel.ts`, `p6-interchange-api.ts` | `Project → Import / Export` | WEB-20 Web unit tests; preview E2E round-trip, `INVALID_XML` and viewer 403 states | implemented-and-verified |
| INT-08 | Excel/XLSX schema and typed I/O. | `resources/excel_schema.py`, `xlsx_io.py` | API/codec | `tests/resources/test_excel_schema.py`, `test_xlsx_io.py` | implemented-and-verified (library); Web UI missing |
| INT-09 | Microsoft Project XML interchange. | `p6_msproject_xml_codec.py` | Interchange API | `tests/test_p6_msproject_xml_*.py` | implemented-and-verified |
| INT-10 | Project portability, backup and restore with calendar/settings/context. | `project_portability.py`, preview storage backup | Python/preview CLI | `tests/test_project_portability.py`, preview DB guard/backup tests | implemented-and-verified (backend); Web UI missing |
| INT-11 | Undo/redo of user-visible edits. | Layout presentation only: append-only revision history + Web undo/redo/restore | Field Chooser Undo/Redo and older-revision restore | Repository/API/HTTP tests; `p6-api.test.ts`; `workspace-view.test.ts`; preview E2E undo → redo → restore older revision → undo after reload with server revision checks | partial (layout presentation only; activity/schedule/settings edits have no undo/redo) |
| INT-12 | Database guard, atomic reset, backup before destructive preview reset. | `preview/storage.py` | Preview CLI | `tests/test_preview_runtime.py`, storage tests | implemented-and-verified (preview only) |

## I. Documents, field operations and procurement

| ID | Requirement | Code path | UI / API path | Test / evidence | Status |
|---|---|---|---|---|---|
| DOC-01 | Document persistence, revisions, search and OCR. | `document_persistence.py`, `document_search.py`, `document_ocr.py`, `document_api.py` | Documents surface partial | `tests/test_document_*.py` | implemented-and-verified (backend) |
| DOC-02 | RFI / Submittal / correspondence lifecycle. | Document/application modules | Documents menu | Document tests; no complete RFI/submittal E2E | partial |
| DOC-03 | Daily field logs, attendance, equipment reports. | `field_operations.py`, `field_operations_api.py` | Control → Daily Field Logs | `tests/test_field_operations*.py`, `workspace-site-log.test.ts` | implemented-and-verified (partial UI) |
| DOC-04 | Inspections, NCR/quality, safety, punch/closeout. | `field_assurance_*` | Field Assurance cards | `tests/test_field_assurance_*.py`, `workspace-field-assurance.test.ts` | implemented-and-verified (backend + partial UI) |
| DOC-05 | Procurement records with idempotency/revision/tenant isolation. | `procurement.py` | Procurement surface | `tests/test_procurement.py`, `workspace-procurement.test.ts` | implemented-and-verified (backend + partial UI) |
| DOC-06 | Contracts/change cases tied to schedule and cost impact. | `control_intelligence/`, `change_claim.py` | Control → Changes & Claims | `tests/test_change_claims.py`, `test_control_intelligence*` | implemented-and-verified (backend + partial UI) |
| DOC-07 | Audit trail for document/commercial changes. | Persistence + audit stores | API/UI | Claims/procurement tests; document tests | implemented-and-verified (backend) |
| DOC-08 | Multilingual help center and documentation coverage. | Help/i18n modules; docs | Help surface | Help infrastructure tests; coverage completeness not proven | partial |

## J. Localization, calendars and time

| ID | Requirement | Code path | UI / API path | Test / evidence | Status |
|---|---|---|---|---|---|
| LOC-01 | English/Persian workspace strings. | `workspace-localization.ts`, `workspace-view.ts` | Whole workspace | Localization tests; preview E2E Persian | implemented-and-verified |
| LOC-02 | RTL/LTR direction and mirrored layout. | `main.ts`, `styles.css`, `workspace-view.ts` | Workspace | Preview E2E RTL; layout tests | implemented-and-verified |
| LOC-03 | Jalali/Gregorian calendar models in the scheduling core and persisted metadata. | `scheduling/calendar.py`, `calendar_master_repository.py`, fixtures | Calendar/settings API | Calendar tests; preview NSE fixture Jalali settings | implemented-and-verified (model/API) |
| LOC-04 | Jalali dates rendered and entered in the workspace UI. | `workspace-calendar-display.ts`, `workspace-jalali-entry.ts`, `schedule-cycle.ts` | Date cells; workspace toggle; DATE_BASED schedule settings start/finish | `workspace-calendar-display.test.ts`, `workspace-jalali-entry.test.ts`; preview E2E display and typed-entry round-trip with stored ISO unchanged | implemented-and-verified (DATE_BASED; explicit fail-closed conversion) |
| LOC-05 | Gregorian dates displayed consistently. | Workspace cells/FACT ISO dates | Grid/Gantt | Preview E2E dates | implemented-and-verified |
| LOC-06 | Timezone-aware date/time handling. | `scheduling/time_calendar.py`, snapshot `timezone` | Schedule snapshot | `tests/scheduling/test_time_calendar*.py` | implemented-and-verified |
| LOC-07 | Calendar metadata preserved through snapshots, export and portability. | Snapshot composer, portability, interchange | API | Calendar snapshot/portability tests; preview calendar test | implemented-and-verified (API) |
| LOC-08 | All declared languages and offline language packs, not only EN/FA. | Language-pack infrastructure; workspace hard-codes EN/FA | Language manager | Infrastructure tests; #1531 remains a gap | partial |
| LOC-09 | Calendar-friendly localized number/date formatting across reports and print. | Reporting print selection | Report/print | No full localized-print test | partial |

## K. Desktop, mobile and cross-client

| ID | Requirement | Code path | UI / API path | Test / evidence | Status |
|---|---|---|---|---|---|
| PLT-01 | Desktop application foundation. | `apps/desktop/src`, package/tsconfig/README | Desktop app | Build/typecheck scripts; no full parity E2E | partial |
| PLT-02 | Mobile application foundation. | `apps/mobile/src`, package/tsconfig/README | Mobile app | Build/typecheck scripts; no full parity E2E | partial |
| PLT-03 | Offline mutation/sync backend and client contract. | `client_sync/`, `sync-runtime.ts` | Sync APIs/UI | Client-sync/atomic-sync tests | implemented-and-verified (backend/contract) |
| PLT-04 | Approved desktop/mobile capabilities at parity with Web. | Not demonstrated | None complete | No parity evidence | missing |
| PLT-05 | Voice-assisted data entry. | `voice-adapters.ts`, `web-speech-provider.ts` | Web speech adapters | Adapter tests | partial |

## L. Delivery, operations and acceptance

| ID | Requirement | Code path | UI / API path | Test / evidence | Status |
|---|---|---|---|---|---|
| OPS-01 | Reproducible local full-stack preview with real WSGI, SQLite and Shared Core. | `src/construction_pm/preview/`, `apps/web/preview-full.mjs` | `npm run preview:full`, `http://127.0.0.1:4174` | Preview E2E 35 checks including the capacity, typed Jalali, layout undo/redo/revision-restore and stale-write conflict workflows; 7 Python preview tests; manual 4174 run | implemented-and-verified (local) |
| OPS-02 | A real, external preview URL. | n/a | None | `has_pages=false`; no deploy performed | blocked-external |
| OPS-03 | In-repo browser E2E covering login, project selection, menus, grid/Gantt, columns, layout undo/redo/restore, stale-write conflict, filter/sort, settings/calendar, typed Jalali entry, schedule calculation, formula validation, persistence, interchange round-trip UI, capacity edit/supersession/resolve/reload/permission, project creation, session/permission errors. | `apps/web/e2e/preview-e2e.mjs` | Browser | 35 checks, 24 screenshots; isolated run passed | implemented-and-verified |
| OPS-04 | Exact-head CI on the final branch before merge. | `.github/workflows/*` | n/a | Split head pending. Earlier PR #1582 head `0dcad35f` passed 9/9 checks ([Python](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40315561582), [PostgreSQL](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40315561686), [Web](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40315561581), [Client typecheck](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40315561589)); those results do not certify this split head | partial |
| OPS-05 | Independent review, PR splitting and merge of complete changes. | `feat/full-stack-preview-workspace` split; PR #1582 | n/a | Preview/Web slices split for independent review; Resource Dependent placement and AI verification remain on PR #1582. Assignment-level backward/early-late and independent-review gaps remain open | partial |
| OPS-06 | Official CUBISITE weights/scores/completion percentage. | n/a | n/a | Workbook unavailable; not invented | blocked-external |
| OPS-07 | No production deployment or secret/admin change without separate permission. | n/a | n/a | None performed | implemented-and-verified (constraint observed) |
| OPS-08 | Honest failure/blocker reporting; unrun tests never reported green. | This matrix and ledger | n/a | Verification log separates run/pending/blocked | implemented-and-verified |

## Highest-priority remaining gaps

1. **RES-07/RES-08 — assignment-level early/late and backward placement.** Activity-level backward leveling exists and is tested. `scheduling/resource_dependent_placement.py` documents a deliberate contract boundary: it consumes only final authoritative activity start/finish and exposes no assignment-level early/late or backward result. This remains an approved gap until a separate, evidence-backed contract is implemented.
2. **WEB-21/INT-11 — undo/redo and restore scope.** Layout presentation undo/redo and explicit restore of any older revision are implemented and verified against append-only history, including undo after reload. Undo/redo for activities, schedule/settings, WBS and commercial edits, plus a project-wide backup/restore UI, remain missing.
3. **WEB-04 — WBS hierarchy.** The workspace has a flat WBS list; no hierarchy editor or rollup navigation.
4. **LIF-06 — production identity.** Supplied by deployment; the preview personas are not production credentials.
5. **OPS-02/OPS-06 — external URL and authoritative weights.** Both are external blockers; neither is claimed or faked.

## Change rule

Any future status change must cite a current-tree code path and a test/runtime result, or name the exact external blocker. A merged PR, green CI or a menu label alone does not upgrade a requirement to `implemented-and-verified`.
