# V31 — Implementation evidence

Tested code SHA: `894d435678796b00113d0a79855c2d4fd3314183`.

## Files

| File | Change |
|---|---|
| `apps/web/src/workspace-activity-copy.ts` | Copy Options model, persisted preference, relationship planner, child-identity helper, dialog |
| `apps/web/src/workspace-activity-copy.test.ts` | Preference, planner and ID tests |
| `apps/web/src/workspace-activity-renumber.ts` | Increment/Auto-Number/Replace planner, duplicate resolution dialog, API client |
| `apps/web/src/workspace-activity-renumber.test.ts` | Planner and request-shape tests |
| `apps/web/src/workspace-activity-fill.ts` | Active-column Fill Down mapping, validation, source read and confirmation dialog |
| `apps/web/src/workspace-activity-fill.test.ts` | Column eligibility and value validation tests |
| `apps/web/src/main.ts` | Paste dialog flow, child replay (codes, notebook, steps, expenses, period actuals, assignments and periods, documents), relationship replay, renumber command, active-column Fill Down, curtain bulk callback |
| `apps/web/src/workspace-view.ts` | Renumber context command enabled, Hide All / Show All curtain controls |
| `apps/web/src/workspace-desktop-shell.ts` | `edit.renumber` command and Edit menu item |
| `apps/web/src/workspace-command-icons.ts` | Renumber icon mapping |
| `apps/web/styles.css` | Layout for the three new dialogs and the curtain bulk group |
| `src/construction_pm/activity_master_repository.py` | Atomic `renumber` on SQLite and PostgreSQL, reference discovery, document JSON rewrite |
| `src/construction_pm/p6_activity_master_api.py` | Authorized `renumber` boundary |
| `src/construction_pm/http/project_lifecycle_routes.py` | `POST /api/projects/{id}/p6/activities/renumber`, error mapping |
| `apps/web/e2e/activity-v31-renumber-copy.mjs` | Browser proof for all four features |
| `apps/web/e2e/activity-edit-v30.mjs` | Paste step now confirms the Copy Options dialog |
| `tests/test_activity_master_repository.py` | Renumber reference-integrity and collision tests |
| `tests/test_p6_activity_master_http_routes.py` | Renumber HTTP contract and stale revision test |

## Renumber transaction

`ActivityMasterRepository.renumber(scope, entries, include_baselines)`:

1. Validates a non-empty, duplicate-free mapping, the 80-character ID ceiling, `expected_revision >= 1`, each source row’s existence and revision, and that no target is owned by an activity outside the selection.
2. For each mapping, stages the activity through `__CUBI_RENUMBER_<uuid>__` and then to the final ID. Each stage inserts the target row, repoints references, then deletes the source row. This keeps foreign keys satisfied and makes swaps safe.
3. References are discovered from the live schema (SQLite `sqlite_master` + `PRAGMA table_info`; PostgreSQL `information_schema.columns`) for every table that carries `tenant_id`, `project_id` and `activity_id`. `relationship_master.predecessor_id` / `successor_id` are updated explicitly. `project_documents.document_json` is parsed and only exact activity identity values are rewritten.
4. `p6_baseline_activity` participates only when `include_baselines` is true. Clearing the dialog checkbox leaves the renamed activity disconnected from the baseline, matching “If you clear this checkbox, all renumbered activities are disconnected from the baselines”.
5. The whole call runs inside the caller’s transaction; a standalone call uses `BEGIN IMMEDIATE` and rolls back on any error.

Security: `P6ActivityMasterAPI.renumber` requires `PROJECT_WRITE`, project checkout ownership, tenant/project scope equality and a valid authorization context before the repository is called.

## Copy replay

| Option | Service path |
|---|---|
| Resource & Role Assignments | `POST /p6/resource-assignments`, then `POST /p6/resource-assignment-periods` for each future-period value |
| Relationships | `POST /p6/relationships` after all new rows exist; planner maps copied endpoints and optionally drops external endpoints |
| Expenses | `POST /cost/expenses` with a collision-free `-C<n>` identity |
| Activity Codes | `POST /p6/activities/{id}/codes` |
| WPs & Docs | Document PUT adding the new activity to `linked_entity_refs`, preserving the stored revision |
| Notebook | `POST /p6/activities/{id}/notebook` |
| Steps | `POST /p6/activities/{id}/steps` |
| Financial Period Data | `POST /p6/activity-period-actuals` with the new activity identity |

Every failure is returned to the operator as a named warning; Paste never reports success for a child it did not write. The choice is saved in `localStorage` under `cubi.activity-copy-options.v1`; “Do not show this dialog again” suppresses later dialogs.

## Fill Down

The renderer records the last clicked `td[data-column-id]`. Fill Down resolves that ID against `FILLABLE_COLUMNS` and only offers columns visible in the current layout. The source value is read from the Activity Master GET, validated (`text`, `decimal`, `integer`, `percent`, `enum`) and written to each target with its current record revision. The dialog shows the exact value and target count before the write; the write is one PATCH per row, so a late conflict is reported rather than hidden.
