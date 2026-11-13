# Contract request — P6 formula column lifecycle API (`p6-formula-column-lifecycle-api.v1`)

Status: **REQUESTED — Agent 3 / Shared Core**
Owner of this request: Agent 1 (frontend / workspace integration)
Requested: 2026-11-13
Related evidence: `docs/workspace/evidence/formula-columns-v26-2026-11-13/`

## Why

Agent 1 completed the frontend lifecycle slice on top of the existing
`p6-formula-column-api.v1` list/create routes: the editor validates an expression
against `p6-field-registry.v1`, creates a definition under `PROJECT_WRITE`, lists
saved definitions with version/data type/result type/dependencies, shows the
column in the grid only on explicit user action, and reads authoritative values
from the control-room projection. 10/10 browser scenarios pass and the frontend
never evaluates an expression.

The acceptance list for FORMULA-001 also requires **edit, delete with revision
protection, version history, audit history and preview against real activities**.
None of these exist in the backend:

- `src/construction_pm/p6_formula_column.py` implements store/list/create only.
- `src/construction_pm/p6_formula_authority_api.py` exposes only validation and
  column create.
- `src/construction_pm/http/project_lifecycle_routes.py` exposes only
  `GET|POST /p6/formula-columns`.

Agent 1 will not fake these surfaces or add a second browser evaluator. The
frontend contract is ready to consume the routes below as soon as they are
available; until then the UI must not render edit/delete/version controls.

## Requested routes

All routes are project-scoped and additive; existing list/create semantics must
not change.

| Method | Path | Permission | Purpose |
|---|---|---|---|
| `PATCH` | `/api/projects/{project_id}/p6/formula-columns/{formula_id}` | `PROJECT_WRITE` | Edit title/expression/context with optimistic concurrency |
| `DELETE` | `/api/projects/{project_id}/p6/formula-columns/{formula_id}` | `PROJECT_WRITE` | Delete with optimistic concurrency |
| `GET` | `/api/projects/{project_id}/p6/formula-columns/{formula_id}/versions` | `PROJECT_READ` | Ordered version history |
| `GET` | `/api/projects/{project_id}/p6/formula-columns/{formula_id}/audit` | `PROJECT_READ` | Audit events (created/updated/deleted, actor, timestamp, revision) |
| `POST` | `/api/projects/{project_id}/p6/formula-columns/{formula_id}/preview` | `PROJECT_READ` | Evaluate the stored (or supplied) definition against project activities |

### Preconditions

Writes carry both preconditions; either failing must reject the whole request:

- `X-Project-Revision` header must equal the project revision the client read.
- `If-Match` (or body `expected_version`) must equal the stored formula `version`.

### Request / response shapes

`PATCH` body:

```json
{
  "contract_version": "p6-formula-column-lifecycle-api.v1",
  "expected_version": 3,
  "title": "Progress Fraction",
  "expression": "[activity.duration_percent_complete] / 100",
  "context_field_id": "activity.actual_finish"
}
```

Response: the updated `P6FormulaColumn` record with `version` incremented, wrapped
in the existing `{contract_version, kind:"formula_column", scope, formula}` envelope.

`DELETE` body:

```json
{ "contract_version": "p6-formula-column-lifecycle-api.v1", "expected_version": 3 }
```

Response: `204` on success, or `{kind:"formula_column_deleted", formula_id, version}`.

`GET .../versions` response:

```json
{
  "contract_version": "p6-formula-column-lifecycle-api.v1",
  "kind": "formula_column_versions",
  "scope": {"tenant_id": "...", "project_id": "...", "project_revision": 41},
  "formula_id": "formula.e2e_progress_fraction",
  "versions": [
    {"version": 1, "title": "...", "expression": "...", "result_type": "number",
     "data_type": "double", "result_unit": null, "dependencies": ["activity.duration_percent_complete"],
     "created_at": "...", "actor": "..."}
  ]
}
```

`GET .../audit` response:

```json
{
  "contract_version": "p6-formula-column-lifecycle-api.v1",
  "kind": "formula_column_audit",
  "scope": {"tenant_id": "...", "project_id": "...", "project_revision": 41},
  "formula_id": "formula.e2e_progress_fraction",
  "events": [
    {"event": "created", "version": 1, "actor": "...", "at": "...", "project_revision": 40},
    {"event": "updated", "version": 2, "actor": "...", "at": "...", "project_revision": 41}
  ]
}
```

`POST .../preview` body:

```json
{
  "contract_version": "p6-formula-column-lifecycle-api.v1",
  "expression": "[activity.duration_percent_complete] / 100",
  "context_field_id": "activity.actual_finish",
  "activity_ids": ["A100", "A110"]
}
```

Response:

```json
{
  "contract_version": "p6-formula-column-lifecycle-api.v1",
  "kind": "formula_column_preview",
  "result_type": {"data_type": "number"},
  "dependencies": {"field_ids": ["activity.duration_percent_complete"]},
  "rows": [
    {"activity_id": "A100", "value": "1.0", "error_code": null},
    {"activity_id": "A110", "value": null, "error_code": "DIVISION_BY_ZERO"}
  ],
  "truncated": false
}
```

Values must be the same textual decimal representation used by the control-room
projection, so the preview and the grid agree exactly. `activity_ids` is bounded
by the server (document the cap; do not silently truncate — set `truncated`).

## Error vocabulary

Keep the existing codes and add the following, each with a `message_key` and a
stable machine code in `error_code`:

| Code | HTTP | Meaning |
|---|---|---|
| `REVISION_CONFLICT` | 409 | `X-Project-Revision` no longer matches |
| `FORMULA_VERSION_CONFLICT` | 409 | `expected_version` no longer matches |
| `FORMULA_COLUMN_NOT_FOUND` | 404 | unknown formula id in the project/tenant |
| `FORMULA_COLUMN_IMMUTABLE` | 409 | definition is referenced by a locked layout/revision |
| `FORMULA_COLUMN_ARCHIVED` | 409 | edit/delete attempted on an archived definition |
| `FORMULA_PREVIEW_LIMIT_EXCEEDED` | 400 | requested activity set exceeds the documented cap |
| `DIVISION_BY_ZERO` | evaluation-time only | returned per row from preview/projection; never a validation failure |
| `EVALUATION_TYPE_ERROR` | evaluation-time only | per-row arithmetic/type failure |
| `EVALUATION_NULL_OPERAND` | evaluation-time only | required operand is null for that activity |

Validation behavior must not change: division by zero continues to validate, and
evaluation-time conditions surface only per row.

## Frontend consumption plan (Agent 1, after availability)

1. `apps/web/src/p6-formula-api.ts`: add `update`, `remove`, `versions`, `audit`,
   `preview`, each shape-checked like `list`/`create`; extend `assertFormulaColumnRecord`
   with an optional `expectedVersion`/error-code reader.
2. `apps/web/src/p6-formula-panel.ts`: enable Edit/Delete only when
   `canWrite`; send `expected_version`; render `REVISION_CONFLICT` /
   `FORMULA_VERSION_CONFLICT` with a reload-and-retry path; render version and
   audit lists; render a preview table with per-row `error_code` messages.
3. `apps/web/src/main.ts`: wire the handlers, invalidate the layout when a
   definition used by the current layout is deleted, and refresh the
   control-room projection afterwards.
4. `apps/web/e2e/formula-columns-v26.mjs`: add scenarios for edit, stale version,
   stale revision, delete, delete-while-in-layout, versions, audit and preview.

## Acceptance for the backend slice

- PATCH/DELETE reject mismatched `expected_version` and `X-Project-Revision`
  with the documented 409 codes and do not mutate storage.
- Version numbers increase monotonically per formula; versions and audit are
  append-only within the tenant/project scope.
- Preview output equals control-room projection values for the same definitions
  and activities, including `null` for division by zero.
- Cross-tenant/cross-project reads return 404, never another project's formula.
- `PROJECT_READ` may preview/read versions/audit; `PROJECT_WRITE` is required for
  PATCH/DELETE.
