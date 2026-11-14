# Contract request — tracking layout lifecycle (`p6-tracking-layout-api.v1`)

Status: **REQUESTED — Agent 3 / Shared Core**
Owner of this request: Agent 1 (frontend / workspace integration)
Requested: 2026-11-14
Related audit: TRK-001 (tracking layout lifecycle and sharing)

## Why

The Tracking window renders a real read model (`tracking-read-model.v1`): the
published schedule FACT projection, persisted activity masters and persisted
assignment facts, with four views (`table`, `bar-chart`, `gantt-profile`,
`resource-analysis`) and scale/group/sort controls. It deliberately runs no CPM,
leveling or money math.

Those controls are **session-only**. `apps/web/src/workspace-tracking.ts` keeps
`state.view` and `state.query` in memory; there is no save, open, share, import,
export or delete operation, and the Publish toolbar entry is disabled with the
truthful reason "no backend". A reload returns the default view. The window also
has no column chooser or filter surface to persist, so a stored layout would
currently cover only the four fields the read model returns.

`p6_code_reference.py` (VIEW-004) records that tracking layouts have no
source-to-renderer map. The activity-layout service
(`p6_layout_definition_api.py`) cannot be reused: its payload is an activity
column layout and it has one user document per view, with no delete route.

The UI will not fake a saved layout in localStorage and call it storage, and it
will not offer Share/Publish against a non-existent project scope.

## Requested routes

| Method | Path | Permission | Purpose |
|---|---|---|---|
| `GET` | `/api/projects/{project_id}/p6/tracking-layouts/{layout_scope}` | `PROJECT_READ` | List stored tracking layouts for `user` or `project` scope |
| `GET` | `/api/projects/{project_id}/p6/tracking-layouts/{layout_scope}/{layout_id}` | `PROJECT_READ` | Read one stored layout and its revision |
| `POST` | `/api/projects/{project_id}/p6/tracking-layouts/{layout_scope}` | `PROJECT_WRITE` | Save or revise a named layout (append-only revision) |
| `DELETE` | `/api/projects/{project_id}/p6/tracking-layouts/{layout_scope}/{layout_id}` | `PROJECT_WRITE` | Delete one layout with revision protection |
| `POST` | `/api/projects/{project_id}/p6/tracking-layouts/import` | `PROJECT_WRITE` | Validate and store a portable layout document |
| `GET` | `/api/projects/{project_id}/p6/tracking-layouts/{layout_scope}/{layout_id}/document` | `PROJECT_READ` | Return the canonical portable document for download |

`layout_scope` is `user` or `project`. Publishing to `project` scope (the Share
operation) requires `PROJECT_ADMIN`; reading project scope requires
`PROJECT_READ`. A user-scope write must bind the authenticated user id and must
not accept another user's id from the request body.

## Layout payload

```json
{
  "contract_version": "p6-tracking-layout-api.v1",
  "kind": "tracking_layout",
  "layout_id": "…",
  "name": "Civil weekly tracking",
  "scope": "user",
  "view": "gantt-profile",
  "scale": "week",
  "group_by": "wbs",
  "sort": "start",
  "direction": "asc",
  "column_ids": ["activity_id", "start", "finish"],
  "show_legend": true,
  "show_data_date": true,
  "show_non_working": true,
  "baseline_id": null,
  "record_revision": 3
}
```

- `view`, `scale`, `sort` and `direction` must be validated against the same
  frozen sets the read model uses (`TRACKING_VIEWS`, `TRACKING_SCALES`,
  `TRACKING_SORTS`, `TRACKING_DIRECTIONS`).
- `column_ids` must resolve against the live field registry. An unknown id is
  rejected, not silently dropped.
- `baseline_id` must reference a stored baseline in the same project scope.
- Unknown extra keys are rejected so a future client cannot smuggle tenant,
  project or revision values.

## Required semantics

- Saves are append-only revisions. A stale `expected_revision` returns
  `TRACKING_LAYOUT_REVISION_CONFLICT` and stores nothing. A repeat of identical
  content at the same revision is idempotent.
- Open returns the stored document; the client applies it to the window state
  and re-reads the tracking projection. Applying a layout never changes activity
  or schedule records.
- The portable document (`cubi-tracking-layout.v1`) contains only format, name,
  layout fields and metadata. It must not contain tenant, project, user or
  revision identity. Import validates the format, name, enums and columns, then
  writes to the caller's user scope at `existing.revision + 1`.
- Delete requires `expected_revision`, removes only the addressed layout and
  returns the deleted revision. A missing layout returns 404, a stale revision
  409.
- Scope isolation: a user-scope layout is visible only to its owner; a
  project-scope layout is visible to every authorized reader but writable only
  by an administrator.

## Failure codes the UI expects

`TRACKING_LAYOUT_NOT_FOUND`, `TRACKING_LAYOUT_REVISION_CONFLICT`,
`TRACKING_LAYOUT_NAME_REQUIRED`, `TRACKING_LAYOUT_SCOPE_INVALID`,
`INVALID_TRACKING_LAYOUT_DOCUMENT`,
`TRACKING_LAYOUT_COLUMN_NOT_IN_REGISTRY`,
`TRACKING_LAYOUT_BASELINE_NOT_FOUND`,
`TRACKING_LAYOUT_IMPORT_CONFLICT`,
`TRACKING_LAYOUT_WRITE_NOT_AUTHORIZED`,
`TRACKING_LAYOUT_DELETE_NOT_AUTHORIZED`.

## What the frontend will do once the contract exists

1. Add a layout selector to the Tracking window (Open, Save, Save As, Rename,
   Delete, Export, Import, Publish) using the same dirty-state and
   revision-conflict patterns as the Activities layout selector.
2. Render Share/Publish only for an administrator, targeting `project` scope,
   and label the resulting layout as shared.
3. Keep the read model as the only source of values; a saved layout stores
   presentation choices and never schedule facts.
4. Show every rejection code verbatim in en and fa, and leave the window state
   unchanged after a rejected write.

## Acceptance evidence requested from Agent 3

- Repository round-trip tests for user and project scope, append-only revisions,
  stale revision, idempotent replay, delete, scope isolation and permission.
- Import/export tests proving the portable document contains no tenant, project,
  user or revision identity and that malformed/foreign documents are rejected.
- A fixture with two stored layouts so the browser suite can prove open, switch,
  reload persistence, rename, delete, export/import round trip and an
  administrator publish, in en and fa RTL.
