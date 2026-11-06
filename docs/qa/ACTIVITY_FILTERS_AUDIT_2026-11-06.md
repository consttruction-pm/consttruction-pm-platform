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

## Not claimed

- No constraint-based, Level of Effort, Longest Path, New Feedback, Non What-If or Normal predefined filters yet.
- No multi-filter combination, global filter publishing, or date/numeric “within range” operators.
- No filter manager window, filter columns in the layout definition, or filter application on non-Activity windows.
- No merge to `main`, no Production deployment, no change to PR #1716.
