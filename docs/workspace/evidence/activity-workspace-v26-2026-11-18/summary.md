# Activity Workspace — 2026-11-18 increment

Issue #2047, PR #2048, branch `feat/2047-activity-workspace-v26`.
Verified code head: `f96478f`. Working tree: evidence and documents only after that
commit.

## Delivered in this increment

1. **Activity Details General tab edit path**
   - `workspace-activity-general.ts` and 9 unit tests.
   - Loads the Activity Master record, writes only changed fields with
     `expected_revision`, surfaces `REVISION_CONFLICT`, never derives schedule facts
     in the browser.
   - Editable: name, activity type, duration type, percent-complete type, leveling
     priority and cost account.
   - Proof: `activity-general-edit-v26.mjs` — EN 1366×768, FA RTL 1280×720 and
     1920×1080, reload persistence and restore.

2. **Activity Details tab keyboard model**
   - ArrowLeft/Right, Home, End; focus, `aria-selected` and the visible panel move
     together, wrap at both ends, and follow the rendered direction in Persian RTL.
   - Proof inside `activity-details-v26.mjs` (`keyboard`, `keyboardRtl`).

3. **Explicit empty selection state**
   - A cleared selection previously presented blank fields as stored values. The
     active tab now renders `data-details-empty-state` with localized copy and
     keeps the tabs visible; it adds no height beyond the panel.
   - Unit coverage in `workspace-activity-details.test.ts`; browser proof
     `activity-details-v26.mjs` `emptyState` and
     `details-empty-selection-en-1366.png`.

4. **Deterministic, non-hanging V26 browser runs**
   - The shared harness pins Chrome to `--lang=en-US` (the host OS locale is
     Persian), terminates the browser tree on process exit, and two suites no
     longer call a non-existent `chrome.close`.
   - `layout-selector-v26` now drives the ordered group-level control
     (`group.field.0`), matching the current dialog contract.
   - Gantt suites write dated evidence instead of overwriting the November-12
     directories.

5. **Acceptance and inventory**
   - Updated `acceptance-matrix.md` with re-verification at `f96478f` and items
     44–52.
   - New `v26-surface-inventory.md`: menus, toolbars, context menus, dialogs,
     panes, tabs, table, Gantt, keyboard, localization, blockers and handoffs.

## Verification (2026-11-18, head `f96478f`)

- `npm run typecheck` — clean.
- `npm test` — 1177 source tests + 15 preview-server tests, 0 failed.
- `npm run build` — clean.
- Python: 99 tests across workspace read/provider, WBS read, read contract,
  preview runtime, activity master and activity validation — 0 failed.
- Browser suites, each with a fresh preview database:
  - `activity-details-v26` — 17 tabs, keyboard EN + FA, writes, unauthorized,
    stale-response guard, customize persistence, empty selection.
  - `activity-general-edit-v26` — 6/4/4 catalogues, revision guard, reload, RTL.
  - `activity-columns-v26` (11), `activity-filters-v26`,
    `activity-group-sort-v26` (9), `activity-wbs-band-v26`,
    `activity-wbs-collapse-v26`, `activity-grid-keyboard-v26`,
    `activity-multi-select-v26`, `activity-scope-v26` (15), `activity-scale-v26`
    (8), `activity-table-font-v26`, `activity-usage-v26`,
    `activity-trace-logic-v26`, `activity-baseline-v26`,
    `activity-udf-values-v26`, `activity-relationships-v26`,
    `activity-network-v26`, `activity-gantt-overlays-v26`,
    `gantt-options-v26`, `gantt-scroll-sync-v26`, `gantt-fit-v26`,
    `gantt-bar-styles-v26`.
  - `toolbars-v26`, `toolbar-rails-v26`, `context-menus-v26`,
    `register-context-menus-v26`, `workspace-canonical-v26`,
    `workspace-shell-v26`, `layout-selector-v26` (15) — passed.
- Evidence: the sibling `*-v26-2026-11-18` directories.

## Failing / blocked in this run

- **`workspace-responsive-v26` fails at 1280×720** (scenario 01). `#workspace` is
  521px tall while `.cp-p6 .cp-p6-workspace` enforces `min-height: 540px`
  (`apps/web/styles.css:5446`), producing a 19px workspace scroller. This is a
  shared shell file owned by #1716/#1711/#1983; the fix is a one-line floor change
  or reduced chrome, not a change to the approved split ratio.
- **Grid refresh after a Details save** still requires the next project read; the
  callback lives in `main.ts` / `workspace-view.ts` (same ownership).
- **`activity.percent_complete_type`** is not in the read model
  (`workspace_read_provider.py`, owned by #1983).
- **Activity code assignment, persisted Notebook, step writes and per-activity
  document assignment** have no HTTP contract; they remain documented gaps rather
  than invented endpoints.
- The Oracle Help host returns **403** from this environment and the 815-page PDF
  is **MISSING / VERIFY**.

## Not verified in this run

- `workspace-responsive-v26` scenarios after 01 (1366, 1920, 844×390) were not
  reached because the suite aborts on the 1280×720 assertion.
- Menu-driven pane show/hide geometry (#36) is covered by the shell inventory but
  not by a dedicated geometry assertion on this head.
