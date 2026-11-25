# ENG-WS-DATA-DATE — Data Date and progress line

| Field | Value |
|---|---|
| Page ID | ENG-WS-DATA-DATE |
| Route | `/app/activities/` (Activity Grid and Gantt), plus the Schedule settings dialog that writes the value |
| Environment | CUBI Engineering workspace (P6 Professional V26 reference) |
| Status | IMPLEMENTED — Data Date is stored in PostgreSQL, rendered from the server record, and consumed by the shared scheduler. Visual parity: **not claimed**. |
| Owner | Engineering surface |
| Base | `main` @ `6ce2838a27d796da2732d82e76a931fe4f6b18b5` (PR #2155) |

## Inheritance chain and source paths

Workspace entry (`apps/web/src/main.ts`) → authenticated shell and desktop windows (`workspace-desktop-shell.ts`) → Activity Grid and Gantt (`apps/web/src/workspace-view.ts`) → Layout Options / Bars dialog and Schedule settings (`apps/web/src/schedule-cycle.ts`) → canonical presentation loader (`loadP6Presentation` in `main.ts`) → API transport (`session-api.ts`, `schedule-cycle.ts`) → server routes (`http/project_lifecycle_routes.py`) → `P6ScheduleSnapshotPublicationAPI` and `PostgresProjectScheduleSettingsRepository` → shared scheduler (`scheduling/schedule_evaluator.py` → `time_schedule` → `scheduling/forward_pass.py`).

Capability/traceability: `C10` Progress/Actuals and `C14` EVM/Earned Schedule in `docs/cubisite/CAPABILITY_PAGE_INHERITANCE_HELP_MATRIX.md`; matrix row `ENG-WS-DATA-DATE` in `docs/engineering/ENGINEERING_PAGE_FIELD_HELP_MATRIX.json` and `docs/traceability/engineering-v26.json`.

## Exact official Help topics

| Topic | URL | Section used |
|---|---|---|
| Using the data date | https://docs.oracle.com/cd/G48902_01/client_help/en_US/using_the_data_date.htm | Data Date definition, its effect on remaining work and the Gantt line |
| The Gantt Chart | https://docs.oracle.com/cd/G48902_01/client_help/en_US/the_gantt_chart.htm | Data Date line and progress line rendering |
| Customize Activity Details | https://docs.oracle.com/cd/G48902_01/client_help/en_US/customize_activity_details.htm | Activity progress fields edited against the Data Date |

All three topics are already registered for `/app/activities/` in `apps/web/src/help-registry.generated.ts`; the page's Help link resolves through `HELP_REGISTRY`, so no URL is synthesised in the UI.

## Functional behavior

- **One authoritative value.** The project Data Date is read only from `GET /api/projects/:id/p6/schedule/settings` (`schedule_options.data_date`). When the record has no Data Date, the Gantt draws **no** line and no date attribute (`data-gantt-data-date` absent); nothing is inferred from the project start or the browser clock.
- **Edit path.** The Schedule settings form (`[data-schedule-settings-form]` in `schedule-cycle.ts`) submits `p6-project-schedule-settings-api.v1` with `schedule_options.data_date` and `expected_record_revision`; the route validates the complete `ScheduleOptions` schema, so a partial or malformed option set is rejected rather than merged.
- **Revision control.** A save with a stale `expected_record_revision` answers `409 REVISION_CONFLICT`; the form keeps the user's draft and reports the conflict instead of overwriting.
- **Gantt line.** The line is rendered at the Data Date's position on the timeline with the saved layout style (`data-gantt-data-date`, `cp-gantt-data-date is-<style>`, `--cp-data-date-color`, `--cp-data-date-width`). The Bars/Layout Options dialog owns the show/hide toggle and persists it as layout presentation (`data-layout-data-date-line`), never as schedule data.
- **Progress-line comparison.** Progress points are classified as behind / on / ahead against the same Data Date (`data-gantt-progress-data-date`, `data-gantt-progress-behind|on|ahead`).
- **Filters.** The activity date-filter context is built from the same Data Date (`createActivityFilterDateContext`), so filters and the drawn line cannot disagree.
- **Downstream reads.** Earned Value and cost reads expose the stored Data Date (`data_date`); they do not compute a second one.
- **Permissions.** Reading the settings requires project read; saving requires project write (`planner`/`project_admin` by the default policy). A viewer receives `403` on save and still reads the line.
- **Empty/error states.** No settings record → no line; failed read → the existing workspace error surface, no fallback date.

## API, data and persistence

| Concern | Source |
|---|---|
| Read/write contract | `p6-project-schedule-settings-api.v1` at `/api/projects/:id/p6/schedule/settings` |
| Persistence | PostgreSQL `project_schedule_settings` through `PostgresProjectScheduleSettingsRepository` |
| Snapshot consumption | `schedule_evaluator.py` passes `data_date` into `time_schedule`; `forward_pass` bounds remaining work at `max(logic_start, actual_start, data_date)` |
| Workspace read | `/api/v2/workspace/control-room/read`; the session loader supplies `projectDataDate` to the view |
| Authorization | `default_project_policy()` (`project.read` / `project.write`); no client-side grant |

No second scheduler, no browser CPM, and no client-computed Data Date exists.

## Acceptance tests and evidence

| Check | Evidence |
|---|---|
| Line absent without a stored Data Date | `apps/web/src/workspace-view.test.ts` — "no fabricated line" |
| Line drawn with saved style and value | `apps/web/src/workspace-view.test.ts` — "an authoritative Data Date draws the line with the saved style" |
| Progress points classified against it | `apps/web/src/workspace-view.test.ts` — "progress points are classified against the authoritative Data Date" |
| Layout toggle persists as presentation only | `apps/web/src/workspace-view.test.ts` — Layout Options test |
| Settings round trip and revision guard | `tests/integration/test_postgres_project_schedule_settings_live.py` (repository) and the live acceptance below |
| End-to-end | `tests/integration/test_cubi_database_operationalization_postgres_live.py::test_data_date_and_progress_are_operational_end_to_end` — Data Date stored/read back; removing it finishes earlier, restoring it reproduces the identical forecast; chain float 0 and critical; Planned Duration and baseline cells untouched; new session reads the same values |
| CI | PR #2155: `test (3.11/3.12/3.13)`, `postgres`, all typecheck jobs and `cubi-web-preview` green |

## Known gaps and decisions

- The Data Date has no dedicated dialog of its own; it is one field of the Schedule settings contract. P6 exposes it in the same Schedule dialog, so no separate page was created.
- Visual parity with the V26 Gantt illustration is not claimed: the official Preview alias is unhealthy from this environment, so only local full-stack screenshots exist at the recorded viewports.
- The line is presentation only; it never moves bars or rewrites Actual dates. Moving the Data Date is a schedule-settings write with its own revision guard.
