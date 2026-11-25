# ENG-WS-TRACKING — Tracking

| Field | Value |
|---|---|
| Page ID | ENG-WS-TRACKING |
| Route | `/app/tracking/` (Tracking window; summary, tabular, histogram and activity usage profile layouts) |
| Environment | CUBI Engineering workspace (P6 Professional V26 reference) |
| Status | IMPLEMENTED — read-only projections of stored schedule and assignment facts, served by PostgreSQL. Visual parity: **not claimed**. |
| Owner | Engineering surface |
| Base | `main` @ `6ce2838a27d796da2732d82e76a931fe4f6b18b5` (PR #2155) |

## Inheritance chain and source paths

Workspace entry (`apps/web/src/main.ts`) → authenticated shell and desktop windows (`workspace-desktop-shell.ts`) → workspace view host (`apps/web/src/workspace-view.ts`) → Tracking client and renderers (`apps/web/src/workspace-tracking.ts`) → API transport (`session-api.ts`) → server route `GET /api/projects/:id/tracking/read` (`http/project_lifecycle_routes.py`) → `TrackingReadAPI` (`tracking_read_model.py`) → published schedule facts (`P6ScheduleSnapshotPublicationAPI`) and assignment facts (activity resource assignments). The shared scheduler is not invoked on this path.

Capability/traceability: `C10` Progress / Actuals and `C14` EVM / Earned Schedule in `docs/cubisite/CAPABILITY_PAGE_INHERITANCE_HELP_MATRIX.md`; matrix row `ENG-WS-TRACKING` in `docs/engineering/ENGINEERING_PAGE_FIELD_HELP_MATRIX.json`, `docs/traceability/engineering-v26.json` and `docs/traceability/CUBI_ENGINEERING_V26_TRACEABILITY.md`.

## Exact official Help topic

| Topic | URL | Section used |
|---|---|---|
| Tracking | https://docs.oracle.com/cd/G48902_01/client_help/en_US/tracking.htm | Tracking layouts (summary, tabular, histogram, activity usage profile) and comparison of work against the target plan |

The topic is registered for `/app/tracking/` in `apps/web/src/help-registry.generated.ts` (source: P6 Professional V26 HTML Help, p. 372); the page's Help link resolves through `HELP_REGISTRY`, so no URL is synthesised in the UI.

## Functional behavior

- **Read-only by contract.** The window never runs CPM and never edits schedule or assignment data. Every displayed value is a stored published fact; the panel states this explicitly.
- **Versioned projection.** The response is `tracking-read-model.v1` and is verified before rendering. A contract, scope, layout or totals inconsistency fails closed with `TRACKING_RESPONSE_VERIFICATION_FAILED`; nothing partial is shown.
- **Scope echo.** The request carries `X-Tenant-Id`, `X-Project-Id` and the project revision; the response `scope` must echo the same tenant, project and revision, or the client rejects the payload.
- **Layouts.** Four documented layouts are exposed as tabs: Summary (counts by status, completed, critical, float), Tabular (per-activity status, percent, start, finish, total float, critical flag, planned finish and finish variance days), Histogram/bars (buckets of completed / in progress / not started by published finish at the selected scale) and Activity Usage Profile (starts and summed published durations per bucket). Authoritative resource assignment totals are rendered from persisted facts when present.
- **Controls.** Scale, group-by (none / WBS), sort and direction feed the documented query string (`trackingPath`); only non-empty values are serialised. Refresh re-reads the projection.
- **Grouping integrity.** WBS groups must cover every row exactly once; a group tally that does not match the row set is rejected rather than displayed.
- **Honest empty and error states.** No published schedule → the server answers `409` with `error.tracking.schedule.not_published`; an empty schedule → `409 error.tracking.schedule.empty`; missing resource assignments → an explicit "not available" panel with the reason, never a zero total. Authorization failure → `403`; the window states the reason and offers refresh.
- **Comparison against plan.** Where a planned finish is stored, the tabular layout exposes `plannedFinish` and `finishVarianceDays` verbatim; no client computation redefines the baseline.
- **Permissions and isolation.** Reading requires project read (`viewer` and above by the default policy); there is no write route. A cross-tenant projection is rejected by the read model and by the route.
- **Relationship to Data Date and progress.** Tracking reads the published schedule produced under the project's Data Date and the recorded progress (actual start/finish, percent complete); it re-derives neither. The same Data Date and progress facts drive `ENG-WS-DATA-DATE`; Tracking only reports their stored consequences.

## API, data and persistence

| Concern | Source |
|---|---|
| Read contract | `tracking-read-model.v1` at `GET /api/projects/:id/tracking/read` |
| Server projection | `TrackingReadAPI` in `src/construction_pm/tracking_read_model.py` |
| Schedule facts | Published schedule snapshot (`P6ScheduleSnapshotPublicationAPI`) |
| Assignment facts | Persisted activity resource assignments in PostgreSQL |
| Authorization | `default_project_policy()` (`project.read`); no write route |
| Workspace read | Tracking is a read-only window over the same project revision as the workspace |

No second scheduler, no browser CPM, and no client-side baseline or variance computation exists.

## Acceptance tests and evidence

| Check | Evidence |
|---|---|
| Documented query and grouping omission | `apps/web/src/workspace-tracking.test.ts` — `trackingPath sends the documented query and omits an empty grouping` |
| Verbatim versioned projection | `apps/web/src/workspace-tracking.test.ts` — `parser accepts the versioned projection and keeps server values verbatim` |
| Fail-closed on contract/scope/layout/totals | `apps/web/src/workspace-tracking.test.ts` — `parser fails closed on contract, scope, layout and inconsistent totals` |
| WBS group coverage | `apps/web/src/workspace-tracking.test.ts` — `parser requires WBS groups to cover every row` |
| Resource totals verbatim | `apps/web/src/workspace-tracking.test.ts` — `parser accepts authoritative resource totals exactly as serialized` |
| Transport failure and malformed payload | `apps/web/src/workspace-tracking.test.ts` — `loadTrackingRead forwards transport failures and rejects malformed payloads` |
| Rendered summary, rows and layouts | `apps/web/src/workspace-tracking.test.ts` — mounted page tests |
| Honest server error state | `apps/web/src/workspace-tracking.test.ts` — `mounted page states the server error honestly and offers refresh` |
| Composition wiring | `tests/test_tracking_production_composition.py`, `tests/test_tracking_read_model.py` |
| Isolated PostgreSQL, exact assignments and tenant isolation | `tests/integration/test_tracking_postgres_live.py` — `test_live_postgres_tracking_projects_exact_assignments_and_isolates_scopes`, `test_live_postgres_tracking_rejects_cross_tenant_projection` |
| End-to-end with Data Date and progress | `tests/integration/test_cubi_database_operationalization_postgres_live.py::test_data_date_and_progress_are_operational_end_to_end` — Tracking-visible early start, finish at/after the Data Date, percent and float/critical from the same run |
| CI | PR #2155: `test (3.11/3.12/3.13)`, `postgres`, all typecheck jobs and `cubi-web-preview` green |

## Known gaps and decisions

- Tracking has no independent write surface; there is nothing to edit on this page. Progress is recorded through the Activities route (`PATCH /api/projects/:id/p6/activities/:aid`) and read here.
- Resource totals require persisted assignments; when they are absent the page shows an explicit unavailable reason instead of inferring totals from activity data.
- Visual parity with the V26 Tracking illustrations is not claimed: the official Preview alias is unhealthy from this environment, so only local full-stack rendering at the recorded viewports exists.
- Baseline comparison is limited to a stored planned finish where one is published; a full multi-baseline comparison is out of scope for this record.
