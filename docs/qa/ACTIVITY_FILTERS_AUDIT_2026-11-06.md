# Activity filters — Chapter 9 audit and live evidence

**Date:** 2026-11-06
**Branch:** `codex/jalal/cubi-shell-v26-20261104`
**Reference:** supplied `p6-professional-help.pdf` (`G57535-02`, October 9 2026), Chapter 9 “Filtering”, PDF pages 403–412 (filter table and create/apply/combine procedures)
**Surface:** authenticated live workspace, project `preview-rps-01`, Chrome at 1280×720
**Code:** `workspace-activity-filters.ts` (new), `workspace-presentation.ts`, `workspace-dialogs.ts`, `workspace-desktop-shell.ts`, `workspace-view.ts`, `styles.css` / `public/styles.css`

## What the reference documents

The Chapter 9 table defines fourteen predefined activity filters on these data
items: Activity Status, Critical, Primary/Secondary Constraint, Activity Type,
Longest Path, Total Float, New Feedback, Project Status. Custom filters are
created from **View > Filter By > Customize > New**, may contain several
criteria joined by `Where / Or`, and support “Is within range of” and “Is not
within range of” for date and numeric items. Several filters can be active at
once, and filters only limit the rows on screen.

## Implemented in this increment

| Reference capability | Status | Implementation / evidence | Remaining gap |
| --- | --- | --- | --- |
| Apply a predefined filter | Implemented | Seven documented filters: In Progress, Not Started, Completed, Critical, Non Critical, Negative Float, Milestone. The dialog lists them in a “Predefined filters” group; applying “In Progress” reduced 14 activities to `A130` in both the table and the Gantt | The other seven documented defaults (Has Finish Constraint, Has Start Constraint, Level of Effort, Longest Path, New Feedback to Review, Non What-If, Normal) need constraint/EF/feedback/type aliases that the current row model does not expose |
| Create a custom filter | Implemented | Name, `All criteria (AND)` / `Any criterion (OR)`, four Field / Is / Value rows, operators contains, equals, is not equal to, greater/less than, is empty, is not empty | The four rows are a fixed working limit; P6 allows an unbounded Add/Delete list. “Is within range of” is not offered |
| Save, edit, re-apply, delete | Implemented | Saved filters persist with the project layout presentation and reappear in a “Saved filters” group. “Civil open” and “Civil or procurement” survived a reload and stayed active | No “Make Global”; saved filters belong to this project/layout only |
| Combine filters | Partial | One active filter may contain many criteria with AND/OR | P6 can combine several whole filters; CUBI applies one definition at a time. This is recorded as a gap, not simulated |
| Filter table and Gantt together | Implemented | The same filtered activity set feeds both views; every capture reports identical table and Gantt IDs | — |
| Filters do not mutate schedule data | Implemented | Applied before display-row construction; no repository write occurs on filter change apart from layout presentation metadata | — |
| WBS criterion uses the displayed WBS value | Implemented | A regression test proves `WBS contains Procurement` matches the row whose internal id is `WBS-RPS-PROC`; `WBS contains WBS-RPS` matches nothing | — |
| Clear the filter | Implemented | Selecting “All activities” clears the active filter and restores all 14 rows; changing the Apply selection also resets the custom builder so stale criteria cannot resave the old filter | — |

## Live capture

Tool: `apps/web/e2e/capture-filters.mjs` against `http://127.0.0.1:4174`.
Raw record: `docs/workspace/evidence/filters-2026-11-06.json`
(`gitHead` at capture time `59a6a42d`; the code changes audited here are the
uncommitted working tree that this commit records).

| Step | Active filter | Table IDs | Gantt IDs | Bands |
| --- | --- | --- | --- | --- |
| Baseline, All activities | `""` | 14 (A100…A200) | 14, identical | 7 |
| Predefined In Progress | `builtin:in-progress` | `A130` | `A130` | 2 |
| Custom AND “Civil open” (WBS contains Civil, status not equal to Completed) | `custom:civil-open` | `A130, A140, A145, A160` | identical | 2 |
| Custom OR “Civil or procurement” (WBS contains Civil OR Procurement) | `custom:civil-or-procurement` | `A120, A130, A140, A145, A160, A150` | identical | 3 |
| After page reload | `custom:civil-or-procurement` | same six rows | identical | 3 |
| Cleared back to All activities | `""` | 14 | identical | 7 |

The Filters dialog measured 640×457 at 1280×720, fully inside the viewport,
with four criteria rows and both filter groups. The header shows
`Filter: <name>` and carries `data-active-filter` for verification.

## Verification

- `npx tsc --noEmit` — passed.
- Web unit tests — **625 passed, 0 failed** (new WBS-name resolution test plus five filter tests and four dialog tests).
- Preview resolver tests — 14 passed, 0 failed.
- `npm run build` — passed (`main.bundle.js` 1.4 MB).
- Targeted real-runtime capture — 7 screenshots, six table states; table and Gantt row IDs equal in every state; persistence proved by reload.

## Evidence files

- `docs/workspace/screenshots/visual/49-filters-dialog-en-1280.png` — dialog at 2× DPR.
- `50-filters-in-progress-en-1280.png` — predefined filter applied to table and Gantt.
- `51-filters-custom-and-en-1280.png` — custom AND filter applied.
- `52-filters-custom-or-en-1280.png` — custom OR filter applied.
- `53-filters-saved-list-en-1280.png` — both saved filters listed, criteria reloaded.
- `54-filters-cleared-en-1280.png` — all activities restored.

## Filter list increment (2026-11-08)

The Version 26 Filter dialog is a list of filters grouped by category, separate
from the filter-details builder. This increment rebuilds the dialog around that
list and wires every documented list action.

| Reference capability | Status | Implementation / evidence |
| --- | --- | --- |
| Filter list grouped by Default / Global / Layout / User | Implemented | Four `tbody` groups in the documented order. Default filters are read-only. Global and layout filters come from the saved layout. The User group states that this runtime keeps per-user filters with the layout rather than in the project database |
| Select several filters with checkboxes | Implemented | `filterSelected` is a multi-valued selection; the highlighted row drives Modify/Delete/Copy/Make Global |
| All Activities toggle | Implemented | Checking it disables the list and shows every activity; the previous selection is retained and returns when unchecked |
| All selected filters / Any selected filter | Implemented | `combine` is stored with the layout and applied when more than one filter is selected |
| Replace vs Highlight | Implemented | Replace narrows the table and Gantt; Highlight adds `is-filter-match` to the matching rows in both views without removing others |
| New / Modify / Delete | Implemented | New clears the builder and starts a global filter; Modify loads the highlighted saved filter; Delete removes the targeted row and, when it was the one loaded in the builder, clears the builder. Default filters cannot be modified or deleted |
| Copy / Paste | Implemented | Copy keeps one definition in this session; Paste inserts it in the selected category and selects the new copy. The clipboard is session-only, matching the documented in-session copy |
| Make Global | Implemented | Moves the targeted saved filter to the Global group and keeps it selected |
| Copy as Layout | Implemented | Creates a layout-scoped copy, selects it, and keeps the fresh selection after the dialog re-renders |
| Apply / OK / Cancel / Default | Implemented | Apply submits without closing; OK applies and closes; Cancel restores the dialog snapshot; Default restores the documented layout defaults |

Live verification (2026-11-08, `http://127.0.0.1:4174`): Modify loaded a saved
filter and Delete cleared it; Copy as Layout created and selected a new row; Make
Global changed the category while keeping the selection; Paste inserted a
layout-scoped copy (seven rows); New opened an empty builder focused on the name
field with the Global category; the All Activities toggle and both apply modes
acted on the real table and Gantt. These followed the filter-dialog regression
tests for selection round-trip, delete targeting and Copy-as-Layout selection.

**Still not claimed:** the four criteria rows are a fixed limit; “Is within
range of” is not offered; predefined filters remain the seven that can be
computed from the current row model; there is no separate filter manager
window; Copy/Paste does not cross sessions; User-defined filters are not stored
in the project database.

## Not claimed

- No constraint-based, Level of Effort, Longest Path, New Feedback, Non What-If
  or Normal predefined filters yet.
- Multi-filter combination and Make Global are implemented as of 2026-11-08
  (see above); date/numeric “within range” operators remain absent.
- No filter manager window, filter columns in the layout definition, or filter
  application on non-Activity windows.
- No merge to `main`, no Production deployment, no change to PR #1716.
