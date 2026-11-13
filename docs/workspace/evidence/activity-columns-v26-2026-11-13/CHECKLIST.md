# ACT-001 — Activities Columns dialog lifecycle (2026-11-13)

Contract: `cubi-activity-columns-v26.v1`
Suite: `apps/web/e2e/activity-columns-v26.mjs`
Report: `activity-columns-v26.json` (11/11 scenarios, 0 exceptions, 0 console errors, 0 failing API responses)
Screenshots: `01`–`12`
Tested code: stamped in the report as `testedCodeSha` / `gitHead`.

## Help topic

- [Define Activity Table columns](https://docs.oracle.com/cd/G48902_01/client_help/en_US/define_activity_table_columns.htm) — View > Columns opens the dialog; fields move between Available Columns and Selected Options; Add, Add All, Remove, Remove All; the display order runs left to right and Move Up/Down changes it; Copy From copies another layout; Edit Column sets title, width and alignment; OK/Apply/Default; at least one column must remain.

## Environment

- `PYTHONPATH=src python3 -m construction_pm.preview --web-root apps/web --host 127.0.0.1 --port 4215 --database /tmp/cubi-columns5.sqlite --reset`
- Fixture: Riverside Pump Station Upgrade (`preview-rps-01`, 20 registry fields in the seeded layout) and Northside Substation Expansion (`preview-nse-02`) for the isolation check; tenant `cubi-preview-tenant`.
- Viewports: en/LTR 1440×900 (desktop flow), fa/RTL 1280×720 and en/LTR 1920×1080.
- The dialog is a body-level `<dialog>` (`[data-p6-columns-dialog]`) so a workspace re-render cannot discard the draft.

## Dialog contract implemented

| Element | Selector | Behaviour |
|---|---|---|
| Available Columns | `[data-columns-available] [data-columns-available-id]` | Registry fields not in the draft, filtered by search (`[data-columns-search]`) and subject area (`[data-columns-subject]`) |
| Selected Options | `[data-columns-selected] [data-columns-selected-id]` | Draft columns in display order, with subject badge and hidden badge |
| Transfer | `[data-columns-action]` | `add`, `add-all`, `remove`, `remove-all`, `move-up`, `move-down` |
| Edit Column | `[data-columns-action="edit"]` | Title (default restorable), width 40–800, alignment left/center/right |
| Visibility | `[data-columns-visibility]` | Toggles `visible` in the layout; the column stays stored but leaves the grid |
| Default | `[data-columns-action="default"]` | Reads `GET /p6/layouts/project/activity/default` into the draft; nothing is saved |
| Copy From | `[data-columns-action="copy-from"]` | Lists the other saved scope (`[data-p6-copy-columns-dialog]`), copies its known columns into the draft |
| OK / Apply / Cancel | `[data-columns-ok]`, `[data-columns-apply]`, `[data-columns-cancel]` | OK saves and closes; Apply saves and stays open; Cancel discards the draft and writes nothing |
| Last-column guard | — | Remove/Remove All are disabled at one column; the pure functions still throw `LAST_COLUMN_REQUIRED` |
| Read-only | `[data-columns-readonly]` | Viewer sees a reason and disabled OK/Apply; transfer/edit remain available on the local draft |

## Scenarios

| # | Proof | Result |
|---|---|---|
| 01 | Selected = 20 (the stored layout), Available = 0, subject options populated; removing two columns returns them to Available; exact-field search narrows to one; subject filter returns only that subject; Copy From reports that no second layout exists. | pass |
| 02 | Remove → Available, Add → Selected (round trip); a filtered Add All adds only the one listed field; Remove All keeps one column and disables both remove actions; Add All restores the set; Move Up/Down swap the draft order; Cancel writes nothing and reopening restores the stored set. | pass |
| 03 | Edit Column sets `E2E Column`, 240 px, center; visibility hides the third column; OK stores label/width/alignment and `visible=false`; the grid header matches; a full reload keeps title, width, alignment and the hidden state; the hidden column has no header. | pass |
| 04 | A later move/hide draft is discarded by Cancel; revision and columns are byte-identical and no write is issued. | pass |
| 05 | Apply moves the first column down, increments the stored revision, updates the grid behind the still-open dialog and shows “Columns applied.”; Cancel after Apply neither rolls back nor writes again. | pass |
| 06 | Default stages exactly the server default column order with no write; Cancel leaves the stored layout untouched; Default + OK persists the defaults. | pass |
| 07 | A user layout seeded through `POST /p6/layouts/user/activity` becomes the single Copy From source; Copy replaces the draft with its four columns and the “Columns copied” notice; OK persists them in the **project** scope and the source user layout is unchanged. | pass |
| 08 | `preview-nse-02` keeps its own columns and revision after all edits; opening it shows none of the edited/copied titles; returning to `preview-rps-01` restores its stored order. | pass |
| 09 | Viewer: read-only reason, disabled OK/Apply, local draft still accepts a column, no layout revision change and no write. | pass |
| 10 | fa/RTL 1280×720 shows `dir=rtl`, the Persian title `ستون‌ها` and 0 px overflow; en/LTR 1920×1080 shows 0 px overflow. | pass |
| 11 | Whole run: 0 exceptions, 0 console errors, 0 5xx. Writes are limited to project open, the four explicit layout saves (03, 05, 06, 07) and the test-fixture user-layout seed. | pass |

## Boundary and persistence

- Reads the registry (`GET /p6/fields/p6-field-registry.v1`) and the persisted layout
  (`GET /p6/layouts/{scope}/activity`). Defaults come from
  `GET /p6/layouts/project/activity/default`; Copy From reads both scopes.
- Writes only through `POST /p6/layouts/{scope}/activity` with `{revision, columns, metadata}`;
  the dialog always keeps the current layout scope (`project` in this run) and never changes it.
- Column title/width/alignment/visibility are presentation state; no activity, date, duration or
  relationship payload is part of the write.
- Permissions: `PROJECT_WRITE` (Planner / Project administrator) may save. The dialog is disabled
  for Viewer with an explicit reason; server authorization remains the authority.
- `apps/web/src/p6-columns-dialog.ts` also owns the pure draft functions
  (`addAllAvailableColumns`, `copyColumnsFrom`, `resetDraftColumns`, `draftToLayout`, …), tested in
  `apps/web/src/p6-columns-dialog.test.ts` (10 tests).

## What this slice changed

- Copy From was permanently disabled with a claim that the view had one layout. It now loads the
  other saved scope lazily, lists scope/name/revision/column count, and copies known columns into
  the draft. Empty catalogues produce an explicit notice.
- Read-only sessions now get `canWrite: false`: a reason line and disabled OK/Apply instead of an
  always-failing save.
- Add All now adds exactly the filtered Available list rather than every registry field.
- The footer no longer claims Copy From is unavailable once a second layout exists; it explains
  what Copy From does.
- CSS for the read-only line and the Copy From picker exists identically in
  `apps/web/styles.css` and `apps/web/public/styles.css`.

## Known limits

- Copy From copies the column set only (title/width/alignment/visibility), not bars, filters or
  other layout metadata.
- The other scope is offered when it exists; there is no cross-project or imported-file source.
- Hidden columns remain in the layout and are counted in Selected Options, matching the reference
  dialog; there is no separate “deleted” state.
- There is no drag-and-drop reorder; Move Up/Down is the supported ordering path.
- Width is clamped to 40–800 px by both the dialog and the resize handle.
