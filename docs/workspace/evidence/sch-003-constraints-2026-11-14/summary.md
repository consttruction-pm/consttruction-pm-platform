# SCH-003 constraints, open ends and relationship lag calendar — 2026-11-14

- **Tested code:** `e81d3bb0` (`feat(schedule): persist activity constraints and move CPM dates`, PR #1967).
- **Requirement:** every supported constraint type must be persisted as scheduling input, applied by the shared calculation core, and editable from Activity Details; open ends and the relationship lag calendar must be honored by the schedule without browser-side date math.

## Audit before the change

- `ConstraintMasterRepository` could create/read/update revision-scoped rows and the authoritative input composer already loaded `constraint_master` rows into `ActivityConstraint` inputs; the forward pass applied the constraint windows.
- There was **no HTTP route**, **no delete**, and **no typed UI** for constraints. The Activity Details Status tab showed only a read-only summary and scripts still described constraints as untouchable. Open-ended criticality and the project-wide relationship lag calendar option existed only in the core and settings model.
- `ConstraintMaster.validate()` accepted a `datetime` because `datetime` subclasses `date`, so a caller could persist a value with a time component that the date-only schedule semantics never intended.

## Change

- **Repository (`src/construction_pm/constraint_master_repository.py`):** `validate()` now rejects datetime precision with `INVALID_CONSTRAINT_DATE`. The protocol gains `delete(scope, constraint_id, *, expected_revision)`; both the SQLite and PostgreSQL implementations delete by tenant/project/revision/id/record_revision and return `True`, raising `CONSTRAINT_NOT_FOUND` or `REVISION_CONFLICT` otherwise.
- **API (`src/construction_pm/p6_constraint_api.py`, new):** `p6-constraint-api.v1` with `kind: "p6_constraint"` and envelope `{contract_version, kind, scope, constraint:{constraint_id, activity_id, constraint_type, constraint_date, record_revision}}`. It enforces scope and `PROJECT_READ`/`PROJECT_WRITE`, the checkout lease on writes, revision-guarded update/delete, activity existence (`ACTIVITY_NOT_FOUND_OR_SCOPE_MISMATCH`), rejects Level of Effort and WBS Summary targets (`CONSTRAINT_ACTIVITY_TYPE_UNSUPPORTED:<type>`), and rejects a second constraint of the same type on one activity (`DUPLICATE_CONSTRAINT_TYPE`). All six `ConstraintType` values are accepted.
- **HTTP (`src/construction_pm/http/project_lifecycle_routes.py`):** `GET/POST /api/projects/{id}/p6/constraints` and `GET/PATCH/DELETE /api/projects/{id}/p6/constraints/{constraint_id}` with `404 P6_CONSTRAINT_NOT_FOUND`, `409 REVISION_CONFLICT`/`PROJECT_CHECKED_OUT_BY_OTHER`, `400 P6_CONSTRAINT_REQUEST_INVALID` and `403` for authorization failures. Dates are parsed with `date.fromisoformat`, types through `ConstraintType`.
- **Composition (`production_composition.py`, `preview/runtime.py`):** the production composition accepts the constraint repository and builds the API; the preview runtime injects `repositories.constraints`. The composer already reads stored constraints, so publishing carries them into the hashed snapshot input.
- **Web (`apps/web/src/workspace-constraints.ts`, new):** typed client with the six values and en/fa labels, strict response parsing (`INVALID_CONSTRAINT_RESPONSE`/`INVALID_CONSTRAINT_RECORD`), payload validation, list/save/delete against the real paths; delete sends `expected_revision`.
- **Web (`apps/web/src/workspace-activity-details.ts`):** the Status tab now renders one **Constraints** section for the selected activity: stored rows with type, date and revision, a Remove action only when `canWrite`, and a typed form (type select offering exactly six options plus a date input) only when `canWrite`. Saving reloads from the API and shows `Saved`; a failed delete surfaces the API error code on the button. The pane states that constraints are inputs and that dates/float/criticality are calculated by the core after the schedule is published and run.

## Browser proof

`apps/web/e2e/preview-e2e.mjs` recorded check `activity constraints persist and move the authoritative schedule`:

1. Select `A140` ("Piling and foundations", 10 days), open Status, and assert no stored constraint and exactly six typed options.
2. Save `START_NO_EARLIER_THAN` / `2026-10-20` through the form and wait for the row plus `Saved`.
3. `GET /p6/constraints` returns `A140`, `START_NO_EARLIER_THAN`, `2026-10-20`, `record_revision: 1`.
4. Publish and run the schedule; the 14-row result table shows `A140` start `2026-10-20`, finish `2026-11-03`, duration `10`, total float `0`, critical `Yes`.
5. Screenshot `07h-constraint-editor.png` shows the real Status tab editor with the grid/Gantt at `2026-10-20`.
6. Remove the constraint through the UI; the API list no longer contains `A140`, and rerunning the schedule returns `A140` start `< 2026-10-20`.

Full run at `e81d3bb0`: 100/100 checks, 54 screenshots, zero uncaught exceptions and zero API 5xx.

## Unit and server coverage at the same code

- `tests/test_p6_constraint_api.py` — create/get/list/update/delete round trip, scope/permission/lease denial, stale-revision update and delete, unknown activity, duplicate type, LOE rejection.
- `tests/test_constraint_master_repository.py` — datetime rejection, revision-guarded delete, stale and cross-revision delete.
- `tests/test_project_lifecycle_http_routes.py` — full HTTP create/read/list/update/delete plus missing/stale/bad-payload/lease-lock mappings.
- `apps/web/src/workspace-constraints.test.ts` — parse/reject, payload validation, paths, delete revision.
- `apps/web/src/workspace-activity-details.test.ts` — constraints filtered to the activity, typed form only for writers, no delete action for read-only users.
- Python `4319 passed, 203 skipped`; Web `1162 tsx` + `15 node --test`; `tsc` and esbuild clean.

## Evidence in this bundle

- `evidence.json` — full suite result at `git_head` `e81d3bb09773eaad4a749204117d507ba59161b1`, 100 checks, 54 screenshots, with the `constraints` block (six editor options, stored record, constrained `A140` row, empty list after delete).
- `07h-constraint-editor.png` — Activity Details Status tab with the constraint editor and the scheduled `A140`.

## Limits

- **External Version 26 fixture comparison is `BLOCKED_EXTERNAL`:** no licensed V26 constraint/schedule export exists in the repository; parity is asserted against the documented V26 behaviour catalogue and the internal CPM/constraint tests.
- **Per-relationship lag-calendar assignment has no editor.** The project-wide `relationship_lag_calendar` option is stored, typed in the Schedule window and consumed by the core; `relationship_lag_calendar_assignment` rows are read by the composer and calendar-usage API, and `save_relationship_lag` exists in both repositories, but there is no HTTP/UI surface to assign an option to one relationship yet.
- Open-ended criticality is produced by the core (`open_ended_criticality` option, covered by `tests/scheduling/test_schedule.py`) rather than by a separate UI control; constraints are one per type per activity, and leveling/resource interactions remain SCH-005.
