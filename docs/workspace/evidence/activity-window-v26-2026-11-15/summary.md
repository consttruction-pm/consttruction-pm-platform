# Activity Window — Acceptance Summary (2026-11-15)

Tested code: `bbacdaa0094d8dccc647ff08c1cf75db59875901` (main).
Runtime: managed Python preview (`python3 -m construction_pm.preview`), fresh SQLite database
per suite, headless Chrome over CDP. Product under test is CUBI; Oracle help page references
are traceability targets only.

## 1. What was audited

Priority zero of the governing order is the Activity window: 16 desktop tabs, menus,
toolbars, filters, columns, context menus, WBS and Gantt. The audit covered the real built
bundle (`apps/web/dist/web/src/main.bundle.js`, served by the preview), not the TypeScript
sources, so every assertion reflects what a user actually receives.

## 2. Changes made

Three source/test files changed; no behavioral thresholds were relaxed.

1. `apps/web/src/workspace-context-menu.ts` — product defect fix in `positionMenu`. The old
   code flipped a menu up and left whenever it overflowed the viewport, then clamped. A tall
   menu that fits on neither side jumped to the top-left corner (rect `top=4` for a pointer
   at `y=324`). The new code flips only when the flipped position still fits, and otherwise
   clamps at the near edge, keeping the menu adjacent to the pointer. Context menus went from
   91/92 to 92/92 after rebuilding the bundle.
2. `apps/web/e2e/toolbars-v26.mjs` — test-scope correction. The rail-button selector now
   scopes to `[data-tool-rail-button]` and measures the command `.cp-icon`, skipping the 12px
   family-handle and 9px drag-grip glyphs. Command icons are 18px; the previous assertion was
   measuring a grip, not a command.
3. `apps/web/e2e/activity-relationships-v26.mjs` — gesture correction. `drawRelationship`
   now scrolls both endpoint rows into the `.cp-gantt-chart` viewport, re-measures, and
   asserts both edge y-coordinates are inside the pane before dragging. Previously a bar
   centre one pixel below the pane bottom hit the splitter instead of the bar.

## 3. Browser proof

28 suites, each on its own port and its own fresh database:

- 351/351 numeric checks passed, 249 screenshots.
- `activity-details-v26`: 17 tabs, 3 write paths, 3 customize actions, 2 unauthorized, 4
  stale-response assertions. `activity-baseline-v26`: before 4, capture 3, afterReload 4,
  details 2, toggle 4, compare 2, wide 2.
- 0 uncaught exceptions, 0 API failures (no 5xx), 1 console error total.
- The single console error is expected: `WBS_HIERARCHY_CYCLE` emitted by
  `wbs-cut-copy-paste-v26`'s deliberate cycle-rejection negative path. It is the product
  correctly refusing an invalid hierarchy, not a failure.

Per-suite results are in `evidence.json`; V26 documentation mapping (topic title, live HTML
Help URL, guide page) is in `v26-traceability.md`.

Suites and the surfaces they prove: details tabs, columns, filters, context menus (92
assertions), WBS hierarchy/status/cut-copy-paste/collapse/band, network, relationships,
grid keyboard, scope, scale, multi-select, group-sort, table font, UDF values, usage,
baseline, trace logic, Gantt overlays/bar styles/options/scroll-sync/fit, toolbars and
toolbar rails.

## 4. Tests and limits

- Full project gates are run separately (`pytest`, `npm test`, TypeScript build) and their
  results are recorded in the PR, not inferred from browser suites.
- Some suites hang after writing their evidence because Chrome/CDP handles keep node alive;
  a watchdog reaps them, so a log tail of exit 137 means "reaped after success", not a
  failed run. Suites whose evidence JSON exists and declares its checks are treated as
  complete.
- Reference limitation: the instruction's 815-page Version 26 PDF is not mounted anywhere
  (`/mnt`, `/mnt/session`, repository). It is recorded as **MISSING / VERIFY**. No page
  number is attributed to it. All guide page numbers are real pages of the retrieved
  303-page official Professional guide and must be re-keyed when the 815-page file arrives.
- Known gaps carried in the traceability document: Feedback tab deferred (no EPPM
  collaboration service), Issues and Calendar are CUBI extensions, Summary/UDFs have no
  standalone help topic, and Update History has no guide section.
