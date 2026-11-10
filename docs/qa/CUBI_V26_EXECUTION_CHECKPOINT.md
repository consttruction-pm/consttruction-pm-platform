# CUBI Version 26 Execution Checkpoint

Source of record: the official Version 26 Help (`p6-professional-help.pdf`, 815 pages) and the
CUBI product identity rules. Every stage below records what shipped, the evidence that it runs,
and what is still honestly unavailable.

Branch: `codex/jalal/cubi-v26-stage-b-layout-trace-20261110` (from `main` @ `e3ce8ef8`).

---

## Stage A — central shell

Status: **merged**. Independent PR
[#1737](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1737) squash-merged into
`main` as `e3ce8ef8` on 2026-11-10 after all nine required checks passed on head `0c87e093`
(test 3.11/3.12/3.13, typecheck apps/mobile, apps/web, apps/desktop, apps/client-sync, web,
plus the Vercel statuses).

### What shipped

1. **Eight top-level menus** in Help order: Workspace | Edit | View | Project | Organization |
   Tools | Administration | Help, each with a unique `Alt+<letter>` access key rendered through
   `aria-keyshortcuts` and claimed by the same handler that opens the popup. Administration is
   gated by the authenticated session roles (`project_admin`), never by a client guess.
   Labels are translated in all nine launch languages (en, fa, de, zh, fr, ja, ko, ar, ru).
2. **Toolbar families** (closed list): Workspace, Edit, Layout, View, Project, Activities, WBS,
   Gantt/Charts, Resources, Reports, Tools. Each button carries a typed icon, a tooltip, a real
   command or window target, and a `windows` context list so the bar only shows commands the
   active window can run. Visibility is a per-user preference (`cubi:workspace-toolbars:<userId>`);
   hiding a family removes the band but every command stays reachable from the View menu toggles
   (`view.toolbar-*`) and the shortcut registry. Clipboard and baseline buttons render disabled
   with an explicit reason because no service exists yet.
3. **Strict icon registry**: closed `WORKSPACE_ICON_NAMES` union; `workspaceIcon` throws
   `UNKNOWN_WORKSPACE_ICON:<name>` instead of silently reusing a glyph. New Stage A glyphs:
   refresh, zoom-in, zoom-out, milestone, excel, fill.
4. **Central shortcut registry** independent of the menus: Ctrl+N/O/W/P/S, Ctrl+Z/Y,
   Ctrl+F, Del, Ins, F1/F3/F5/F7/F9/F10, Shift+F9, Shift+F12, Ctrl+Num+/-, Alt+1…9 for open
   windows. The registry mirrors the keydown handler exactly (unmodified letters never match),
   ignores typing targets, and documented-but-unserviced bindings (clipboard, delete, find-next,
   leveling, commit) are listed as unavailable with their reason and never dispatch. The
   shortcuts dialog is generated from the same registry.
5. **Window tabs**: open/close/switch, drag-and-drop reorder, Ctrl+Shift+Left/Right keyboard
   reorder, persisted custom order (`cubi:workspace-window-order`) applied on read while the
   open set stays canonical, dirty indicator on the active window when it holds unsaved edits,
   and a discard confirmation before closing a dirty window. Switching windows keeps typed but
   unsubmitted values (drafts are restored).
6. **Status bar, Layout bar, splitters and dialog infrastructure** retained from the previous
   increments; Stage A only re-verified them in the browser.

### Honest limits (no fake capability)

- Save on close is not offered: there is no generic save path for half-typed forms, so the
  close prompt only offers Discard/Cancel.
- Clipboard, activity delete, find-next, resource leveling and commit remain unavailable and are
  labelled as such in the toolbar, menus and shortcuts dialog.
- Refresh re-reads the project from the server (`ProjectBootstrap.start`) instead of re-rendering
  in-memory state.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `npx tsc --noEmit -p tsconfig.json` | clean |
| Test build | `npx tsc -p tsconfig.test.json` | clean |
| Unit/integration | `npm test` | 704 `tsx` tests + 14 `node --test` tests pass |
| Full-stack browser E2E | `npm run test:e2e:preview` | 98 checks pass (53 screenshots) |
| Master order E2E | `CUBI_PREVIEW_URL=… node e2e/workspace-master-order.mjs` | 18 checks pass |
| Context menus v26 | `CUBI_PREVIEW_URL=… node e2e/context-menus-v26.mjs` | 82 checks pass |
| Activities v26 scenarios | `CUBI_PREVIEW_URL=… node e2e/activities-v26-scenarios.mjs` | 18/18 scenarios pass |
| Build | `npm run build` | bundles written to `dist/web/src` |

The master-order suite was updated from the old `File` menu to the Help-ordered `Workspace`
menu and asserts the real translations (ru/fr/ja/ko/ar) plus the View menu state. Its splitter
drag check is a known intermittent CDP drag race; a clean re-run passed.

### Next stage

Stage B — Activities/Gantt/Details parity work, followed by the remaining B–I stages in the
execution order. Gaps already recorded in
`docs/qa/CUBI_V26_WORKSPACE_WINDOW_ICON_DIALOG_AUDIT_2026-11-10.md` stay the backlog.

---

## Stage B — Activities Show on Top, Show on Bottom and Trace Logic

Status: implemented and verified on this branch against the real full-stack preview; independent
PR opened from this branch and merged only after CI is green on the exact head SHA.

### What shipped

1. **Show on Top** (View menu and Layout Options): Activity Table, Activity Table + Gantt Chart,
   and Activity Network. The choice is stored per user-tenant-project-window
   (`cubi:workspace:top-layout:<tenant>:<project>:<menu>`), re-validated on read against the
   loaded data, and falls back to Table + Gantt when the stored view is no longer backed by data.
   Table-only removes the Gantt pane and its splitter; Activity Network renders the real persisted
   plan logic (14 activities / 15 relationships in the Riverside project) and never estimates or
   recalculates dates.
2. **Show on Bottom** (View menu and Layout Options): Activity Details, Trace Logic, and None.
   The choice is stored per window (`cubi:workspace:bottom-layout:…`). None collapses the bottom
   allocation instead of leaving an empty pane; choosing Details (or the Details toggle) restores
   the Activity Details surface and its per-user visibility preference.
3. **Trace Logic**: a real bottom view built from the persisted activity relationships. It walks
   predecessors and successors level by level, shows the relationship type and lag (`FS`, `SS+5d`,
   …), the destination activity and progress, marks critical activities, and supports depth 1–5
   (default 2, persisted in `cubi:workspace:trace-logic-depth`). An ancestor repeat is reported as
   a circular dependency, while two branches that meet again (a diamond) are reported once and are
   not labelled circular. Relationship endpoints that are not loaded activities are counted and
   explained instead of being invented. Clicking a trace row selects that activity in the table,
   the Gantt and the activity context used by Details. Every rendered label is escaped.
4. **Menus and dialog**: the View menu exposes the six commands with real checked state and honest
   disabled reasons — Activity Network needs loaded relationships, Trace Logic needs a selected
   activity and loaded relationships, and all six are scoped to the Activities window. The Layout
   Options dialog reads and writes the same model; the usage spreadsheet/profile views that have
   no renderer stay disabled.
5. **Regression found and fixed during the live run**: the interactive Activity Details
   enhancement replaced the bottom host after every render, which erased a freshly chosen Trace
   Logic surface (the menu command stored the preference but the pane showed Details). The
   enhancement now runs only while the bottom surface actually is Activity Details, including
   after selection changes and after switching back from Trace Logic or None; a unit test pins
   that Trace Logic is never overwritten.

### Honest limits (no fake capability)

- Activity Usage Spreadsheet/Profile and Resource Usage Spreadsheet/Profile remain disabled: no
  renderer exists, so they are never shown as available.
- Trace Logic reads persisted plan logic only; it does not recalculate dates, driving paths or
  floats, and the view states this.
- Layout preferences are browser-local per user-tenant-project; they are not written to the
  project database.
- Trace Logic is unavailable without a selected activity or without loaded relationships, and the
  menu and dialog show that reason instead of opening an empty chain.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `npx tsc --noEmit` (apps/web) | clean |
| Test build | `npx tsc -p tsconfig.test.json` | clean |
| Unit/integration | `npm test` | 717 `tsx` tests + 14 `node --test` tests pass |
| Layout/Trace browser E2E | `CUBI_PREVIEW_URL=http://127.0.0.1:4174 node e2e/layout-trace-v26.mjs` | 11/11 scenarios pass |
| Evidence bundle | `docs/workspace/evidence/layout-trace-v26-2026-11-10/` | JSON report + 11 screenshots |
| Build | `npm run build` | bundles written to `dist/web/src` |

The browser run logs in as the Planner persona on the real local full-stack preview, selects
`A130` (the seeded activity with one predecessor and three successors), and verifies the real
chain: A120/A110 as predecessors and A140, A145, A150, A155, A160, A170 as successors including
the persisted `SS+5d` link. It also verifies that table-only hides the Gantt and splitter, the
network draws all 15 relationships, None closes the bottom pane while keeping the selection,
depth 1 narrows the chain to one level, a trace row re-selects A120 in the table, and the chosen
layout survives a full reload.

### Next stage

Stage C — Projects/WBS windows, followed by Resources/Calendars, Progress/Cost/Expenses,
Documents/Reports/Tracking, Issues/Risks/Thresholds/Control/Administration, the six-skin
integration pass, and the final full matrix.
