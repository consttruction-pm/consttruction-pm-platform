# V29 — Activity child collections: Codes, Notebook, Steps, WPs & Docs

All four write paths are a vertical slice:
UI → HTTP → authorization → application service → repository → SQLite persistence →
read-back → UI reload. No browser-only store and no sample data is used for writes.

## Activity Codes (R4)

- Contract: `p6-activity-code-api.v1`, kind `p6_activity_code_list` / `p6_activity_code`.
- Routes: `GET/POST /api/projects/{p}/p6/activities/{id}/codes`,
  `DELETE …/codes/{assignmentId}`.
- Storage: `p6_activity_code_assignment` (tenant, project, assignment, activity,
  code type, code value, description, record revision, timestamps) with a unique
  `(tenant, project, activity, code_type)` index.
- Behaviour: assigning an existing type **replaces** its value and increments the
  assignment's record revision. Delete is scoped by activity and assignment, so a
  wrong activity cannot delete another activity's code.
- Authorization: `PROJECT_READ` for list, `PROJECT_WRITE` for assign/remove; a
  viewer receives 403. Cross-tenant/project scopes are rejected before storage.
- Verified: `tests/test_p6_activity_children.py`, `tests/test_activity_children_http_routes.py`,
  E2E `activity-children-v29` (assign → reload → remove).
- Boundary: the *Enterprise Activity Codes dictionary* (code type definitions) is an
  Enterprise-menu capability and remains outside the Activities workspace; the Details
  tab stores the assigned type/value honestly instead of inventing dictionary rows.

## Notebook (R5)

- Contract: `p6-activity-notebook-api.v1`.
- Routes: `GET/POST …/notebook`, `PATCH/DELETE …/notebook/{topicId}`.
- Storage: `p6_activity_notebook_topic` with `sequence`, `record_revision`, timestamps.
- Add/modify/delete are real; ordering is server-assigned (max + 1).
- HTML body: the server sanitises to an allow-list (`b, strong, i, em, u, br, p, ul,
  ol, li`); scripts, attributes and unknown elements are removed, text is escaped.
  The E2E asserts `<b>agreed</b>` survives and `<script>` does not.
- Modify and delete require `expected_record_revision`; a stale revision returns
  **409 REVISION_CONFLICT** and the UI shows `REVISION_CONFLICT`.
- Comments in the rail remain a separate conversation surface; the Notebook tab no
  longer displays browser-local comments as if they were notebook topics.
- Verified: same Python/HTTP tests and E2E (add → reload → modify → delete).

## Steps (R6)

- Read contract unchanged in shape; each step now carries `percent_complete` from the
  separate `p6_activity_step_completion` record.
- New write API `P6ActivityStepWriteAPI`:
  `POST …/steps`, `PATCH …/steps/{stepId}`, `DELETE …/steps/{stepId}`.
- Create-only `upsert` and its immutable-replay test are preserved. Editing goes through
  `replace`, which requires the step to exist at the caller's project revision; delete
  removes both the step definition and its completion record.
- Move is implemented as two ordered PATCH calls swapping sequence numbers; the UI
  disables the first/last move direction. A single-step list is a no-op.
- Step percent and weight are **step-level values**. They are not used to recompute the
  activity percent complete, dates, float or critical path. The activity value stays
  the Shared Scheduling Core's authoritative number.
- Verified: `tests/test_p6_activity_step_write_api.py`, route tests, E2E add → reload
  (percent 10) → modify (percent 60) → move → delete.

## WPs & Docs (R7)

- No new document service was created. Link/unlink writes `linked_entity_refs` through
  the existing `updateDocument` contract and the document revision guard.
- Link appends the activity ID; unlink removes refs equal to the activity ID/code.
- The tab lists the authoritative document records, exposes unlink controls only when
  the document collection is loaded and writable, and offers a real picker for
  unlinked documents. When the fixture has no unlinked document, the control is
  disabled rather than faked.
- Verified: E2E creates a document through the existing service, links it to A130,
  reloads, sees the link, unlinks, and confirms the link is gone.

## Risks and Issues

Existing `workspace-issues.ts` / `workspace-risks.ts` and their APIs (create, update,
delete, history/comment) remain the single path; no parallel form or model was added.
Their list data is read into the Details tabs, and the project Issues/Risks windows are
unchanged. The disposition matrix records which individual issue/risk topics were not
individually exercised in this round.

## Error handling and isolation

- 403: cross-scope or missing permission.
- 404: child record not found (`*_NOT_FOUND`).
- 409: record revision conflict (Notebook) or project revision conflict (Steps).
- 400: invalid payload/field.
- Tenant and project are taken from the authenticated lifecycle context, never from
  browser-supplied scope fields.
- Writes are idempotent where the contract is create-by-id (steps, codes replace);
  duplicate protection is the unique code-type constraint and the fixed step IDs.
