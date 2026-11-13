# Contract request — P6 layout lifecycle API (`p6-layout-lifecycle-api.v1`)

Status: **REQUESTED — Agent 3 / Shared Core**
Owner of this request: Agent 1 (frontend / workspace integration)
Requested: 2026-11-13
Related evidence: `docs/workspace/evidence/layout-selector-v26-2026-11-13/`

## Why

WS-007 now covers Open/preview, Apply, Cancel, Save, Save As, Rename, New from
defaults, Reset to Default, Export/Import, dirty state, the unsaved-changes prompt,
revision-conflict recovery and reload restoration in the Activities window.
15/15 browser scenarios pass against the existing layout routes.

The remaining WS-007 operation is **Delete with revision protection** (Oracle:
[Delete a layout](https://docs.oracle.com/cd/G48902_01/client_help/en_US/delete_a_layout.htm)).
The layout service offers save/get/default/revisions only:

- `src/construction_pm/p6_layout_definition_api.py` exposes `save`, `get`,
  `default_layout`, `list_revisions`.
- `src/construction_pm/http/project_lifecycle_routes.py` serves only
  `GET|POST /p6/layouts/{scope}/{view}` plus `/default` and `/revisions`.
- `apps/web/src/p6-api.ts` therefore has no delete call, and the selector renders
  Delete disabled with the truthful reason “the layout service has no delete
  endpoint”.

The UI will not fake a removal or hide the button silently. Once the route exists,
the frontend can enable the action without a redesign.

## Requested route

| Method | Path | Permission | Purpose |
|---|---|---|---|
| `DELETE` | `/api/projects/{project_id}/p6/layouts/{layout_scope}/{view_id}` | `PROJECT_WRITE` | Delete one stored layout scope with optimistic concurrency |

### Preconditions

- `X-Project-Revision` header must equal the project revision the client read.
- Body `expected_revision` (or `If-Match`) must equal the stored layout revision.
- A stale revision must return `409 REVISION_CONFLICT` and delete nothing.
- Deleting an absent scope returns `404 P6_LAYOUT_NOT_FOUND`.
- Scope rules: `project` requires the project-layout write privilege; `user` may be
  deleted by the owning session. Global layouts are out of scope (the preview
  service has no global scope).

### Request / response shapes

Body:

```json
{
  "contract_version": "p6-layout-lifecycle-api.v1",
  "expected_revision": 7
}
```

Response: `200` with the deletion record so the client can update its catalogue:

```json
{
  "contract_version": "p6-layout-lifecycle-api.v1",
  "kind": "layout_definition_deleted",
  "scope": { "tenant_id": "...", "project_id": "...", "project_revision": 12 },
  "layout_scope": "user",
  "view_id": "activity",
  "deleted_revision": 7
}
```

Alternative acceptable shape: `204 No Content` plus the same envelope on the next
`GET` as a `404 P6_LAYOUT_NOT_FOUND`.

### History semantics

The layout history is append-only. A delete must not rewrite or renumber historical
revisions. The recommended model is a tombstone row:

- append a `layout_definition_deleted` event keyed by
  `{tenant_id}:{project_id}:{layout_scope}:{view_id}@{deleted_revision}`;
- `GET /p6/layouts/{scope}/{view}` then returns `404 P6_LAYOUT_NOT_FOUND`;
- `GET /p6/layouts/{scope}/{view}/revisions` keeps the prior revisions and may
  expose `{revision, deleted_at}` for the tombstone.

If a tombstone is not possible, state the chosen behaviour; the frontend only needs
a deterministic post-delete read (404) and a non-destructive history.

## Optional follow-ups (not required for WS-007 Delete)

Oracle layouts are a **named collection** per user/project
([Create a new activity layout](https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_a_new_activity_layout.htm)).
CUBI currently stores one project document and one user document per view, which is
why New/Save As/Import replace the user slot. A future contract could add:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/projects/{project_id}/p6/layouts/{layout_scope}/{view_id}/definitions` | List named layouts in a scope |
| `POST` | `.../definitions` | Create a named layout (`PROJECT_WRITE`, unique name per scope) |
| `PATCH` | `.../definitions/{layout_id}` | Rename/replace with `expected_revision` |
| `DELETE` | `.../definitions/{layout_id}` | Delete one named layout |

This would let the catalogue show more than two entries and make Delete scoped to a
single named layout rather than the whole user slot. It is not needed to unblock the
current button; the single-scope delete above is the minimal change.

## Return-to-Agent-1 criteria

- The route is registered in preview and production composition.
- Permission and scope tests cover `PROJECT_READ` denial, stale revision, absent
  scope, project vs user scope, and tenant/project isolation.
- A browser scenario can delete the user layout, see it disappear from the
  catalogue, keep the project layout intact, and recover after reload.
- Until then, WS-007 Delete stays **BLOCKED_EXTERNAL** and no UI claim says the
  layout was deleted.
