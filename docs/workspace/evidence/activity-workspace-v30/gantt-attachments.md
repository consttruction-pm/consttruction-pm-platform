# V30 — Gantt curtain, text and notebook attachments

## Contract

- Module: `src/construction_pm/p6_gantt_attachment.py`
- API version: `p6-gantt-attachment-api.v1`
- Kinds: `curtain | text | notebook`
- Route: `/api/projects/{project_id}/p6/gantt/attachments` (GET, POST) and
  `/api/projects/{project_id}/p6/gantt/attachments/{attachment_id}` (PATCH, DELETE)
- Permissions: `PROJECT_READ` for GET, `PROJECT_WRITE` for writes, checked through the same
  authorization policy as every other P6 route. Tenant/project scope is `BackendScope`; a
  cross-tenant or cross-project scope raises `CROSS_SCOPE_ACCESS`.
- Persistence: SQLite table `p6_gantt_attachment`, unique on
  `(tenant_id, project_id, kind, attachment_id)`, indexed by project revision.
- Revision guard: every record carries `record_revision`; PATCH/DELETE require
  `expected_record_revision`. A stale value returns **409 REVISION_CONFLICT**. Create returns 201.
- Validation: colour `#rrggbb`; curtain needs a start and finish date with `start <= finish`;
  text/notebook need an activity; notebook also needs a topic ID. Visibility defaults to true.

## Drawing

`workspace-view.ts` projects the stored dates with the same `viewScale` used by the bars:

- Curtains are rendered inside `.cp-gantt-body` in a `.cp-gantt-curtains` layer at z-index 1
  (behind rows and bars), with persisted left/width and `--cp-curtain-color`. They scroll with the
  chart and are clipped to the visible range.
- Text and notebook links are rendered at the activity bar’s left edge and row top in a
  `.cp-gantt-attachments` layer at z-index 4, carrying `data-gantt-attachment-kind` and
  `data-gantt-attachment-activity`.
- The board exposes `data-gantt-curtains`, `data-gantt-text-attachments` and
  `data-gantt-notebook-attachments` counts.
- Hidden records are not drawn but remain listed and persisted.
- No attachment changes a schedule date, percent, float or critical path. Notebook bodies stay in
  the Activity Details Notebook tab.

## UI

`workspace-gantt-attachments.ts` parses the authoritative DTO and owns the four client calls.
`main.ts` loads the project’s attachments with the workspace, keeps them per project and re-reads
after each write. `workspace-view.ts` renders the dialog described in `dialog-field-audit.md`.

## Evidence

- `gantt-attachments-v30.json` (E2E, dedicated port 4200, fresh SQLite):
  - created a curtain from two real timescale dates and asserted it drew with a real pixel width;
  - created a text mark and a notebook mark on A130 and asserted kind/activity attributes;
  - hid the curtain (gone from the Gantt, still stored), reloaded the workspace and proved the
    hidden state persisted while text/notebook remained;
  - showed it again, edited the text label (revision advanced), rejected a stale PATCH with 409;
  - deleted every created record; a read-only **viewer** received 200 on GET and **403** on POST.
- `test_p6_gantt_attachment.py` (5 tests): round trip, validation, revision guard, scope isolation.
- `test_gantt_attachment_http_routes.py` (3 tests): 201/200/409/404 route mapping.
- `visual-matrix-v30`: 12 dialog cells (6 themes × EN/FA) with fitted-dialog assertions.

## Remaining limits

- Attachment files (WPs & Docs notebook link kinds) are not copied into attachments; only a topic
  ID link is stored, which matches the reference’s “attach notebook items to bars” surface.
- Drag-to-edit a curtain on the chart is not implemented; ranges are edited in the dialog.
- No separate “hide all curtains” button; the per-record Hide action covers the reference’s
  behaviour, and the dialog can hide each row.
