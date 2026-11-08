# Activity Table Columns and Edit Column — reference audit (2026-11-06)

**Branch:** `codex/jalal/cubi-shell-v26-20261104`
**Reference:** supplied Version 26 help `G57535-02`, PDF pages 330–331 (help pages 6–8 of 48), Chapter 7 “Activity Table”.
**Scope:** View > Columns (also Layout Options > Columns, toolbar Columns, grid context menu > Columns…), the Columns dialog and the Edit Column dialog.

No Oracle/Primavera branding, screenshots, icons or proprietary assets were copied. The UI keeps CUBI branding and reuses the existing workspace token palette.

## Reference behaviour

- View > Columns opens a Columns dialog with an **Available Columns** section and a **Selected Options** section.
- Add a column by selecting it in Available Columns and clicking the add (right) button; add all uses the double-right button.
- Remove a column from Selected Options with the remove (left) button; remove all uses the double-left button. At least one column must remain.
- Change display order with the move-left / move-right buttons inside Selected Options.
- Copy From copies a column set from another activity layout (select layout, Open).
- OK updates the table and closes; Apply updates without closing; Default restores the layout’s default column settings.
- Edit Column changes the title, width and alignment. The default title appears in parentheses after a custom title in the dialog, but only the custom title appears in the table. Default inside Edit Column restores the default title.

## Implementation

### Server-owned default layout (owning layer)

`src/construction_pm/p6_layout_defaults.py` defines the canonical Activity Table column set
(`activity.id`, `activity.name`, `activity.planned_duration`, `activity.remaining_duration`,
`activity.duration_percent_complete`, `activity.early_start`, `activity.early_finish`,
`activity.status`) with the reference titles Activity ID, Activity Name, Original Duration,
Remaining Duration, Schedule % Complete, Start, Finish and Status.

`P6LayoutDefinitionAPI.default_layout()` returns that set as revision `0` with metadata
`{"source": "p6-layout-defaults.v1"}` and writes nothing. The HTTP route
`GET /api/projects/<project>/p6/layouts/<scope>/<view>/default` enforces session, project scope
and `PROJECT_READ`; it returns `404 P6_LAYOUT_DEFAULT_NOT_DEFINED` for a view without defaults.
The browser loads it through `loadP6DefaultLayout()`; defaults are not duplicated in the client.

### Columns dialog

`apps/web/src/p6-columns-dialog.ts` is a pure draft model plus a DOM mount:

- Draft operations: search, subject filter, select available / selected, add, add all, remove,
  remove all (keeps the first column and raises `LAST_COLUMN_REQUIRED` otherwise), move by one,
  edit title/width/alignment, restore default title, reset to server defaults filtered by the
  live registry, and `draftToLayout()` which normalises order/width/alignment and keeps the
  revision unchanged.
- Visibility is toggled per selected column; hidden columns stay in the layout and leave the grid.
- The selected list shows the custom title followed by the default title in parentheses, and the
  Edit Column dialog shows the same default title plus a Default action that restores it while
  preserving width and alignment.
- OK saves through the real layout endpoint and closes; Apply saves and keeps the dialog open,
  rebasing the draft on the saved revision so repeated applies do not produce revision conflicts;
  Cancel discards the draft. The dialog is created in `document.body`, traps focus as a modal,
  closes on Escape, and removes itself on `close`.
- **Copy From is disabled with the real reason:** the runtime stores exactly one layout per
  (scope, view) and exposes no named-layout list to copy from. A second note under the footer
  states this in both languages rather than opening a simulated picker.

`main.ts` routes `view.fields` and `layout.open` to `openColumnsDialog()`; the toolbar Columns
button, View > Columns and the grid context menu all reach the same dialog. Commits use
`currentWorkspaceState` so a dialog opened before a re-render still commits onto the latest
layout.

Both `apps/web/styles.css` and `apps/web/public/styles.css` contain the identical dialog CSS
(860 px card, three-column transfer body, selected/available lists, footer, notice, responsive
single-column layout at ≤720 px) and remain byte-identical.

## Live evidence — preview-rps-01, 1280×720

Preview runtime on port 4174, seeded database `cubi-wbs-collapse.sqlite3`, session role planner,
English LTR then Persian RTL.

| Check | Observed |
| --- | --- |
| View > Columns opens the dialog | `open: true`; Available 1 field, Selected 20 fields (the stored layout had 20 of the 21 registry fields) |
| Dialog geometry EN | 860×571 at (210, 75) inside 1280×720, direction `ltr`, selected list viewport 298 px of 334 px content (scrolls) |
| Edit Column | Activity Name: title `Activity Name`, default title `Name`, width `151`, alignment Left; opening from the selected row enables the footer Edit Column button |
| Default | 8 selected / 13 available; titles Activity ID, Activity Name, Original Duration, Remaining Duration, Schedule % Complete, Start, Finish, Status |
| OK persists | Table headers after closing: Activity ID, Activity Name, Original Duration, Remaining Duration, Schedule % Complete, Start, Finish, Status, plus the fixed Predecessors and Edit columns |
| Reload | The same headers return, proving the new layout revision is stored server-side, not only in memory |
| Apply | Dialog stays open and reports “Columns applied.”; Cancel then closes it |
| Copy From | Disabled with the one-layout-per-view reason; no fake layout picker |
| Persian RTL | 860×575 at (210, 73), direction `rtl`, panes and footer mirrored, add/remove arrows mirrored by the bidi algorithm, footer تأیید/اعمال/لغو/راهنما |

Screenshots (committed under `docs/workspace/screenshots/visual/`):

- `68-columns-dialog-en-1280.png` — dialog opened from View > Columns.
- `69-edit-column-dialog-en-1280.png` — Edit Column on Activity Name.
- `70-columns-dialog-default-en-1280.png` — after Default, canonical eight-column set.
- `71-columns-saved-default-grid-en-1280.png` — table after OK.
- `72-columns-dialog-fa-1280.png` — Persian RTL dialog.
- `73-columns-applied-en-1280.png` — Apply without closing.

Capture scripts: `docs/workspace/qa/columns-dialog-shot.mjs` and
`docs/workspace/qa/columns-dialog-measure.mjs`.

## Verification

- `npx tsc --noEmit` — clean.
- `npx tsx --test src/*.test.ts` — 646 passed, 0 failed (8 new Columns dialog tests plus the
  default-layout client test).
- `node --test preview-server.test.mjs` — 14 passed.
- `py -3 -m pytest tests/test_p6_layout_definition_api.py tests/test_project_lifecycle_http_routes.py -q` — 100 passed (default layout, scope, unknown view and HTTP route tests).
- `npm run build` — passed; `cmp styles.css public/styles.css` — identical.

## Gaps and honest limits

- The registry’s technical display names for eight activity fields are short (`Id`, `Name`,
  `Planned Duration`, `Duration % Complete`, `Early Start`, `Early Finish`, `Status`,
  `Remaining Duration`). The default layout carries the reference titles as column labels, so the
  grid matches the reference, but the Columns dialog shows those titles as customized and prints
  the short names in parentheses. Edit Column > Default therefore restores the registry name
  rather than the reference title. This is a field-metadata gap, not a rendering hack; fixing it
  means updating the seeded registry labels, which is left for the registry increment.
- Copy From needs a named-layout list service; it stays disabled rather than simulated.
- Move is exposed as up/down in the vertical Selected Options list; the reference describes the
  same operation as moving a column left/right in the table.
- The Available Columns Options bar in the reference (grouping and expand/collapse of available
  fields) is represented by the search box and subject filter; no grouping of the available list
  is claimed.
- No multi-layout naming, sharing or per-user column sets. Only the single project activity layout
  is edited.
- Production composition is unchanged; no `main` merge and no Production deployment was performed.
  PR #1716 must not merge independently.
