# CUBI Version 26 Execution Checkpoint

Source of record: the official Version 26 Help (`p6-professional-help.pdf`, 815 pages) and the
CUBI product identity rules. Every stage below records what shipped, the evidence that it runs,
and what is still honestly unavailable.

Branch: `codex/jalal/cubi-v26-shell-stage-a-20261110` (from `main` @ `94ad2330`).

---

## Stage A — central shell

Status: implemented and locally verified; independent PR opened from this branch and merged only
after CI is green on the exact head SHA.

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
