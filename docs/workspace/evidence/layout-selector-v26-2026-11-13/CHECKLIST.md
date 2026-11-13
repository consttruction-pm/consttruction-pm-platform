# WS-007 — Activities saved-layout lifecycle (2026-11-13)

Contract: `cubi-layout-selector-v26.v1`
Suite: `apps/web/e2e/layout-selector-v26.mjs`
Report: `layout-selector-v26.json` (15/15 scenarios, 0 exceptions, 0 console errors, 0 failing API responses)
Screenshots: `01`–`18`
Tested code: stamped in the report as `testedCodeSha` / `gitHead`.

## Help topics

- [Customizing Activity Layouts](https://docs.oracle.com/cd/G48902_01/client_help/en_US/customizingactivitylayouts.htm) — layouts hold table columns, grouping and display settings; they are saved, named, reopened and deleted per user/project.
- [Open a layout](https://docs.oracle.com/cd/G48902_01/client_help/en_US/open_a_layout.htm) — View > Layout > Open; “You are prompted to save the current layout”; selecting a layout and clicking Apply previews it without closing the dialog.
- [Create a new activity layout](https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_a_new_activity_layout.htm) — a new layout starts from an existing/default format under a new name, then Save publishes later edits.
- [Save a layout in the Activities or Resource Assignments window](https://docs.oracle.com/cd/G48902_01/client_help/en_US/save_a_layout_in_the_activities_or_rsrc_assignments_window.htm) — saving requires the activity-layout privilege; project layouts need the project-layout privilege.
- [Delete a layout](https://docs.oracle.com/cd/G48902_01/client_help/en_US/delete_a_layout.htm) — Delete is offered inside the Open Layout dialog and is gated by the global layout privilege.

CUBI divergence: the preview layout service stores **one project document and one user
document per view**, not a named collection. New, Save As and Import therefore write the
user slot (confirming replacement). Delete cannot be implemented until the service exposes
a delete route; the control renders disabled with that truthful reason and the contract
request `docs/workspace/architecture/p6-layout-lifecycle-contract-request.md` asks for it.

## Environment

- `PYTHONPATH=src python3 -m construction_pm.preview --web-root apps/web --host 127.0.0.1 --port 4218 --database /tmp/cubi-ws007b.sqlite --reset`
- Fixture: Riverside Pump Station Upgrade (`preview-rps-01`, seeded project layout “Classic Schedule Layout” r1) and Northside Substation Expansion (`preview-nse-02`) for isolation; tenant `cubi-preview-tenant`.
- Roles: Planner (write) and Viewer (read-only).
- Viewports: en/LTR 1440×900 desktop flow, fa/RTL 1280×720, en/LTR 1920×1080.

## Lifecycle implemented

| Operation | Path | Behaviour |
|---|---|---|
| Open / preview | `[data-layout-option]` | Reads both scopes from `GET /p6/layouts/{scope}/activity`; previews the stored revision; `[data-layout-state="preview"]` |
| Apply | `[data-layout-action="apply"]` | Keeps the preview locally and remembers it per tenant/project/user; no write |
| Cancel | `[data-layout-action="cancel"]` | Restores the definition that owned the window before the preview |
| Save | `[data-layout-action="save"]` / `layout.save` | `POST /p6/layouts/{scope}/activity` with `revision + 1` and the current presentation/group-sort metadata |
| Save As | `[data-layout-action="save-as"]` / `layout.save-as` | Copies the current layout into the user scope under a new name |
| Rename | `[data-layout-action="rename"]` | Appends a revision of the same scope with a new `layoutName` |
| New | `[data-layout-action="new"]` | Reads `GET /p6/layouts/user/activity/default`, writes the canonical columns to the user scope under the prompted name (confirms replacement) |
| Reset to Default | `[data-layout-action="reset-default"]` | Writes default columns + `normalizePresentation(undefined)` + `wbs`/`wbs asc` plan to the user scope, keeping the stored name; updates the browser presentation before render |
| Delete | `[data-layout-action="delete"]` | Disabled; title states the layout service has no delete endpoint. **BLOCKED_EXTERNAL** |
| Export / Import | `[data-layout-action="export"]`, `[data-layout-action="import"]` | `cubi-layout.v1` file; import always validates against the registry and writes the user scope |
| Reload | `[data-layout-action="reload"]` | Re-reads the current scope from the server |
| Dirty state | `[data-layout-state="dirty"]` | `layoutHasUnsavedChanges` compares group mode, ordered sort levels and presentation with the stored metadata |
| Unsaved prompt | `window.confirm` via `confirmDiscard` | Asked before previewing another layout, Reload, New or Reset when dirty |
| Revision conflict | `reportLayoutFailure` | `REVISION_CONFLICT` / `IMMUTABLE_LAYOUT_REVISION` reload the authoritative head and show the localized conflict notice |
| Reload restoration | `restoreStoredLayoutSelection` | Per-user selection key restores the chosen user layout after a full reload and a project switch |
| Isolation | selection store + API scope | Keyed `tenant:project` in `cubi:workspace-layout-selection:<user>`; the server scopes layouts by tenant/project/revision |

## Scenarios

| # | Proof | Result |
|---|---|---|
| 01 | Selector sits above the table, shows the stored name `Classic Schedule Layout` and `Project layout · r1`, menu starts closed, rows/columns rendered. | pass |
| 02 | Catalogue lists only stored scopes (project), marks the current one, and enables Save As for Planner. | pass |
| 03 | Save As prompts, writes a real user layout `Field team view` at r0, the trigger switches and the menu shows two options. | pass |
| 04 | Hiding a column commits it to the user layout; previewing the project layout restores the hidden column and shows the preview badge; Cancel restores the user layout exactly. | pass |
| 05 | Apply + full reload restores the selected project and user layouts; scope/revision match the server. | pass |
| 06 | Save advances the user revision, keeps the name, and leaves rows, widths and visible columns unchanged. | pass |
| 07 | The second project has its own project layout and no user layout; returning to the first project restores its user selection and two-option catalogue. | pass |
| 08 | fa/RTL: `dir=rtl`, selector visible, menu stays inside the viewport, two options. | pass |
| 09 | 1280×720, 1366×768 and 1920×1080: selector visible, <120 px tall, menu inside the viewport. | pass |
| 10 | Rename writes the new name; Export produces `cubi-layout.v1` without scope/revision/tenant/project; Import writes `Imported crew layout`, advances the revision, preserves columns and activity rows. | pass |
| 11 | Group & Sort changes group mode to `none`: the chip reads `Unsaved changes`, the stored revision and `groupSort` metadata are unchanged; Save appends a revision with `groupBy: "none"`, clears the chip and keeps the rows. | pass |
| 12 | New writes `Default crew layout` with the exact canonical default column ids to the user scope at a higher revision; the project revision and columns are byte-identical; rows unchanged. | pass |
| 13 | Hiding a column then Reset to Default restores the default column ids/visibility and presentation, keeps the stored name, sets `groupBy: "wbs"`, un-hides the column, keeps rows, and survives a full reload. | pass |
| 14 | Delete is disabled with the “delete endpoint” reason; New/Reset enabled for Planner; with unsaved changes, opening the project layout asks the discard prompt — declining keeps the user layout, accepting previews the project layout, and Cancel restores. | pass |
| 15 | Viewer: Save, Save As, Rename, New, Reset, Import and Delete are disabled with the role reason; opening the menu appends no revision. | pass |

## Boundary and persistence

- Reads: `GET /p6/layouts/{scope}/activity`, `GET /p6/layouts/{scope}/activity/default`, `GET /p6/layouts/{scope}/activity/revisions` (history), `GET /p6/fields/p6-field-registry.v1`.
- Writes: only `POST /p6/layouts/{scope}/activity` with `{revision, columns, metadata}`; the service appends a revision and rejects stale bases (`REVISION_CONFLICT`, `IMMUTABLE_LAYOUT_REVISION`).
- Payload is presentation only (columns, widths, alignment, visibility, presentation, group/sort, collapsed WBS). No activity, relationship, WBS or date field is part of any write.
- Project layout is never written by New, Reset, Save As or Import; only an explicit Save of the currently open project layout appends a project revision.
- Permissions: `PROJECT_WRITE` (Planner / Project administrator). Viewer gets the read-only reason and no enabled write.
- No Oracle branding was introduced; labels are CUBI/localized (`en`, `fa`).

## Known limits

- Delete is **BLOCKED_EXTERNAL**: no `DELETE /p6/layouts/{scope}/activity` route exists. Request filed in `docs/workspace/architecture/p6-layout-lifecycle-contract-request.md`.
- One user layout document per project/view: New/Save As/Import replace that slot (with a confirmation for New); there is no independent named collection to list, so the catalogue shows at most two entries.
- Dirty state covers group/sort and presentation only; column edits are appended by the layout service immediately, so they are never “unsaved”.
- Resource Assignments and Tracking layouts are outside this slice.
