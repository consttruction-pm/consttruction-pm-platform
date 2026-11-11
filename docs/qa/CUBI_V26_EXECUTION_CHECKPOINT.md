# CUBI Version 26 Execution Checkpoint

Source of record: the official Version 26 Help (`p6-professional-help.pdf`, 815 pages) and the
CUBI product identity rules. Every stage below records what shipped, the evidence that it runs,
and what is still honestly unavailable.

Branch: `main` @ `03d61a39` (Stage A merged as `e3ce8ef8`, Stage B as `b241699b`,
Stage C as `cb9cc002`, Stage D1 as `4d0b5783`, the Activities layout selector as `71ca85cf`,
Stage D2a as `9cfd4813`, Stage D2b as `f959a7dc`, Stage D2c as `a9cdc362`,
Stage D3a as `03d61a39`).

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

Status: **merged**. Independent PR
[#1738](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1738) squash-merged into
`main` as `b241699b` on 2026-11-10 after twelve of twelve checks passed on head `7ba4ee07`
(test 3.11/3.12/3.13, typecheck apps/mobile, apps/web, apps/desktop, apps/client-sync, web,
Vercel Preview Comments, plus the Vercel statuses). The post-merge run on `b241699b` passed all
eleven checks (test, typecheck, web, build, deploy, postgres-sync).

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
integration pass, and the final full matrix. Stage C starts from `main` @ `b241699b`.

---

## Stage C — Projects window and Project Details

Status: **merged**. Independent PR
[#1740](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1740) squash-merged into
`main` as `cb9cc002` on 2026-11-10 after all eight check-runs passed on head `941a532d`
(test 3.11/3.12/3.13, typecheck apps/web, apps/mobile, apps/desktop, apps/client-sync, and web). The
post-merge run on `cb9cc002` also concluded success (ConstructionPM CI, Web CI, Client Typecheck,
PostgreSQL Sync State Integration, Deploy CUBI Web to GitHub Pages).

### What shipped

1. **Projects window table** built from the session service (`GET /api/projects`), not from a
   fixture: one row per authorized project with id, name, planned start, date system and primary
   calendar. The active project is marked `aria-current`; every other row carries a real **Open**
   button that calls `ProjectBootstrap.selectProject`, which re-reads that project's workspace
   from the server instead of reusing in-memory state. The same window keeps the real WBS tree
   (7 rows in the Riverside project). A footer states that the list is exactly the session's
   membership.
2. **Authoritative Project Details**: the bottom surface becomes the project's own record
   (`GET /api/projects/:id`) with General, Dates and Settings tabs, instead of the placeholder
   "detail tabs are not implemented yet" panel. General shows name, id, description, planned
   start, date system, primary calendar and settings revision; Dates shows the stored planned
   start; Settings shows the stored date system, calendar and revision.
3. **Revision-guarded Edit Project dialog**: the form is seeded from the loaded record and saves
   name, description, planned start, date system and primary calendar with the revision it read.
   A stale write returns `PROJECT_REVISION_CONFLICT`, which shows the conflict state and a
   "reload latest" action instead of overwriting; a successful save adopts the new settings
   revision and publishes the new project revision to the workspace context.
4. **Stable title-bar identity**: the header keeps the project **id** in `data-project-id` and
   `title` while displaying the authoritative **name**, resolved from the project record or, on
   first paint, from the session's own project list — so the bar never flashes the id and then
   swaps to the name.
5. **Preview seed v3** persists `start_date`, `date_system` and `primary_calendar_id` for both
   seeded projects (Gregorian Riverside, Jalali Eastern), with `ALTER TABLE` migrations so an older
   preview database gains the columns instead of being recreated.
6. **Two real regressions found by CI and fixed at the source, not in the assertions**:
   - the E2E still expected the id inside `.cp-project` after the label became the name; the
     header now exposes id and name separately and the check verifies both against
     `/api/projects/:id` (a stronger assertion than the original);
   - the asynchronous project-record read re-rendered the whole workspace when it resolved, which
     could discard an editor the user had just opened and changed the header label after reload.
     The read now re-renders only when a visible surface depends on it, preserving drafts, and
     `createProject` refreshes the openable list before the workspace renders.

### Honest limits (no fake capability)

- The Dates tab shows only the planned start that the project record stores. Forecast, actual and
  finish dates belong to the scheduling core and are stated as such rather than filled in.
- Fiscal year start, default price per unit and activity ID numbering are not stored on the project
  record this server exposes, so Settings shows that boundary instead of editable fields.
- Opening another project re-reads the workspace from the server; there is no silent in-memory
  swap, and no project data outside the session's membership is synthesized.
- The Projects window does not offer project deletion or archival: no service backs it, so no
  button implies it.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `npx tsc --noEmit` (apps/web) | clean |
| Test build | `npx tsc -p tsconfig.test.json` | clean |
| Unit/integration | `npm test` | 723 `tsx` tests + 14 `node --test` tests pass |
| Full-stack browser E2E | `CUBI_PREVIEW_URL=… node e2e/preview-e2e.mjs` | 97 checks pass (51 screenshots) on `cb9cc002` |
| Projects v26 scenarios | `CUBI_PREVIEW_URL=… node e2e/projects-v26.mjs` | 6/6 scenarios pass on `cb9cc002` |
| Forms E2E | `node e2e/form-builder-e2e.mjs` | 14 checks pass |
| Evidence bundle | `docs/workspace/evidence/projects-v26-2026-11-10/` | JSON report (`gitHead` = `cb9cc002`) + 7 screenshots, 0 exceptions, 0 console errors, 0 API failures |
| Build | `npm run build` | bundles written to `dist/web/src` |

The browser run logs in as the Planner persona on the real local full-stack preview and verifies,
against `/api/projects` on the same session: the table lists exactly the two authorized projects
with the current row marked; the title bar and General tab show `Riverside Pump Station Upgrade`
with its stored planned start, Gregorian system and `CUBI-RPS-CAL` calendar; the Dates and Settings
tabs show the stored fields and state their boundaries; Edit Project opens the same record with
its settings revision; opening `preview-nse-02` re-reads that project's workspace (title bar
`نوسازی سامانه شرقی`); and returning to `preview-rps-01` restores its record and table.

### Next stage

Stage D — Resources/Calendars windows, followed by Progress/Cost/Expenses,
Documents/Reports/Tracking, Issues/Risks/Thresholds/Control/Administration, the six-skin
integration pass, and the final full matrix. Stage D starts from `main` @ `cb9cc002`.

---

## Stage D1 — Resource read register and Calendar verification

Status: **merged**. Independent PR
[#1742](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1742), branch
`codex/jalal/cubi-v26-stage-d-resources-20261110`, squash-merged into `main` as `4d0b5783` on
2026-11-11 (merge confirmed by the GitHub API: `merged=true`, `merged_at=2026-11-11T05:13:57Z`).
Post-merge CI on `4d0b5783`: test 3.11/3.12/3.13, typecheck apps/web, apps/mobile, apps/desktop,
apps/client-sync, build and postgres-sync all succeeded. This is a partial slice of the macro
Stage D: it completes the stored Resource read surface and verifies one calendar end to end. It
does **not** complete the Resources or Calendars windows.

Help topics used: `activities_window.htm`, `using_main_windows.htm`, `layout_toolbar.htm`,
`open_a_layout.htm`, `save_a_layout_in_the_activities_or_rsrc_assignments_window.htm`,
`create_a_new_activity_layout.htm`, plus the PDF sections on the Resources window, Resource
Assignments and Calendars. PDF page numbers are recorded as `VERIFY` where the printed page could
not be matched to the attached 815-page PDF.

### What shipped

1. **Resource register built from three stored contracts**: `resource_assignment` envelopes,
   `p6-resource-capacity-read-api.v1` and `p6-resource-rate-read-api.v1`. The register is the union
   of the resource ids those contracts return; every row exposes assignment count, budgeted units,
   planned cost, actual cost, latest effective capacity and rate count. No row is invented for a
   resource that only exists in a fixture.
2. **Exact decimal aggregation** (`BigInt` scaling with trailing-zero trimming) for budgeted units
   and both cost columns, so repeated `0.1` units cannot drift the totals.
3. **Effective-dated detail tabs** — General, Assignments, Capacity, Rates — populated from the same
   stored facts. Capacity and Rates keep every segment with its effective-from date; an open-ended
   segment renders as `Open-ended` instead of a guessed end date. The General tab states the
   boundary: this server exposes no resource master record (display name, type, e-mail), so those
   fields are absent rather than synthesized.
4. **Keyboard and pointer selection** on the register (click, Enter, Space), `aria-selected`, and a
   **Refresh** action that re-reads all three contracts from the server, re-enables itself and
   reports a reload error instead of keeping stale rows.
5. **Calendar verification** in the same window set: the register lists exactly `GET /p6/calendars`
   with its revision, and the snapshot reads the stored workweek version (seven days, Mon–Fri
   working, Sat–Sun non-working) rather than a client default.
6. Unit tests: `workspace-resources.test.ts` covers exact decimal sums, parser field fidelity and
   foreign-kind rejection, grouping/sorting with the latest segment, endpoint paths, and fail-closed
   contract handling. Browser E2E: `e2e/resources-v26.mjs` with six scenarios.

### Honest limits (definite, not planned)

- There is still no independent **Resource Master** in the server read contract; the register is an
  aggregation of assignments, capacity and rates.
- Resource name, resource type and full resource attributes are not served, so they are not shown.
- Resource **Create/Edit/Delete** does not exist in this slice.
- The E2E scenario contains **one** resource id and **zero** assignments; two capacity segments and
  two rates are exercised for that resource.
- Calendar coverage is the register, the snapshot and one Gregorian calendar's workweek. Global/
  project/resource calendar management, split shifts, exceptions and Jalali calendars remain open.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `npx tsc --noEmit` (apps/web) | clean |
| Test build | `npx tsc -p tsconfig.test.json` | clean |
| Unit/integration | `npm test` | 728 `tsx` tests + 14 `node --test` tests pass |
| Build | `npm run build` | bundles written to `dist/web/src` |
| Resources v26 scenarios | `CUBI_PREVIEW_URL=http://127.0.0.1:4301 node e2e/resources-v26.mjs` | 6/6 scenarios pass, 7 screenshots, 0 exceptions, 0 console errors, 0 API 5xx |
| Full-stack browser E2E | `CUBI_PREVIEW_URL=… node e2e/preview-e2e.mjs` | 97 checks, 51 screenshots, twice on two clean previews (`4302`, `4303`) |
| Projects v26 regression | `CUBI_PREVIEW_URL=http://127.0.0.1:4300 node e2e/projects-v26.mjs` | 6/6 scenarios pass |
| Forms E2E | `node e2e/form-builder-e2e.mjs` (own reset runtime) | 14 checks pass |
| Evidence bundle | `docs/workspace/evidence/resources-v26-2026-11-10/` | `resources-v26.json` + 7 screenshots |

Recorded provenance (two independent facts):

| Field | Value |
| --- | --- |
| Tested code SHA | `9023efb39c490a3d4c75940c77d0c2fc4963fb32` |
| Evidence commit | `6f0d433b9c1edd7f07679abd85410de9616e31af` |
| Branch head at merge | `3305aa8ceb8f4ee205e556a43e796c71475e5ab0`, squash-merged as `4d0b5783` |

The stored report previously claimed `gitHead cecce5fd`, which was the base commit at capture time
rather than the code that ran. The bundle now carries `testedCodeSha` and `evidenceCommitSha` as
separate fields, and every scenario was re-run from `9023efb3` on a clean preview.

One observation, kept rather than hidden: the first `preview-e2e` attempt reused the preview runtime
that the Resources suite had just driven and failed the splitter assertion at check 13; two runs on
fresh preview runtimes passed all 97 checks. The preview runtime is documented as single-suite, so
the out-of-contract reuse — not a code change — explains that attempt.

### Next stage

Stage D2 — Resource Master, Resource Assignments, Roles and full Calendar management, then
Progress/Cost/Expenses, Documents/Reports/Tracking,
Issues/Risks/Thresholds/Control/Administration, the six-skin integration pass and the final matrix.

---

## Stage D1b — Activities Classic Schedule Layout selector

Status: **merged**. Independent PR
[#1743](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1743), branch
`feat/activities-layout-selector-v26`, squash-merged into `main` as `71ca85cf` on 2026-11-11
(merge confirmed by the GitHub API: `merged=true`, `merged_at=2026-11-11T05:35:54Z`, 24 changed
files). Post-merge CI on `71ca85cf`: deploy, build, test 3.11/3.12/3.13, typecheck
apps/web, apps/mobile, apps/desktop, apps/client-sync, postgres-sync and web all succeeded. Stage
D1 ([#1742](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1742)) had merged
as `4d0b5783`, and the branch was synced with that `main` first, so the merged diff was
layout-only. Requirement implemented: the mandated Classic Schedule Layout dropdown at the
top-left of Activities, above the table and Gantt.

Help topics used: `open_a_layout.htm`,
`save_a_layout_in_the_activities_or_rsrc_assignments_window.htm`,
`create_a_new_activity_layout.htm`, `layout_toolbar.htm`, `activities_window.htm`. Printed PDF
pages are recorded as `VERIFY` where the page could not be matched in the attached 815-page PDF.

### What shipped

1. **A real selector row above the split** inside `.cp-p6-primary`, rendered by the workspace shell
   and mounted from `main.ts`. It is not the static `chromeProject.layout` label, not the demo bar,
   and not the View menu, skin selector, Show on Top/Bottom toggle, Layout Options dialog or
   Timescale control; those keep their own meaning.
2. **Catalogue read from the layout service**: both stored scopes (`project`, `user`) are read with
   `createP6LayoutPersistence` against `GET /api/projects/:id/p6/layouts/{scope}/activity` and its
   `revisions` route. The trigger shows the real name, scope label and revision the server returned;
   the seeded project layout is `Classic Schedule Layout` r1. A scope that answers 404 is omitted
   rather than replaced with a fabricated entry, and a read failure is reported as an error.
3. **Preview, Apply and Cancel**: choosing a stored layout previews it in the real table and Gantt
   and shows a visible preview badge. Cancel restores the saved layout exactly; Apply keeps the
   preview in the window and records it as the selection for that tenant and project.
4. **Save, Save As and Reload with real write semantics**: Save posts a new revision of the loaded
   scope using the optimistic guard, surfacing `REVISION_CONFLICT` and
   `IMMUTABLE_LAYOUT_REVISION` instead of reporting success. Save As writes a `user`-scope revision
   under the typed name and never overwrites the shared project layout. Reload re-reads the stored
   revision from the server. Write controls mirror the server `PROJECT_WRITE` permission
   (planner / project_admin) and state the reason when disabled.
5. **Persistence and isolation**: the selection is stored per tenant and project and re-applied
   after reload; switching projects reads that project's own catalogue and does not leak the
   previous selection. A stored layout holds columns, widths and presentation only: switching never
   mutates activities, relationships, WBS or dates, which the tests assert by comparing row ids,
   widths and column lists before and after each switch.
6. **Layout and accessibility**: LTR and RTL, 1280×720, 1366×768 and 1920×1080, `aria-haspopup`,
   `aria-expanded`, `role="menu"`, `role="menuitemradio"`, Escape closes and returns focus, and the
   menu wraps instead of hiding on narrow viewports.
7. Unit tests: `workspace-layout-selector.test.ts` (16 tests: naming, catalogue, selection store,
   load paths, markup states). Browser E2E: `e2e/layout-selector-v26.mjs` (9 scenarios).

### Honest limits (definite, not planned)

- Persistence is scoped by **layout scope**, not by user identity: `p6_layout_definition_revisions`
  is keyed by tenant, project, project revision, scope, view and revision and has no user id, so a
  `user` layout is shared inside that scope. The UI says "User layout", never "My/private layout".
- Only the Activities window has this selector. Resource Assignments and Tracking layouts —
  including share, import, export and delete — remain absent.
- Save As targets the `user` scope only; it does not rename or delete existing layouts.
- No reset-to-default action; Reload re-reads the stored revision.
- Filter, group and timescale remain separate commands and are not stored inside this layout
  revision.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `npx tsc --noEmit` (apps/web) | clean |
| Test build | `npx tsc -p tsconfig.test.json` | clean |
| Unit/integration | `npm test` | 744 `tsx` tests + 14 `node --test` tests pass |
| Build | `npm run build` | bundles written to `dist/web/src` |
| Layout selector E2E | `CUBI_PREVIEW_URL=http://127.0.0.1:4315 node e2e/layout-selector-v26.mjs` | 9/9 scenarios, 11 screenshots, 0 exceptions, 0 console errors, 0 API failures (run on the synced head `f585df0e`) |
| Full preview regression | `node e2e/preview-e2e.mjs` (managed runtime) | 98 checks, 53 screenshots, status passed; 0 exceptions, 0 API failures, 2 expected layout-conflict console probes |
| Evidence bundle | `docs/workspace/evidence/layout-selector-v26-2026-11-11/` | `layout-selector-v26.json` + 11 screenshots |

Recorded provenance (two independent facts):

| Field | Value |
| --- | --- |
| Tested code SHA | `f585df0eb6fca95aa432a177fba0f97d5a23e846` (branch synced with `main` @ `4d0b5783`) |
| Evidence commit | `cd0cd8338cbd0e776e9bfadfd02c311b88da6e2d` |
| Branch head at merge | `1f56a56575f566e51c2e88fc1570ba0c7734d97a`, squash-merged as `71ca85cf` |

The first evidence run on `b01f199b` failed scenario 03: after the catalogue load the mount
replaced `host.innerHTML`, which detached the trigger that carried the click listener, so the menu
could not be reopened. The fix delegates every listener on the stable host and tracks the open
state. The suite then ran on `4a9ccc8b`, and after Stage D1 was squash-merged and `main` was merged
into this branch, both the nine layout scenarios and the 98-check preview regression were re-run on
`f585df0e`; this table records that final run.

### Next stage

Stage D2 (Resource Master, Resource Assignments, Roles, full Calendar management), then the
remaining Activities Details/Gantt/Network/Trace Logic/WBS slices and Stages E–G.

---

## Stage D2a — Authoritative Resource Master, hierarchy and revision-guarded editor

Status: **merged**. Independent PR
[#1745](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1745), branch
`codex/jalal/cubi-v26-stage-d2-20261111`, squash-merged into `main` as `9cfd4813` on 2026-11-11
(merge confirmed by the GitHub API: `merged=true`, `merged_at=2026-11-11T09:04:31Z`,
`merge_commit_sha=9cfd4813e14d8713a7848d27b95aa998d14aaae5`, main ref at that SHA, 31 changed
files). The PR was created from `main` @ `5df9c0a5` and every required check was green on the
exact head `c82f8e43` before the merge. Post-merge CI on `9cfd4813`: all 11 checks succeeded
(deploy, web, test 3.11/3.12/3.13, build, typecheck apps/web, apps/desktop, apps/client-sync,
apps/mobile, postgres-sync). This is the first slice of macro Stage D2: the Resources window now
reads and writes an authoritative stored resource master instead of aggregating assignment,
capacity and rate facts only. Resource Assignments grouping, Role management and full Calendar
management remain open.

Help topics used: the Version 26 Resources window sections on resource types (labor, non-labor,
material), resource hierarchy, adding and editing a resource, the General/Capacity/Rates/
Assignments detail tabs, and the calendar reference on a resource. The attached 815-page PDF has no
extractable text in this environment, so topic filenames and printed page numbers are recorded as
`VERIFY` rather than guessed.

### What shipped

1. **Stored resource master with revisions**: new `P6Resource` frozen dataclass and
   `P6ResourceRepository` (SQLite table plus the PostgreSQL mirror) keyed by tenant, project,
   project revision and resource id. Every update writes a new `record_revision`, and a write
   accepts only the `expected_revision` that matches the stored one; a stale writer receives
   `REVISION_CONFLICT` instead of overwriting newer data.
2. **Create never overwrites**: `POST` on an existing resource id returns
   `RESOURCE_ALREADY_EXISTS` (HTTP 409). Before this guard, a duplicate create silently replaced
   the stored record; a dedicated test now proves the stored name and revision stay unchanged.
   Creation validates the parent reference (`RESOURCE_PARENT_NOT_FOUND`) and rejects hierarchy
   cycles (`RESOURCE_HIERARCHY_CYCLE`), both mapped to 409.
3. **Real HTTP surface under `p6-resource-api.v1`**: `GET .../p6/resources` (list),
   `GET .../p6/resources/{id}`, `POST .../p6/resources` and `PATCH .../p6/resources/{id}` with a
   required `expected_revision`. The DTO envelope carries contract version, kind, scope and the
   resource. Write routes require the project write permission and answer 403 otherwise.
4. **Preview runtime wiring**: `PreviewRepositories.resources`, `seed_resource_master` and
   `p6_resource_api` are composed into the managed preview; `/preview/health` now reports
   `resource_count` (2 seeded masters: `RPS-CIVIL-CREW` and `NSE-DESIGN-TEAM`).
5. **Resources window reads the master**: the register shows resource id, name, type, parent,
   calendar, assignment count, budgeted units, planned/actual cost and rate count. Rows are ordered
   parents-first and each child is indented by hierarchy depth; the tree is cycle-safe. The
   register no longer invents rows for ids that only appear in fixtures.
6. **Real create and edit**: the window exposes a create form and a revision-aware edit form. Both
   write through the API, show the returned record revision, report conflicts instead of claiming
   success, and keep the General/Capacity/Rates/Assignments tabs bound to the same stored record.
   The type filter and the expand/collapse control operate on the real rows.
7. **Honest disabled states**: write controls state the missing permission reason when the session
   cannot write; read-only personas keep a working register, detail tabs and refresh.

### Defects found by reviewing the rendered evidence and fixed

- The eight-column register was clipped at 1440×900; a Resources-specific grid override now gives
  the register `minmax(380px, 1.4fr)` and the editor the remaining column, collapsing to one column
  below 900 px in both CSS copies.
- The editor tab strip rendered half-cut text because `overflow-x:auto` turned it into a vertical
  scroll container; it now wraps (`flex-wrap:wrap`) and all four tabs render fully.
- The edit scenario asserted before the asynchronous reload finished; the harness now waits for the
  reloaded row and the General panel before asserting, and the whole suite was re-run on the final
  code SHA.

### Honest limits (definite, not planned)

- **Delete/archive** of a resource does not exist; the UI exposes no delete control.
- The Assignments tab remains a **read-only** view of stored assignment facts. Creating, editing and
  deleting assignments, assignment grouping/spreadsheet/profile views and the Resource Assignments
  window belong to the next Stage D2 slice.
- Resource **types are the closed set** `labor | nonlabor | material`; there is no user-defined type
  catalogue.
- `calendar_id` is stored as supplied; it is not yet validated against the calendar service, and the
  Calendars window still has no management actions beyond the verified read surface.
- **Roles** are untouched in this slice.
- `default_units_per_time` is stored as text and is not yet consumed by scheduling or cost math.
- No bulk select, copy, rename wizard, resource code/description fields, or import.
- The new create/edit forms are English-only; the nine-locale pass for these strings is pending.
- Hierarchy depth is bounded only by data; the tree ordering is parents-first and cycle-safe, but
  there is no drag-and-drop reparenting.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `npx tsc --noEmit` (apps/web) | clean |
| Test build | `npx tsc -p tsconfig.test.json` | clean |
| Unit/integration | `npm test` | 747 `tsx` tests + 14 `node --test` tests pass |
| Web unit suite | `workspace-resources.test.ts` | 8 tests: master parsing, hierarchy ordering, revision guard, create/edit paths, filter and error handling |
| Python suites | `python -m pytest` | 3328 passed, 139 skipped (includes 8 API, 3 HTTP and the preview round-trip test) |
| Build | `npm run build` | bundles written to `dist/web/src` |
| Resources v26 scenarios | `CUBI_PREVIEW_URL=http://127.0.0.1:4183 node e2e/resources-v26.mjs` | 11/11 scenarios pass, 12 screenshots, 0 exceptions, 0 console errors, 0 API failures |
| Layout regression at 1280×720 | scenario 11 of the same suite | toolbar `1178×37`, register `682×259`, 2 rows, no clipping |
| CSS copies | `cmp apps/web/styles.css apps/web/public/styles.css` | byte-identical |
| Evidence bundle | `docs/workspace/evidence/resources-v26-2026-11-11/` | `resources-v26.json` + 12 screenshots |

Recorded provenance (two independent facts):

| Field | Value |
| --- | --- |
| Tested code SHA | `4c3d034813a6019e21f9604f428b1ee2025327f0` |
| Evidence commit | `825981fe384d38566b57b7759796130b64a51f68` |
| Code commit | `37748b7a81a1e132a91555b420a84192286597aa` |
| Harness timing fix | `4c3d034813a6019e21f9604f428b1ee2025327f0` |
| Branch head at merge | `c82f8e436dd4e276165f647c3738d14404e30345`, squash-merged as `9cfd4813` |
| Merge commit | `9cfd4813e14d8713a7848d27b95aa998d14aaae5` |
| Post-merge CI | 11/11 checks success on `9cfd4813` |

The evidence report keeps `testedCodeSha` and `evidenceCommitSha` as separate fields: the scenarios
ran on `4c3d0348`, and the screenshots plus report were committed afterwards as `825981fe`.

---

## Stage D2b — Resource Assignments grouping, spreadsheet, profile and revision workflow

Status: **merged**. Independent PR
[#1747](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1747), branch
`codex/jalal/cubi-v26-stage-d2b-20261111`, squash-merged into `main` as `f959a7dc` on 2026-11-11
(merge confirmed by the GitHub API: `merged=true`, `merged_at=2026-11-11T11:11:41Z`,
`merge_commit_sha=f959a7dc0dd83c327ac7cacd94098119ac6032a8`, main ref at that SHA, 24 changed
files). The PR was created from `main` @ `6f5af025` and every required check was green on the
exact head `bc655d3d` before the merge. Post-merge CI on `f959a7dc`: all 11 checks succeeded
(deploy, build, web, postgres-sync, test 3.11/3.12/3.13, typecheck apps/web, apps/mobile,
apps/desktop, apps/client-sync). This slice is the second part of macro Stage D2: the Resource
Assignments window now reads and writes stored assignment and period facts instead of showing a
read-only aggregate. Role management and full Calendar management remain open.

Help topics used: the Version 26 Resource Assignments sections on grouping assignments by resource
and role, the assignment table columns (budgeted units, unit, planned/actual cost, currency),
assignment details, time-phased spreadsheets and resource usage profiles. The attached 815-page PDF
has no extractable text in this environment, so topic filenames and printed page numbers are
recorded as `VERIFY` rather than guessed.

### What shipped

1. **Register bound to stored facts**: the register reads
   `GET .../p6/resource-assignments` and renders the stored decimal strings; fixture-only rows are
   gone. Empty state, column chooser defaults and the canonical eight columns are real.
2. **Real create with duplicate protection**: the create form POSTs a new assignment under
   `p6-resource-write-api.v1`, re-reads the list and keeps the new row selected. Creating an
   existing id returns HTTP 409 `IMMUTABLE_RESOURCE_ASSIGNMENT` and leaves the stored row intact.
3. **Grouping with exact subtotals**: group by resource, role or activity; totals are summed from
   stored strings with BigInt-scaled decimal parts (no floating point), empty roles/activities get a
   stable label, each group collapses independently, and the group-by choice persists per project.
4. **Sorting, search and filters**: numeric sort on units and costs with `aria-sort` and nulls last;
   case-insensitive text search plus exact resource and activity filters. Filtering hides rows only;
   stored facts are never rewritten by a view operation.
5. **Column chooser**: hide/show columns through real checkboxes; the selection persists per project
   in `cubi.assignments.view.v1` and survives window switches and remounts.
6. **Spreadsheet writes period facts**: the Spreadsheet tab POSTs period facts to
   `resource-assignment-periods`, then re-reads and renders the stored buckets and exact totals
   (for example `12` units / `961` cost). A duplicate period with different values is rejected with
   HTTP 400 `P6_RESOURCE_REQUEST_INVALID` and the stored period keeps its units. The period parser
   reports `INVALID_ASSIGNMENT_PERIOD_RECORD` for malformed records instead of a generic error.
7. **Profile derives from stored periods only**: the summary reports units, cost, peak and the
   number of periods, and each bar's height is proportional to the stored peak; no synthetic
   histogram is invented.
8. **Auditable revision flow**: stored assignment facts are append-only, so "Revise" creates a new
   `-R2`/`-R3` assignment through the real create API, leaves the original untouched and states the
   immutability rule in the UI. The submit label always reads "Create assignment"; it never claims
   to save an in-place revision that the platform cannot perform.
9. **Layout fixes found in the rendered evidence**: group bands no longer inherit the global
   `td[colspan]` height of 76 px (which hid the second group), and the detail tab strip no longer
   flex-shrinks and clips when the panel content is tall.
10. **Browser evidence**: a 15-scenario harness creates every fixture through the window and
   verifies the same session's API afterwards, including the duplicate paths, reload and the
   1280×720 layout.

### Defects found by reviewing the rendered evidence and fixed

- Group subtotal rows rendered 76 px tall and centred because of the global `td[colspan]` rule; the
  second group fell outside the visible register. Scoped assignment rules now restore compact
  start-aligned bands.
- The detail tab row was flex-shrunk and clipped when the General panel grew; the tabs and content
  now have explicit `flex` bases.
- Period parsing surfaced `INVALID_ASSIGNMENT_RECORD` for a malformed period; it now reports the
  period-specific code (two unit tests failed before the fix and pass after).
- Changing the group-by select back to "None" was ignored because the empty `data-assignment-group`
  value is falsy; the handler now matches the select element instead of the dataset value.
- A misleading "Save revision" submit label was shown when the draft id already existed; the label
  is always "Create assignment" because the flow is a create, not an in-place update.
- The E2E recorder let scenario details override the status field, producing a false "1 failed"
  summary; record ordering is now fixed and the duplicate status is stored under its own key.

### Honest limits (definite, not planned)

- Stored assignments are **append-only**: there is no in-place edit or delete. "Revise" creates a
  new `-R2` id; the original fact is never mutated.
- Period facts are immutable per assignment + period start; there is no period edit or delete.
- No assignment import, bulk create, copy-down, or automatic resource-curve distribution.
- The assignment form labels and notices are English-only; the nine-locale pass is pending.
- The Profile is derived from stored assignment periods; availability, overallocation and limits
  are not enforced in this window.
- Role management (effective-dated rates, proficiency, limits) and full Calendar management remain
  open in Stage D2.
- Drill-through from the Resources register into a filtered assignments view is not wired yet.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `cd apps/web && npm run typecheck` | clean |
| Unit/integration | `cd apps/web && npm test` | 759 `tsx` tests + 14 `node --test` tests pass, 0 fail |
| Web unit suite | `workspace-assignments.test.ts` | exact decimal totals, grouping, sort/filter, profile, revision ids, period parse/payload and view-preference persistence |
| Build | `cd apps/web && npm run build` | bundles written to `dist/web/src` |
| Assignments v26 scenarios | `CUBI_PREVIEW_URL=http://127.0.0.1:4184 node e2e/assignments-v26.mjs` | 15/15 scenarios pass, 15 screenshots, 0 exceptions, 0 console errors, 0 API failures |
| Layout regression at 1280×720 | scenario 15 of the same suite | no horizontal overflow, register and tabs visible |
| CSS copies | `cmp apps/web/styles.css apps/web/public/styles.css` | byte-identical |
| Evidence bundle | `docs/workspace/evidence/assignments-v26-2026-11-11/` | `assignments-v26.json` + 15 screenshots |

Recorded provenance (two independent facts):

| Field | Value |
| --- | --- |
| Tested code SHA | `de89d44c8c4b520acbd84cebd532a06a264359c2` |
| Evidence commit | `50e351127f4bae2a144d95dbde52602ede340737` |
| Branch head at merge | `bc655d3d7e6c5dda92b8e946b9297910afafeb9a` |
| PR | [#1747](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1747) |
| Merge commit | `f959a7dc0dd83c327ac7cacd94098119ac6032a8` |
| Post-merge CI | 11/11 checks success on `f959a7dc` |

The evidence report keeps `testedCodeSha` and `evidenceCommitSha` as separate fields: the scenarios
ran on `de89d44c`, and the report plus screenshots were committed afterwards as `50e35112`.

### Next stage

Role management (hierarchy, proficiency, effective-dated rates, limits) and full Calendar
management (global/project/resource calendars, split shifts, exceptions, Jalali), then Stages E–G.

---

## Stage D2c — Role hierarchy, proficiency, effective-dated rates and limits

Status: **merged**. Independent PR
[#1749](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1749), branch
`feat/v26-stage-d2c-roles`, squash-merged into `main` as `a9cdc362` on 2026-11-11
(merge confirmed by the GitHub API: `merged=true`, `merged_at=2026-11-11T19:48:04Z`,
`merge_commit_sha=a9cdc362b1b5ffdca81b15737e0525be33253c67`, main ref at that SHA, 31 changed
files). The PR was created from `main` @ `90abd873` and every required check was green on the
exact head `78b4ddfc` before the merge. Post-merge CI on `a9cdc362`: all 11 checks succeeded.
The Roles window now reads and writes the stored role dictionary instead of a read-only register:
hierarchy, revision-guarded general facts, resource proficiency with exactly one primary role,
and effective-dated rates and limits.

Help topics used: the Version 26 Roles sections on role hierarchy and assigning a parent role,
the five proficiency levels (Master, Expert, Skilled, Proficient, Inexperienced), role prices per
unit with effective dates and units (m/h/d/w/mo/y), role limits per effective date (units or
percentage), assigning a role to a resource with proficiency and primary-role status, and
"Calculate Costs from Units". The attached 815-page PDF has no extractable text in this
environment, so topic filenames and printed page numbers are recorded as `VERIFY` rather than
guessed.

### What shipped

1. **Hierarchy register from stored rows**: `GET .../p6/roles` returns `role_tree_order`, so parents
   always precede children; the register indents by depth (14 px at level one), shows the parent
   column and keeps the stored list authoritative. Create offers only stored roles as parents.
2. **Duplicate-safe create and revision-guarded edit**: creating an existing identifier returns
   HTTP 409 `ROLE_ALREADY_EXISTS` and leaves the stored row unchanged. `PATCH` requires
   `expected_revision >= 1`; a stale revision returns 409 `REVISION_CONFLICT`, and a successful
   edit returns the incremented revision (1 → 2 in the evidence run).
3. **Cycle-safe hierarchy**: the edit form never offers the edited role as its own parent, and the
   server rejects a cycle with 409 `ROLE_HIERARCHY_CYCLE` (`ROLE_PARENT_NOT_FOUND` for an unknown
   parent).
4. **Resources tab with real assignment**: stored resources from the resource master can be
   assigned to a role with one of the five proficiency levels and an `is_primary` flag. Making an
   assignment primary demotes the previous primary for the same resource on another role
   (`record_revision` 1 → 2 in the evidence run), so a resource never has two primary roles.
   Editing changes proficiency and primary state; unassigning calls the real `DELETE` and the row
   disappears from the server list.
5. **Units & Prices tab**: effective-dated price/unit rates with rate type, amount, unit
   (m/h/d/w/mo/y) and currency; at most five rates per effective date (a sixth returns 409
   `ROLE_RATE_LIMIT_EXCEEDED`). Limits are one per effective date, expressed in units or percent;
   a duplicate date returns 409 `ROLE_LIMIT_ALREADY_EXISTS`. Both tabs support editing with record
   revisions, and the effective date of an existing fact is preserved.
6. **"Calculate Costs from Units" round-trips**: the checkbox is stored in the role record, shows
   the stored value, and changes survive the API re-read (`true` → `false` in the evidence run).
7. **Real transport, no fixtures**: new SQLite tables `p6_role_rate`, `p6_role_limit` and
   `p6_role_resource` behind `P6RoleDictionaryRepository`; the extracted `P6RoleDetailsAPI` is
   injected by the preview runtime and production composition. Routes under
   `/api/projects/{project}/p6/roles` (list/get/create/update plus `/rates`, `/limits`, `/resources`
   list/save/edit/delete) map domain codes to 409/404/400 and refuse unknown writes with
   `P6_ROLE_REQUEST_INVALID`; every write records `manual-entry:<user>` as its source.
8. **Window layout**: the Roles window owns its General / Resources / Units & Prices detail tabs,
   so the shared bottom Details pane is retired for this window. One visibility helper is used by
   the initial render, the bottom-layout re-render and the incremental window switch, and the
   shared pane's generic fallback text is not rendered for Roles even while hidden.
9. **Browser evidence**: an 11-scenario harness drives the window through the real UI, verifies
   the stored facts through the same session's API, and keeps screenshots at 1440×900 and
   1280×720.

### Defects found by reviewing the rendered evidence and fixed

- The resource assignment select visually preselected the first stored resource while the draft
  was still empty; submitting then failed with "select a resource" although the control looked
  filled. The select now has an explicit empty placeholder bound to the draft.
- The shared bottom Details pane came back after switching windows or re-applying a bottom layout:
  the menu-switch and layout-only paths recomputed visibility without the Roles rule. All three
  paths now call one helper, and the pane is also emptied for Roles so the false "detail tabs are
  not implemented yet" text cannot remain in the DOM.
- The E2E create/edit classifier treated the readonly identifier in the edit form as a create
  field; it now distinguishes the two forms by the presence of the editable `role-id` input.
- The rate-row expectation first counted seven rows; the correct count is six because the sixth
  same-date rate must be rejected rather than rendered. The assertion now encodes the cap.

### Honest limits (definite, not planned)

- Role rates, limits and resource assignments persist in SQLite only; the role master has a
  Postgres mirror, these new dictionary facts do not yet.
- There is no role delete, copy, replace/merge or organizational chart view.
- Limits are stored facts only: neither resource leveling nor availability enforcement consumes
  them yet.
- "Calculate Costs from Units" is persisted but not yet consumed by assignment cost calculation;
  assignment-level role cost and drill-through from assignments are open.
- Role window labels and notices are inline English/Persian; the nine-locale catalogs are pending.
- No bulk assignment, import or "assign all resources" path; resources are assigned one at a time.
- Provider-specific product names are not shown in the UI or Help text.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `cd apps/web && npm run typecheck` | clean |
| Unit/integration | `cd apps/web && npm test` | 766 `tsx` tests + 14 `node --test` tests pass, 0 fail |
| Roles web suite | `workspace-roles.test.ts` | 14 tests: hierarchy fields, fail-closed contracts, create/update payloads and revisions, rates/limits/resources parsing and mutations |
| Python role suites | `pytest tests/test_p6_role_dictionary.py tests/test_p6_role_http_routes.py tests/test_preview_roles.py tests/test_p6_role_api.py` | 23 passed |
| Build | `cd apps/web && npm run build` | bundles written to `dist/web/src` |
| Roles v26 scenarios | `CUBI_PREVIEW_URL=http://127.0.0.1:4184 node e2e/roles-v26.mjs` | 11/11 scenarios pass, 11 screenshots, 0 exceptions, 0 console errors, 0 API failures |
| Layout regression at 1280×720 | scenario 11 of the same suite | register, detail tabs and rates table fit; shared bottom pane collapsed (`display:none`, `data-details-collapsed="true"`) |
| CSS copies | `cmp apps/web/styles.css apps/web/public/styles.css` | byte-identical |
| Evidence bundle | `docs/workspace/evidence/roles-v26-2026-11-11/` | `roles-v26.json` + 11 screenshots |

Recorded provenance (two independent facts):

| Field | Value |
| --- | --- |
| Tested code SHA | `adec57fe30bc2b3c9f023332e0582f6faacffffa` |
| Evidence commit | `e06a69dcb60fc230364b29adb5342d0577ac7edd` |
| Branch head at merge | `78b4ddfc5ce27c09f3d774983cecd2955f968642` |
| PR | [#1749](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1749) |
| Merge commit | `a9cdc362b1b5ffdca81b15737e0525be33253c67` |
| Post-merge CI | 11/11 checks success on `a9cdc362` |

The evidence report keeps `testedCodeSha` and `evidenceCommitSha` as separate fields: the scenarios
ran on `adec57fe`, and the screenshots plus report were committed afterwards as `e06a69dc`.

### Next stage

Full Calendar management (global/project/resource calendars, split shifts, exceptions, Jalali),
then Stages E–G.

Changed files: `apps/web/src/workspace-roles.ts`,
`apps/web/src/workspace-roles.test.ts`, `apps/web/src/workspace-view.ts`,
`apps/web/styles.css`, `apps/web/public/styles.css`, `apps/web/e2e/roles-v26.mjs`,
`src/construction_pm/p6_role_dictionary_repository.py`,
`src/construction_pm/p6_role_details_api.py`, `src/construction_pm/p6_role_api.py`,
`src/construction_pm/p6_role_repository.py`,
`src/construction_pm/http/project_lifecycle_routes.py`,
`src/construction_pm/http/production_composition.py`, `src/construction_pm/preview/runtime.py`,
`tests/test_p6_role_dictionary.py`, `tests/test_p6_role_http_routes.py`,
`tests/test_preview_roles.py`.

---

## Stage D3a — Calendar create-from-base, workweek and split-shift editing, exception removal

Status: **merged**. Independent PR
[#1751](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1751), branch
`feat/v26-stage-d3a-calendars`, squash-merged into `main` as `03d61a39` on 2026-11-11
(merge confirmed by the GitHub API: `merged=true`, `merged_at=2026-11-11T21:48:04Z`,
`merge_commit_sha=03d61a39f929f7fee095a37bfb827ab1c852826c`, main ref at that SHA, 30 changed
files). The PR was created from `main` @ `a7e39e9e` and all 8 required checks were green on the
exact head `f93d08ac` before the merge. Post-merge CI on `03d61a39`: 11/11 checks succeeded after
one rerun; the first `web` run was a runner flake (`CHROME_DID_NOT_START` in the assistant-avatar
E2E, then the job timed out at 8 minutes) and the rerun passed without a code change.
The Calendars window now creates real calendars from a stored base calendar, edits the workweek
and split-shift intervals through the calendar API with revision guards, and deletes stored
exceptions instead of only adding them.

Help topics used: the Version 26 Calendars sections on global, project and resource calendars,
base calendar inheritance, working-day versus working-time calendars, workweek and daily hours,
split shifts, exceptions and holidays, and the Gregorian/Jalali date system. The attached 815-page
PDF has no extractable text in this environment, so topic filenames and printed page numbers are
recorded as `VERIFY` rather than guessed.

### What shipped

1. **Create from base with copied facts**: `POST .../p6/calendars` accepts
   `base_calendar_id`/`base_calendar_version`; the server validates completeness, existence, kind
   and snapshot (`INCOMPLETE_BASE_CALENDAR_REFERENCE`, `BASE_CALENDAR_NOT_FOUND`,
   `BASE_CALENDAR_KIND_MISMATCH`, `BASE_CALENDAR_SNAPSHOT_NOT_FOUND`) and, inside one
   transaction, stores the new master and copies the base snapshot, exceptions and all four
   work-hour kinds. The read contract now returns `base_calendar_id`/`base_calendar_version`.
2. **New-calendar dialog**: the window toolbar New action opens a real dialog with base calendar,
   id, version, name and type; it creates a stored calendar and selects it in the register.
   The copy action was refactored onto the same `_copy_calendar_facts` path.
3. **Workweek editor**: each weekday has a working checkbox, an hours field and (working-time
   only) a shifts field. Saving writes `standard_work_week` and `standard_detailed_work_hours`
   rules through the API; working-day hours are read-only with an explanatory title because the
   day-based scheduler consumes the weekday flag, not per-day hours. Changing Friday to
   non-working in the evidence run changes the authoritative CPM result and survives a restart.
4. **Split shifts**: strict `HH:MM-HH:MM` parsing, sorted non-overlapping intervals, hours derived
   from the intervals; overlapping intervals are rejected in the browser and never reach the
   server. The seeded working-time calendar carries morning/afternoon shifts; the evidence run
   saves a third interval and re-reads three intervals with total 10 hours.
5. **Revision-guarded work-hour writes**: new rules bump the calendar master revision; replacing
   an existing rule requires `expected_revision` and a stale revision is rejected. Work-hour GET
   returns every kind without a body (a GET cannot carry JSON); an optional `kind` filter remains.
6. **Exception removal**: `DELETE .../exceptions/{date}` validates an ISO date, deletes the stored
   exception scoped by project revision, and returns `{contract_version, deleted}`. Exception rows
   in the window now have a real Remove action with a success notice.
7. **Preview runtime parity**: the preview registry no longer fails closed on work-hour rules or
   working-time calendars. It loads persisted rules, applies standard workweek and standard
   detailed hours through the shared resolver, registers day and time resolvers plus exception
   overlays, validates base references after all calendars, and keeps dated detailed/total hours
   explicitly unsupported. A seeded `CUBI-RPS-CAL-TIME` working-time calendar provides a real
   split-shift target independent of the project calendar used by CPM.
8. **Window layout**: Calendars owns its General / Workweek / Exceptions detail surface, and the
   shared bottom Details pane is retired for this window through the same visibility rule used by
   Roles, including the layout-only and incremental menu paths.

### Defects found by reviewing the rendered evidence and fixed

- The created calendar's read record had no base reference, so the API could not prove
  inheritance. The read DTO, TS model, workspace mapping and PATCH payload now carry both base
  fields.
- Snapshots serialize clock values with seconds (`08:00:00`); the editor showed that raw text.
  Display now normalizes to `HH:MM` while parsing and saving keep the strict form.
- Saving two first-time work-hour rules did not bump the calendar revision, so the register
  revision was stale. A new rule now bumps the master revision, and the evidence run records
  revision 2 (Friday rule) and 3 (standard + detailed split shifts).
- The E2E harness hung after a failed assertion because the CDP socket kept the event loop alive;
  it now exits explicitly after `main()`, and the preview database is reset before every run to
  avoid edits leaking between runs.

### Honest limits (definite, not planned)

- The preview's day-based CPM consumes the working-day flag; per-day hours and split-shift
  intervals are stored and shown, and the time-aware resolver exists, but the project schedule
  does not yet consume working-time capacity.
- Dated detailed work hours and total-hours rules are stored but not consumed by the resolver and
  fail closed instead of being silently ignored.
- No calendar delete, replace, versioned "Copy as", or scoped assignment editor from Project
  Details/Resources yet; the seeded calendars are project-type.
- Jalali display is exposed by the date-system field and the existing Jalali toggle, but the
  window's Jalali browser evidence is pending.
- Recurring exceptions, exception editing (delete + recreate is the current path) and detailed
  hours per exception are not implemented.
- Calendar labels and notices are inline English/Persian; the nine-locale catalogs are pending.
- Provider-specific product names are not shown in the UI or Help text.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `cd apps/web && npm run typecheck` | clean |
| Unit/integration | `cd apps/web && npm test` | 771 `tsx` tests + 14 `node --test` tests pass, 0 fail |
| Calendars web suite | `workspace-calendars.test.ts` | 14 tests: fail-closed parsing, split-shift parsing/formatting, create/update payloads, revision tracking |
| Python calendar suites | `pytest` calendar, exception, API, HTTP and preview suites | 159 passed |
| Full Python suite | `pytest tests` | 3350 passed, 139 skipped |
| Build | `cd apps/web && npm run build` | bundles written to `dist/web/src` |
| Calendars v26 scenarios | `CUBI_PREVIEW_URL=http://127.0.0.1:4184 CUBI_TESTED_CODE_SHA=c95c1cd5 node e2e/calendars-v26.mjs` | 8/8 scenarios pass, 8 screenshots, 0 exceptions, 0 console errors, 0 API failures |
| Layout regression at 1280×720 | scenario 08 of the same suite | register, workweek and detail surface fit without horizontal clipping; shared bottom pane collapsed |
| CSS copies | `cmp apps/web/styles.css apps/web/public/styles.css` | byte-identical |
| Evidence bundle | `docs/workspace/evidence/calendars-v26-2026-11-12/` | `calendars-v26.json` + 8 screenshots |

Recorded provenance (two independent facts):

| Field | Value |
| --- | --- |
| Tested code SHA | `c95c1cd5e0b7028488c2b17b2cb7931c14f484eb` |
| Evidence commit | `ec95b9ec09a427773ed8ceb24bd2fb73ae476736` |
| Branch head at merge | `f93d08ac254c5a74098b765a66f4a4b6f8263e59` |
| PR | [#1751](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1751) |
| Merge commit | `03d61a39f929f7fee095a37bfb827ab1c852826c` |
| Post-merge CI | 11/11 checks success on `03d61a39` after one rerun of the flaky `web` job |

The evidence report keeps `testedCodeSha` and `evidenceCommitSha` as separate fields: the
scenarios ran on `c95c1cd5`, and the screenshots plus report were committed afterwards as
`ec95b9ec`.

### Next stage

Remaining Calendar scope (Jalali browser evidence, resource/project calendar assignments,
exception editing, multi-view), then Stages E–G.

Changed files: `apps/web/src/workspace-calendars.ts`,
`apps/web/src/workspace-calendars.test.ts`, `apps/web/src/workspace-model.ts`,
`apps/web/src/workspace-read-api.ts`, `apps/web/src/workspace-view.ts`, `apps/web/styles.css`,
`apps/web/public/styles.css`, `apps/web/e2e/calendars-v26.mjs`,
`src/construction_pm/p6_calendar_api.py`, `src/construction_pm/p6_calendar_read_api.py`,
`src/construction_pm/p6_versioned_resource_calendar_resolver.py`,
`src/construction_pm/preview/runtime.py`, `tests/test_p6_calendar_api.py`,
`tests/test_preview_calendar_exceptions.py`.

---

## Stage D3b — Jalali calendar system and revision-guarded exception editing

Status: **code complete and verified on the exact head `418425d3`; evidence committed as
`8e65ca20`; PR open, merge pending.** Branch `feat/v26-stage-d3b-calendar-jalali`, created from
`main` @ `f3b90e0e`.

Help topics used: the Version 26 Calendars sections on the Gregorian/Jalali date system, typed
calendar dates, exceptions and holidays, and editing stored exception facts. The attached 815-page
PDF has no extractable text in this environment, so topic filenames and printed page numbers are
recorded as `VERIFY` rather than guessed.

### What shipped

1. **Date system on creation**: `POST .../p6/calendars` accepts `system` (`gregorian`|`jalali`,
   validated; anything else returns `INVALID_CALENDAR_SYSTEM`). Create-from-base applies the
   requested system to the copied definition while preserving the base weekdays, holidays,
   exceptions and work-hour rules; a system choice without a base definition is rejected with
   `CALENDAR_SYSTEM_REQUIRES_BASE_DEFINITION` because there is no definition to carry it.
2. **Immutable system on edit**: `PATCH` rejects a system change with `CALENDAR_SYSTEM_IMMUTABLE`;
   renaming a calendar cannot silently reinterpret previously typed dates.
3. **Jalali exception entry and display**: a Jalali calendar renders the exception date input as
   Jalali text (`1405/10/01`), converts it locally with the shared `parseJalaliDateInput` and
   stores the canonical ISO date (`2026-12-22`). The stored row is displayed as the Jalali date
   with the ISO date beside it, so entry and display agree without shifting the date.
4. **Revision-guarded exception editing**: stored exceptions remain immutable through a plain
   save; editing uses a separate `PUT .../exceptions/{date}` with `expected_revision`. The
   repository updates the row and raises `record_revision` (1 → 2 in evidence); a stale revision
   returns `EXCEPTION_REVISION_CONFLICT`, a missing row `EXCEPTION_NOT_FOUND`, and an invalid
   expected revision `EXPECTED_EXCEPTION_REVISION_REQUIRED`. The response and list DTOs now carry
   `record_revision`.
5. **Real UI edit path**: exception rows have an Edit action that loads the stored mode, hours or
   interval into the form, locks the date, saves through the PUT and shows the new revision
   (`r2` in evidence); Remove and Add keep their existing paths.
6. **Browser evidence**: five scenarios drive the real window: create a Jalali calendar from the
   stored base, add an exception typed in Jalali, edit it to total work hours with the record
   revision, reload the page and confirm persistence, and render at 1280×720.

### Defects found while building the evidence and fixed

- The harness first queried a schedule-panel holiday list instead of the calendar window's own
  list; the selector is now scoped to the Calendars exceptions panel.
- The first harness exit called a close method that the shared launcher does not expose; it now
  stops the launched Chrome through the supported `stop()` API, so a scenario failure reports
  its real assertion instead of a teardown error.
- The exception date control was a Gregorian `type=date` input even for Jalali calendars, so a
  Jalali date could not actually be typed. It is now a Jalali text control for Jalali definitions.

### Honest limits (definite, not planned)

- The Jalali choice changes entry and display; storage and scheduling stay canonical Gregorian.
  There is no Jalali-formatted read of activity dates in this window and no Hijri or other
  calendar system.
- Exception editing supports one detailed interval per exception (the form's existing shape);
  multiple intervals and recurring exceptions remain unsupported.
- The preview's day-based CPM still consumes the working-day flag, not per-day hours/split-shift
  capacity; dated detailed and total-hours work-hour rules fail closed.
- No calendar delete/replace from the window beyond the existing toolbar actions, no scoped
  assignment editor from Project Details/Resources, and no Postgres mirror for the new exception
  revision path.
- Calendar labels and notices are inline English/Persian; nine-locale catalogs are pending.
- Provider-specific product names are not shown in the UI or Help text.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `cd apps/web && npm run typecheck` | clean |
| Unit/integration | `cd apps/web && npm test` | 773 `tsx` tests + 14 `node --test` tests pass, 0 fail |
| Calendars web suite | `workspace-calendars.test.ts` | 16 tests: Jalali system payload, invalid system, revision PUT payload and stale guard, plus the D3a parser/create/update coverage |
| Backend calendar suites | `pytest tests/test_p6_calendar_api.py tests/test_project_lifecycle_http_routes.py tests/test_calendar_exception_repository.py` | 131 passed |
| Full Python suite | `pytest tests` | 3353 passed, 139 skipped |
| Build | `cd apps/web && npm run build` | bundles written to `dist/web/src` |
| Jalali scenarios | `CUBI_PREVIEW_URL=http://127.0.0.1:4184 CUBI_TESTED_CODE_SHA=418425d3 node e2e/calendars-jalali-v26.mjs` | 5/5 scenarios pass, 5 screenshots, 0 exceptions, 0 console errors, 0 API failures |
| Layout at 1280×720 | scenario 05 of the same suite | register, Jalali exception panel and shared pane fit; shared bottom pane collapsed |
| CSS copies | `cmp apps/web/styles.css apps/web/public/styles.css` | byte-identical |
| Evidence bundle | `docs/workspace/evidence/calendars-jalali-v26-2026-11-12/` | `calendars-jalali-v26.json` + 5 screenshots |

Recorded provenance (two independent facts):

| Field | Value |
| --- | --- |
| Tested code SHA | `418425d3065171ab0131a555aaf7e47585dbcf03` |
| Evidence commit | `8e65ca20ca3c2354b548be9fb5aa8358f6a40806` |
| Branch head at merge | pending |
| PR | pending |
| Merge commit | pending |
| Post-merge CI | pending |

The evidence report keeps `testedCodeSha` and `evidenceCommitSha` as separate fields: the
scenarios ran on `418425d3`, and the screenshots plus report were committed afterwards as
`8e65ca20`.

### Next stage

Scoped calendar assignments (project and resource selectors from stored calendars), multi-view
calendar rendering and recurring exceptions, then Stages E–G.

Changed files: `apps/web/src/client.ts`, `apps/web/src/workspace-calendars.ts`,
`apps/web/src/workspace-calendars.test.ts`, `apps/web/e2e/calendars-jalali-v26.mjs`,
`src/construction_pm/calendar_exception_repository.py`,
`src/construction_pm/p6_calendar_api.py`,
`src/construction_pm/http/project_lifecycle_routes.py`, `tests/test_p6_calendar_api.py`,
`tests/test_project_lifecycle_http_routes.py`.
