# Column formulas — audit record (2026-11-06)

Scope: the directive requirement "Column Formula / formula settings". A saved
formula column is a real computed Activity field, persisted as an immutable
formula definition and evaluated only by the Shared Formula Core on the server.
The browser never evaluates an expression and never invents a result type.

## Reference position

- The supplied Version 26 help (`G57535-02`) documents the Columns dialog and
  Edit Column on PDF pages 330–331 (help pages 7–8 of 48): add/remove columns,
  order, Copy From, Apply, Default, title, width and alignment.
- It documents calculated fields with a worked formula on PDF page 129 and
  page 749, but it does **not** document a formula-column editor. The editor is
  therefore an extension built to satisfy the delivery directive; it is not
  claimed as a verbatim v26 dialog.
- No Oracle/Primavera branding or proprietary assets were introduced.

## What was built

### Owning backend layer

- `src/construction_pm/p6_formula_column.py` — `P6FormulaColumnService` and
  `P6FormulaColumnAPI`. A definition is normalised to the `formula.` prefix,
  compiled by the shared formula engine, rejected on unknown fields or
  self-reference, persisted through the existing formula definition repository
  (`FormulaDefinitionCreateRequest`, metadata
  `{"source":"cubi-formula-column","subject_area":"Activity"}`), and evaluated
  in dependency order per activity. Invalid rows and missing cells return
  `null`; nothing is synthesized.
- `src/construction_pm/p6_formula_definition_repository.py` — `list_all` added
  to the protocol and to the SQLite, PostgreSQL and application-service
  implementations. The SQLite preview row is stored in
  `p6_formula_definitions` with `semantic_version = cubi-formula-column.v1`.
- `src/construction_pm/p6_field_registry_api.py` — formula columns are projected
  into the Activity field registry as `computed`, `read_only`, with their real
  `data_type` and the persisted `formula` expression.
- `src/construction_pm/p6_formula_authority_api.py` — the validator's field
  schema includes saved formula columns, so an expression can reference one.
- `src/construction_pm/backend_p0/workspace_read_provider.py` — evaluated
  values are injected as `formula.<id>` cells for formula columns visible in the
  saved layout. `activity.percent_complete` was added to the persisted cell map;
  it is read from the schedule, not derived in the browser.
- `src/construction_pm/preview/runtime.py` — the SQLite repository, definition
  service, column service, registry, validator and both read providers are
  wired in the preview composition.
- `src/construction_pm/http/project_lifecycle_routes.py` — 
  `GET /api/projects/<project>/p6/formula-columns` returns
  `p6-formula-column-api.v1`; `POST` validates `formula_id`, `title` and
  `expression`, returns 400 on a `P6FormulaColumnError`, and enforces the
  project scope and write permission.
- `src/construction_pm/http/production_composition.py` — accepts the column-API
  parameter but the production composition does not construct it. Production
  therefore does not silently expose the preview capability.

### Web layer

- `apps/web/src/p6-formula-api.ts` — `createP6FormulaColumnClient` with `list`
  and `create`; every record is shape-checked (`assertFormulaColumnRecord`), so
  a malformed response throws instead of rendering.
- `apps/web/src/p6-formula-panel.ts` — the editor now has a save section
  (column title, formula column ID, submit) and a saved-column catalogue. Saving
  is gated by the authoritative validator; an invalid expression is never
  persisted.
- `apps/web/src/main.ts` — after a successful save, the registry is re-read,
  the new field is added to the persisted layout, the layout is committed and
  the workspace is re-rendered from the server.
- `apps/web/src/workspace-model.ts` — `setP6Presentation` carries the registry
  `formula` expression instead of forcing `null`.
- `apps/client-sync/src/p6-presentation-contract.ts` — `P6Field.formula` added;
  a formula is only accepted on a `computed` field.
- `apps/web/styles.css` and `apps/web/public/styles.css` — identical save and
  catalogue styles (byte-identical check below).

## Live evidence (real preview runtime)

Runtime: `preview-rps-01`, data date not yet set, 14 activities, local SQLite
`cubi-wbs-collapse.sqlite3`, local full-stack preview, not production. Signed in
as `preview-planner` (Planner).

| Check | Result |
| --- | --- |
| Validate `[activity.duration_percent_complete] * 2` | Valid expression; dependency `activity.duration_percent_complete`; result type `double` |
| Save title `Double progress`, ID `formula.double_progress` | Succeeded; catalogue lists title, ID, `double` and the expression |
| Persisted row (`p6_formula_definitions`) | `formula.double_progress`, version 1, expression, `number`, dependencies JSON, `cubi-formula-column.v1` |
| Grid after save | Header `Double progress ƒx`; A100/A110/A120 `200.0`, A130 `75.0`, not-started rows `—`, WBS band rows blank |
| Grid after full page reload | Same header and values, proving persistence rather than local state |
| Workspace read API | Column `{id: formula.double_progress, data_type: double, editable: false, formula: "[activity.duration_percent_complete] * 2"}`; A100 cell `"200.0"` |
| Invalid expression `[activity.missing_field] * 2` | Rejected with `FIELD_NOT_FOUND:activity.missing_field`; nothing saved |
| Persian RTL | Same column and values, mirrored table, WBS band colour kept in the last columns |

Screenshots (1280×720, real authenticated runtime):

- `docs/workspace/screenshots/visual/62-formula-column-grid-en-1280.png` — grid
  scrolled to the last columns; `Double progress ƒx` and `Predecessors` both
  visible, band colour continues through them.
- `63-formula-column-reloaded-en-1280.png` — identical after a full reload.
- `64-formula-editor-catalogue-en-1280.png` — Project > Formula editor with the
  context field, expression and Validate controls.
- `67-formula-editor-saved-catalogue-en-1280.png` — save section and the saved
  column entry.
- `65-formula-invalid-en-1280.png` — authoritative rejection of an unknown field.
- `66-formula-column-grid-fa-1280.png` — Persian RTL at the same columns.

Capture tool: `docs/workspace/qa/formula-column-shot.mjs` (headless Chrome over
CDP; logs in through the real `/preview/login` persona form).

## Verification

- `py -3 -m pytest tests/test_p6_formula_column.py tests/test_project_lifecycle_http_routes.py tests/backend_p0 -q` — **191 passed**.
- `npx tsc --noEmit` — passed.
- `npx tsx --test src/*.test.ts` — **637 passed, 0 failed**.
- `npm test` preview resolver — **14 passed, 0 failed**.
- `npm run build` — passed.
- `cmp apps/web/styles.css apps/web/public/styles.css` — identical.

## Deliberately not claimed

- Production composition does not construct `P6FormulaColumnAPI`; formula
  columns are a preview capability until production wiring is authorised.
- No formula column deletion, rename, reorder or edit-in-place; no expression
  function catalogue beyond the shared engine; no cross-project formula sharing.
- The reference PDF does not describe a formula-column dialog, so this is an
  extension, not a v26 visual match.
- No `main` merge and no Production deployment were performed. PR #1716 must not
  merge independently.
