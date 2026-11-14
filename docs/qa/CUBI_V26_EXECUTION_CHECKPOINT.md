# CUBI Version 26 Execution Checkpoint

Source of record: the official Version 26 Help (`p6-professional-help.pdf`, 815 pages) and the
CUBI product identity rules. Every stage below records what shipped, the evidence that it runs,
and what is still honestly unavailable.

Branch: `main` @ `66e106a` (Stage G merged as `85e24df`, recorded in `66e106a`). Earlier
merges: Stage A `e3ce8ef8`, Stage B `b241699b`, Stage C `cb9cc002`, Stage D1 `4d0b5783`, the
Activities layout selector `71ca85cf`, Stage D2a `9cfd4813`, Stage D2b `f959a7dc`,
Stage D2c `a9cdc362`, Stage D3a `03d61a39`, Stage D3b `1ba5c9ef`; Stage D3c–G merges are
recorded in their own sections below.

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

Status: **merged**. Independent PR
[#1753](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1753), branch
`feat/v26-stage-d3b-calendar-jalali`, squash-merged into `main` as `1ba5c9ef` on 2026-11-11
(merge confirmed by the GitHub API: `merged=true`, `merged_at=2026-11-11T23:19:14Z`,
`merge_commit_sha=1ba5c9ef326dda316ca5a6686f703e918075c905`, main ref at that SHA, 18 changed
files). The PR was created from `main` @ `f3b90e0e`, all 8 required checks were green on the exact
head `4e37b6f1`, and post-merge CI on `1ba5c9ef` succeeded 11/11 without a rerun.

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
| Branch head at merge | `4e37b6f19f31c860555a22d596b0af320f9f6082` |
| PR | [#1753](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1753) |
| Merge commit | `1ba5c9ef326dda316ca5a6686f703e918075c905` |
| Post-merge CI | 11/11 checks success on `1ba5c9ef` |

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

---

## Stage D3c — Calendar usage references and assignment calendar selection

Status: **merged**. Independent PR
[#1769](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1769), branch
`feat/v26-stage-d3c-calendar-usage`, squash-merged into `main` as `cef505e9` on 2026-11-12
(merge confirmed by the GitHub API: `merged=true`, `merged_at=2026-11-12T03:47:43Z`,
`merge_commit_sha=cef505e93f3a729f9bcca9686f7a658af05f7c00`, 17 changed files). The PR was
created from `main` @ `64a51a9b`, all 9 required checks were green on the exact head
`7c97e522`, and post-merge CI on `cef505e9` succeeded 5/5 without a rerun.

Help topics used: the Version 26 Calendars sections on calendar assignments, resource
calendars and seeing which activities, relationships and resources use one calendar. The
attached 815-page PDF has no extractable text in this environment, so topic filenames and
printed page numbers remain `VERIFY` rather than guessed.

### What shipped

1. **Calendar usage read model**: new `p6-calendar-usage-api.v1` composes usage from the
   authoritative repositories instead of a separate projection: activity calendar
   assignments, relationship-lag calendar assignments, resource masters and resource
   assignments. It never fabricates a reference and matches explicit references on the exact
   calendar id and version pair.
2. **Usage HTTP read**: `GET /api/projects/{project}/p6/calendars/{calendar}/{version}/uses`
   returns `contract_version`, the resolved calendar reference, `total`, per-kind `counts`
   and per-reference rows. A denied read or cross-scope request is 403, a malformed or empty
   reference is 400 `P6_CALENDAR_REQUEST_INVALID`, and an unknown calendar or version is 404
   `P6_CALENDAR_NOT_FOUND`. The route is wired into both the preview runtime and the
   production composition.
3. **Used By tab**: the Calendars window detail gains a read-only Used By tab with the total,
   a localized per-kind summary and one row per reference, including the assignment/activity
   identifier. The payload parser fails closed on a mismatched contract, calendar reference,
   wrong array length or non-integer counts, so a drifted server cannot render partial usage.
4. **Assignment calendar reference**: the Assignments register form gains a calendar select
   with a `Project default` option and every stored calendar as an exact `id|version` value.
   Saving sends `calendar_id` and `calendar_version`; a half-filled reference throws
   `INCOMPLETE_CALENDAR_REFERENCE` before the request, and the register's calendar column
   shows the stored reference.
5. **Role gating in the register**: New and Revise assignment controls render only for
   planner/project_admin roles, so a viewer sees the register and the usage tab but cannot
   start a write. The server still enforces the write permission independently.
6. **Browser evidence**: six scenarios drive the real window: baseline usage shows the stored
   resource master, a new assignment is saved with an explicit calendar reference, usage then
   counts both reference kinds, unknown calendar/stale version return 404, a viewer reads
   usage and is refused a create with 403, and the Persian usage tab renders at 1280×720
   without overflow.

### Defects found while building the evidence and fixed

- The first harness run reused a preview database that already contained an assignment from
  an earlier interrupted run, so the baseline assertion saw a total of 2. Evidence runs now
  start from a `--reset` preview and the report pins the code SHA.
- The harness exit called `chrome.close()`, which the shared launcher does not expose; it now
  calls the supported `stop()` so a failing scenario reports its real assertion and Chrome
  does not keep the process alive.
- `WorkspaceCalendarRecord` was not exported from the calendars module; it is re-exported
  from the shared model so the assignments form can type the calendar catalogue.
- Assignment tests failed typecheck once the calendar field became part of the input; the
  fixtures and expected payloads were updated and a half-reference rejection test was added.
- The New Assignment control was initially visible to viewers; it is now gated by the same
  write-role check `main.ts` already knows.

### Honest limits (definite, not planned)

- Usage is derived on read; there is no stored usage projection, no Postgres mirror and no
  cross-project aggregate.
- A resource master stores only a calendar id, so those rows are matched by id and reported
  with `calendar_version: null`; changing a calendar version does not invalidate a resource
  master reference.
- Activity and relationship-lag calendar assignments can be counted only when another flow
  stored them; this slice adds no UI to create those assignments.
- The assignment form offers the project's stored calendars only; there is no scoped
  assignment editor launched from Project Details or Resources.
- Multi-view calendar rendering, recurring exceptions and calendar delete/replace remain
  unsupported in this window.
- Calendar and register labels remain inline English/Persian; the nine-locale catalogs are
  still pending.
- Provider-specific product names are not shown in the UI or Help text.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `cd apps/web && npx tsc --noEmit` | clean |
| Unit/integration | `cd apps/web && npm test` | 832 `tsx` tests + 14 `node --test` tests pass, 0 fail |
| Calendars web suite | `workspace-calendars.test.ts` | 36 tests including the usage parser/loader coverage |
| Assignments web suite | `workspace-assignments.test.ts` | 19 tests including the calendar payload and half-reference rejection |
| Backend usage suite | `pytest tests/test_calendar_usage_api.py` | 2 passed |
| Full Python suite | `pytest tests` | 3492 passed, 109 skipped |
| Build | `cd apps/web && npm run build` | bundles written to `dist/web/src` |
| Usage scenarios | `CUBI_PREVIEW_URL=http://127.0.0.1:4193 CUBI_TESTED_CODE_SHA=f714cf94 node e2e/calendars-usage-v26.mjs` | 6/6 scenarios pass, 5 screenshots, 0 exceptions, 0 console errors, 0 API failures |
| Layout at 1280×720 | scenario 06 of the same suite | Persian RTL usage panel and table inside the viewport |
| Evidence bundle | `docs/workspace/evidence/calendars-usage-v26-2026-11-12/` | `calendars-usage-v26.json` + 5 screenshots |

Recorded provenance (two independent facts):

| Field | Value |
| --- | --- |
| Tested code SHA | `f714cf9453a2742f4d9222cdbbdde506549f712b` |
| Evidence commit | `8c3c17afaf9b989ea1ee5735096331e896d2ec0a` |
| Branch head at merge | `7c97e5226c7854add03ef07f28b8234fcaec7061` |
| PR | [#1769](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1769) |
| Merge commit | `cef505e93f3a729f9bcca9686f7a658af05f7c00` |
| Post-merge CI | 5/5 workflow runs success on `cef505e9` |

The evidence report keeps `testedCodeSha` and `evidenceCommitSha` as separate fields: the
scenarios ran on `f714cf94`, and the screenshots plus report were committed afterwards as
`8c3c17af`; a follow-up commit pinned that value into the report.

### Next stage

Remaining calendar multi-view rendering and recurring exceptions stay recorded as a gap.
Execution moves to Stage F — Reports, Administration, Import/Export and Backup/Recovery —
then Stage G workspace integration and the final review.

Changed files: `src/construction_pm/p6_calendar_usage_api.py`,
`src/construction_pm/http/project_lifecycle_routes.py`,
`src/construction_pm/http/production_composition.py`, `src/construction_pm/preview/runtime.py`,
`tests/test_calendar_usage_api.py`, `apps/web/src/workspace-calendars.ts`,
`apps/web/src/workspace-calendars.test.ts`, `apps/web/src/workspace-assignments.ts`,
`apps/web/src/workspace-assignments.test.ts`, `apps/web/src/main.ts`,
`apps/web/e2e/calendars-usage-v26.mjs`.

---

## Stage E1 — Project Issue register, status graph and history

Status: **merged**. Independent PR
[#1757](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1757) squash-merged into
`main` as `c920dc19` on 2026-11-12. Post-merge CI on `c920dc19`: deploy, build, test
3.11/3.12/3.13, typecheck apps/web, apps/mobile, apps/desktop, apps/client-sync, postgres-sync
and web all succeeded.

### What shipped

1. **Authoritative issue register** (`p6_issue_repository.py`): project-scoped records with
   validated `cost|schedule|quality|safety|scope|resource|other` types,
   `open|in_progress|resolved|closed` statuses and `low|normal|high|critical` priorities.
   The domain enforces ISO dates, `due_date >= date_identified`, a resolution note for resolved
   and closed records, record revisions `1..MAX_SAFE_REVISION`, and the documented transition
   graph (closed is final; resolved may reopen). Every create, field change, status change,
   comment and delete appends an immutable `p6_issue_event` row with actor, timestamp and detail;
   delete removes the record but keeps its audit trail.
2. **Versioned API and HTTP routes** (`p6-issue-api.v1`): `GET/POST /p6/issues`,
   `GET/PUT/PATCH/DELETE /p6/issues/{id}`, `GET /p6/issues/{id}/history` and
   `POST /p6/issues/{id}/comments`, with project read/write authorization, cross-scope denial,
   duplicate protection (409 `ISSUE_ALREADY_EXISTS`), stale-write protection
   (409 `ISSUE_REVISION_CONFLICT`) and the public 404 `P6_ISSUE_NOT_FOUND`. Writes run inside
   the repository transaction manager in preview; production composition receives the same API.
3. **Issues window** (`workspace-issues.ts`): the static register shell and its submenu status
   moved to Partial. The window reads the server with status/priority/type/search filters, creates
   issues, edits with `expected_revision`, changes status through the server graph, comments,
   deletes with confirmation, and renders general, details, document-reference and history tabs.
   A 409 reloads the authoritative record instead of showing the stale form; closed issues disable
   edit and remove the comment form with a truthful "Closed issues are final" note. Status and
   priority badges, RTL-safe labels, English/Persian copy and the empty/loading/error/filtered
   states are implemented.
4. **Query-string carriage**: the WSGI layer now forwards `QUERY_STRING` for `/p6/issues` (as it
   already did for forms), because the router reads filters from the routed query. Without this,
   the browser's server-side filters silently returned the full register; the preview suite now
   creates two records and proves a filter returns exactly one.
5. **Bottom-pane parity**: Issues owns its detail tabs, so the shared bottom details pane is
   collapsed and hidden for this menu, matching Roles and Calendars and avoiding a duplicate
   generic surface.

### Honest limits

- No notification or email delivery; the Help topic's notification part is not implemented.
- Owner and responsible manager are free-text fields, not a user-directory assignment.
- Document references are stored and displayed as text; they are not linked to the document
  register, and there is no attachment upload.
- No bulk import/export, no issue-to-activity drill-through beyond the stored references, and
  deleted records are not readable through the detail/history routes (the event trail is retained
  only in repository storage).
- The Postgres repository mirror exists but is not exercised by the default test suite.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `cd apps/web && npm run typecheck` | clean |
| Unit/integration (web) | `cd apps/web && npm test` | 786 `tsx` tests + 14 `node --test` tests pass, 0 fail |
| Issues web suite | `apps/web/src/workspace-issues.test.ts` | 9 tests: parsing, filters, validation, create, revision update/conflict, comment/history, delete |
| View/navigation regression | `workspace-view.test.ts`, `workspace-navigation.test.ts` | 102 focused tests pass, including the first-class Issues window and collapsed bottom pane |
| Backend issue suites | `pytest tests/test_p6_issue_repository.py tests/test_p6_issue_api.py tests/test_p6_issue_http_routes.py tests/test_preview_issues.py` | 18 passed |
| Full Python suite | `pytest tests` | 3378 passed, 109 skipped |
| Build | `cd apps/web && npm run build` | bundles written to `dist/web/src` |
| Browser E2E | `CUBI_PREVIEW_URL=… CUBI_CHROME_NO_SANDBOX=1 node e2e/issues-v26.mjs` | 13/13 scenarios pass, 12 screenshots, 0 exceptions, 0 console errors, 0 API failures |
| Layout at 1280×720 | scenario 13 of the same suite | toolbar, filters, register and window fit; shared bottom pane collapsed |
| CSS copies | `cmp apps/web/styles.css apps/web/public/styles.css` | byte-identical |
| Evidence bundle | `docs/workspace/evidence/issues-v26-2026-11-12/` | `issues-v26.json` + 12 screenshots |

Recorded provenance (two independent facts):

| Field | Value |
| --- | --- |
| Tested code SHA | `f7ff537d4d3d124e5fc58b4ca304974eec54fd84` |
| Evidence commit | `545ed4a5371d9c85cd6e36b34163a1a6745be3ae` |
| Branch head at merge | `3028f5211c10fb0059cdc5277b6d39e02f9d2e17` |
| PR | [#1757](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1757) |
| Merge commit | `c920dc195cb0cd8aa4c0b1f5440b031e44026d9f` |
| Post-merge CI | 5/5 workflows success on `c920dc19` |

The evidence report keeps `testedCodeSha` and `evidenceCommitSha` as separate fields: the
scenarios ran on `f7ff537d`, and the screenshots plus report were committed afterwards.

### Next stage

Stage E2 Documents (shipped below), then Thresholds and the Risk register.

## Stage E2 — Project document register, audited status graph and history

Status: **merged**. Independent PR
[#1759](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1759) squash-merged into
`main` as `8f9b37a0` on 2026-11-12. Post-merge CI on `8f9b37a0`: ConstructionPM CI, Web CI,
Client Typecheck, PostgreSQL Integration, PostgreSQL Sync State Integration and the Pages deploy
all succeeded.

### What shipped

1. **Authoritative document register** (`document_persistence.py`): `SQLiteDocumentStore`
   mirrors the existing `PostgresDocumentStore` metadata boundary. Documents keep
   `contract|drawing|correspondence|rfi|submittal|delay_claim|evidence` types and
   `draft|submitted|approved|rejected|superseded` statuses, an explicit
   `sha256:` 64-hex content hash and a `storage_ref`; bytes are never stored here.
   Create records an idempotency fingerprint (`DOCUMENT_IDEMPOTENCY_KEY_REUSE` on reuse,
   `DOCUMENT_ALREADY_EXISTS` on a duplicate id), list supports type/status/search filters with
   project isolation, updates are revision-guarded and every create, update and status
   transition appends an immutable `project_document_audit` row.
2. **Application boundary** (`document_application.py`): `list` and `history` require
   `PROJECT_READ` and confirm the document exists inside the project. `update` now refuses any
   status change (`DOCUMENT_STATUS_REQUIRES_TRANSITION`) so a metadata edit cannot bypass the
   approval endpoint; the transition call passes the authenticated roles to the authorizer.
   `RolePermissionDocumentLifecycleAuthorizer` gates `approved`/`rejected` on
   `project_admin` without hard-coding a user id.
3. **Versioned API and HTTP routes** (`DocumentAPI` v1.0): `GET/POST /api/projects/{id}/documents`,
   `GET /documents/{id}`, `GET /documents/{id}/history`, `PUT/PATCH /documents/{id}` and
   `POST /documents/{id}/status`, with project read/write authorization and honest
   `404 DOCUMENT_NOT_FOUND`, `409 DOCUMENT_REVISION_CONFLICT`,
   `400 DOCUMENT_INVALID_STATUS_TRANSITION` and `403` authorization DTOs. The status endpoint
   rebuilds the record from the stored row so a caller cannot smuggle other fields. WSGI carries
   the list query string in preview and production.
4. **Documents window** (`workspace-documents.ts`): replaces the static register shell. The page
   reads the server with type/status/search filters, creates drafts, edits metadata with
   `expected_revision`, offers only the declared status transitions with a reason, renders
   general/history tabs and the append-only trail, and reloads the authoritative record after a
   409. The content hash input is validated as a real SHA-256 and never generated. `canWrite`
   mirrors `PROJECT_WRITE` (planner/project_admin) and `canApprove` mirrors the approval role, so
   read-only users see disabled actions rather than decorative ones.
5. **Bottom-pane parity and cleanup**: Documents owns its detail pane, so the shared bottom
   surface stays collapsed, matching Roles, Calendars and Issues. The legacy static document
   renderer, its tab/selection caches and the unused documents empty-state branch were removed.

### Honest limits

- The register is metadata-only. Binary upload/download is not exposed; callers must supply an
  existing `storage_ref` and the hash computed by the upload source (`GAP-DOC-02`).
- No document links to WBS/activity records beyond stored free-text references, no categories
  dictionary, no revision file history and no bulk import/export.
- Approval is role-gated but there is no multi-step workflow, delegation or notification.
- The Postgres store gains `list` and timestamp coercion but is not exercised by the default
  test suite.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `cd apps/web && npx tsc -p tsconfig.json --noEmit` | clean |
| Unit/integration (web) | `cd apps/web && npm test` | 795 `tsx` tests + 14 `node --test` tests pass, 0 fail |
| Documents web suite | `apps/web/src/workspace-documents.test.ts` | 11 tests: parsing, contract, transition graph, payload/hash validation, filter/history paths, create/update/status envelopes |
| Backend document suites | `pytest tests/test_document_sqlite_store.py tests/test_document_application_reads.py tests/test_document_api_v1.py tests/test_document_http_routes.py tests/test_preview_documents.py` | 25 passed |
| Full Python suite | `PYTHONPATH=src pytest tests` | 3403 passed, 109 skipped |
| Build | `cd apps/web && npm run build` | bundles written to `dist/web/src` |
| Browser E2E | `CUBI_PREVIEW_URL=… CUBI_CHROME_NO_SANDBOX=1 node e2e/documents-v26.mjs` | 13/13 scenarios pass, 11 screenshots, 0 exceptions, 0 console errors, 0 API failures |
| Layout at 1280×720 | scenario 13 of the same suite | Persian RTL, toolbar/filters/register/window fit, shared bottom pane collapsed |
| CSS copies | `cmp apps/web/styles.css apps/web/public/styles.css` | byte-identical |
| Evidence bundle | `docs/workspace/evidence/documents-v26-2026-11-12/` | `documents-v26.json` + 11 screenshots |

Recorded provenance (two independent facts):

| Field | Value |
| --- | --- |
| Tested code SHA | `b22c795581d8773f890b12915ed0e078c4153f09` |
| Evidence commit | `cbd783b28a140d85447c978721786e389c7c1ee9` |
| Branch | `feat/v26-stage-e-documents` |
| PR | [#1759](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1759) |
| Merge commit | `8f9b37a02d0bd910ad6db5d67017f765eb9ad018` |
| Post-merge CI | 6/6 workflows success on `8f9b37a0` |

The evidence report keeps `testedCodeSha` and `evidenceCommitSha` as separate fields: the
scenarios ran on `b22c7955`, and the screenshots plus report were committed afterwards.

## Stage E3 — Project budget register, pending changes and funding sources

PR [#1761](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1761) squash-merged
into `main` as `9c11331b` on 2026-11-12. Post-merge CI on `9c11331b`: ConstructionPM CI, Web CI,
Client Typecheck, PostgreSQL Integration, PostgreSQL Sync State Integration and the Pages deploy
all succeeded.

### What shipped

1. **Persistent budget domain** (`budget_persistence.py`): `SQLiteBudgetStore` owns
   `project_budget_line`, `project_budget_change`, `project_budget_funding` and the immutable
   `project_budget_audit` trail. Money is parsed by one shared `parse_budget_amount` routine that
   rejects booleans, floats, exponents, non-finite values and more than two decimals, and is
   formatted back as two-decimal text. Creates carry idempotency fingerprints
   (`BUDGET_IDEMPOTENCY_KEY_REUSE` on reuse, `BUDGET_ALREADY_EXISTS` on a duplicate id), updates
   require `expected_revision` (`BUDGET_REVISION_CONFLICT`), and a change can only leave
   `pending` once (`BUDGET_CHANGE_ALREADY_RESOLVED`).
2. **Derived budget arithmetic** (`budget_application.py`): the stored original amount is never
   rewritten by approvals. The current budget is `original + approved changes`; pending changes
   are reported separately; funding balance is `current − funding sources`. Summaries are
   grouped per currency with exact two-decimal `Decimal` arithmetic. A line's currency is locked
   once changes exist (`BUDGET_CURRENCY_LOCKED`).
3. **Application boundary and versioned API** (`BudgetAPI`, `p6-budget-api.v1`): project-scoped
   reads and writes behind `PROJECT_READ`/`PROJECT_WRITE`, actor identity checked against the
   authenticated principal, and approval restricted to `project_admin`
   (`BUDGET_APPROVAL_REQUIRES_ADMIN`, 403). The HTTP layer maps not-found, conflict and
   validation codes to honest 404/409/400 envelopes.
4. **HTTP, preview and production wiring**: `GET/POST /api/projects/{id}/budget/lines`,
   `GET/PUT/PATCH /budget/lines/{id}`, `GET/POST /budget/lines/{id}/changes`,
   `GET /budget/lines/{id}/history`, `POST /budget/changes/{id}/status`,
   `GET/POST /budget/funding`, `PUT/PATCH /budget/funding/{id}` and `GET /budget/summary`.
   WSGI carries the line-filter and funding query strings through the real app, and the preview
   runtime persists everything across restarts.
5. **Cost workspace panel** (`workspace-budget.ts`): the Cost page now mounts a real budget panel
   with per-currency totals, line create/edit, pending change entry, admin-only approve/reject,
   funding sources, history and revision-conflict notices. Planner can write; viewer is read-only;
   only `project_admin` sees approval controls.

### Honest limits

- There is no actual-cost or spending engine yet: `period_id` is a stored string, and variance
  against actuals, expenses and cost accounts remains `COST-001`/`COST-002` work.
- Lines are not periodized into a time-phased curve, and there is no bulk import/export.
- Budget facts live in SQLite only; there is no Postgres mirror for this slice.
- Funding sources are recorded, not reconciled against real receipts.
- The new budget labels are inline English/Persian rather than part of the eight-locale dictionary.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `cd apps/web && npx tsc --noEmit` | clean |
| Web unit/integration | `cd apps/web && npm test` | 801 `tsx` tests + 14 `node --test` tests pass, 0 fail |
| Budget web suite | `apps/web/src/workspace-budget.test.ts` | 6 tests: parsers, contract drift, payload validation, money text, filtered reads, write envelopes |
| Budget backend suites | `pytest tests/test_budget_sqlite_store.py tests/test_budget_application.py tests/test_budget_api.py tests/test_budget_http_routes.py tests/test_preview_budget.py` | 23 passed |
| Adjacent regression | same run plus documents/preview/WSGI suites | 35 passed |
| Full Python suite | `PYTHONPATH=src pytest tests` | 3426 passed, 109 skipped |
| Build | `cd apps/web && npm run build` | bundles written to `dist/web/src` |
| Browser E2E | `CUBI_PREVIEW_URL=… CUBI_CHROME_NO_SANDBOX=1 node e2e/budget-v26.mjs` | 12/12 scenarios pass, 12 screenshots, 0 exceptions, 0 console errors, 0 API failures |
| Layout at 1280×720 | scenario 12 of the same suite | Persian RTL, summary/lines/changes/funding fit without clipping |
| CSS copies | `cmp apps/web/styles.css apps/web/public/styles.css` | byte-identical |
| Evidence bundle | `docs/workspace/evidence/budget-v26-2026-11-12/` | `budget-v26.json` + 12 screenshots |

Recorded provenance (two independent facts):

| Field | Value |
| --- | --- |
| Tested code SHA | `32028937fe5be1755331afa21d7d0dc35cfe20b5` |
| Evidence commit | `6fd7262393086b4d4b532f5ba74938c7ffa00f34` |
| Branch | `feat/v26-stage-e3-budget` |
| PR | [#1761](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1761) |
| Merge commit | `9c11331b5f20b82e84f68c877ebbc47e71ca7250` |
| Post-merge CI | 6/6 workflows success on `9c11331b` |

### Next stage

Stage E3 Expenses/Cost Accounts and Thresholds, then the Risk register.

## Stage E3b — Expense and cost-account register

PR [#1763](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1763) squash-merged
into `main` as `67b69adb` on 2026-11-12. Post-merge CI on `67b69adb`: ConstructionPM CI,
ConstructionPM Web CI, Client Typecheck, PostgreSQL Sync State Integration and the Pages deploy
all succeeded (5/5 workflows).

### What shipped

1. **Persistent cost domain** (`cost_persistence.py`): `SQLiteCostStore` owns
   `project_cost_account`, `project_expense` and the immutable `project_cost_audit` trail. One
   shared `parse_cost_amount` routine rejects booleans, `None`, floats, exponents, non-finite
   values and more than two decimals, and `parse_cost_date` accepts only ISO calendar dates.
   Creates carry idempotency fingerprints (`COST_IDEMPOTENCY_KEY_REUSE`), updates and deletes
   require `expected_revision` (`COST_REVISION_CONFLICT`), and deleting an account that has
   children or is referenced by an expense fails with `COST_ACCOUNT_HAS_CHILDREN` /
   `COST_ACCOUNT_IN_USE`.
2. **Accounts and expenses** (`cost_application.py`): accounts support a parent hierarchy with
   ancestry-cycle rejection, copy (server clones parent/description with `is_default = false`),
   and exactly one project default — clearing the previous default bumps its revision and writes
   a `default_cleared` audit event. Expenses store a validated category
   (`labor\|material\|equipment\|subcontract\|overhead\|other`), a three-letter currency,
   activity/WBS/cost-account references, expense and accrual dates and planned/actual/remaining
   amounts, with server-side category/cost-account/activity/search filters and a per-currency
   summary.
3. **Application boundary and versioned API** (`CostAPI`, `p6-cost-api.v1`): project-scoped reads
   and writes behind `PROJECT_READ`/`PROJECT_WRITE`, actor identity checked against the
   authenticated principal, and flat versioned DTOs. The HTTP layer maps not-found to 404,
   conflicts to 409 and validation to 400, including the copy, default and history routes.
4. **HTTP, preview and production wiring**: `GET/POST /api/projects/{id}/cost/accounts`,
   `GET/PUT/PATCH/DELETE /cost/accounts/{id}`, `GET /cost/accounts/{id}/history`,
   `POST /cost/accounts/{id}/copy`, `POST /cost/accounts/{id}/default`,
   `GET/POST /cost/expenses`, `GET/PUT/PATCH/DELETE /cost/expenses/{id}`,
   `GET /cost/expenses/{id}/history` and `GET /cost/summary`. WSGI carries the query strings for
   account/expense reads, and the preview runtime persists everything across restarts.
5. **Expenses window** (`workspace-expenses.ts`): the page now mounts a real cost register over
   `p6-cost-api.v1` with an expense table, details pane, create/edit/delete, category and
   cost-account selects, accrual date, and a cost-account table with parent links, default badge,
   copy, set-default, edit and delete. Revision conflicts reload the authoritative record, and
   planner/admin see write controls while viewer is read-only in the UI and on the server.

### Honest limits

- Expenses have no approval workflow, periodization or derived variance; the summary is a direct
  per-currency roll-up of stored amounts.
- A cost account can be re-parented only through the edit form; there is no drag-based hierarchy
  editor, archive state or account merge.
- Expenses do not link to budget lines yet; the cost account is the shared reference.
- Cost facts live in SQLite only; there is no Postgres mirror for this slice.
- The new register labels are inline English/Persian rather than part of the eight-locale
  dictionary.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `cd apps/web && npx tsc --noEmit` | clean |
| Web unit/integration | `cd apps/web && npm test` | 807 `tsx` tests + 14 `node --test` tests pass, 0 fail |
| Cost web suite | `apps/web/src/workspace-expenses.test.ts` | 14 tests: parsers, contract drift, payload validation, filters, create/edit/delete, copy/default |
| Cost backend suites | `pytest tests/test_cost_sqlite_store.py tests/test_cost_application.py tests/test_cost_api.py tests/test_cost_http_routes.py tests/test_preview_cost_register.py` | 23 passed |
| Adjacent regression | same run plus budget repository/application/API/HTTP suites | 46 passed |
| Full Python suite | `PYTHONPATH=src pytest tests` | 3450 passed, 109 skipped |
| Build | `cd apps/web && npm run build` | bundles written to `dist/web/src` |
| Browser E2E | `CUBI_PREVIEW_URL=… CUBI_CHROME_NO_SANDBOX=1 node e2e/expenses-v26.mjs` | 12/12 scenarios pass, 12 screenshots, 0 exceptions, 0 console errors, 0 API failures |
| Layout at 1280×720 | scenario 12 of the same suite | Persian RTL, expense table and account panel fit without clipping |
| Evidence bundle | `docs/workspace/evidence/expenses-v26-2026-11-12/` | `expenses-v26.json` + 12 screenshots |

Recorded provenance (two independent facts):

| Field | Value |
| --- | --- |
| Tested code SHA | `605678a8547d666f7601c5234222184d23394ad6` |
| Evidence commit | `49a59396daea5109cd26979f7c034242fba7f072` |
| Branch | `feat/v26-stage-e3b-cost-register` |
| PR | [#1763](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1763) |
| Merge commit | `67b69adbeb56018d81120531d33fcd67b9eb9dea` |
| Post-merge CI | 5/5 workflows success on `67b69adb` |

### Next stage

Stage E Thresholds (definitions, monitoring and generated issues) and the Risk register.


## Stage E4 — Project threshold register, monitoring runs and generated issues

PR [#1765](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1765) squash-merged
into `main` as `a761b5be` on 2026-11-12. Post-merge CI on `a761b5be`: ConstructionPM CI,
Client Typecheck, PostgreSQL Sync State Integration and the Pages deploy succeeded on the first
run; ConstructionPM Web CI failed its browser job with `CHROME_DID_NOT_START` (runner
infrastructure, no test assertion ran), and the re-run of the failed job succeeded.

### What shipped

1. **Persistent threshold domain** (`threshold_persistence.py`): `SQLiteThresholdStore` owns
   `project_threshold`, the immutable `project_threshold_audit` trail and the immutable
   `project_threshold_run` log. One shared `parse_threshold_number` routine rejects booleans,
   floats, exponents, non-finite values and more than four decimals; bounds may be negative,
   levels may not, and every definition requires `issue_level > warning_level` with at least one
   bound. Creates carry idempotency fingerprints (`THRESHOLD_IDEMPOTENCY_KEY_REUSE`), updates and
   deletes require `expected_revision` (`THRESHOLD_REVISION_CONFLICT`), and a duplicate id fails
   with `THRESHOLD_ALREADY_EXISTS`.
2. **Authoritative metrics and level evaluation** (`threshold_metrics.py`): `ProjectMetricReader`
   reads live facts instead of cached totals — `open_issue_count` counts open and in-progress
   issues, `expense_actual_total` sums stored actual expense amounts per currency, and
   `budget_balance` derives `original + approved changes - funding` per currency. A monetary
   parameter without a currency fails with `THRESHOLD_CURRENCY_REQUIRED`; an unknown parameter
   fails closed.
3. **Monitoring and generated issues** (`threshold_application.py`): each `POST
   /thresholds/{id}/monitor` reads the metric, evaluates `normal|warning|issue` from the
   deviation against the configured bounds and levels, allocates the next immutable run
   sequence, and records a `project_threshold_run` with the observed value and currency. A
   generated P6 issue is raised only on a transition into `issue` (previous run was not `issue`),
   with id `THR-<threshold_id>-R<sequence>`, through the existing issue API so authorization and
   audit stay in one path. Repeating a monitor while the level stays `issue` does not duplicate
   the issue; a run that returns to `normal`/`warning` and later crosses into `issue` again raises
   a new one.
4. **Versioned API and HTTP surface** (`threshold_api.py`, `p6-threshold-api.v1`): flat DTOs for
   definitions, runs, history and errors, project-scoped behind `PROJECT_READ`/`PROJECT_WRITE`
   with actor identity checked against the principal. Routes: `GET/POST
   /api/projects/{id}/thresholds`, `GET/PUT/PATCH/DELETE /thresholds/{id}`, `GET
   /thresholds/{id}/history`, `GET /thresholds/{id}/runs`, `POST /thresholds/{id}/monitor`, with
   server-side subject/parameter/status/search filters. Not-found maps to 404, conflicts to 409,
   validation to 400.
5. **Preview, production and workspace wiring**: the preview runtime composes the threshold store,
   metric reader and issue writer against the real issue, cost and budget stores and persists
   across restarts; production composition accepts an optional `ThresholdAPI`. The Thresholds
   window (`workspace-thresholds.ts`) mounts a real register over the API with toolbar
   create/refresh, filters, a definitions table, create/edit form, monitor action, run log and
   history panel. A stale write reloads the authoritative record after a 409; planner/admin see
   write controls while viewer is read-only in the UI and receives server 403s.

### Honest limits

- Only three monitoring parameters exist (`open_issue_count`, `expense_actual_total`,
  `budget_balance`); quality, safety, resource and scope subjects can be stored but have no
  metric source yet.
- Monitoring is manual; there is no scheduler, background evaluation, escalation policy or
  notification delivery. A generated issue is a normal P6 issue with a free-text owner.
- Generated issues are not linked back from the issue to the threshold beyond the id pattern,
  and deleting a threshold keeps its audit trail but makes its runs unreachable through the API.
- Threshold facts are SQLite only; there is no Postgres mirror, and definitions have no separate
  version history beyond revisions and audit events.
- New register labels are inline English/Persian rather than part of the eight-locale dictionary.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `cd apps/web && npx tsc --noEmit` | clean |
| Web unit/integration | `cd apps/web && npm test` | 818 `tsx` tests + 14 `node --test` tests pass, 0 fail |
| Threshold web suite | `apps/web/src/workspace-thresholds.test.ts` | 10 tests: strict parsers, payload normalization, create/patch/delete paths, runs/history, monitor envelope |
| Workspace view suite | `apps/web/src/workspace-view.test.ts` | 89 tests, including the first-class Thresholds window |
| Threshold backend suites | `pytest tests/test_threshold_sqlite_store.py tests/test_threshold_metrics.py tests/test_threshold_application.py tests/test_threshold_api.py tests/test_threshold_http_routes.py tests/test_preview_thresholds.py` | 22 passed |
| Full Python suite | `PYTHONPATH=src pytest tests` | 3472 passed, 109 skipped |
| Build | `cd apps/web && npm run build` | bundles written to `dist/web/src` |
| Browser E2E | `CUBI_CHROME_NO_SANDBOX=1 CUBI_TESTED_CODE_SHA=47ab370 node e2e/thresholds-v26.mjs` | 13/13 scenarios pass, 13 screenshots, 0 exceptions, 0 console errors, 0 API failures |
| Generated issue readback | scenario 05 of the same suite | the run created `THR-<id>-R3`, and the issue is readable from `/p6/issues/{id}` |
| Layout at 1280×720 | scenario 12 of the same suite | Persian RTL, table, filters and details panel fit without clipping |
| Evidence bundle | `docs/workspace/evidence/thresholds-v26-2026-11-12/` | `thresholds-v26.json` + 13 screenshots |

Recorded provenance (two independent facts):

| Field | Value |
| --- | --- |
| Tested code SHA | `47ab370ae6dc706c9175f7069d0f440bcfcac714` |
| Evidence commit | `a2ab8c2f767c3a8b216ab0cc9ad673b630768569` |
| Branch | `feat/v26-stage-e-thresholds` |
| PR | [#1765](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1765) |
| Merge commit | `a761b5be76ab739a6ab718bcb677be02c4c63464` |
| Post-merge CI | 5/5 workflows success on `a761b5be` (Web CI browser job re-run after a `CHROME_DID_NOT_START` runner flake) |

### Next stage

Stage E Risk register (delivered as Stage E5 below), remaining Calendar work, then Stage F
(Reports; Administration; Import/Export; Backup/Recovery).

## Stage E5 — Project risk register, scoring matrix and response history

PR [#1767](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1767) squash-merged
into `main` as `1342b60a` on 2026-11-12. Post-merge CI on `1342b60a`: ConstructionPM CI, Client
Typecheck, PostgreSQL Sync State Integration, the Pages deploy and ConstructionPM Web CI all
succeeded on the first run.

### What shipped

1. **Persistent risk domain** (`risk_persistence.py`): `SQLiteRiskStore` owns `project_risk` and
   the immutable `project_risk_audit` trail. A risk carries a title, description, one of nine
   categories (`technical|commercial|schedule|cost|quality|safety|resource|external|other`), one
   of four statuses (`open|monitoring|mitigating|closed`), integer probability and impact in
   `1..5` (booleans and floats rejected), one of five response strategies
   (`avoid|transfer|mitigate|accept|escalate`), owner, optional response owner, response due date,
   responsible manager, identification date and closure note. Score is derived as `p × i`; the
   exposure band is `low ≤ 4`, `medium ≤ 9`, `high ≤ 16`, `critical` otherwise. The status graph
   allows movement among `open`, `monitoring` and `mitigating`, `closed → open` only, same-status
   writes as no-ops, and requires a closure note whenever the target status is `closed`
   (`RISK_CLOSURE_NOTE_REQUIRED`).
2. **Revision and idempotency guards**: creates require an idempotency key
   (`RISK_IDEMPOTENCY_KEY_REUSE` on reuse with a different payload), duplicate ids fail with
   `RISK_ALREADY_EXISTS`, edits and deletes require `expected_revision`
   (`RISK_REVISION_CONFLICT`), illegal transitions fail with `RISK_STATUS_TRANSITION_INVALID`, and
   every accepted write appends an immutable event (`created`, `updated`, `status_changed`,
   `deleted`) with actor, timestamp and revision.
3. **Versioned API and HTTP surface** (`risk_api.py`, `p6-risk-api.v1`): flat DTOs for risks,
   history and errors; project-scoped behind `PROJECT_READ`/`PROJECT_WRITE` with actor identity
   checked against the principal. Routes: `GET/POST /api/projects/{id}/risks`, `GET/PUT/PATCH/
   DELETE /risks/{id}`, `GET /risks/{id}/history`, with server-side category, status, response
   strategy, exposure and search filters and score-descending ordering. Not-found maps to 404,
   conflicts to 409, validation to 400; WSGI carries the risk query strings.
4. **Preview, production and workspace wiring**: the preview runtime composes
   `SQLiteRiskStore` → `RiskApplicationService` → `RiskAPI` against the shared authorization
   policy and transaction manager and persists across restarts; production composition accepts an
   optional `RiskAPI`. The Risks window (`workspace-risks.ts`) mounts a real register with
   toolbar create/refresh, five filters, a register table, a 5×5 exposure matrix whose cells show
   counts by band and outline the selected risk, a create/edit form with closure-note validation,
   a details panel and an audit history list. A stale write reloads the authoritative record
   after a 409; planner/admin see write controls while viewer is read-only in the UI and receives
   server 403s.

### Honest limits

- Risks are project-level records; they are not assigned to activities, WBS nodes, resources or
  owners as tracked assignments, and there is no risk-response action plan or residual-risk
  tracking.
- No notification, escalation, review cadence, risk-report export or risk-to-issue conversion
  exists. The register records response strategy and due date but does not enforce or remind.
- The 5×5 matrix is a live count of stored risks by band; it has no time dimension, no history
  snapshots and no per-category or per-strategy breakdown.
- Deleting a risk removes the row and leaves its audit trail unreachable through the API; there
  is no archive or restore.
- Risk facts are SQLite only; there is no Postgres mirror, and new register labels are inline
  English/Persian rather than part of the eight-locale dictionary.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `cd apps/web && npx tsc --noEmit` | clean |
| Web unit/integration | `cd apps/web && npm test` | 830 `tsx` tests + 14 `node --test` tests pass, 0 fail |
| Risk web suite | `apps/web/src/workspace-risks.test.ts` | 11 tests: exposure bands, strict parsers, payload normalization, save/delete paths, history envelope |
| Workspace view suite | `apps/web/src/workspace-view.test.ts` | 90 tests, including the first-class Risks window |
| Risk backend suites | `pytest tests/test_risk_sqlite_store.py tests/test_risk_application.py tests/test_risk_api.py tests/test_risk_http_routes.py tests/test_preview_risks.py` | 18 passed |
| Full Python suite | `PYTHONPATH=src pytest tests` | 3490 passed, 109 skipped |
| Build | `cd apps/web && npm run build` | bundles written to `dist/web/src` |
| Browser E2E | `CUBI_CHROME_NO_SANDBOX=1 CUBI_TESTED_CODE_SHA=97826cd node e2e/risks-v26.mjs` | 11/11 scenarios pass, 12 screenshots, 0 exceptions, 0 console errors, 0 API failures |
| Scoring and matrix readback | scenarios 02–04 of the same suite | `3×4` stored as score 12 / high, matrix cell `3-4` counts 1, edit to `4×5` gives 20 / critical, stale PATCH returns 409 |
| Closure and history readback | scenarios 05–06 of the same suite | closing without a note returns `RISK_CLOSURE_NOTE_REQUIRED`, closing with a note records revision 3, and history returns `created` + two `status_changed` events |
| Layout at 1280×720 | scenario 10 of the same suite | Persian RTL, toolbar, table and matrix fit without clipping |
| Evidence bundle | `docs/workspace/evidence/risks-v26-2026-11-12/` | `risks-v26.json` + 12 screenshots |

Recorded provenance (two independent facts):

| Field | Value |
| --- | --- |
| Tested code SHA | `97826cda5f349ba885ec9b33cdea29be4d05bf20` |
| Evidence commit | `a6466b2c26596d8bfb6d51efaa22bd72f95c0f05` |
| Branch | `feat/v26-stage-e-risks` |
| PR | [#1767](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1767) |
| Merge commit | `1342b60a0ec97e19528541bf68cdc5169f21d6f6` |
| Post-merge CI | 5/5 workflows success on `1342b60a` |

### Next stage

Remaining Calendar work, then Stage F (Reports; Administration; Import/Export; Backup/Recovery).

## Stage F1 — Project report register, stored runs and report window

PR [#1771](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1771) squash-merged
into `main` as `09022f87` on 2026-11-12. Post-merge CI on `09022f87`: ConstructionPM CI, Client
Typecheck, PostgreSQL Sync State Integration, the Pages deploy and ConstructionPM Web CI all
succeeded on the first run.

### What shipped

1. **Persistent report register** (`report_persistence.py`): a `REPORT_CATALOGUE` fixes three
   authoritative subjects and their typed fields — activities (`activity_id`, name, type, status,
   actual start, expected finish, duration, percent complete), resources (`resource_id`, name,
   type, parent, calendar, unit of measure, active) and risks (`risk_id`, title, category, status,
   probability, impact, score, exposure). A definition stores one subject and an ordered,
   duplicate-free subset of that subject's columns. `SQLiteReportStore` owns
   `project_report_definition`, `project_report_audit`, `project_report_idempotency` and the
   immutable `project_report_run` tables. Creates require an idempotency key
   (`REPORT_IDEMPOTENCY_KEY_REQUIRED`, `REPORT_IDEMPOTENCY_KEY_REUSE`), duplicate ids fail with
   `REPORT_ID_ALREADY_EXISTS`, edits and deletes require `expected_revision`
   (`REPORT_REVISION_CONFLICT`), and every accepted write appends a `created`, `updated` or
   `deleted` audit event.
2. **Authoritative runs** (`report_application.py`): `AuthoritativeReportDataset` materializes
   activity rows from the activity repository, resource rows from `ResourceRepository.list` and
   risk rows from the risk store at the caller's project revision. `run_report` composes only the
   selected columns in definition order and stores the rows verbatim with the definition revision,
   project revision, subject, timestamp and actor. `RUN-<report_id>-<n>` ids are monotonic;
   re-running never mutates an earlier run, and a definition edit cannot rewrite stored output.
3. **Versioned API and HTTP surface** (`report_api.py`, `p6-report-api.v1`): list (with catalogue),
   catalogue, read, history, create, update, delete, run, run summaries and stored-run readback.
   All definition writes are project-scoped behind `PROJECT_WRITE` with actor identity pinned to
   the principal; reads and runs require `PROJECT_READ`. Not-found maps to 404, conflicts to 409
   and validation to 400. The WSGI boundary now carries `/reports` query strings so subject and
   search filters reach the route.
4. **Preview, production and workspace wiring**: the preview runtime composes `SQLiteReportStore`
   → `ReportApplicationService` → `ReportAPI` against the shared authorization policy, transaction
   manager and authoritative repositories; production composition accepts an optional
   `ReportAPI`. The Reports window (`workspace-reports.ts`) replaces the placeholder with a real
   register: toolbar create/refresh, subject and search filters, a definition table, a create/edit
   form driven by the server catalogue (subject switch re-renders the column set), details with
   selected columns, run, immutable run history and an output table with exact row count and meta
   (`run id · rows · definition revision · project revision`). A stale write reloads the
   authoritative record after a 409; viewer sees no create/edit/delete controls but can run and
   read output, and direct writes receive server 403s.

### Honest limits

- Reports are definition-and-run only: there is no scheduled/batch execution, no parameter
  prompts, no grouping/subtotals/sorting/aggregates, no charts, no page layout or print pipeline,
  and no file export (CSV/PDF/XLSX).
- The catalogue is fixed to three subjects and their stored fields; project, WBS, assignment,
  calendar, expense, budget, issue, document and threshold subjects are not reportable.
- Runs are snapshots of the current authoritative rows at one project revision; there is no
  delta/variance run, no cross-project or portfolio run, and no retention or run deletion.
- Deletes hide the definition and its runs from the API; the audit trail remains in SQLite but is
  unreachable. Report facts are SQLite only with no Postgres mirror.
- The window's new labels are inline English/Persian rather than part of the eight-locale
  dictionary.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `cd apps/web && npx tsc --noEmit` | clean |
| Web unit/integration | `cd apps/web && npm test` | 842 `tsx` tests + 14 `node --test` tests pass, 0 fail |
| Report web suite | `apps/web/src/workspace-reports.test.ts` | 10 tests: fail-closed catalogue/definition/list/run parsers, subject+search URL, idempotent create with catalogue re-read, revision-pinned PATCH, run and stored-run paths, delete body |
| Report backend suites | `pytest tests/test_report_api.py tests/test_project_lifecycle_wsgi.py` | 8 passed |
| Full Python suite | `PYTHONPATH=src pytest tests` | 3497 passed, 109 skipped |
| Build | `cd apps/web && npm run build` | bundles written to `dist/web/src` |
| Browser E2E | `CUBI_CHROME_NO_SANDBOX=1 CUBI_TESTED_CODE_SHA=bb30ec9 node e2e/reports-v26.mjs` | 9/9 scenarios pass, 9 distinct screenshots, 0 exceptions, 0 console errors, 0 API failures |
| Run materialization | scenarios 03–05 of the same suite | activity run stores exactly 14 rows and the four selected columns, run 1 readback is unchanged after run 2, edited columns apply to revision 2 with `definition revision 2` stored |
| Filters and authorization | scenarios 06–08 of the same suite | subject `resources` and search `Activity Status` reduce the server and UI lists, resource run returns `RPS-CIVIL-CREW`, viewer runs/reads but the UI has no write controls and a direct POST returns 403 `REPORT_PERMISSION_DENIED` |
| Layout at 1280×720 | scenario 09 of the same suite | Persian RTL heading `گزارش‌های پروژه`, toolbar/register/detail fit without overflow, no external product branding |
| Evidence bundle | `docs/workspace/evidence/reports-v26-2026-11-12/` | `reports-v26.json` + 9 screenshots |

Recorded provenance (two independent facts):

| Field | Value |
| --- | --- |
| Tested code SHA | `bb30ec913f2905eeef6b7c4be5324ca071e1f33e` |
| Evidence commit | `861c69a3f79ede269a9cd5fb0b2ca2f51232e1aa` |
| Branch | `feat/v26-stage-f1-reports` |
| PR | [#1771](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1771) |
| Merge commit | `09022f870e91d515d180d2ce6ee5ff9a0b600448` |
| Post-merge CI | 5/5 workflows success on `09022f87` |

### Next stage

Stage F2 (Administration: users/security profiles/permission matrix, preferences and dictionaries,
currency/units/financial periods), then Import/Export, Backup/Recovery and Stage G integration.

## Stage F2 — Project administration preferences, dictionaries and permission matrix

PR [#1773](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1773) squash-merged
into `main` as `0337a7ad` on 2026-11-12. Post-merge CI on `0337a7ad`: ConstructionPM CI,
ConstructionPM Web CI, Client Typecheck, PostgreSQL Integration, PostgreSQL Sync State Integration
and the Pages deploy all succeeded on the first run.

### What shipped

1. **Persistent preferences and dictionaries** (`administration_persistence.py`): one
   revision-guarded `project_administration_preferences` record per project (currency, unit of
   measure, date display, decimal places, fiscal year start month) with explicit defaults
   (`USD`, `day`, `gregorian`, `2`, `1`). Validation is typed and bounded: a three-letter
   uppercase currency, a unit of measure up to 20 characters, `gregorian` or `jalali` date
   display, 0–4 decimal places and a fiscal month in `1..12`. A code-namespaced
   `project_administration_dictionary` covers five fixed codes (`cost_category`,
   `risk_category`, `issue_type`, `document_type`, `expense_category`); entries carry an id
   (≤32 alphanumeric/`_`/`-`), a label (≤80), a sequence `0..9999`, an active flag and their own
   revision. `project_administration_audit` is append-only and `project_administration_idempotency`
   stores request hashes. Creates are idempotent, duplicate entry ids fail with
   `ADMIN_DICTIONARY_ENTRY_ALREADY_EXISTS`, edits and deletes require `expected_revision`
   (`ADMIN_DICTIONARY_REVISION_CONFLICT`, `ADMIN_PREFERENCES_REVISION_CONFLICT`), and reusing a
   key for different content fails with `ADMIN_IDEMPOTENCY_KEY_REUSE`.
2. **Project-scoped application service** (`administration_application.py`): every call validates
   the tenant/project scope (`CROSS_SCOPE_ACCESS`), reads require `PROJECT_READ`, writes require
   `PROJECT_ADMIN`, and the acting principal must equal the payload actor
   (`ADMIN_ACTOR_MISMATCH`). Writes go through the shared transaction manager and append the
   audit event in the same unit of work.
3. **Derived permission matrix** (`administration_api.py`, `p6-administration-api.v1`): role
   grants are not stored in the administration tables. `permission_matrix()` derives the three
   default roles (viewer, planner, project_admin) against all 14 `Permission` values from the
   single `default_role_permissions()` policy, so the screen cannot drift from enforcement. Endpoints: `GET .../administration/permission-matrix`,
   `GET`/`PUT .../preferences` (revision-pinned), `GET .../dictionaries` (server-side code and
   search filters), `POST .../dictionaries` (idempotency key), `GET`/`PATCH`/`DELETE
   .../dictionaries/{code}/{entry}` and `GET .../history`. Authorization maps to 403,
   `_NOT_FOUND` to 404, conflicts/duplicates/idempotency reuse to 409, everything else to 400.
   The WSGI boundary now carries `/administration` query strings so filters reach the route.
4. **Financial periods tab over the existing contract**: the window lists and creates periods
   through `p6-financial-periods` (`OPEN`/`CLOSED`, start before end) rather than inventing a
   second store; the tab is a read/create projection of the already-persisted period metadata.
5. **Preview, production and workspace wiring**: the preview runtime composes
   `SQLiteAdministrationStore` → `AdministrationApplicationService` → `AdministrationAPI` against
   the shared authorization policy and transaction manager, and production composition accepts an
   optional `AdministrationAPI`. The Administration window (`workspace-administration.ts`, menu key
   `administration`, the 19th workspace menu) has four tabs: Preferences (validated form with
   client-visible revision), Dictionaries (create, edit, delete, server and UI filters), Permission
   Matrix (read-only roles × permissions) and Financial Periods (create and list). A stale write
   returns a 409 and reloads the authoritative record, and the audit history is visible per
   dictionary entry. Viewer sees the data with no write controls; a direct write receives a server
   403 `ADMIN_PERMISSION_DENIED`.

### Honest limits

- Preferences are stored, validated and displayed but are not yet consumed by other windows:
  currency/decimal precision, Jalali date display and the fiscal calendar do not change formatting
  or calculations elsewhere.
- The permission matrix is derived read-only. There is no user directory, no security-profile
  editor, no role-to-user assignment, no custom roles and no per-project grant overrides.
- Dictionaries are limited to five fixed codes and are not yet used as pickers by the document,
  cost, risk or issue windows; there is no bulk import/export, merge or reordering UI.
- Financial periods support list and create only: no close/reopen action, no overlapping-period
  detection across periods, and period boundaries do not gate cost or budget postings.
- Administration facts are SQLite-only with no Postgres mirror; deleting a dictionary entry hides
  its audit trail from the API, and the history route reads one entry at a time.
- New labels are inline English/Persian rather than part of the eight-locale dictionary.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `cd apps/web && npx tsc --noEmit` | clean |
| Web unit/integration | `cd apps/web && npm test` | 852 `tsx` tests + 14 `node --test` tests pass, 0 fail |
| Administration web suite | `apps/web/src/workspace-administration.test.ts` | 10 tests: fail-closed preferences/matrix/dictionary/period parsers, filter and URL construction, revision-pinned save/edit/delete, idempotent create, period create, viewer/admin mounting |
| Administration backend suites | `pytest tests/test_administration_api.py` | 4 HTTP-level tests: defaults + derived matrix + viewer read, admin-only revision-guarded preferences, dictionary CRUD/idempotency/history, validation and idempotency reuse |
| Full Python suite | `PYTHONPATH=src pytest tests` | 3501 passed, 109 skipped |
| Build | `cd apps/web && npm run build` | bundles written to `dist/web/src` |
| Browser E2E | `CUBI_CHROME_NO_SANDBOX=1 CUBI_TESTED_CODE_SHA=99f4a308 node e2e/administration-v26.mjs` | 9/9 scenarios pass, 9 distinct screenshots, 0 exceptions, 0 console errors, 0 API failures |
| Preferences and matrix | scenarios 01–02 of the same suite | four tabs render, 14 permissions across three roles match the policy, save bumps to revision 1 and a stale second save returns 409 |
| Dictionaries | scenarios 03–05 of the same suite | create returns 201, duplicate id and reused key return 409, server filter and UI filter agree, edit bumps the revision, delete returns 200 and a read afterwards is 404 |
| Financial periods | scenario 06 of the same suite | `E2E-PERIOD-*` is created and appears in the list with its start date |
| Authorization | scenario 07 of the same suite | viewer renders no create/edit/delete controls and a direct `POST` returns 403 `ADMIN_PERMISSION_DENIED` |
| Audit history | scenario 08 of the same suite | `created`, `updated` and `deleted` events are read back for the dictionary entry |
| Layout at 1280×720 | scenario 09 of the same suite | Persian RTL heading `مدیریت`, four tabs and tables fit without overflow, no external product branding |
| Evidence bundle | `docs/workspace/evidence/administration-v26-2026-11-12/` | `administration-v26.json` + 9 screenshots, 0 duplicate checksums |

Recorded provenance (two independent facts):

| Field | Value |
| --- | --- |
| Tested code SHA | `99f4a308822dd3b6e367170a87d00df3776afdfe` |
| Evidence commit | `aeed0efa6e8f2ec5ee310fd5a4148ebfe80cd9d8` |
| Branch | `feat/v26-stage-f2-administration` |
| PR | [#1773](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1773) |
| Merge commit | `0337a7ad827d83277910edeb2be543eae4ecb129` |
| Post-merge CI | 6/6 workflows success on `0337a7ad` |

### Next stage

Stage F4 (Backup/Recovery) is complete; Stage G canonical workspace integration and the final
review report remain.

## Stage F3 — Project CSV import/export with validated resource writes

Date: 2026-11-12. Contract: `p6-exchange-api.v1`. Window: Import / Export (20th workspace menu).

### What shipped

1. **Import-run ledger and idempotency store** (`exchange_persistence.py`): SQLite tables
   `project_exchange_import_run` (tenant/project scope, run id, dataset, mode, row counts, content
   SHA-256, actor, timestamp, idempotency key, stored result) and `project_exchange_idempotency`;
   run ids are `EXR-<dataset>-<n>` per project and the store exposes history newest first.
2. **Dataset catalogue and export** (`exchange_application.py`): `activities`, `resources` and
   `risks` are exported from their authoritative repositories at the current project revision with
   fixed contract columns (`resource_id`…`is_active`, `activity_id`…`wbs_id`, `risk_id`…`date_identified`).
   Only `resources` is importable; `activities` and `risks` reject imports with
   `EXCHANGE_DATASET_READ_ONLY`, unknown datasets with `EXCHANGE_DATASET_UNKNOWN`.
3. **Strict CSV validation before any write**: required header, unknown/missing columns
   (`EXCHANGE_COLUMN_MISSING`/`EXCHANGE_COLUMN_UNKNOWN`), row arity, empty content and the
   1,000,000-character ceiling, duplicate ids in the file, ids that already exist
   (`RESOURCE_ALREADY_EXISTS`), unknown parents (`RESOURCE_PARENT_NOT_FOUND`), hierarchy cycles
   (`RESOURCE_HIERARCHY_CYCLE`), calendar existence, resource type, email, units and active-flag
   validation. Every error carries the 1-based row number (header is row 1), field and code; a
   preview returns `accepted`/`rejected` counts and never writes.
4. **Parents-first apply through the resource API**: accepted rows are ordered by hierarchy depth
   then id and created through `P6ResourceAPI.create`, so authorization, calendar checks, parent
   existence and audit stay in one authoritative path. Apply requires an idempotency key
   (`EXCHANGE_IDEMPOTENCY_KEY_REQUIRED`), replays the stored run for identical content and key,
   and rejects key reuse for different content (`EXCHANGE_IDEMPOTENCY_KEY_REUSE`, 409). Reads
   require `PROJECT_READ`, imports require `PROJECT_WRITE`; a viewer direct write receives 403
   `EXCHANGE_PERMISSION_DENIED`. Cross-scope calls fail `CROSS_SCOPE_ACCESS`.
5. **Preview, production and workspace wiring**: the preview runtime composes
   `SQLiteExchangeStore` → `ExchangeService` → `ExchangeAPI` over the activity/resource/risk
   repositories and the shared authorization policy; production composition accepts an optional
   `ExchangeAPI`, and the WSGI boundary carries `/exchange` query strings. The window
   (`workspace-exchange.ts`, menu key `exchange`) mounts Export, Import and Import History tabs:
   dataset switch with contract table and CSV download, dataset selector plus pasted/selected CSV
   content, validation summary with row/field/code errors, apply for `planner`/`project_admin`
   writer roles, created ids and the run history table.

### Honest limits

- Only resources can be imported. Activities and risks are export-only readbacks; there is no
  activity, relationship, WBS, cost or assignment import.
- There is no global search, “Find”, remote-project exchange or round-trip re-import of an edited
  export; UTIL-002's search and remote-data-exchange requirements remain unimplemented.
- Validation covers the resource contract only: no cross-file reference checks beyond parents and
  calendars, no unit-of-measure or rate/limit import, no dry-run diff against current values, and
  previews are capped at 20 returned rows in the payload (counts cover the whole file).
- Import history is append-only with no delete, retry-from-history, download of the applied file
  or per-row audit detail; the run stores the result JSON but no Postgres mirror.
- The CSV parser is a strict single-line, comma-separated reader: no quoted fields, embedded
  commas/newlines, delimiters other than comma or XLSX/JSON formats.
- Exports read the SQLite preview repositories; the production Postgres resource mirror is not
  exercised by the default suite.
- New labels are inline English/Persian rather than part of the eight-locale dictionary.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `cd apps/web && npx tsc --noEmit` | clean |
| Web unit/integration | `cd apps/web && npm test` | 858 `tsx` tests + 14 `node --test` tests pass, 0 fail |
| Exchange web suite | `apps/web/src/workspace-exchange.test.ts` | 6 tests: fail-closed catalogue/export/preview/history parsers, URL and body construction, read-only viewer, invalid and valid writer flows |
| Exchange backend suite | `pytest tests/test_exchange_api.py` | 5 HTTP-level tests: catalogue + three exports, preview/apply/history with idempotent replay, row/field validation errors, existing ids + read-only dataset + missing key, viewer read/403 and planner apply |
| Full Python suite | `PYTHONPATH=src pytest tests` | 3506 passed, 109 skipped |
| Build | `cd apps/web && npm run build` | bundles written to `dist/web/src` |
| Browser E2E | `CUBI_CHROME_NO_SANDBOX=1 CUBI_TESTED_CODE_SHA=f7fdedc node e2e/exchange-v26.mjs` | 8/8 scenarios pass, 8 screenshots, 0 exceptions, 0 console errors, 0 API 5xx |
| Catalogue and exports | scenarios 01–02 of the same suite | three datasets, `resource_id`/`activity_id`/`risk_id` headers match the contract, row counts match the CSV line count, download control present |
| Valid preview and apply | scenarios 03–04 of the same suite | two rows accepted with apply enabled; apply creates both ids, replay returns the same run, key reuse returns 409, export contains the new resources, history shows preview and apply runs |
| Invalid file | scenario 05 of the same suite | row/field/code table shows type, calendar, email and active-flag errors and apply stays disabled |
| Existing id, cycle and read-only dataset | scenario 06 of the same suite | `RESOURCE_ALREADY_EXISTS`, two `RESOURCE_HIERARCHY_CYCLE` errors and `EXCHANGE_DATASET_READ_ONLY` are reported before writing |
| Authorization | scenario 07 of the same suite | viewer export works, editor and apply are disabled, direct apply returns 403 `EXCHANGE_PERMISSION_DENIED` |
| Layout at 1280×720 | scenario 08 of the same suite | Persian RTL heading `ورود / خروجی`, three tabs, no external product branding |
| Evidence bundle | `docs/workspace/evidence/exchange-v26-2026-11-12/` | `exchange-v26.json` + 8 screenshots, contract `cubi-exchange-v26.v1` |

Recorded provenance (two independent facts):

| Field | Value |
| --- | --- |
| Tested code SHA | `f7fdedcd7bc0d2453a2c48ad29e4d81ae151f79f` |
| Evidence commit | `0edef46c53807b56b205ad6bb14127113c30d8d5` |
| Branch | `feat/v26-stage-f3-exchange` |
| PR | [#1775](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1775) |
| Merge commit | `20f49d5b5df76e1c9990b858a582cdc21e74ecf5` |
| Post-merge CI | 5/5 triggered workflows success on `20f49d5b`; PostgreSQL Integration was not selected by the main push path filters (it ran and passed on the PR) |

Two consecutive browser runs failed on script defects (doubled escape sequences, a misaligned CSV
row and an over-strict history count) before the evidence run; each fix is a separate `test(stage-f3)`
commit on the PR so the tested SHA stays honest.

### Next stage

Stage F4 (Backup/Recovery), then Stage G canonical workspace integration and the final review
report.

## Stage F4 — Project and layout backup/recovery

Status: merged. Stage F4 completes the Administration/Utilities block. Stage G canonical
workspace integration is complete; the final review, regression and blocker report remains.

### What shipped

1. **Versioned backup contract**: `p6-backup-api.v1` over `SQLiteBackupStore`, the authoritative
   WBS, activity, relationship and resource repositories and the layout-definition repository.
   `POST /api/projects/{p}/backup` captures; `GET .../backup` lists; `GET .../backup/{id}` and
   `GET .../backup/{id}/content` read one snapshot and its verified manifest;
   `POST .../backup/{id}/restore` restores; `GET .../backup/restores` lists runs.
2. **Checksummed snapshots**: a `project` snapshot stores canonical JSON for `wbs`, `activities`,
   `resources` and `relationships`; a `layouts` snapshot stores stored layout definitions only.
   Every snapshot carries `section_counts`, `content_sha256`, the project revision, actor and
   timestamp. Content reads recompute the checksum and reject drift with 409
   `BACKUP_INTEGRITY_FAILED` before returning rows.
3. **Non-destructive restore**: `merge` creates records missing from the project and leaves
   existing records untouched; `overwrite` updates records that differ using each record's stored
   revision; identical records are skipped in both modes. Restores run in one transaction and
   append an immutable `RSR-<n>` run with per-section created/updated/skipped counts. Restore
   never deletes a record.
4. **Authorization and idempotency**: capture requires `PROJECT_WRITE`, snapshot/content/list
   reads `PROJECT_READ`, restore `PROJECT_ADMIN`; cross-scope calls fail `CROSS_SCOPE_ACCESS`.
   Capture and restore require an idempotency key; identical requests replay the stored result
   (`replayed: true`), different requests under a used key return 409
   `BACKUP_IDEMPOTENCY_KEY_REUSE`.
5. **Preview, production and workspace wiring**: the preview runtime composes
   `SQLiteBackupStore` → `BackupService` → `BackupAPI` over the existing repositories; production
   composition accepts an optional `BackupAPI`; WSGI carries the `/backup` path through the
   query-carry whitelist. The window (`workspace-backup.ts`, menu key `backup`) mounts Snapshots,
   Restore and Restore History tabs: kind/label capture, snapshot table with section counts and
   SHA-256, verified manifest with JSON download, snapshot/mode selection with counted restore
   summary, and the run table.

### Honest limits

- Restore never deletes; there is no snapshot delete, purge or retention policy, and no scheduled
  or offsite copy, encryption-at-rest or object storage. Snapshot content stays in the project
  SQLite store.
- Snapshots are project-scoped only: no cross-project restore, portfolio backup or tenant-wide
  export, and layouts cover the single stored activity-grid view.
- The Postgres mirror and production backup store are not exercised by the default suite.
- New labels are inline English/Persian rather than part of the eight-locale dictionary.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `cd apps/web && npx tsc --noEmit` | clean |
| Web unit/integration | `cd apps/web && npm test` | 862 `tsx` tests + 14 `node --test` tests pass, 0 fail |
| Backup web suite | `apps/web/src/workspace-backup.test.ts` | 5 tests: fail-closed snapshot/content/run parsers, path and idempotency payloads, viewer read-only, writer capture and administrator restore |
| Backup backend suite | `pytest tests/test_backup_api.py` | 6 HTTP-level tests: checksummed project snapshot + list/detail/content, layouts snapshot and merge restore, additive merge + replay + key-reuse 409, overwrite rewind, validation/missing snapshot/section/mode, viewer/planner/admin gates |
| Full Python suite | `PYTHONPATH=src pytest tests` | 3512 passed, 109 skipped |
| Build | `cd apps/web && npm run build` | bundles written to `dist/web/src` |
| Browser E2E | `CUBI_CHROME_NO_SANDBOX=1 CUBI_TESTED_CODE_SHA=04d3d0f node e2e/backup-v26.mjs` | 7/7 scenarios pass, 8 screenshots, 0 exceptions, 0 console errors, 0 API 5xx |
| Snapshot capture and manifest | scenarios 01–02 of the same suite | project snapshot has four sections and a 64-hex SHA; manifest shows section counts and download; layouts snapshot contains only `layouts` |
| Idempotency and validation | scenario 03 of the same suite | replay returns the same `BKP-<n>`, changed label returns 409, bad mode 400 and unknown snapshot 404 |
| Overwrite restore | scenario 04 of the same suite | an edited activity is rewound to the snapshot name, revision advances and the `RSR-<n>` run appears in history |
| Merge safety | scenario 05 of the same suite | merge creates/updates nothing and skips existing records; replay returns the same run |
| Authorization | scenario 06 of the same suite | viewer capture/restore are disabled and 403; planner captures but restore is disabled and 403 |
| Layout at 1280×720 | scenario 07 of the same suite | Persian RTL heading `پشتیبان‌گیری / بازیابی`, three tabs, no external product branding |
| Evidence bundle | `docs/workspace/evidence/backup-v26-2026-11-12/` | `backup-v26.json` + 8 screenshots, contract `cubi-backup-v26.v1` |

Recorded provenance (two independent facts):

| Field | Value |
| --- | --- |
| Tested code SHA | `04d3d0fc32eb619202cbd49ed7ae215e0d3dd5be` |
| Evidence commit | `97bfc7370dd8f9b26dfa3675f2ca3818ed2abe9e` |
| Branch | `feat/v26-stage-f4-backup` |
| PR | [#1777](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1777) |
| Merge commit | `90863b31c149ebe3ef14d0f380f32d2663dc32e2` |
| Post-merge CI | 5/5 triggered workflows success on `90863b3` (ConstructionPM CI, Web CI, Client Typecheck, PostgreSQL Sync State Integration, Pages deploy) |

### Next stage

Stage G canonical workspace integration (complete — see below), then the final full review,
regression and blocker report.

## Stage G — Canonical workspace integration

Status: merged. All Version 26 implementation stages are complete; the final review, regression
and blocker report remains.

### What shipped

1. **Tools menu reaches the exchange and backup windows**: `Project CSV Import / Export…` opens
   `exchange` and `Project Backup / Recovery…` opens `backup`, next to the existing Reports entry.
   The three Stage F/G windows are now reachable from the canonical menu bar rather than only from
   the left navigation rail or a direct URL.
2. **Administration menu rewired to real windows**: a new `Permission matrix…` entry opens
   `administration`; `Categories…` and `Financial period calendars…` open `administration`; and
   `Recovery…` opens `backup`. The previous "not available in this workspace yet" reasons were
   removed from those four entries because the surfaces now exist.
3. **Truthful remaining gaps**: `Users…`, `Security profiles…`, `Currencies…` and
   `Audit history…` keep an explicit disabled reason because no user directory, security-profile
   editor, currency administration or audit viewer ships. The existing invariant that every menu
   entry opens a window, runs a command or states why it is unavailable still holds in both locales,
   and no entry advertises a window it cannot open.
4. **Regression pinning**: `workspace-desktop-shell.test.ts` now asserts each canonical entry against
   its window in English and Persian, keeps the role-gated Administration menu out of a
   non-administrator's menu bar while leaving the project-level Tools entries visible, and covers the
   non-administrator path explicitly.
5. **Browser proof**: the new workspace E2E drives the real preview through headless Chrome and
   reaches Reports, Import / Export, Backup / Recovery and Administration only through
   `[data-desktop-menu]` triggers and `[data-desktop-item]` entries — never a direct URL or the rail.

### Honest limits

- Menu entries do not carry a per-entry permission column; the Administration menu is gated as a
  whole by `project_admin`, and window-level write controls remain the enforcement point.
- Active-window adaptation of the menu bar is still per window only; entries are not dynamically
  hidden or renamed per active surface.
- Several legacy commands still resolve to dialogs or explicit disabled reasons; Stage G wires the
  Stage F windows, it does not audit every legacy menu command.
- No Python or API contract changed in this stage.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `cd apps/web && npx tsc --noEmit` | clean |
| Web unit/integration | `cd apps/web && npm test` | 863 `tsx` tests + 14 `node --test` tests pass, 0 fail |
| Canonical menu invariants | `apps/web/src/workspace-desktop-shell.test.ts` | reports/exchange/backup/administration entries pinned per locale, disabled reasons preserved, administrator gate and every-entry-has-an-effect invariant |
| Build | `cd apps/web && npm run build` | bundles written to `dist/web/src` |
| Browser E2E | `CUBI_CHROME_NO_SANDBOX=1 CUBI_TESTED_CODE_SHA=60370c4 node e2e/workspace-canonical-v26.mjs` | 7/7 scenarios pass, 11 screenshots, 0 exceptions, 0 console errors, 0 API 5xx |
| Tools menu | scenario 01 of the same suite | Reports/Import-Export/Backup entries enabled, mapped to their windows and opened from the menu bar |
| Exchange and backup | scenarios 02–03 | real `Import / Export` and `Backup / Recovery` windows with their dataset/snapshot tabs |
| Administration menu | scenario 04 | permission matrix, categories, periods and recovery reach real windows; Users/Security/Currencies/Audit stay disabled with reasons; no duplicate tab |
| Window lifecycle | scenario 05 | all four windows survive tab switching with their surfaces mounted |
| Role gate | scenario 06 | a viewer has no Administration menu but opens read-only backup/reports windows |
| Layout at 1280×720 | scenario 07 | Persian RTL menu bar and headings, CUBI names only |
| Evidence bundle | `docs/workspace/evidence/workspace-canonical-v26-2026-11-12/` | `workspace-canonical-v26.json` + 11 screenshots, contract `cubi-workspace-canonical-v26.v1` |

Recorded provenance (two independent facts):

| Field | Value |
| --- | --- |
| Tested code SHA | `60370c40d5e93c5268b17e19471d6da1c2aec994` |
| Evidence commit | `13610e4eeebf1868afccda862a054f9f3f5255f8` |
| Branch | `feat/v26-stage-g-canonical-workspace` |
| PR | [#1779](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1779) |
| Merge commit | `85e24df939a0ea8af6b5977cd561550899bbedcb` |
| Post-merge CI | 5/5 triggered workflows success on `85e24df` (ConstructionPM CI, Web CI, Client Typecheck, PostgreSQL Sync State Integration, Pages deploy) |

### Next stage

Final full review, regression sweep and blocker report — complete in
[`CUBI_V26_FINAL_REVIEW.md`](CUBI_V26_FINAL_REVIEW.md).

## Priority Zero — Activities / WBS / Gantt visual acceptance (in progress)

Reference: Version 26 HTML Help only — <https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm>.
No requirement in this section cites a printed PDF page.

### Shipped in this increment

1. **Gantt bar-label edge handling** (`34981bb`). A bar whose configured `right`, `above` or
   `below` label finishes at or beyond 78% of the rendered timeline track now mirrors the label
   to the left of the bar instead of pushing it outside the scrollable content. When the bar also
   starts at the left edge (a full-width WBS summary), the label moves to `inside-right` because a
   mirrored label would clip on the left. `inside-*` positions are unchanged.
   - Help: [Change a Gantt Chart bar's label](https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_gantt_chart_bars_label_layouts.htm)
   - Code: `apps/web/src/workspace-gantt.ts` (`resolveGanttLabelPosition`),
     `apps/web/src/workspace-view.ts` (`renderGanttBar`, `renderGanttWbsRow`),
     `apps/web/styles.css` + `apps/web/public/styles.css` (`is-left`).
   - Tests: `workspace-gantt.test.ts` unit matrix; `workspace-view.test.ts` render assertions
     (mid-timeline label stays `right`, timeline-edge label becomes `left`, full-width summary
     becomes `inside-right`).
2. **Independent visual acceptance suite** (`apps/web/e2e/workspace-visual-acceptance-v26.mjs`).
   It opens the real Activities window in the real preview and measures, per cell: page/body
   horizontal overflow, toolbar bounds and the presence of a More control when the toolbar
   scrolls, table/Gantt command-strip containment, details-pane viewport bounds and size,
   per-row height and first-row offset parity between table and Gantt, WBS band/group counts,
   bar-label containment and edge resolution, and the Columns dialog bounds. Window switching to
   Reports and back is exercised in the 1366×768/en cell.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `cd apps/web && npx tsc --noEmit` | clean |
| Web unit/integration | `cd apps/web && npm test` | 865 `tsx` tests + 14 `node --test` tests pass, 0 fail |
| Build | `cd apps/web && npm run build` | bundles written to `dist/web/src` |
| Visual acceptance | `CUBI_CHROME_NO_SANDBOX=1 CUBI_PREVIEW_URL=http://127.0.0.1:4193 CUBI_TESTED_CODE_SHA=34981bb node e2e/workspace-visual-acceptance-v26.mjs` | 6/6 cells pass, 21 screenshots, 0 exceptions, 0 console errors, 0 API 5xx |
| 1280×720 en + fa | cell 1–2 | 14/14 rows, 7 bands, 21 labels, 0 clipped, details 163–190px, toolbar fits |
| 1366×768 en + fa | cell 3–4 | 14/14 rows, 7 bands, 21 labels, 0 clipped, details 236–263px, Reports switch round-trip |
| 1920×1080 en + fa | cell 5–6 | 14/14 rows, 7 bands, 21 labels, 0 clipped, details 441–468px |
| Evidence bundle | `docs/workspace/evidence/visual-acceptance-v26-2026-11-12/` | `workspace-visual-acceptance-v26.json` + 21 PNGs, contract `cubi-workspace-visual-acceptance-v26.v1` |

Recorded provenance:

| Field | Value |
| --- | --- |
| Tested code SHA | `34981bbf4edacb67cc5aac94b84fef24d59446fd` |
| Evidence commit | `164d9de` (this documentation commit records the merge/CI values) |

### Status after this increment

- ACT-010 label placement: `WIRED_READ` (real browser, three viewports, en/fa).
- ACT-009 bar shape/fill/height: remains `NOT_AUDITED`.
- ACT-010 filters, legend and background lines: remain `NOT_AUDITED`.
- WBS, Activity Details tab content, context-menu completeness, and the large-project
  calculation-scope tests remain on the priority-zero queue and are **not** claimed as verified.

## Priority Zero — Gantt calendar non-working background (2026-11-12)

Reference: Version 26 HTML Help only — <https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm>.

Prior increment recorded late: PR [#1782](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1782)
(edge-safe Gantt bar labels) merged as `24d1c4adf687488a8304779de26ef14791e37a1a`.

### Shipped in this increment

The Activities Gantt shades non-working days from the version-bound snapshot of the project's
primary calendar. It never infers a workweek from schedule dates and never recomputes a schedule
date.

- Help: [Change a Gantt Chart bar's settings](https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_gantt_chart_bar_s_settings.htm)
  (step 6, "Calendar nonwork time"), [Change the background lines in the Gantt chart](https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_the_background_lines_in_the_gantt_chart.htm),
  [The Gantt Chart](https://docs.oracle.com/cd/G48902_01/client_help/en_US/the_gantt_chart.htm).
- Read path: `apps/web/src/project-bootstrap.ts` and `apps/web/src/main.ts` pass
  `ProjectSummary.primary_calendar_id`; `WorkspaceReadClient.readProjectCalendar` in
  `apps/web/src/workspace-read-api.ts` resolves the catalog record and calls
  `loadCalendarSnapshot` → `GET /api/projects/{project_id}/p6/calendars/{calendar_id}/{calendar_version}/snapshot`
  (`p6-calendar-read-api.v1`, calendar read authorization). The facts live in
  `WorkspaceState.projectCalendar`.
- Geometry/render: `createGanttNonWorkingBands` in `apps/web/src/workspace-gantt.ts` converts
  Python weekday numbers (Monday = 0) to UTC days, merges contiguous weekend/holiday days into
  bands, clips them to the visible scale and applies a 0.05% minimum width; `renderGantt` in
  `apps/web/src/workspace-view.ts` paints them behind grid lines, sight lines and bars in a
  non-interactive layer. `apps/web/styles.css` and `apps/web/public/styles.css` add the
  weekend/holiday fills.
- Fail-closed: no primary calendar → `not-loaded` (no request, no shading); unknown id →
  `CALENDAR_NOT_FOUND`; empty `workingWeekdays` → `CALENDAR_WORKWEEK_MISSING`.
- Tests: `apps/web/src/workspace-gantt.test.ts` (Mon–Fri and Sat–Wed workweeks, holiday-on-weekend
  precedence, invalid scale/workweek/range), `apps/web/src/workspace-read-api.test.ts` (loaded
  facts and exact request order, missing calendar, no primary, empty workweek),
  `apps/web/src/workspace-view.test.ts` (holiday and weekend bands rendered; zero bands without
  loaded facts), `apps/web/src/project-bootstrap.test.ts` (primary calendar travels with the read).

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `cd apps/web && npx tsc --noEmit` | clean |
| Web unit/integration | `cd apps/web && npm test` | 876 `tsx` tests + 14 `node --test` tests pass, 0 fail |
| Build | `cd apps/web && npm run build` | bundles written to `dist/web/src` |
| Visual acceptance | `CUBI_CHROME_NO_SANDBOX=1 CUBI_PREVIEW_URL=http://127.0.0.1:4193 CUBI_TESTED_CODE_SHA=9378378 node e2e/workspace-visual-acceptance-v26.mjs` | 6/6 cells pass, 21 screenshots, 0 exceptions, 0 console errors, 0 API 5xx |
| Non-working bands | every cell | 11 bands (10 weekend + holiday `2026-10-28`), `outside=0` |
| Evidence bundle | `docs/workspace/evidence/visual-acceptance-v26-2026-11-12/` | `workspace-visual-acceptance-v26.json` + 21 PNGs, contract `cubi-workspace-visual-acceptance-v26.v1` |

Recorded provenance:

| Field | Value |
| --- | --- |
| Tested code SHA | `9378378b6b22e65f77afa5c9e5892d9de384b88f` |
| Evidence commit | `77f7b674fa1dd312e2eac7b61e008895ffe73860` |
| Branch | `feat/v26-gantt-nonworking-periods` |
| PR | [#1783](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1783) |

### Status after this increment

- ACT-010 calendar non-working background: `WIRED_READ` (real browser, three viewports, en/fa).
- ACT-008 five-scale timescale/pan/zoom: remains `NOT_AUDITED`.
- ACT-010 filters, legend and sight/background lines: remain `NOT_AUDITED`.
- Remaining honest gap: stored `calendar_exception` rows are not overlaid, there is no
  show/hide toggle, and resource/activity calendars are not consulted.

## Priority Zero — Gantt legend, sight lines, bar filters and five scales (2026-11-12)

Reference: Version 26 HTML Help only — <https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm>.

Prior increments recorded late: PR [#1783](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1783)
(calendar-aware Gantt non-working background) merged as `c926a88b5a65aeac36dff33bcfb4cad6876f132f`;
all five post-merge workflows succeeded on that commit (ConstructionPM CI, ConstructionPM Web CI,
Client Typecheck, PostgreSQL Sync State Integration, Deploy CUBI Web to GitHub Pages).

### Shipped in this increment

1. **Bottom legend overlay fixed.** `.cp-gantt-legend.is-bottom` was `position: sticky` inside a
   non-scrolling flex column, so it painted over the last chart rows. It now takes its own space
   below the chart (`apps/web/styles.css` and `apps/web/public/styles.css`).
2. **Timescale dialog no longer resets zoom.** The dialog duplicated the toolbar Scale select, and
   `readLayoutPatch` overwrote `ganttScale` from the interval on every submit. The duplicate control
   is removed; only a real interval change derives a new tick scale
   (`apps/web/src/workspace-dialogs.ts`).
3. **Browser suite** `apps/web/e2e/gantt-options-v26.mjs` (contract `cubi-gantt-options-v26.v1`)
   covers legend placement/content, three sight-line kinds, per-bar filter/Show fallback, all five
   scales, zoom in/out/Fit, and WBS collapse/expand.

- Help: [Change a Gantt Chart bar's settings](https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_gantt_chart_bar_s_settings.htm),
  [Change the background lines in the Gantt chart](https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_the_background_lines_in_the_gantt_chart.htm),
  [The Gantt Chart](https://docs.oracle.com/cd/G48902_01/client_help/en_US/the_gantt_chart.htm),
  [Change a layout's timescale format](https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_layout_s_timescale_format_50.htm),
  [Zoom in and out of a timescaled layout](https://docs.oracle.com/cd/G48902_01/client_help/en_US/zoom_in_and_out_of_a_timescaled_layout.htm).
- Unit tests: `apps/web/src/workspace-dialogs.test.ts` (format-only edit leaves `ganttScale`
  untouched; duplicate scale control absent; interval change derives the tick scale).

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `cd apps/web && npx tsc --noEmit` | clean |
| Web unit/integration | `cd apps/web && npm test` | 878 `tsx` tests + 14 `node --test` tests pass, 0 fail |
| Build | `cd apps/web && npm run build` | bundles written to `dist/web/src` |
| Gantt options | `CUBI_CHROME_NO_SANDBOX=1 CUBI_PREVIEW_URL=http://127.0.0.1:4193 CUBI_TESTED_CODE_SHA=b20501f node e2e/gantt-options-v26.mjs` | 2/2 cells pass (1366×768 en/fa), 22 screenshots, 0 exceptions/console errors/5xx |
| Visual acceptance | same command with `e2e/workspace-visual-acceptance-v26.mjs` | 6/6 cells pass at the same code |
| Legend | both cells | 7 items for 7 visible kinds; hide critical → 6 items; top/bottom placement correct |
| Sight lines | both cells | 7 major, 10 minor horizontal, 3 minor vertical (all plotted ticks except the edge) |
| Bar filter/Show | both cells | critical 7 → 0, task 6 → 13, total 17 unchanged (documented task fallback) |
| Scales | both cells | 520/640/800/1100/1600 widths and 1/2/4/11/38 ticks for year/quarter/month/week/day |
| Zoom/Fit + collapse | both cells | quarter↔month, Fit→month; 14→0→14 rows, 7 summary groups, no overflow |

Recorded provenance:

| Field | Value |
| --- | --- |
| Tested code SHA | `b20501f587a2673dd81271af6e1090b6284c091f` |
| Evidence commit | `7ea89d54a41c7ee15e6a20a288c8e2d8eedac4c6` |
| Branch | `feat/v26-gantt-options` |
| PR | [#1784](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1784) |

### Status after this increment

- ACT-008 five scales and zoom/Fit: `WIRED_READ`.
- ACT-010 legend, sight lines and per-bar filters: `WIRED_READ`.
- Remaining honest gap: Fit maps to the month scale instead of measuring the pane; free pan and
  scroll-sync are not audited; Add/Delete bar and some bar shapes remain absent.
- Activity Details tab content, context-menu completeness, and the large-project
  calculation-scope tests remain on the priority-zero queue.

## Priority Zero — Fit measures the visible Gantt pane (2026-11-12)

Previous increment merged: PR [#1784](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1784)
squashed as `d7629a8`; all five post-merge workflows on that commit are green
(ConstructionPM CI, ConstructionPM Web CI, Client Typecheck, PostgreSQL Sync State Integration,
Deploy CUBI Web to GitHub Pages).

### Defect and fix

`view.fit` always jumped to the month scale. In a pane narrower than the month timeline (800 px)
that created horizontal scrolling; it never used the width of the pane it was asked to fill.

- `fitGanttScale(viewportWidthPx)` in `apps/web/src/workspace-gantt.ts` returns the finest of
  day/week/month/quarter/year whose `GANTT_CONTENT_WIDTH` (1600/1100/800/640/520) fits the pane,
  keeps year as the floor, and returns month for an unlaid-out pane (0/NaN).
- `GANTT_CONTENT_WIDTH` and `GANTT_SCALE_ORDER` moved to `workspace-gantt.ts`;
  `apps/web/src/workspace-view.ts` imports the table instead of declaring a second copy.
- `view.fit` in `apps/web/src/main.ts` measures `#cp-gantt .cp-gantt-chart` and passes its
  `clientWidth`; a hidden Gantt or the Activity Network keeps the documented month default.

### Help and tests

- Help: [Zoom in and out of a timescaled layout](https://docs.oracle.com/cd/G48902_01/client_help/en_US/zoom_in_and_out_of_a_timescaled_layout.htm).
- Unit: `fitGanttScale` boundaries 1600/1100/800/640/520 plus 0/NaN, and the strictly decreasing
  width table, in `apps/web/src/workspace-gantt.test.ts` (879 `tsx` tests total).
- Browser: new `apps/web/e2e/gantt-fit-v26.mjs` (contract `cubi-gantt-fit-v26.v1`) at
  1366×768 and 1920×1080 in en/LTR and fa/RTL. It starts at year, runs Fit, and asserts the chosen
  width fits the measured pane, no finer scale would have fitted, a still-wider scale keeps a
  scroll range reaching its content end, the wider window never selects a coarser scale, and the
  page does not overflow. The five-scale Gantt-options suite still passes on the same code; it was
  run with `CUBI_GANTT_EVIDENCE_DIR=/tmp/gantt-options-check` so the merged 2026-11-12 evidence
  directory was not overwritten.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `cd apps/web && npm run typecheck` | clean |
| Web unit/integration | `cd apps/web && npm test` | 879 `tsx` tests + 14 `node --test` tests pass, 0 fail |
| Build | `cd apps/web && npm run build` | `dist/web/src/main.bundle.js` contains `fitGanttScale` |
| Fit acceptance | `CUBI_CHROME_NO_SANDBOX=1 CUBI_PREVIEW_URL=http://127.0.0.1:4193 CUBI_TESTED_CODE_SHA=08302a5 node e2e/gantt-fit-v26.mjs` | 4/4 cells pass, 4 screenshots, 0 exceptions/console errors/5xx |
| Gantt options regression | same command with `e2e/gantt-options-v26.mjs` | 2/2 cells pass (Fit now year at the 638 px pane) |
| Pane 638 px | 1366×768 en/fa | year (520 ≤ 638), chart scroll range equals the pane (fa adds 5 px of RTL axis decoration) |
| Pane 915 px | 1920×1080 en/fa | month (800 ≤ 915); week (1100) does not fit, so it is not chosen |

Recorded provenance:

| Field | Value |
| --- | --- |
| Tested code SHA | `08302a5df027b7c454352a00afa03881db8de5a1` |
| Acceptance harness | `ca7cc4f` |
| Evidence commit | `f2523c1a342c0e6a5a2533de0f547b297dc31321` |
| Branch | `feat/v26-gantt-fit` |
| PR | [#1785](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1785); merge SHA recorded in the next checkpoint entry |

### Status after this increment

- ACT-008 pane-aware Fit: `WIRED_READ`.
- Remaining honest gap: Fit is stepped by the five documented scales, not continuous; free pan
  and pixel-level fit are still unimplemented or unaudited (scroll-sync is covered by the next
  increment).
- Activity Details tab content, context-menu completeness and the large-project
  calculation-scope tests remain on the priority-zero queue.

## Priority Zero — table/Gantt scroll-sync and sticky headers (2026-11-12)

### Defect and fix

The audit of the shared vertical surface found a real regression: a later
`.cp-p6 #cp-activity-grid thead th[data-column-id] { position: relative; }` rule overrode the
sticky header of every data column. Scrolling the table moved its column headers out of view while
the Gantt timescale stayed fixed, so the two panes no longer read as one surface.

- The override is removed from `apps/web/styles.css` and `apps/web/public/styles.css`; `sticky`
  already establishes the containing block for the absolutely positioned column resize handles.
- `apps/web/src/workspace-presentation-css.test.ts` now asserts the header rule keeps
  `position: sticky; top: 0` and that the relative override is gone (880 `tsx` tests).

The existing delegated scroll handler in `apps/web/src/workspace-view.ts` already compensates for
the table-header/Gantt-axis height difference; the new suite proves it end to end.

### Help and tests

- Help: [Zoom in and out of a timescaled layout](https://docs.oracle.com/cd/G48902_01/client_help/en_US/zoom_in_and_out_of_a_timescaled_layout.htm).
- Browser: `apps/web/e2e/gantt-scroll-sync-v26.mjs` (contract `cubi-gantt-scroll-sync-v26.v1`)
  at 1280×720 and 1366×768 in en/LTR and fa/RTL. It scrolls the table half way (Gantt follows to
  the same rows, ≤1 px drift), returns the chart to the top (table returns), scrolls both panes to
  their clamped bottom (last table row and last bar fully visible; alignment, not an absolute
  clamp, because content heights differ by a couple of pixels), and scrolls the Gantt horizontally
  on the day scale (timeline reaches its end — 1005/1600 px at a 595 px pane, −1010 in RTL — while
  the table does not move and the axis stays pinned).
- Fix verification: the first run failed on the header check, which led to the CSS fix; the suite
  passes 4/4 at `eaf2d91`.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Type check | `cd apps/web && npm run typecheck` | clean |
| Web unit/integration | `cd apps/web && npm test` | 880 `tsx` tests + 14 `node --test` tests pass, 0 fail |
| Scroll-sync acceptance | `CUBI_CHROME_NO_SANDBOX=1 CUBI_PREVIEW_URL=http://127.0.0.1:4193 CUBI_TESTED_CODE_SHA=eaf2d91 node e2e/gantt-scroll-sync-v26.mjs` | 4/4 cells pass, 12 screenshots, 0 exceptions/console errors/5xx |
| Row alignment | all 4 cells | 14 shared rows, 0 px at rest, ≤1 px while scrolling and at the clamped bottom |
| Sticky chrome | all 4 cells | table header and Gantt axis keep their top while rows scroll (en and fa) |
| Horizontal scroll | all 4 cells | 1005 px (1600 content − 595 pane) in LTR and −1010 px in RTL, table unchanged, axis pinned |

Recorded provenance:

| Field | Value |
| --- | --- |
| Tested code SHA | `eaf2d91c7e3dac4598f26a3892b83659b07cc9bd` |
| Acceptance harness | `ddd7889` |
| Evidence commit | `4156d22aeee448c2cb8b8694bc433e117ad97fc5` |
| Branch | `feat/v26-gantt-scroll-sync` |
| PR | [#1786](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1786) |

### Status after this increment

- ACT-008 table/Gantt vertical sync, sticky table header and sticky timescale axis: `WIRED_READ`.
- Remaining honest gap: ~1 px subpixel row drift while scrolling; Fit is stepped by five scales;
  free mouse pan is not implemented.
- Activity Details tab content, context-menu completeness, multi-select and the server capability
  gaps remain on the priority-zero queue.

## Priority Zero — baseline capture and the Cost → EVM journey (2026-11-12)

### Capability

`POST /api/projects/{project_id}/p6/baselines/capture`
(`p6-baseline-capture-api.v1`, permission `PROJECT_WRITE`) closes `GAP-BAS-03`. The service
`P6BaselineCaptureService` reads the latest published schedule snapshot through
`PublishedScheduleCaptureSource` **before** opening the write transaction (calendar and snapshot
adapters commit on their own, which would destroy the outer savepoint), then inside one
transaction resolves activity masters, rolls up stored `planned_cost`/`currency` from resource
assignments and expenses, and writes baseline metadata plus immutable `p6_baseline_activity` rows.

Honest boundaries, all returned in the response instead of being hidden:

- Schedule facts come only from the calculated snapshot; the request body supplies identity,
  type, notes and an optional currency. Dates, durations and costs are never accepted from the UI.
- One-day calculated windows (milestones) are excluded and listed in `excluded_activity_ids`.
  Completed multi-day activities remain measurable.
- WBS/project-level expenses have no activity to attribute to, so they are listed in
  `unattributed_expense_ids` rather than being absorbed into an activity row.
- An explicit currency must match every detected cost currency; otherwise capture fails with
  `BASELINE_CAPTURE_CURRENCY_MISMATCH` or `BASELINE_CAPTURE_CURRENCY_AMBIGUOUS`.
- Replaying the same identity with identical metadata and rows returns `replayed: true` and the
  stored rows; different metadata or rows return 409 `BASELINE_CAPTURE_TARGET_EXISTS`.
- A stale `expected_revision` returns 409 `BASELINE_CAPTURE_STALE_REVISION`; writes are
  revision-scoped through `P6Baseline(scope, ..., scope.project_revision, ...)`.

The Cost Overview window adds a capture form (baseline id, name, type, currency, notes), reloads
the baseline list, selects the new baseline and clears any stale measurement. Nothing is computed
in the browser.

### Help and tests

- Help: [Add New Baseline dialog box](https://docs.oracle.com/cd/G48902_01/client_help/en_US/add_new_baseline_dialog_box.htm)
  (save the current project as a baseline / convert another project) and
  [Assign Baselines dialog box](https://docs.oracle.com/cd/G48902_01/client_help/en_US/assign_baselines_dialog_box.htm)
  (project, primary, secondary, tertiary assignment).
- Python: `tests/test_p6_baseline_capture.py` — 16 tests covering cost rollup, explicit currency,
  mixed-currency rejection, one-day exclusion, all-unmeasurable rejection, idempotent replay,
  target-exists conflict, missing snapshot, WBS and technique projection, permission/cross-scope,
  stale revision/contract, API provenance, HTTP 201/200 replay, unknown fields 400 and missing
  snapshot 404; `test_preview_capture_feeds_the_evm_read_model` proves capture → EVM in the real
  preview runtime (BAC `1000`, non-empty PV).
- Web: `apps/web/src/workspace-cost.test.ts` — payload trimming, optional fields, invalid type and
  revision, POST request shape, fail-closed response kind and the 409 passthrough.
- Browser: `apps/web/e2e/cost-capture-v26.mjs` (contract `cubi-cost-capture-v26.v1`) — 9/9
  scenarios: empty register, stored expense rollup, UI capture, idempotent replay, stale 409,
  EVM from the captured baseline (PV `500.000`, BAC `1000.00`), full reload, viewer read-only 403,
  and a 1280×720 Persian capture-form cell; 4 viewport/locale cells, 8 screenshots, zero
  exceptions/console errors/5xx.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Python suite | `PYTHONPATH=src python3 -m pytest -q` | 3528 passed, 109 skipped |
| Capture tests | `PYTHONPATH=src python3 -m pytest tests/test_p6_baseline_capture.py -q` | 16 passed |
| Type check | `cd apps/web && npm run typecheck` | clean |
| Web unit/integration | `cd apps/web && npm test` | 882 `tsx` + 14 `node --test` tests pass, 0 fail |
| Web bundle | `cd apps/web && npm run build` | three bundles written |
| Browser suite | `CUBI_CHROME_NO_SANDBOX=1 CUBI_PREVIEW_URL=http://127.0.0.1:4193 CUBI_TESTED_CODE_SHA=2a1c6b3 node e2e/cost-capture-v26.mjs` | 9/9 scenarios, 8 screenshots, 0 exceptions/console errors/5xx |

Recorded provenance:

| Field | Value |
| --- | --- |
| Implementation commit | `b04d851` |
| Browser-tested code SHA | `2a1c6b3c7d1a2bfebb590e101cd031059316c42d` |
| Evidence commit | `1b367ba` |
| Evidence bundle | `docs/workspace/evidence/cost-capture-v26-2026-11-12/` |
| Branch | `feat/v26-baseline-capture` (merged via PR) |

### Post-merge CI for the preceding increments

| Merge | Workflows |
| --- | --- |
| `921754f` (PR #1787, baseline capture → earned value) | 5/5 success: ConstructionPM CI, Web CI, Client Typecheck, PostgreSQL Sync State Integration, Deploy CUBI Web to GitHub Pages |
| `4be217e` (PR #1786, sticky headers + scroll sync) | 5/5 success: ConstructionPM CI, Web CI, Client Typecheck, PostgreSQL Sync State Integration, Deploy CUBI Web to GitHub Pages |
| `f7a5560` (PR #1785, pane-aware Fit) | 5/5 success on the same workflow set |

### Status after this increment

- GAP-BAS-03: resolved (`WIRED_WRITE`); BASE-001 and PRO-003 updated in the window matrix.
- Remaining honest gap: no baseline delete route, WBS/project expenses are reported as
  unattributed rather than allocated, EVM measurements are per request and not stored, and the
  Cost page offers no copy/update-from-current-project action.
- Priority-zero queue continues with table multi-select, Activity Details tab content, per-target
  context menus, duplicated text command bands and the remaining server capabilities
  (GAP-PRG-02, GAP-TRK-01, GAP-PRJ-02 — resolved 2026-11-12 —, GAP-DOC-02).

## GAP-PRG-02 — persisted progress history and out-of-sequence review (2026-11-12)

Reference: Oracle Primavera P6 Professional Help Version 26 — [Update progress for individual activities](https://docs.oracle.com/cd/G48902_01/client_help/en_US/update_progress_for_individual_activities_manually.htm)
and [Update progress for all activities](https://docs.oracle.com/cd/G48902_01/client_help/en_US/update_progress_for_all_activities.htm).
The first topic defines the per-activity Status-tab workflow (Started/Finished actual dates, Remaining
duration, percent complete) that the Progress page mirrors; the second defines the bulk Apply Actuals
scope that this increment deliberately does not implement.

### Implemented

- `activity_progress_history.py`: append-only `activity_progress_event` persistence for SQLite and
  PostgreSQL, with `event_id = activity_id@to_record_revision`, `ON CONFLICT DO NOTHING` plus
  read-back, deterministic ordering and no update/delete path. Tracked fields are actual start/finish,
  percent complete, remaining duration, remaining start, expected finish, status and status code.
- `p6_activity_progress_api.py`: wraps the existing activity-master PATCH, reads the previous row,
  writes through the same revision guard, re-reads the stored row and appends the event in the same
  transaction (`SQLiteTransactionManager`, savepoint-aware). FS/SS/FF findings are evaluated from
  persisted actual dates at write time and captured with the event they describe.
- `GET /api/projects/{id}/p6/activities/{activity_id}/progress-history`
  (`p6-activity-progress-history-api.v1`, `PROJECT_READ`) returns events, a persisted
  percent-complete trend and the latest review; unknown activities return 404
  `P6_ACTIVITY_PROGRESS_HISTORY_NOT_FOUND`; a missing composition returns
  `P6_ACTIVITY_PROGRESS_HISTORY_UNAVAILABLE`.
- Preview and production composition both build `P6ActivityProgressAPI` with the relationship and
  activity repositories, so the review reads authoritative stored logic rather than browser state.
- `workspace-progress.ts`: history table (revision, recorded time, actor, changes, sequence), inline
  percent trend, localized out-of-sequence summary and per-row sequence flag; reloaded after every
  save and every selection.
- `tests/integration/test_activity_progress_history_postgres_live.py` runs against live PostgreSQL in
  the PostgreSQL Integration workflow (append/list/isolation/latest, idempotent replay, concurrent
  identical append).

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Python suite | `PYTHONPATH=src python3 -m pytest -q` | 3537 passed, 142 skipped (psycopg installed; without it the live modules skip as whole modules) |
| Progress tests | `PYTHONPATH=src python3 -m pytest tests/test_activity_progress_history.py -q` | 9 passed |
| Live PostgreSQL | `CONSTRUCTION_PM_POSTGRES_DSN=... python3 -m pytest tests/integration/test_activity_progress_history_postgres_live.py -q` | 3 passed |
| Type check | `cd apps/web && npm run typecheck` | clean |
| Web unit/integration | `cd apps/web && npm test` | 885 `tsx` + 14 `node --test` tests pass, 0 fail |
| Web bundle | `cd apps/web && npm run build` | three bundles written |
| Browser suite | `CUBI_CHROME_NO_SANDBOX=1 CUBI_PREVIEW_URL=http://127.0.0.1:4193 CUBI_TESTED_CODE_SHA=256b1c0 node e2e/progress-history-v26.mjs` | 7/7 scenarios, 6 screenshots, 4 viewport/locale cells, 0 exceptions/console errors/5xx |

Recorded provenance:

| Field | Value |
| --- | --- |
| Implementation commit | `256b1c0` |
| Browser-tested code SHA | `256b1c0fe6eb28a0f7c13a55a45a005f0862950d` |
| Evidence | `docs/workspace/evidence/progress-history-v26-2026-11-12/` (`report.json` `gitHead`) |
| Branch | `feat/v26-progress-history` (merged via PR) |

### Status after this increment

- GAP-PRG-02: resolved (`WIRED_WRITE`); PRO-001 updated in the window matrix.
- Honest limits: the review compares persisted actual dates only (no float or calendar calculation, so
  it is not a rescheduled forecast); updates remain per activity with no all/selected bulk apply; the
  Progress page has no period cost/unit actuals and the trend is the persisted percent series.
- Remaining server capabilities: GAP-TRK-01 (tracking read model), GAP-PRJ-02 (project close/archive/status; resolved 2026-11-12), GAP-DOC-02 (binary document storage); GAP-V26-01 stays `BLOCKED_EXTERNAL`.
- Priority-zero queue continues with Activity Details tab content, per-target context menus and
  duplicated text command bands; table multi-select is complete (see below).

## GAP-PRJ-02 — audited project status lifecycle (2026-11-12)

Reference: Oracle Primavera P6 Professional Help Version 26 — [General tab - Project Details](https://docs.oracle.com/cd/G48902_01/client_help/en_US/general_tab_-_project_details.htm)
(Status identifies active/inactive projects and offers What If for analysis and Planned for the planning
phase) and [Filter by project status](https://docs.oracle.com/cd/G48902_01/client_help/en_US/filter_by_project_status.htm)
(the same Active/Inactive/Planned/What-If vocabulary used for portfolios and filters).

### Implemented

- `application/project_lifecycle.py`: `ProjectSummary.status`, `PROJECT_STATUSES`
  (`active|inactive|planned|what_if`), `normalize_project_status`, the append-only
  `ProjectStatusEvent`, and `set_project_status`/`project_status_history` on the service. The write
  requires `PROJECT_ADMIN`, honours `settings_revision`, and returns the stored row unchanged
  (no revision bump, no event) when the requested status equals the stored status.
- `application/project_lifecycle_api.py` and `http/project_lifecycle_routes.py`:
  `POST /api/projects/{id}/status` (`project-status-api.v1`) returns the persisted project row;
  `GET /api/projects/{id}/status-history` (`PROJECT_READ`) returns events with actor, transition,
  revision and recorded time. `PROJECT_STATUS_INVALID` maps to 400 and a read-back mismatch to 500.
- Persistence: SQLite preview and PostgreSQL repositories write the conditional status update and
  the event with `event_id = {project_id}@{new_settings_revision}`, `ON CONFLICT DO NOTHING` and a
  post-write read-back; `infra/project_lifecycle_schema.sql` adds the `status` column (with CHECK) and
  `project_lifecycle_status_event` plus its index. Replays are idempotent and history is append-only.
- `apps/web/src/main.ts`: the Project settings dialog gains a status select, a save control, the
  configuration revision and the event list; `session-api.ts`/`project-bootstrap.ts` call the new
  contract, and `bootstrap-labels.ts` supplies en/fa labels. Authorization failures from either the
  metadata save or the status save now render the permission message instead of a generic failure.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Python suite | `PYTHONPATH=src python3 -m pytest -q` | 3546 passed, 143 skipped (psycopg installed) |
| Status service | `PYTHONPATH=src python3 -m pytest tests/test_project_status_lifecycle.py -q` | 7 passed |
| PostgreSQL repository | `PYTHONPATH=src python3 -m pytest tests/test_postgres_project_lifecycle.py -q` | 8 passed |
| Live PostgreSQL | `CONSTRUCTION_PM_POSTGRES_DSN=... python3 -m pytest tests/integration/test_project_status_postgres_live.py -q` | 1 passed |
| Type check | `cd apps/web && npm run typecheck` | clean |
| Web unit/integration | `cd apps/web && npm test` | 887 `tsx` + 14 `node --test` tests pass, 0 fail |
| Web bundle | `cd apps/web && npm run build` | three bundles written |
| Browser suite | `CUBI_CHROME_NO_SANDBOX=1 CUBI_PREVIEW_URL=http://127.0.0.1:4193 CUBI_TESTED_CODE_SHA=e1b82363 node e2e/project-status-v26.mjs` | 6/6 scenarios, 6 screenshots, 4 viewport/locale cells, 0 exceptions/console errors/5xx |

Recorded provenance:

| Field | Value |
| --- | --- |
| Implementation commit | `e1b82363` |
| Browser-tested code SHA | `e1b82363df2673f3a20de903bfb0ed77d79551d6` |
| Evidence | `docs/workspace/evidence/project-status-v26-2026-11-12/` (`report.json` `gitHead`) |
| Branch | `feat/v26-project-lifecycle-status` (PR [#1789](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1789)) |

### Status after this increment

- GAP-PRJ-02: resolved (`WIRED_WRITE`); PRJ-002 updated in the window matrix and the Project row in
  the surface matrix.
- Honest limits: no close/archive operation beyond the status field, no EPS/OBS hierarchy, no
  responsible-manager, leveling-priority, checkout or web-site fields, no status-based project
  filtering/portfolios, and defaults application is not audited.
- Remaining server capabilities: GAP-TRK-01 (tracking read model), GAP-DOC-02 (binary document
  storage); GAP-V26-01 stays `BLOCKED_EXTERNAL`.
- Priority-zero queue continues with Activity Details tab content, per-target context menus and
  duplicated text command bands; table multi-select is complete (see below).

## Activities multi-row selection (2026-11-12)

Reference: Oracle Primavera P6 Professional Help Version 26 — [Select multiple items](https://docs.oracle.com/cd/G48902_01/client_help/en_US/select_multiple_items.htm)
(Shift selects a contiguous group, Ctrl selects non-adjacent items).

### Implemented

- `apps/web/src/workspace-model.ts`: `WorkspaceState.selectedActivityIds` and `selectionAnchorId`
  alongside the existing `selectedActivityId` primary row; `selectActivity` collapses to one row,
  `toggleActivitySelection` adds/removes one row (the added row becomes primary), and
  `selectActivityRange` resolves the inclusive range in displayed row order from the fixed anchor.
  `selectWbs` clears the selection and `withActivities` prunes ids that no longer exist.
- `apps/web/src/workspace-view.ts`: every selected row is marked `is-selected`/`aria-selected`, the
  grid declares `aria-multiselectable="true"`, Gantt bars use the same set for `aria-pressed`, and
  the real Ctrl/Cmd/Shift modifiers travel with the row or bar click.
- `apps/web/src/main.ts`: applies single, toggle and range requests; the incremental re-render
  updates all rows from the shared set instead of one primary id.
- No server write is involved: selection is view state and is cleared by a reload.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Python suite | `PYTHONPATH=src python3 -m pytest -q` | 3546 passed, 143 skipped |
| Type check | `cd apps/web && npm run typecheck` | clean |
| Web unit/integration | `cd apps/web && npm test` | 891 `tsx` + 14 `node --test` tests pass, 0 fail |
| Web bundle | `cd apps/web && npm run build` | three bundles written |
| Browser suite | `CUBI_CHROME_NO_SANDBOX=1 CUBI_PREVIEW_URL=http://127.0.0.1:4193 CUBI_TESTED_CODE_SHA=0a56e7a node e2e/activity-multi-select-v26.mjs` | 8/8 scenarios, 5 screenshots, 2 viewport/locale cells, 0 exceptions/console errors/5xx |

Recorded provenance:

| Field | Value |
| --- | --- |
| Implementation commit | `0a56e7a` |
| Browser-tested code SHA | `0a56e7a29e2bfd700aeb9b7f0d98d39cbb899ff4` |
| Evidence | `docs/workspace/evidence/activity-multi-select-v26-2026-11-12/` (`report.json` `gitHead`) |
| Branch | `feat/v26-activity-multi-select` (PR [#1790](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1790)) |

### Status after this increment

- ACT-020: `WIRED_READ` for multi-row selection; select-all, count reconciliation, search-driven
  selection and export scope remain.
- Priority-zero queue continues with Activity Details tab content, per-target context menus and
  duplicated text command bands.

## 2026-11-12 — Activities menu, toolbar and rail alignment

- Menu bar now uses the Version 26 names and order File / Edit / View / Project / Enterprise /
  Tools / Admin / Help, with one icon per command from `workspace-command-icons.ts` and a reserved
  check column so toggles never shift labels.
- One icon toolbar is grouped as Standard, Edit, Layout, Display, Project, Activities, WBS, Chart,
  Resources and Tools. The Layout family owns Open Layout, Save, Save As, Bars, Columns, Timescale,
  Filters, Group & Sort, Line Numbers, Table Font and User Preferences once. Duplicate
  print/import/search/preferences entries and the dead `workspace-command-shell.ts` parallel
  menubar are removed.
- The chart board keeps only chart-local scale presets and the relationship toggle; grid head
  actions use four distinct reset glyphs, a separator and 22px targets. Menu, toolbar and rail
  sizes were raised for readability in LTR and RTL, and both stylesheet copies remain identical.
- The Classic Schedule Layout selector was re-verified end to end: stored catalogue, apply and
  reload restore `Classic Schedule Layout`.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Python suite | `PYTHONPATH=src python3 -m pytest -q` | 3546 passed, 143 skipped |
| Type check | `cd apps/web && npm run typecheck` | clean |
| Web unit/integration | `cd apps/web && npm test` | 888 `tsx` + 14 Node tests pass, 0 fail |
| Web bundle | `cd apps/web && npm run build` | bundles written |
| Toolbar acceptance | `CUBI_CHROME_NO_SANDBOX=1 CUBI_PREVIEW_URL=http://127.0.0.1:4193 node e2e/toolbars-v26.mjs` | 6/6 cells, 7 screenshots, 0 exceptions/console errors/5xx |
| Visual acceptance | `… node e2e/workspace-visual-acceptance-v26.mjs` | 6/6 cells, 0 exceptions/console errors/5xx |
| Matrix | `docs/qa/V26_TOOLBAR_COMPLIANCE_MATRIX_2026-11-12.md` | 12 MATCH / 8 PARTIAL / 0 GAP for this increment |

Recorded provenance:

| Field | Value |
| --- | --- |
| Implementation commit | `9ddb1fa` |
| Browser-tested code SHA | `9ddb1fa235eb20c89339e73622719ffb1915cb99` |
| Toolbar evidence | `docs/workspace/evidence/toolbars-v26-2026-11-12/report.json` |
| Visual evidence | `docs/workspace/evidence/visual-acceptance-v26-2026-11-12/workspace-visual-acceptance-v26.json` |

### Status after this increment

- Menu/toolbar/rail structure is measured and clean; the remaining PARTIAL rows are named in the
  matrix (long-tail edit/layout/display/project commands and per-command browser click-through).
- Next queue: Activity Details tab content, GAP-TRK-01 tracking read model, GAP-DOC-02 binary
  document storage. GAP-V26-01 remains BLOCKED_EXTERNAL.

## Typed UDF values in Activity Details (2026-11-12)

Status: **branch-ready** on `feat/activity-udf-value-editing-20261112`, implementation
`3aec9777`, definition-listing repair `dd5347cb`, evidence `ed34653f`.

Reference: Oracle Primavera P6 Professional Help Version 26 — [Activity Details](https://docs.oracle.com/cd/G48902_01/client_help/en_US/activity_details.htm)
(the UDFs tab lives in the bottom details pane) and the [Enterprise menu](https://docs.oracle.com/cd/G48902_01/client_help/en_US/49097.htm)
(user-defined fields are project data registered before they become activity fields).

### What shipped

1. The typed value repository now persists `STRING` values and clears nullable values; every
   other type was already validated. Rows are keyed by
   `tenant/project/project_revision/udf_id/object_type/object_id`.
2. `P6UserDefinedFieldValueAPI` exposes `read_values` and `save_value` with project-scope,
   `PROJECT_READ`/`PROJECT_WRITE`, subject-area, writability and type checks. Unknown UDFs are
   404, unwritable or revision-conflicting writes 409, malformed values 400 with an
   authoritative code.
3. HTTP `GET|PUT /api/projects/{project}/p6/udf-values/{registry}/{objectType}/{objectId}[/{udfId}]`
   is wired through preview and production composition.
4. The Activity Details UDFs tab reads stored values for the selected activity and renders an
   editable form only for writable sessions; viewers keep the read-only grid. Saving submits
   only changed writable definitions and reloads the tab.
5. UDF definition listings filter subject areas case-insensitively, so preview's seeded
   `activity` definitions appear for the canonical `Activity` caller. Before the repair the
   route returned an empty list.

### Evidence

| Check | Command | Result |
| --- | --- | --- |
| Python suite | `PYTHONPATH=src python3 -m pytest -q` | 3811 passed, 147 skipped |
| Web unit/integration | `cd apps/web && npm test` | 928 `tsx` + 14 Node tests pass |
| Type check / build | `cd apps/web && npm run typecheck && npm run build` | clean, bundles written |
| Browser suite | `… node e2e/activity-udf-values-v26.mjs` | 4/4 scenarios at 1280×720 en, 1366×768 fa RTL, 1920×1080 en, viewer |
| Evidence SHA | `activity-udf-values-v26.json` | `testedCodeSha` = `dd5347cb38d8a8d1ef6db8995fd95ec65d031d57` |

The five PDF-export tests fail on import when the declared `arabic-reshaper` and `python-bidi`
dependencies are absent; after installing them the full Python suite passes. That is an
environment setup condition, not a regression from this change.

### GAP-V26-01 — what licensed evidence must still cover

GAP-V26-01 remains `BLOCKED_EXTERNAL`: this environment has no licensed Version 26 dataset,
database alias or authorized reference run. No numerical parity is claimed anywhere. The
following comparisons need that evidence before any row may move from
`IMPLEMENTED_AND_TESTED` to parity-tested:

- **Schedule arithmetic**: computed start/finish, total/free float, critical path and
  out-of-sequence flags for the same activities, calendars, constraints and relationships.
- **Calendar and duration semantics**: work-hour, exception and time-period behavior for
  8-hour, 24-hour and shift calendars, including cross-calendar relationships.
- **Resource and cost roll-ups**: assignment units, costs by cost account/expense category,
  financial-period buckets and summarization results.
- **Progress and baseline comparisons**: actual dates, percent-complete, baseline variance and
  earned-value figures after the same progress updates.
- **Layout and filter parity**: P6 layout/filter/group-sort export evaluated against CUBI's
  stored layout output on the same project.
- **Interchange round-trip**: a licensed P6 XML/XER exchange file imported and re-exported with
  field-level diffing, including UDF and code values.

Without an authorized dataset these remain explicitly unverified; CUBI persists and re-reads
its own values but does not assert equality with P6 outputs.

## Typed datetime and duration UDF controls (2026-11-12)

Status: **branch-ready** on `feat/activity-udf-value-editing-20261112`, implementation
`4f76241b`. Note: the feature commits were later rebased onto origin/main and re-verified at `4f76241b93266693e150bb6a5948ba9b073aa171`.

The Activity Details UDFs tab previously asked for datetime and duration values as free
text. A datetime definition now renders a `datetime-local` control and saves a
timezone-aware ISO instant; a duration definition renders a number amount plus a unit
selector, rejects a non-token unit before writing, and reads both back after a reload.
The five-scenario browser suite records the typed journey alongside the existing enum,
clearance and viewer checks at `4f76241b` (Web 935 + 14 pass, typecheck and build clean;
evidence `docs/workspace/evidence/activity-udf-values-v26-2026-11-12/`).

Remaining UDF gaps are unchanged: no definition search or subject filter, definition
lifecycle is not exposed, values stay revision-scoped, and the other Activity Details
tabs remain read-only.

## Classic Schedule Layout: rename, export and import (2026-11-12)

Status: **branch-ready** on `feat/activity-udf-typed-controls-20261112`, implementation
`4f76241b`.

The layout selector already opened, previewed, applied, cancelled and saved stored layouts.
It now also renames, exports and imports them, still through the append-only layout service:

- **Rename** reuses `saveCurrentLayout(name)`, so it appends a revision in the same scope and
  never rewrites history.
- **Export** writes `cubi-layout.v1` JSON containing only the format, name, columns and
  metadata; tenant, project, scope and revision are deliberately absent so a shared file
  cannot leak or overwrite another project's state.
- **Import** parses the file, rejects malformed, foreign-format and unnamed documents, validates
  every column against the live `FieldRegistry`, and always writes **user** scope at
  `existing.revision + 1`. Importing therefore never touches the project layout, and a column
  that no longer exists in the registry is refused instead of being silently dropped.

The browser suite `apps/web/e2e/layout-selector-v26.mjs` records 10/10 scenarios at
`4f76241b93266693e150bb6a5948ba9b073aa171` across 1280×720, 1366×768, 1920×1080 and a
Persian RTL cell, including the rename → export → import round trip with the revision
advancing, columns preserved and activity rows unchanged. The typed-UDF suite is re-recorded
at the same head (5/5). Evidence: `docs/workspace/evidence/layout-selector-v26-2026-11-12/`
and `docs/workspace/evidence/activity-udf-values-v26-2026-11-12/`.

An earlier run of the layout suite failed scenario 03 with `attempt to write a readonly
database`. The cause was environmental: a second `--reset` server had replaced
`/tmp/layout-e2e.sqlite3` while the listening process still held the unlinked inode
(`/proc/<pid>/fd/4 -> ... (deleted)`). After stopping the stray process and verifying the
listening PID's descriptor points at the on-disk inode, the suite passed 10/10 on the same
code — no product change was needed.

Remaining WS-007 gaps: delete with confirmation, dirty-state save/discard/cancel,
reset-to-default, Resource Assignments and Tracking layouts, and layouts are still scoped by
layout scope rather than by user identity.

## Activities scale and presentation-free schedule input (2026-11-12)

Status: **branch-ready** on `feat/activity-scale-invariants-20261112`, implementation
`2b9bec96`.

The Activities window now has a real 250+ population proof instead of an assertion that
"the code looks uncapped":

- The browser suite seeds 240 activities through the authenticated Activity Master API on
  top of the 14 seeded masters, so the read model, the table and the Gantt all hold **254**
  rows. The table renders 254 data rows and the Gantt 254 bars, the scroll container reaches
  its clamped bottom with the last row visible, and a reload returns the same population.
- A quick filter narrows the drawn rows to the 240 seeds, collapsing every WBS branch draws
  zero activity rows, and hiding `activity.name` keeps 254 rows — while the authoritative
  run is identical each time: the published snapshot and `/api/v1/schedule/query` report
  `activity_count: 254`.
- `AuthoritativeScheduleInputComposer.compose(scope, *, snapshot_id)` accepts no filter,
  collapse, column or selection argument. A test pins the signature so a future change
  cannot add presentation state to schedule input, and a 260-activity composition test
  proves the input carries every persisted activity and is identical across fresh reads.
- Web unit tests render 300 activities and check 300 table rows plus 300 Gantt bars,
  deterministic markup, filter narrowing without mutation, collapse without data loss and
  hidden columns without row or cell loss.

Evidence: `docs/workspace/evidence/activity-scale-v26-2026-11-12/` (`activity-scale-v26.json`,
8/8 scenarios, zero exceptions/console errors/5xx) at `2b9bec966b3c4cfaf57baf4e4be1ed1cdda51771`.
Remaining gaps: no 250+ scroll-sync stress, no multi-project population test, and the grid
renders every row rather than windowing, which is correct at this scale but may need
virtualisation for much larger projects.

## Context menu focus restore and dismissal (2026-11-12)

HTML Help topic: [Use shortcut menus](https://docs.oracle.com/cd/G48902_01/client_help/en_US/use_shortcut_menus.htm).
Implementation `5d21ebb5`; test surface `apps/web/e2e/context-menus-v26.mjs`.

- The viewport portal already opened every menu at the pointer, flipped and clamped it at the
  viewport edges, and kept it open while the grid scrolled. The new assertions found that
  **Escape did not return focus** after a pointer invocation: right-clicking an activity row
  selects it, the selection re-renders the grid, and the element the menu was anchored to was
  already detached, so `focus()` hit a disconnected node and focus fell to `document.body`.
- `close(restoreFocus)` now re-resolves the same logical object from stable identity
  attributes (`data-activity-id`, `data-gantt-activity-id`, `data-column-id`, `data-wbs-row`,
  `data-gantt-wbs-id`, `id`) and focuses the live element. Column headers, Gantt group rows,
  the timescale axis and both panes are programmatically focusable (`tabindex="-1"`), and a
  relationship menu anchors to its successor row instead of an SVG path that cannot take
  focus.
- The browser matrix now asserts outside-click dismissal, and Escape focus restore for a
  pointer-opened row, a keyboard-opened row (Shift+F10), a column header and the timescale in
  en/LTR and fa/RTL.

Evidence: `docs/workspace/evidence/context-menus-v26-2026-11-12/` (`context-menus-v26.json`,
92/92 checks, 0 failed, `build.git_head` `5d21ebb51b779609cad7109bc23fbe1dd3c6b489`,
screenshots 01–04). Web suite at the same code: 940 + 14 tests pass, `tsc --noEmit` and
`npm run build` pass. Remaining gaps: enabled command side effects are exercised only for
Columns, Add and Customize Details; permission enforcement is inherited from each command's
action; cut/copy/paste/fill-down/export/assign stay truthfully disabled with no write/export
route; the Activity Network has no context menu and there is no touch long-press path.

## Gantt bar styles (2026-11-12)

ACT-009 moves from `NOT_AUDITED` to `WIRED_WRITE` on a real-browser audit of the Bar Styles
dialog (`View, Bars` → `Bar Style` tab in the V26 Help).

- **Write path.** The dialog renders one fieldset per built-in kind from
  `WorkspacePresentation.bars`; submit normalises the kinds present in `FormData` and writes a
  presentation-only layout patch, so bar styling cannot reach schedule dates, durations or
  relationships. `renderGanttActivityRow`/`renderGanttBar` apply shape, pattern, colour,
  height, row and label to the live bar element.
- **Verified behaviour.** Task bars take diamond body, hatched fill, triangle-up/circle
  endpoints, `#123456` body and `#654321` border, 12 px, row 2, duration label above; the
  style survives a full reload; every task bar keeps its date-derived `left`/`width`; 14
  primary bars stay unchanged. Moving the task bar off row 1 (the default progress row)
  exposes the two progress fills as independent layers at the same unchanged span — a
  layout consequence, not schedule movement. A milestone write changes only the milestone
  layer. Persian RTL at 1366×768 and en at 1280×720/1920×1080 render without overflow.
- **Packing note.** Layer heights are packed to `rowHeight - 2`, so a requested 12 px task bar
  sharing a row with a 4 px progress layer renders at 11 px; the suite asserts the rendered
  height within 1 px and the persisted style value separately.

Evidence: `docs/workspace/evidence/gantt-bar-styles-v26-2026-11-12/` (`gantt-bar-styles-v26.json`,
9/9 scenarios, 0 exceptions/console errors/5xx, `testedCodeSha`
`d998336604b8690b143cb280ea093059cf582cea`, screenshots 01–07). Web suite at the same code:
942 + 14 tests pass. Remaining gaps: no dialog preview graphic, no user-defined bar rows
(Add/Delete), per-endpoint patterns and the Show-when-collapsed/summary-bar-only flags are not
modelled, and WBS summary bars use a separate renderer that this slice does not restyle.

## Activity filters (2026-11-12)

- **Scope.** ACT-003 moved from NOT_AUDITED to WIRED_WRITE at code `85722109`. The Filters
  dialog now offers typed criteria instead of a fixed operator list.
- **Engine.** `activityFilterFieldType` classifies every field as text/choice/number/date/
  boolean and `activityFilterOperatorsFor` limits the Is list to the operators that type
  supports; dates and numbers add `is within range of`. `resolveFilterDateValue` parses ISO
  dates and `CD`/`CS`/`CF` tokens with `±n[dwmy]` offsets against a date context built from
  the project data date and the loaded activity span. `validateActivityFilterCriterion`
  reports missing values, missing high values and invalid dates. `previewActivityFilter`
  counts matches across the whole project.
- **UI.** The editor renders Where/Field/Is/Value/High value/actions, an And/Or join cell
  after the first row, Add (up to eight rows), per-row Move up/down and Delete, a token
  datalist and a live preview (`data-filter-preview-valid|matched`). High value is only
  shown and persisted for `within-range`. The dialog snapshot keeps rows, joins and high
  values, so Cancel is exact.
- **Invariant.** Applying a filter only replaces or highlights presentation rows; the
  layout patch carries the saved filter definition and nothing from the schedule.
- **Verified behaviour.** Start offers `within range` and no text operators; a range without
  a high value is invalid; `next week` is rejected; `CS`…`CS+6w` matches 9 of 14 activities;
  adding `Activity % Complete is not equal to 100` narrows it to one row, the grid row count
  equals the preview count, and the saved `Six-Week Lookahead` survives a full reload.
  Any + Highlight keeps all 14 rows and highlights only the matches; All Activities clears
  both. Persian RTL at 1280×720 and en at 1366×768/1920×1080 render without overflow.
- **Known limits.** The preview fixture has no data date, so `CD` is inert there and the
  suite uses `CS`. `CS`/`CF` are derived from the loaded activity span rather than persisted
  project dates. Choice fields have no value picker, there is no Optimize action, Make Global
  is a scope label inside the project, and row-level copy/paste is not offered.

Evidence: `docs/workspace/evidence/activity-filters-v26-2026-11-12/`
(`activity-filters-v26.json`, 9/9 scenarios, 0 exceptions/console errors/5xx,
`testedCodeSha` `857221097f4e6cbb878f225b3f409ad4aedec01f`, screenshots 01–07,
`CHECKLIST.md`). Web suite at the same code: 948 + 14 tests pass; `tsc --noEmit` and
`npm run build` pass.

## Grouping and sorting (2026-11-12)

- **Scope.** ACT-002 moved from NOT_AUDITED to WIRED_WRITE at code `79712844`. The Group and
  Sort plan is now part of the saved Activities layout instead of an in-session-only state.
- **Engine.** `filterAndSortActivities` orders WBS bands from the persisted node tree and
  applies up to three sort levels inside each band; without grouping the same plan orders
  the flat table. `buildWorkspaceDisplayRows` supplies the bands and their display
  summaries. Expected orders in the browser suite are computed from the rendered cells, so
  the test does not hard-code fixture order.
- **Persistence.** `workspace-layout-settings.ts` validates and writes `metadata.groupSort`
  (`wbs|none` plus up to three `{columnId, direction}` levels) and `groupSortUpdatedAt`.
  Save and Save As merge the current plan; `hydrateGroupSortFromLayout` applies the stored
  plan once per layout revision. Malformed blocks are dropped, and a layout without one
  leaves the current plan in place.
- **Invariant.** The plan only reorders/hides presentation rows; no schedule date, duration,
  relationship or activity row is written, and the sort reads displayed cells only.
- **Verified behaviour.** Start desc then Activity name asc renders
  `A210…A100` flat, the Gantt follows, Save stores both levels at revision 2, and reload
  restores the exact order. WBS grouping shows 7 bands with name-ascending activities in
  every band and survives Save + reload. Persian RTL at 1280×720 and en at 1366×768 and
  1920×1080 render without overflow.
- **Known limits.** Grouping remains WBS or none (no group by field, WBS path or a second
  group level); the toolbar sort exposes only the first level; a layout without stored
  settings does not reset the plan; bands carry no totals formatting.

Evidence: `docs/workspace/evidence/activity-group-sort-v26-2026-11-12/`
(`activity-group-sort-v26.json`, 5/5 scenarios, 0 exceptions/console errors/5xx,
`testedCodeSha` `79712844d24317ee843c946a00347f10b93344da`, screenshots 01–05,
`CHECKLIST.md`). Web suite at the same code: 951 + 14 tests pass; `tsc --noEmit` and
`npm run build` pass.

## Multi-level grouping and nested field bands (2026-11-13)

- **Scope.** ACT-002 gained the ordered multi-level plan the V26 Help describes: up to three
  group levels, WBS hierarchy or activity fields, stable band order, nested bands and an
  independent collapse per band. Status remains WIRED_WRITE; the slice is presentation-only.
- **Model.** `WorkspaceState.activityGroupLevels` is the ordered source of truth (max three,
  unique valid fields). `activityGroupBy` still mirrors only whether the outer band is WBS,
  so the tree actions, Collapse To and the existing WBS tests keep their meaning.
- **Catalog and keys.** `workspace-grouping.ts` lists `wbs`, `activity_status`,
  `activity_type`, `is_critical`, `activity_code` and `total_float`, reads each value from the
  persisted `cells` (criticality falls back to the Gantt fact, never recalculated), and builds
  attribute-safe typed keys (`s:`, `n:`, `b:`, `e:`). Sibling bands order naturally and
  numerically, with "No value" last in either direction. A top-level WBS band keeps the node
  id, so the per-project collapse store and "Collapse To" still address it; nested bands use
  `<parent>><field>:<key>` and `<parent>>wbs:<nodeId>`.
- **Builder.** `buildWorkspaceDisplayRows` walks the persisted WBS tree in sequence order and
  emits field bands by typed value, nesting field→WBS and WBS→field. Each band carries a
  derived start/finish/duration/progress rollup and an activity count; a WBS level with no
  loaded nodes is skipped rather than inventing bands from raw ids. Activities inside the
  innermost band keep the caller's order; a field that already groups is removed from the
  in-band sort (including P6 column aliases such as `activity.status`).
- **UI and persistence.** The Group and Sort dialog has three field+direction rows backed by
  the shared catalog; the toolbar select remains the single-level shortcut. The plan is
  stored as `metadata.groupSort.groupLevels` (legacy `groupBy` reads as one WBS level) and is
  hydrated once per revision, saved by Save/Save As/New/Reset, and compared by the layout
  selector's dirty state. Band collapse keys use the existing
  `cubi:workspace-wbs-collapse` store, so nested bands collapse independently and survive
  reload.
- **Verified behaviour (contract `cubi-activity-group-sort-v26.v2`, 9/9).** Expected bands
  are computed from the workspace read API, not fixture constants: Activity Status renders
  `Completed (3)`, `In Progress (1)`, `Not Started (10)` with table/Gantt alignment and a
  collapse to 11 visible rows; WBS + Status nests status bands inside each WBS node with
  exact per-node counts and independent collapse in both directions; `is_critical` → WBS
  forms `Critical (7)`/`Non-critical (7)` outer bands with WBS bands inside; every plan
  survives Save Layout plus a full reload; Persian RTL at 1280×720 and en at 1366×768 and
  1920×1080 render with 0 px overflow.
- **Known limits.** The toolbar select changes only the first level; field bands inherit the
  WBS band palette (no per-band font/colour editor yet); the WBS level is the persisted
  hierarchy rather than a hand-typed path string; sorting by a grouped field is skipped; the
  grid is not virtualised for very large grouped projects.

Evidence: `docs/workspace/evidence/activity-group-sort-v26-2026-11-13/`
(`activity-group-sort-v26.json`, 9/9 scenarios, 0 exceptions/console errors/5xx,
`testedCodeSha` `5945c90723fe63d221d213588fbbfcfd2089475c`, screenshots 01–09,
`CHECKLIST.md`). Web suite at the same code: 1016 + 14 tests pass; `tsc --noEmit`,
`tsc -p tsconfig.test.json --noEmit` and `npm run build` pass.

## Table font and row height (2026-11-12)

- **Scope.** ACT-005 moved from NOT_AUDITED to WIRED_WRITE at code `dbe361ae`.
- **Controls.** The Table Font and Row dialog writes family, size, text and background
  colour, row mode (`keep|fixed|content`), fixed height and Show-icons. `applyDesktopVisuals`
  publishes them as CSS variables on the document root; the layout metadata carries the same
  table presentation, so a reload restores it.
- **Reset.** A new Reset to defaults action replaces only `DEFAULT_PRESENTATION.table`
  (Tahoma 11 px, `#000000`/`#ffffff`, fixed 18 px, icons on) and publishes it with a new
  layout revision.
- **Defect fixed.** Unchecked Show-icons / Show-line-numbers were absent from `FormData`, so
  the saved `true` survived and the toggle was one-way. Marker inputs (`tableFields`,
  `tableLineNumbers`) now make both flags read as booleans; a unit regression test covers it.
- **Verified behaviour.** Cairo 14 px, `#102030`, `#fdf6e3`, fixed 26 px rows and hidden icons
  appear in the computed cell style and rendered row height and survive a reload; Reset
  returns the shipped values and survives a reload; Persian RTL at 1280×720 and 1920×1080
  render without overflow.
- **Known limits.** Content-optimised row height is a flag rather than measured text; the
  font list is the five installed families; WBS band fonts/colours remain ACT-004; line
  numbers live in User Preferences.

Evidence: `docs/workspace/evidence/activity-table-font-v26-2026-11-12/`
(`activity-table-font-v26.json`, 5/5 scenarios, 0 exceptions/console errors/5xx,
`testedCodeSha` `dbe361aeed4e4e5feb2b48bcd44b8d7db6579db8`, screenshots 01–05,
`CHECKLIST.md`). Web suite at the same code: 953 + 14 tests pass; `tsc --noEmit` and
`npm run build` pass.

## WBS band format (2026-11-12)

- **Scope.** ACT-004 moved from NOT_AUDITED to WIRED_WRITE at code `138208c8`.
- **Controls.** User Preferences gained a WBS Band Format fieldset that writes a band
  typeface, size, ink mode (automatic contrast or a custom colour), band height and the
  three text fields (Show Title, Show Code, Show Name) plus the six level colours. The
  values live in `WorkspacePresentation.wbs` and are published as `--cp-wbs-font-family`,
  `--cp-wbs-font-size`, `--cp-wbs-ink` and `--cp-wbs-row-height` on each band row, so the
  table rows keep their own font and height.
- **Reset.** Reset band format restores only `DEFAULT_PRESENTATION.wbs` (Tahoma 11 px,
  automatic ink, 22 px, code and name shown, shipped level colours) and publishes it with a
  new layout revision; the timescale, table and Gantt settings are untouched.
- **Defect fixed.** The Gantt advanced between rows by the activity row height only, so each
  band pushed every following bar 4 px out of step with the table. `ganttDisplayMetrics`
  now assigns a per-row height (band pitch for WBS groups), link geometry and progress
  points use those centres, and every Gantt row is told its height, so the chart and table
  rows agree to within the 1 px row rule.
- **Verified behaviour.** The default bands show 7 rows with code and name in Tahoma 11 px
  on the shipped level colours; the dialog writes Cairo 14 px, `#102030`, 30 px and
  Show Title only, the table stays Tahoma 11 px, the layout publishes revision 2 and the
  Gantt offsets match the table; a full reload restores it; Reset returns the defaults and
  survives a reload; Persian RTL at 1280×720 and en at 1920×1080 render without overflow.
- **Known limits.** One typeface and ink rule applies to every level (automatic mode still
  derives ink per level colour); the band height is a single value for all levels; Show
  Title prints the literal label WBS; WBS bands appear only under WBS grouping.

Evidence: `docs/workspace/evidence/activity-wbs-band-v26-2026-11-12/`
(`activity-wbs-band-v26.json`, 6/6 scenarios, 0 exceptions/console errors/5xx,
`testedCodeSha` `138208c805ec2ee52bc3a85cb16e949868a103d4`, screenshots 01–06,
`CHECKLIST.md`). Web suite at the same code: 963 + 14 tests pass; `tsc --noEmit` and
`npm run build` pass.

## WBS expand/collapse and Gantt row mapping (2026-11-13)

- **Scope.** ACT-006 and ACT-007 moved from NOT_AUDITED to WIRED_WRITE at code
  `98e309c0`.
- **Controls.** The band `+`/`−` button, a double-click on the band, the toolbar
  Expand All / Collapse All / Collapse To actions, the `table-wbs` context menu,
  Ctrl+Numpad +/− and Enter/Space on a focused band all drive the same collapsed
  set. Nested children keep their own state when an ancestor collapses and
  reopens; Collapse All leaves the top-level bands open, as the desktop grid
  does.
- **Persistence.** `cubi:workspace-wbs-collapse` remains the immediate view
  store; the same ids now travel with the saved layout as
  `metadata.wbsCollapse` (trimmed, deduplicated, capped at 500, absent means no
  opinion, `[]` means fully expanded). `commitLayout` and Save As merge the block
  on every write, and `hydrateCollapseFromLayout` applies it once per
  `tenant:project:scope:revision`, so a reload or layout switch restores the tree
  even after the browser-local state is cleared.
- **Defects fixed.** Collapse state existed only in localStorage, so Save Layout,
  a layout switch and another browser lost it. The focusable band row also
  ignored Enter/Space; the key handler now toggles it and skips the native
  button activation to avoid a double toggle.
- **Verified behaviour.** The fixture starts with 7 bands and 14 activities. The
  Civil works branch collapses to 9 activities in both the table and the Gantt,
  and its summary band stays; the root collapses to one band and no activity
  rows; a nested Civil works branch survives a root collapse/reopen; Collapse
  All / Expand All and Collapse This Branch behave identically; Save Layout
  stores the branch, an emptied local store plus a reload still restores it, and
  saving an expanded tree restores all 14; no collapse step issues a non-GET
  `/api/` request. Every visible table row keeps its Gantt row id, kind, height
  and ≤2 px offset in en and fa; Persian RTL at 1280×720 and en at 1920×1080
  show 0 px overflow.
- **Known limits.** No server-side per-user tree preference outside a layout
  revision; the Gantt group row is display-only rather than a toggle target;
  Collapse All keeps top-level bands open and Collapse To is the only level
  control.

Evidence: `docs/workspace/evidence/activity-wbs-collapse-v26-2026-11-13/`
(`activity-wbs-collapse-v26.json`, 9/9 scenarios, 0 exceptions/console errors/5xx,
`testedCodeSha` `98e309c02604a956de37ef504b319c6dcd6e0c85`, screenshots 01–09,
`CHECKLIST.md`). Web suite at the same code: 966 + 14 tests pass; `tsc --noEmit`
and `npm run build` pass.

## Data Date and Gantt overlays (2026-11-13)

- **Scope.** ACT-011: the authoritative project Data Date, the Data Date line,
  the progress-point line and the always-present critical bar display.
- **Defect fixed.** The server already published
  `schedule_options.data_date = "2026-10-12"` through
  `GET /api/projects/{id}/p6/schedule/settings`, but `apps/web/src/main.ts`
  hard-coded `"—"`/`null` for the status bar, the Gantt, Activity Details and
  the filter date context. `loadActiveProjectDataDate` now reads the existing
  `loadScheduleDataDate` adapter once per opened project, keeps the value keyed
  by project id, clears it when the project changes, leaves it unset on a failed
  or malformed read, and re-renders preserving drafts. One value now feeds all
  four consumers, so the Bars-dialog Data Date fieldset and the rendered line
  stop being disabled, and the `CD` token receives a real date.
- **Progress line.** A new `progressPointRelation` helper classifies each saved
  `% complete` point against the Data Date (left = behind, within half a day =
  on, right = ahead), matching the P6 Help wording. The layer exposes the date
  and the three counts; the Bars-dialog note now states the positional rule
  instead of claiming the model has no date.
- **Verified behaviour.** On the Day timescale the line sits at 28.8 %, the
  exact position the axis ticks assign to 12 Oct 2026, and stays inside the
  chart body at 1366, 1280 RTL and 1920. The status bar reads
  `Data Date: 2026-10-12` and Activity Details shows the same value. Enabling
  the progress line draws 14 points: 4 behind, 0 on, 10 ahead. Dashed 4 px
  renders as a 1 px dashed line; solid 4 px renders 4 px in the chosen colour.
  Save Layout stores `dataDateLine` (solid, 3 px, `#112233`) and `progressLine`
  (visible, 2 px, `#ff8800`), and a full reload restores both. Seven critical
  bars stay drawn. No overlay edit issues a schedule write; the only write is
  the explicit Save Layout.
- **Known limits.** No baseline snapshot or baseline activity dates exist in the
  project, so baseline bars cannot be drawn; the Bars editor says so and the
  suite asserts zero baseline bars. The progress line keeps one configured
  colour (ahead/behind is positional). A non-solid Data Date style stays 1 px,
  as the dialog documents. The `CD` token now has a date but is not exercised
  end-to-end by this suite.

Evidence: `docs/workspace/evidence/activity-gantt-overlays-v26-2026-11-13/`
(`activity-gantt-overlays-v26.json`, 7/7 scenarios, 0 exceptions/console
errors/5xx, `testedCodeSha` `10659a0281588f25a95ff50cd092a197c5e7d55b`,
screenshots 01–07, `CHECKLIST.md`). Web suite at the same code: 968 + 14 tests
pass; `tsc -p tsconfig.test.json` and `npm run build` pass.

## Gantt relationship drawing and arrow editing (2026-11-13)

- **Scope.** ACT-012 moved from NOT_AUDITED to WIRED_WRITE at code
  `04fba0298652cd6e29d9e436b665dd615f691314`.
- **Gesture.** With Show Relationships on, every primary bar exposes a start
  and a finish handle. A pointer press on either edge starts a drag that draws
  a dashed elbow preview and a localized hint naming the relationship that will
  be created. Releasing over a successor bar's edge creates finish→start,
  finish→finish, start→finish or start→start, exactly the Help table.
  `relationshipTypeFromEdges` is the single pure encoder of that table.
- **Hit testing.** The default task bar is a clipped triangle, so
  `elementFromPoint` cannot find it at mid-height. The row is resolved by the
  pointer Y against row boxes and the edge by the bar's own box; the successor
  is resolved geometrically with a bounded reach, which also makes the fa RTL
  cell use the same physical edges.
- **Persistence.** The gesture only proposes: it calls the existing
  `onRelationshipCreate` callback, so writes still go through
  `P6RelationshipAPI` (`POST/PATCH/DELETE /api/projects/{project}/p6/relationships`)
  with `PROJECT_WRITE`, duplicate and cycle rejection, and `expected_revision`.
  Escape (document capture listener) or a drop without a target removes the
  overlay and writes nothing.
- **Verified behaviour.** A reset preview draws all 15 stored arrows with their
  FS/SS types and the `+5d` badge; dragging A100→A120, A110→A140, A120→A145
  and A140→A150 creates FS, FF, SS and SF; a full reload keeps all four; the
  arrow menu edits A100→A120 to SS lag 2 with `expected_revision: 1`; delete
  sends nothing on cancel and removes exactly one row on confirm; hidden lines
  remove handles and disable drawing; fa RTL 1280 and en 1920 draw with 0 px
  overflow. No non-GET schedule or activity request is made.
- **Known limits.** New arrows start with 0 working days of lag; lag is edited
  through the arrow context menu afterwards. The hint is a positioned label,
  not the Oracle hint-window chrome.

Evidence: `docs/workspace/evidence/activity-relationships-v26-2026-11-13/`
(`activity-relationships-v26.json`, 11/11 scenarios, 0 exceptions/console
errors/5xx, 0 schedule writes, `testedCodeSha`/`gitHead`
`04fba0298652cd6e29d9e436b665dd615f691314`, screenshots 01–08, `CHECKLIST.md`).
Web suite at the same code: 969 + 14 tests pass; `tsc --noEmit` and
`npm run build` pass.

## Activity Network nodes, edges and selection (2026-11-13)

- **Scope.** ACT-013 moved from NOT_AUDITED to WIRED_WRITE at code
  `a9776bb9ed8d16a2f5752b5b0909f74f002a5c2a`, covering the Help topics
  Activity Network, Move around in the Activity Network, and View Activity
  Network Activity Details.
- **Projection.** `buildActivityNetwork` keeps its longest-path layout: every
  persisted activity becomes one node and every persisted relationship one
  edge, so the fixture draws 14 nodes, 15 edges and 10 levels, marks critical
  activities, and keeps the SS `REL-RPS-170` A140→A170 `+5d` visible. Nothing
  is recalculated, invented or dropped.
- **Edge details.** Each edge now carries `data-network-relationship-id` and
  `data-link-from/to/type` identity, a wide transparent hit path, a `<title>`
  with the type, endpoints and lag, and keyboard focusability. Hovering or
  focusing highlights the line; double-clicking or pressing Enter on it opens
  the existing relationship editor in the Tools drawer with the stored
  revision.
- **Selection.** Network nodes already carry `data-gantt-activity-id`, so the
  shared `onGanttActivitySelect` / `onActivitySelect` path is reused: node and
  table stay synchronised in both directions, and Enter on a focused node
  selects it. There is no second selection store.
- **Menus.** `workspaceContextAt` now classifies `network-activity` and
  `network-link`; right-clicking a node opens the activity menu and
  right-clicking an edge opens the relationship menu with Edit, Delete, Go to
  Predecessor and Go to Successor.
- **Zoom.** Header controls expose Zoom In, Zoom Out and Zoom to Best Fit.
  `clampNetworkZoom` bounds the value to 0.2–2.0, `readNetworkZoom` /
  `storeNetworkZoom` persist it per tenant, project and window, and the SVG
  only changes its rendered size. A reload restores the stored zoom; Best Fit
  frames the full ten-level diagram at 20 %.
- **Persistence.** Zoom is a presentation preference and never touches the
  schedule. Opening the edge editor writes nothing; this suite observed zero
  relationship writes, zero non-GET schedule or activity requests, 0 console
  errors and 0 failing API responses.
- **Verified behaviour.** 14 nodes/15 edges/10 levels with FS and SS types and
  tooltips; A120↔A145 selection sync; Enter selects A150; edge
  `REL-RPS-100` opens revision 1; the edge menu's Go to Successor selects
  A110; the node menu lists Details through WBS collapse; 100 %→120 %→reload→
  110 %→Best Fit 20 %; fa RTL at 1280 and en at 1920 both render with 0 px
  horizontal overflow.
- **Known limits.** The layout is deterministic longest path, not
  user-positioned: Reorganize, box dragging and saved Activity Network layouts
  are not offered yet. The left pane is the shared Activity Table with WBS
  bands rather than a WBS-only hierarchy. Node boxes show ID, name and progress
  only. Zoom is browser-local, not saved layout metadata.

Evidence: `docs/workspace/evidence/activity-network-v26-2026-11-13/`
(`activity-network-v26.json`, 9/9 scenarios, 0 exceptions/console
errors/5xx, 0 schedule writes, 0 relationship writes, `testedCodeSha`/`gitHead`
`a9776bb9ed8d16a2f5752b5b0909f74f002a5c2a`, screenshots 01–07,
`CHECKLIST.md`). Web suite at the same code: 970 + 14 tests pass;
`tsc --noEmit` and `npm run build` pass.

## Trace Logic predecessor and successor levels (2026-11-13)

- **Scope.** ACT-016 moved from NOT_AUDITED to WIRED_READ at code
  `446de0e970f304916adde1cfc7e03ed17db8f707`, covering the Help topics Trace
  Logic, Set Trace Logic preferences, Move around in Trace Logic and Display
  Trace Logic.
- **Projection.** `buildTraceLogic` walks the persisted relationships in both
  directions for the selected activity. Each direction now has its own limit,
  matching Bottom Layout Options, which specifies the predecessor and successor
  levels separately. A repeated ancestor is reported as a cycle, a converging
  diamond is not, and endpoints that are not loaded are counted rather than
  invented.
- **Controls.** The Trace Logic header exposes a predecessor select and a
  successor select (1–5). Each change stores the pair under
  `cubi:workspace:trace-logic-predecessor-depth` and
  `cubi:workspace:trace-logic-successor-depth` and re-renders only the bottom
  surface. The previous single-depth key is migrated to both sides.
- **Selection.** A chain row selects its activity in the table, the details
  pane and the chain. Selecting in the Activity Network or on a Gantt bar
  redraws the lower chain because all surfaces share
  `onActivitySelect`/`onGanttActivitySelect`.
- **Critical.** A critical activity keeps the red `rgb(192, 57, 43)` start
  border named by the Help topic and now also carries a localized
  `Critical activity` title.
- **Verified behaviour.** A130 at depth 2 shows A120/A110 predecessors and
  A140/A150/A145/A155/A160/A170 successors with `SS+5d`; depths 1/3 persist
  through a full reload; following A120 selects it; A160 from the Network and
  A145 from the Gantt both redraw the chain; a critical row is marked; A100
  shows an explicit empty predecessor group; fa RTL 1280 and en 1920 keep the
  chain with 0 px overflow. No schedule or relationship write is issued.
- **Known limits.** At the time of this slice the Activity Usage
  Spreadsheet/Profile was not implemented; ACT-015 (below) now supplies it and
  its selection source. There is no dedicated Bottom Layout Options dialog and
  the depth pair is browser-local rather than saved layout metadata. The chain
  is a two-list layout, not the graphical activity-box diagram.

Evidence: `docs/workspace/evidence/activity-trace-logic-v26-2026-11-13/`
(`activity-trace-logic-v26.json`, 9/9 scenarios, 0 exceptions/console errors/5xx,
0 schedule writes, 0 relationship writes, `testedCodeSha`/`gitHead`
`446de0e970f304916adde1cfc7e03ed17db8f707`, screenshots 01–08,
`CHECKLIST.md`). Web suite at the same code: 971 + 14 tests pass;
`tsc --noEmit` and `npm run build` pass.

## Activity Usage Spreadsheet and Profile (2026-11-13)

- **Scope.** ACT-015 moved from NOT_AUDITED to WIRED_READ at code
  `218977dc72405061b4fc3d0f228db7e70df7e140`, covering the Help topics The
  Activity Usage Spreadsheet, Display the Activity Usage Spreadsheet, The
  Activity Usage Profile, Display the Activity Usage Profile and Define the
  Activity Usage Profile.
- **Source binding.** Both views are a read-only projection of the stored
  assignment periods read from
  `GET /api/projects/{id}/p6/resource-assignment-periods` (`PROJECT_READ`) via
  `loadAssignmentPeriods`. `buildActivityUsageSpreadsheet` groups the rows by
  activity and `period_start` and sums units or cost with the shared
  `addDecimalText` helper; nothing is spread across activity dates and no zero
  is invented. The profile aggregates the same period totals into vertical
  bars with value labels and a total/peak summary.
- **Controls.** Units/Cost and All/Selected scope are presentation-only; they
  persist under `cubi:workspace:activity-usage:<tenant>:<project>`. The bottom
  layout itself uses `cubi:workspace:bottom-layout:<tenant>:<project>:<menu>`.
  The View menu (`view.bottom-usage-spreadsheet`, `view.bottom-usage-profile`)
  and Bottom Layout Options expose the views only after a successful non-empty
  period read; loading, error, empty and scope-empty states are explicit.
- **Verified behaviour.** The browser suite seeds 4 assignments and 6 periods
  through the write API, then checks units A130 5/3=8, A160 4/–/6=10, A170
  –/1/–=1 with period totals 11/4/6 and grand total 21; cost totals
  1100.25/390/640.5 and grand total 2130.75 restore after a reload; A160-only
  scope gives 4/6 and grand 10; the profile bars are 11/4/6 at 100/36/55 %
  with `Units: total 21 · peak 11 over 3 period(s)`; Refresh picks up a newly
  stored 2027-01-01 period (4 columns, grand 23); A100 shows scope-empty; fa
  RTL 1280×720 and en 1920×1080 render with 0 px overflow. No non-GET `/api/`
  request is issued while using the views.
- **Known limits.** The desktop two-pane split is one table whose first column
  is the activity; there is no user-defined calendar bucket, cumulative curve,
  bar/background styling, past-period-actual switch or right-pane field
  chooser, and the profile overlays no resource limits. Refresh re-reads the
  project collection rather than receiving pushes.

Evidence: `docs/workspace/evidence/activity-usage-v26-2026-11-13/`
(`activity-usage-v26.json`, 11/11 scenarios, 0 exceptions/console errors/5xx,
0 interaction writes, `testedCodeSha`/`gitHead`
`218977dc72405061b4fc3d0f228db7e70df7e140`, screenshots 01–10b,
`CHECKLIST.md`). Web suite at the same code: 981 + 14 tests pass;
`tsc --noEmit` and `npm run build` pass.

## Activity Details tab inventory and write paths (2026-11-13)

- **Scope.** ACT-014 remains WIRED_WRITE, now evidenced across the full tab
  set at code `8d27c88f041e061f013042c4ed14cbfe213959b0`. The Help topics are
  Activity Details and Customize Activity Details.
- **Inventory.** The bottom pane renders the 16 desktop tabs in contract order
  (General, Status, Resources, Predecessors, Successors, Relationships, Codes,
  Notebook, Steps, WPs & Docs, Expenses, Issues, Risks, Summary, UDFs, Update
  History) plus the CUBI Calendar tab. Tasks, Discussion and Feedback are P6
  EPPM-only and are not offered.
- **Data binding.** General/Status/Codes/Summary/Calendar and the relationship
  tabs read the authoritative workspace state. Resources, Expenses, Issues,
  Risks, Steps, UDFs and Update History read their project-service endpoints
  when activated, with explicit loading, empty and error states.
- **Write paths.** Resources, Expenses and Issues submit through `saveAssignment`,
  `saveExpense` and `saveIssue` (existing `/p6/resource-assignments`,
  `/p6/expenses`, `/p6/issues` routes under `PROJECT_WRITE`) and then reload the
  stored list. UDFs keep the typed value PUT from the earlier slice.
- **Verified behaviour.** 17 tabs in order with Calendar last; every data tab
  settles with a Reload action and no error; A130 lists its three stored step
  definitions in sequence with no invented completion percentage; assignment,
  expense and issue writes each report `Saved. The list was reloaded from the
  project service.` and reappear from the service; removing Status in Customize
  Tabs survives a full reload; zero exceptions, console errors or 5xx.
- **Known limits.** Risks has no activity reference and remains a read-only
  project register; WPs & Docs and Update History are read surfaces; Notebook
  defers to the browser-local Comments rail; the Customize dialog changes only
  the display set.

Evidence: `docs/workspace/evidence/activity-details-tabs-v26-2026-11-13/`
(`activity-details-tabs-v26.json`, `testedCodeSha`/`gitHead`
`8d27c88f041e061f013042c4ed14cbfe213959b0`, 17 tabs, 3 write paths,
screenshot `details-en-1366.png`, `CHECKLIST.md`).

## Formula columns — frontend lifecycle slice (2026-11-13)

- **Scope.** FORMULA-001 (CUBI extension) is WIRED_WRITE at the tested frontend
  commit. Help traceability is the Activity Table column model:
  `define_activity_table_columns.htm` and `user_defined_fields.htm`. V26 HTML
  Help has no formula-column editor topic, so no parity is claimed.
- **Behaviour.** The Tools > Formula panel validates every expression through
  `POST /p6/formulas/p6-field-registry.v1` (`PROJECT_READ`) and never evaluates
  in the browser. A valid expression is saved through the existing
  `p6-formula-column-api.v1` create route (`PROJECT_WRITE`) and listed with
  version, data type, result type and dependencies. Saving does not touch the
  layout; **Show in grid** adds the field to the persisted activity layout. Grid
  cells are the control-room server values verbatim (`1.0`, `0.375`, null → `—`).
- **Failure behaviour.** Authoritative codes are normalized to plain messages:
  `FIELD_NOT_FOUND:<id>`, `EXPECTED_EXPRESSION_AT_<pos>`,
  `NUMERIC_OPERANDS_REQUIRED`, `UNSUPPORTED_P6_FORMULA_FIELD_TYPE:duration`,
  `FORMULA_SELF_REFERENCE`, `FORMULA_COLUMN_ALREADY_EXISTS`. Invalid input is
  never persisted; a duplicate id does not overwrite the stored definition.
- **Permissions.** Viewer receives validation only: no save, no apply, and a
  visible read-only reason. Planner/project administrator can create and apply.
- **Known limits.** Division by zero is an evaluation-time condition in the
  authoritative core: validation accepts it, all 14 server cells stay null, and
  the UI does not fabricate `NaN`/`Infinity`/`0`. Update, delete, version list,
  audit and server preview endpoints do not exist yet; the contract request is
  `docs/workspace/architecture/p6-formula-column-lifecycle-contract-request.md`
  (`p6-formula-column-lifecycle-api.v1`). The preview fixture is 14 activities,
  not the 250+ acceptance population.

Evidence: `docs/workspace/evidence/formula-columns-v26-2026-11-13/`
(`formula-columns-v26.json`, 10/10 scenarios, 0 exceptions/console errors/5xx,
interaction writes only validate/create/layout, screenshots 01–10,
`CHECKLIST.md`).

## Activities Columns dialog — picker lifecycle (2026-11-13)

- **Scope.** ACT-001 picker slice is WIRED_WRITE. Help topic:
  `define_activity_table_columns.htm`.
- **Behaviour.** `apps/web/src/p6-columns-dialog.ts` edits a body-level draft:
  Available Columns / Selected Options, Add / Add All / Remove / Remove All,
  Move Up/Down, Edit Column (title, 40–800 px width, alignment), visibility,
  Default, Copy From and OK / Apply / Cancel. Remove/Remove All are disabled at
  one column and the pure functions still throw `LAST_COLUMN_REQUIRED`.
- **Persistence.** Only `POST /p6/layouts/{scope}/activity` writes, and the
  dialog preserves the current scope. Defaults come from the server default
  route; Copy From lazily reads the other saved scope. No schedule payload is
  part of the write.
- **Permissions.** Planner / Project administrator may save; Viewer gets a
  read-only reason and disabled OK/Apply (local draft still inspectable) and the
  E2E proves zero writes for Viewer and for Cancel.
- **Defects fixed.** Copy From was permanently disabled although WS-007 can save
  a user layout; read-only sessions could press OK and get a server failure;
  Add All ignored the search/subject filter; the footer claimed no second
  layout existed even after one was saved.
- **Known limits.** No drag-and-drop reorder; Copy From copies columns only and
  only from the other in-project scope; hidden columns remain counted in
  Selected Options.

Evidence: `docs/workspace/evidence/activity-columns-v26-2026-11-13/`
(`activity-columns-v26.json`, 11/11 scenarios, 0 exceptions/console errors/5xx,
screenshots 01–12, `CHECKLIST.md`).

## Activities saved-layout lifecycle — WS-007 completion (2026-11-13)

- **Scope.** WS-007 is WIRED_WRITE for the Activities layout selector; Delete is
  **BLOCKED_EXTERNAL** (no layout delete route). Help topics:
  `customizingactivitylayouts.htm`, `open_a_layout.htm`,
  `create_a_new_activity_layout.htm`,
  `save_a_layout_in_the_activities_or_rsrc_assignments_window.htm`,
  `delete_a_layout.htm`.
- **Behaviour.** `apps/web/src/workspace-layout-selector.ts` now exposes
  New, Reset to Default and Delete beside Open/Apply/Cancel/Save/Save As/
  Rename/Export/Import/Reload. `layoutHasUnsavedChanges` compares the window's
  group mode, ordered sort levels and presentation with the stored
  `groupSort`/`presentation` metadata (a revision without a plan is compared
  with the Activities defaults). The selector renders an `Unsaved changes` chip
  and asks `confirmDiscard` before previewing another layout, Reload, New or
  Reset. `layout.open` opens this chooser rather than the Columns dialog.
- **Persistence.** New reads `GET /p6/layouts/user/activity/default` and writes
  the canonical default columns to the user scope under the prompted name;
  Reset to Default writes default columns, `normalizePresentation(undefined)`
  and the `wbs`/`wbs asc` plan to the user scope while keeping the stored name.
  Both append a revision through `createP6LayoutPersistence`; the project
  layout is never rewritten. Delete is disabled with the truthful reason and
  the contract request `docs/workspace/architecture/p6-layout-lifecycle-contract-request.md`
  (`p6-layout-lifecycle-api.v1`).
- **Permissions.** New/Reset/Save/Save As/Rename/Import require Planner or
  Project administrator (`PROJECT_WRITE`); Viewer sees every write disabled
  with `Your role cannot save layouts` and opening the menu appends nothing.
- **Preserved.** Preview/Apply/Cancel, Save, Save As, Rename, Export/Import,
  revision-conflict recovery (`REVISION_CONFLICT` /
  `IMMUTABLE_LAYOUT_REVISION` reload the authoritative head) and per-user,
  per-project reload restoration are unchanged.
- **Known limits.** The service keeps one user document per project/view, so
  New/Save As/Import replace that slot (New confirms replacement); there is no
  named layout collection. Dirty state covers group/sort and presentation only
  because column edits append immediately. Resource Assignments/Tracking
  layouts remain out of scope.

Evidence: `docs/workspace/evidence/layout-selector-v26-2026-11-13/`
(`layout-selector-v26.json`, 15/15 scenarios, 0 exceptions/console errors/5xx,
screenshots 01–18, `CHECKLIST.md`).

## ACT-003 filters — typed list values, Optimize and Duplicate (2026-11-13)

- **Delivered.** List parameters (Activity Status, Activity Type, Critical) now
  render the documented value picker (`select[name="filter.value.N"]`,
  `data-filter-choice`) instead of a free-text box; an unknown stored value is
  preserved, and `is-empty`/`is-not-empty` disable the picker. Critical shows
  Yes/No while storing `true`/`false`. The builder gained the Help's Optimize
  review: blank rows are dropped only when a complete criterion remains, exact
  duplicates collapse, and criteria implied by another are removed (All keeps
  `equals X` over `contains X`, the longer `contains`, and `not-contains X`
  over `not-equals X`; Any keeps the broader criterion), with the matched row
  set proven unchanged. Duplicate stores `Name (copy)` in the same category,
  selects it, and leaves built-in filters read-only.
- **Boundary.** Every edit still travels through `readLayoutPatch` into
  `WorkspacePresentation.filters` and the saved-layout metadata; no schedule
  input changes.
- **Known limits.** Make Global is still a within-project scope label (no
  tenant-wide sharing), nested AND/OR groups are not modelled, Optimize does
  not compare numeric/date bounds, and criterion-level copy/paste is absent.

Evidence: `docs/workspace/evidence/activity-filters-v26-2026-11-13/`
(`activity-filters-v26.json`, contract `cubi-activity-filters-v26.v2`, 12/12
scenarios, 0 exceptions/console errors/5xx, screenshots 01–11, `CHECKLIST.md`).
Code `d9452209`; unit tests 999 `tsx` + 14 `node --test`, `tsc --noEmit` and
`npm run build` pass.

## Dual tool-rail customizable toolbar — 2026-11-14

- **Scope.** Replaced the duplicated left/right icon maps and the
  contextual-only command strip with one registry-driven toolbar system on both
  rails. This is the mandatory correction requested after the rails and
  floating widgets work; it is not the baseline API increment and is not
  evidenced by PR #1923 alone.
- **Architecture.** `apps/web/src/workspace-toolbar-registry.ts` is the single
  typed command table (stable id, localized label/tooltip, icon, families,
  supported windows, admin gate, enabled reason, handler target, default
  visibility, customization actions). Six left families and exactly eighteen
  right families (Project Tools, Assign, Edit, Layout, Enterprise, Print,
  Action, Administrator, Bottom Layout, Display, Find, Dictionaries, Publish,
  Standard Reports, Tools, Activity, Critical Check, Schedule) render from it.
  A command may appear in several families but is defined once.
- **Customization.** Every family ends with its own Add or Remove control that
  opens the complete registered command list, checked = visible, supports
  multiple changes per open menu, and offers Reset Toolbar. Rail context menus
  offer visibility, Add or Remove, Customize, Lock/Unlock, Reset Toolbar, Reset
  All, Create Custom Toolbar, Rename and Delete. Icon context menus offer Move
  Up/Down, Move to toolbar, Hide/Delete, Rename, Default/Text/Image+Text style,
  Begin a Group and Reset. A body-level Customize dialog toggles all families
  without closing and provides per-family reset, dock/rail moves and custom
  toolbar create/delete.
- **Drag and keyboard.** Pointer capture, a 5px threshold, a ghost and an
  insertion line support reordering buttons, moving commands between families
  and across left/right rails, dragging a whole family into the horizontal dock
  above the workspace, re-docking it, and reordering toolbar rows. Alt+Arrow
  reorders the focused button; menus support Arrow/Home/End/Escape and outside
  click. A drag suppresses the subsequent click so a command never fires by
  accident.
- **Persistence.** `apps/web/src/workspace-toolbar-config.ts` stores a versioned
  `cubi:workspace-toolbars:v2:<user>` document with
  `workspaces["project:<id>"]` for lock/family state, plus button visibility,
  order, rail/dock, custom definitions, labels and styles. The legacy
  `cubi:workspace-toolbars:<userId>` key is migrated. No project, Activity
  Layout or schedule record is written by toolbar operations.
- **Permissions.** Admin-only and capability-gated commands are disabled in
  both the rail and the Add or Remove menu with a stable reason, and disabled
  buttons carry no executable target. Existing APIs still re-authorize every
  command server-side; toolbar preferences grant no data permission.
- **Verification.** `apps/web/e2e/toolbar-rails-v26.mjs` passes 24/24 checks with
  17 screenshots at
  `docs/workspace/evidence/toolbar-rails-v26-2026-11-14/`: both rails, all 24
  families hide/restore, multi-toggle Add or Remove, per-family and global
  reset, empty-family restore, right-click toolbar/icon menus, icon hide and
  restore, pointer reorder, cross-family and cross-rail moves, drag to dock,
  re-dock, toolbar-row reorder, keyboard reorder, custom toolbar
  create/add/rename/reload/delete/reload, user isolation, viewer permissions,
  Persian RTL, and 1280×720/1366×768/1920×1080 with no page overflow, zero
  uncaught exceptions, zero console errors and zero API 5xx. Unit tests: 1117
  `tsx` + 14 `node --test` pass; `tsc --noEmit` and `npm run build` pass.
- **Evidence and code.** Code `7aa9a2d4d29e5492c212ea8bfaf8c74eed13d9a2` on
  `feat/vercel-preview-fixtures` (PR #1923 remains open). Acceptance detail and
  the 20 required browser tests are in
  `docs/qa/V26_DUAL_RAIL_TOOLBAR_MATRIX_2026-11-14.md`.
- **Known limits.** The "floating" state is a persisted horizontal dock above
  the workspace, not a free-position palette with saved coordinates; icon style
  is family-level; browser coverage is English and Persian while the other
  registered locale packs use the shared translation fallback; preferences are
  browser-local per user/project. Enterprise, administrator, publish, report
  and other unavailable commands remain visibly disabled. P4 custom formula
  lifecycle stays BLOCKED_EXTERNAL.
- **CI alignment, 2026-11-14 (`82d1cc1d`).** The pre-existing
  `apps/web/e2e/preview-e2e.mjs` journey still assumed the public floating
  assistant and the old inline navigation. It now asserts the single
  rail-owned `action.assistant` entry against `#cp-ai-assistant-chat` and
  drives the `[data-nav-flyout]` menu, including scoping the right-rail button
  inside its own scroll container and keeping the failed-bootstrap page free of
  a duplicate assistant. The full suite passes locally (97 recorded checks, 51
  screenshots), and all PR #1923 checks — including `web`, PostgreSQL, Python
  3.11/3.12/3.13 and all client typechecks — pass on `82d1cc1d`
  (`feat/vercel-preview-fixtures`). The toolbar implementation code remains
  `7aa9a2d4`; this commit changes tests and docs only.
