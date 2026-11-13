# FORMULA-001 — Computed Formula Column Lifecycle (2026-11-13)

Contract: `cubi-formula-columns-v26.v1`
Suite: `apps/web/e2e/formula-columns-v26.mjs`
Report: `formula-columns-v26.json` (10/10 scenarios, 0 exceptions, 0 console errors, 0 failing API responses)
Screenshots: `01`–`10`
Tested code: stamped in the report as `testedCodeSha` / `gitHead` (the suite writes the exact commit it ran against).

## Help topics

V26 HTML Help has **no native formula-column editor topic**. This is a CUBI extension built on
the Activity Table column model, so the claim is traceability to the column model, not parity with a
P6 dialog:

- [Define Activity Table columns](https://docs.oracle.com/cd/G48902_01/client_help/en_US/define_activity_table_columns.htm) — View > Columns; add/remove individual columns, add all/remove all, order left to right, Copy From, OK/Apply/Default, and at least one column must remain.
- [User defined fields](https://docs.oracle.com/cd/G48902_01/client_help/en_US/user_defined_fields.htm) — custom fields are shown as Activity Table columns and can be used to group, sort and filter. The formula column is presented in the same column surface.

The audit note `docs/qa/COLUMN_FORMULA_AUDIT_2026-11-06.md` records that no official V26 topic
documents a formula editor; the expression language is the project field registry contract
(`p6-field-registry.v1`), and every value shown is computed by the server.

## Environment

- `PYTHONPATH=src python3 -m construction_pm.preview --web-root apps/web --host 127.0.0.1 --port 4206 --database /tmp/cubi-formula16.sqlite --reset`
- Fixture: Riverside Pump Station Upgrade (`preview-rps-01`), tenant `cubi-preview-tenant`, 14 activities A100–A210, 15 relationships, resource `RPS-CIVIL-CREW`.
- Viewport: en/LTR 1440×900.
- Formula panel location: Tools drawer (`[data-tools-drawer]`), opened by Project >
  `project.formula` (`tools.formula`), then `#cp-formula-editor [data-formula-editor]`.
- The grid shows the column only after an explicit **Show in grid** action; saving a definition
  does not mutate the layout (presentation stays separate from the stored definition).

## Scenarios

| # | Proof | Result |
|---|---|---|
| 01 | Planner opens the formula editor, sets title `Progress Fraction`, ID `formula.e2e_progress_fraction`, expression `[activity.duration_percent_complete] / 100`, and saves. | pass |
| 02 | Four invalid expressions are rejected with authoritative codes and plain-language messages, and nothing is persisted: `FIELD_NOT_FOUND:activity.nope`, `EXPECTED_EXPRESSION_AT_38`, `NUMERIC_OPERANDS_REQUIRED`, `UNSUPPORTED_P6_FORMULA_FIELD_TYPE:duration`. | pass |
| 03 | A valid expression reports its dependencies (`activity.duration_percent_complete`) and result type (`number`) from the validation response, never from the browser. | pass |
| 04 | Save persists the definition; the catalogue shows title, ID, `Definition version 1`, `Data type: double`, `Result type: number`, expression, referenced fields and the **Show in grid** action. | pass |
| 05 | Show in grid adds the field to the persisted layout; the header renders `Progress Fraction` with the `ƒx` marker and every grid cell equals the server value from `GET /api/v2/workspace/control-room/read` (`1.0`, `0.375`, `null` → `—`). | pass |
| 06 | A full reload restores the column and the same authoritative cell values. | pass |
| 07 | A duplicate ID is rejected with `FORMULA_COLUMN_ALREADY_EXISTS`; the stored definition is not overwritten. | pass |
| 08 | Division by zero (`... / 0`) validates; all 14 server cells are `null` and the grid renders `—`. The UI never fabricates `NaN`, `Infinity` or `0`. | pass |
| 09 | Viewer: save and apply are absent, a read-only reason is shown, validation still works, and no write is issued. | pass |
| 10 | No evaluation endpoint is contacted by the browser; the final read returns the stored definition and there are zero exceptions, console errors and 5xx responses. | pass |

## API / persistence boundary

- Validation: `POST /api/projects/{project_id}/p6/formulas/p6-field-registry.v1`
  body `{expression, context_field_id?}` → `{validation:{valid,error_code,message_key}, dependencies:{field_ids}, result_type:{data_type}}`.
  Requires `PROJECT_READ`.
- Definition list/create: `GET|POST /api/projects/{project_id}/p6/formula-columns`
  (`p6-formula-column-api.v1`); create requires `PROJECT_WRITE`.
- Layout: `POST /api/projects/{project_id}/p6/layouts/project/activity` (presentation only).
- Values: `GET /api/v2/workspace/control-room/read` returns the columns and the server-evaluated
  cell strings; the client projects them verbatim.
- Frontend never evaluates an expression. `apps/web/src/p6-formula-api.ts` shape-checks every
  record; `apps/web/src/p6-formula-panel.ts` renders validation, catalogue and errors;
  `apps/web/src/main.ts` wires `canWrite`, layout membership, projection refresh and apply.

## Permissions

| Action | Role | Result |
|---|---|---|
| Validate expression | any reader (`PROJECT_READ`) | allowed, including Viewer |
| Create definition | `PROJECT_WRITE` (Planner, Project administrator) | allowed |
| Show in grid / commit layout | `PROJECT_WRITE` | allowed |
| Viewer save/apply | — | not rendered; read-only reason displayed |

## Known limits and contract gaps (Agent 3 / Shared Core)

1. No update, delete, version-list, audit-history or server-side preview endpoint exists yet. The
   backend exposes only list/create. A lifecycle contract request is tracked in
   `docs/workspace/architecture/p6-formula-column-lifecycle-contract-request.md`
   (`p6-formula-column-lifecycle-api.v1`).
2. Division by zero is an **evaluation-time** condition: validation accepts it and the server
   returns `null` cells with no per-cell error. A future contract should report
   `DIVISION_BY_ZERO` (or a null reason) so the grid can annotate the cell.
3. The preview fixture has 14 activities, not the 250+ acceptance fixture; pagination/performance
   at 250+ is not evidenced here.
4. The formula editor is a CUBI extension; no Oracle V26 Help topic documents it. No Oracle
   branding is used in the UI.
5. Saved definitions are revision-scoped by the server (`scope.project_revision`); concurrent
   stale-revision create/update semantics cannot be exercised until the update endpoint lands.
