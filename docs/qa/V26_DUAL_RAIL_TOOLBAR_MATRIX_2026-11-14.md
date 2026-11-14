# Version 26 dual tool-rail toolbar — acceptance matrix (2026-11-14)

Scope: the mandatory correction that replaced the duplicated rail icon maps and
the contextual-only command list with one customizable, registry-driven toolbar
system on both rails. This matrix is separate from
`V26_TOOLBAR_COMPLIANCE_MATRIX_2026-11-12.md`, which records the standard
toolbar and menu-bar increment; that increment is not evidence for this work.

- **Code:** `7aa9a2d4d29e5492c212ea8bfaf8c74eed13d9a2` on
  `feat/vercel-preview-fixtures` (PR #1923; not merged).
- **Tests:** `tsc --noEmit`; 1117 `tsx` + 14 `node --test` passed; esbuild
  bundle built. Browser suite `apps/web/e2e/toolbar-rails-v26.mjs`: 24/24
  checks, 17 screenshots, 0 uncaught exceptions, 0 console errors, 0 API 5xx.
- **Evidence:** `docs/workspace/evidence/toolbar-rails-v26-2026-11-14/`
  (`evidence.json` + PNG set).
- **Status vocabulary:** MATCH = implemented and exercised in the browser;
  PARTIAL = implemented with a stated limit; BLOCKED_EXTERNAL = requires a
  service outside this frontend slice.

## Architecture and behaviour

| # | Requirement | Implementation | Browser evidence | Status | Limit |
| --- | --- | --- | --- | --- | --- |
| 1 | One authoritative typed registry for both rails; no duplicated definitions | `apps/web/src/workspace-toolbar-registry.ts`: single `TOOLBAR_COMMANDS` table with stable id, CUBI label/tooltip, icon, families, windows, admin gate, enabled reason, handler target, default visibility, customization actions | Unit tests assert unique ids and one definition per command; both rails render from the same table | MATCH | None |
| 2 | Two independent rails, both fully customizable; neither is a navigation menu | `workspace-toolbar-view.ts` renders `renderToolbarRails` for `left`, `right` and `floating`; visibility, order, styles, add/remove, drag and persistence are per family and per rail | `rails-both-1366x768-en.png`; 6 left and 18 right families with 24 Add or Remove controls | MATCH | None |
| 3 | Right rail registers the 18 required families with original names | `TOOLBAR_FAMILIES` order: Project Tools, Assign, Edit, Layout, Enterprise, Print, Action, Administrator, Bottom Layout, Display, Find, Dictionaries, Publish, Standard Reports, Tools, Activity, Critical Check, Schedule | Family order and labels measured in DOM and at three viewports | MATCH | None |
| 4 | Every family has its own Add or Remove control that opens all registered commands | `addRemoveContent` lists the family's registry commands (all registry commands for custom toolbars), checked = visible, with a per-family Reset Toolbar | `add-remove-menu-1366x768-en.png`; hide/restore two commands in one open menu | MATCH | None |
| 5 | Multiple changes in one open menu update immediately and commands stay reachable | `toggle-button` applies the config and repaints the menu without closing it | Schedule test hides two commands, then resets the family | MATCH | None |
| 6 | Empty toolbars remain visible and restorable | Family renders `[data-tool-family-empty]`; Add or Remove still opens; Reset Toolbar restores defaults | `empty-family-restored-1366x768-en.png` | MATCH | None |
| 7 | Per-family reset and global reset | `reset-family` and `reset-all` in the Add or Remove menu, rail menu and Customize dialog | Reset one family, then Reset All restores 18 right families | MATCH | None |
| 8 | Right-click toolbar area opens customization, not the Add or Remove checklist | `contextmenu` on a family head opens `kind=rail`; visibility toggles, Add or Remove list, Customize, Lock/Unlock, Reset Toolbar/All, Create, Rename/Delete custom | `right-click-toolbar-1366x768-en.png`; E2E asserts `data-tool-menu !== "add-remove"` | MATCH | None |
| 9 | Right-click icon offers Move, Hide/Delete, Rename, styles, group separator, Reset | `buttonContent`: Move Up/Down, Move to toolbar, Hide/Delete Button, inline Rename form, Default/Text/Image+Text, Begin a Group, Reset Toolbar; custom toolbars also offer Delete | E2E executes Hide Button and restores it with Reset Toolbar; menu actions asserted | MATCH | Style choices apply to the whole family, matching a toolbar-level V26 style rather than a single icon |
| 10 | Toolbar menus are distinct from Activity Table/Gantt context menus | Toolbar surfaces use `.cp-tool-menu` plus `data-tool-menu`; they are body-level popovers and never reuse the grid context-menu handler | Right-click assertions on toolbar and icon | MATCH | None |
| 11 | Real pointer drag reorders buttons inside a family | `pointerdown` + pointer capture, 5px threshold, ghost and insertion line; `moveButton` persists order | E2E reorders `layout.open` and `layout.columns`; sorted set unchanged | MATCH | None |
| 12 | Pointer drag moves buttons between families and between rails | Drop target resolves the destination family and index; cross-family moves leave a hidden source entry so normalization cannot resurrect a duplicate | Critical Check and Activity moves captured; no duplication | MATCH | None |
| 13 | Drag a whole family out to a horizontal toolbar above the workspace, keep it docked, re-dock it | Family handle drag targets `[data-toolbar-dock]` (horizontal `.is-horizontal`) or a rail; dock order is persisted | `drag-out-1366x768-en.png`, `docked-1366x768-en.png`; re-dock empties the dock | PARTIAL | The dock is a horizontal strip above the workspace, not a free-position floating window with saved coordinates |
| 14 | Reorder toolbar rows | `setFamilyRail` accepts a destination index; family drag and Customize up/down reorder within rails and within the dock | E2E drags the Layout family onto Edit, proves the order changes without losing a family, and after reload | MATCH | None |
| 15 | Insertion indicators, cancellation, pointer capture, no accidental command activation | Drop line, ghost, `pointercancel`, capture-phase click suppression after a drag | Drag journeys do not fire the dragged command; page keeps rendering | MATCH | None |
| 16 | Keyboard accessibility and no focus traps | Buttons are native `<button>`; Alt+Arrow reorders; menus support Arrow/Home/End/Escape/outside click; focus returns to a stable item | `focusableButtons === buttonCount`; Alt+ArrowDown reorders; menus close with Escape | MATCH | Drag itself requires a pointer; keyboard uses Alt+Arrow and the icon menu |
| 17 | Left rail uses the same registry and engine with independent state | Left families (`navigation`, `project`, `planning`, `resources-cost`, `information`, `administration`) are ordinary registry families | Left families hide/restore, reset and persist independently | MATCH | None |
| 18 | Custom toolbars: create/name/add/remove/reorder/move/rename/delete/reset | `createCustomFamily`, add/remove from the full registry, `moveButton`, `setFamilyRail`, `renameCustomFamily`, `deleteCustomFamily`, `resetFamily`; body-level create form | Create "QA checks", add two commands, rename, reload, delete and reload | MATCH | A custom toolbar starts in the workspace dock because it has no predefined rail |
| 19 | Disabled commands explain why | Every disabled button/menu item has a stable reason and no executable target; admin-only items are disabled for non-admins | Viewer cannot use `admin.permissions`; disabled rail button has no `data-desktop-*` target | MATCH | Commands without a server contract are visibly disabled, never presented as complete |
| 20 | Permissions enforced by the UI and by the service | Registry checks capabilities; all commands call existing APIs which re-authorize `PROJECT_WRITE`/admin | Viewer permission journey; existing API suites remain authoritative | MATCH | Toolbar preferences themselves are browser-local and user-scoped; they grant no data permission |
| 21 | Persist left/right config, visibility, order, docks, custom definitions, styles and lock state | Versioned `cubi:workspace-toolbars:v2:<user>` document; `workspaces["project:<id>"]`; separate top-level toolbar state; legacy `cubi:workspace-toolbars:<userId>` migrated | Reload preserves custom toolbar, buttons, family arrangement; second user gets defaults | MATCH | Preferences are per browser profile, not synchronized across devices |
| 22 | Never overwrite project, Activity Layout or schedule data | The config module only reads/writes its own localStorage key; no API or layout write is performed by toolbar operations | No API 5xx and no layout mutation in the journey | MATCH | None |
| 23 | CUBI identity, compact rails, menus over non-essential space | Deep Navy/Engineering Blue/Copper palette retained; 48px/40px compact rails expand to 150px; popovers placed against the viewport | Screenshots at three viewports and Persian RTL | MATCH | None |
| 24 | RTL/LTR and all launch languages | `dir` follows the active locale; menus inherit it; labels use the workspace translator with en/fa registered strings and English fallback for other packs | Persian RTL menu stays inside the viewport; English LTR measured | PARTIAL | Browser coverage is en + fa; other registered locale packs rely on the shared fallback and were not re-run in this suite |
| 25 | 1280×720, 1366×768 and 1920×1080 without overflow | Responsive rail widths and scrollable families | All three cells captured; `pageOverflow === false` | MATCH | None |

## Required browser test coverage

| Directive test | Result |
| --- | --- |
| Show/hide each family | All 24 families hidden and restored through the Customize dialog |
| Add a button | Print family first button restored; custom toolbar commands added |
| Remove a button | Schedule/print and layout commands hidden |
| Multiple selections in one Add or Remove menu | Two schedule commands hidden without reopening |
| Reset one toolbar | Schedule, print and layout families reset individually |
| Reset all | All 18 right families restored |
| Right-click toolbar customization | Rail menu opened and asserted distinct from Add or Remove |
| Right-click icon customization | Icon menu opened; Hide Button executed and restored |
| Reorder icons | Pointer drag and Alt+Arrow both reorder |
| Move between families | Tools → Critical Check with no duplicate |
| Move between rails | Planning → Activity |
| Drag toolbar into upper workspace | Print family docked above the workspace |
| Re-dock | Docked family returned to the right rail |
| Reorder toolbar rows | Layout row dragged above Edit; sets compared |
| Create/rename/delete custom toolbars | "QA checks" created, renamed, reloaded, then deleted and proven absent after reload |
| Save/reload every customization | Custom toolbar, buttons, family arrangement and names survive reload |
| Independent user configurations | Planner does not inherit the admin's custom toolbar |
| Permission restrictions | Viewer sees disabled administrator commands with no target |
| RTL/LTR | Persian RTL and English LTR measured |
| Viewports | 1280×720, 1366×768, 1920×1080 |
| Keyboard accessibility/no overflow | All rail buttons focusable; no horizontal page overflow |

## Remaining limitations

1. The "floating" state is a persisted horizontal dock above the workspace. There
   is no free-position floating palette with saved x/y coordinates.
2. Icon style is a family-level choice (Default/Text/Image+Text), not a
   per-button style.
3. The browser suite exercises English and Persian. The other registered locale
   packs use the shared translation fallback and were not re-run here.
4. Toolbar preferences are intentionally browser-local and per user/project;
   they are not synchronized through a server preference API.
5. No schedule, layout or project record is written by any toolbar operation.

## Non-claims

- The baseline API work and PR #1923 are not evidence that this toolbar system
  is complete; this matrix and its browser suite are the evidence.
- No disabled or unimplemented command is marked operational. Enterprise,
  administrator, publish, report and other unavailable commands remain visibly
  disabled with a reason.
