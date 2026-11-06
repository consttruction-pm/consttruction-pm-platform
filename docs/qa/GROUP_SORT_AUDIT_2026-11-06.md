# Group and Sort — Chapter 8 audit and live evidence

**Date:** 2026-11-06
**Branch:** `codex/jalal/cubi-shell-v26-20261104`
**Reference:** supplied `p6-professional-help.pdf` (`G57535-02`, October 9 2026), Chapter 8 “Project Table”, PDF pages 377–378 (help pages 6–7 of 31): “Group and sort a tracking layout using standard settings” and “Group and sort a tracking layout using custom settings”
**Surface:** authenticated live workspace, project `preview-rps-01`, Chrome at 1280×720
**Code:** `workspace-model.ts`, `workspace-filter-sort.ts`, `workspace-dialogs.ts`, `workspace-desktop-shell.ts`, `workspace-view.ts`, `main.ts`, `styles.css` / `public/styles.css`

## What the reference documents

The custom Group and Sort procedure selects a first grouping category, optional
indentation for WBS, grouping-band title/ID/name options, band font and colour,
“Sort grouping bands alphabetically”, “Hide if empty”, “Show Grand Totals” and
“Show Summaries Only”. Sort fields are added with **Add**, each with a field
name and Ascending/Descending/Hierarchical order, and removed with **Delete**.
The standard procedure picks one of the predefined group and sort options.

## Implemented in this increment

| Reference capability | Status | Implementation / evidence | Remaining gap |
| --- | --- | --- | --- |
| Open Group and Sort | Implemented | View > Group and Sort…, the Group & Sort toolbar button and the activity context menu share `dialog.group-sort` | — |
| Order multiple sort fields | Implemented | Three ordered Field/Order rows (Ascending or Descending). Empty rows are ignored; duplicates collapse to their first position | P6 uses an unbounded Add/Delete list; CUBI is bounded to three rows |
| First sort field drives the toolbar | Implemented | The first row becomes the toolbar “Sort by” value and its direction button; changing the toolbar select replaces the plan with that single field | — |
| Direction toggle keeps deeper levels | Implemented | The toolbar ↑/↓ button flips only level one; levels two and three keep their direction | — |
| WBS grouping stays intact | Implemented | Grouping by WBS remains the primary hierarchy; the sort plan applies inside each WBS block, and a WBS level in the plan is ignored because the group already supplies it | P6 can group by other categories (Status, OBS, Activity Type, dates); CUBI offers WBS or no grouping only |
| Deterministic order | Implemented | Numeric values compare numerically, blank values stay last in both directions, and the activity ID is the final tie-break only after every requested level | — |
| No schedule mutation | Implemented | Sorting is applied after filtering and before display-row construction; no repository write and no re-dating occurs | — |
| Validation and immutability | Implemented | Unknown columns are dropped, the list is capped at three, the state object is replaced rather than mutated, and no-op plans return the same state | — |
| Grouping band presentation | Not implemented | — | Band title/ID/name toggles, band font/colour, alphabetical bands, Hide if empty, Show Grand Totals and Show Summaries Only |
| Persist the plan with the layout | Not implemented | The plan lives in the workspace state for the session | Grouping/sort are not yet part of the saved layout metadata, unlike filters and bar styles |

## Live capture

Tool: `apps/web/e2e/capture-group-sort.mjs` against `http://127.0.0.1:4174`.
Raw record: `docs/workspace/evidence/group-sort-2026-11-06.json`
(`gitHead` at capture time `4af7b880`; the code audited here is the working tree
that this commit records).

Plan applied: **Status descending**, then **Activity Name ascending**, third row
empty, group by WBS.

| State | Table order (activity IDs) | Gantt order | Counts |
| --- | --- | --- | --- |
| Default WBS order | `A100, A110, A210, A120, A130, A140, A145, A160, A150, A155, A180, A170, A190, A200` | identical | 14 / 14 |
| Status ↓, Name ↑ | `A210, A110, A100, A140, A145, A160, A130, A120, A150, A155, A180, A190, A170, A200` | identical | 14 / 14 |
| Restored WBS | the original order | identical | 14 / 14 |

The reordered groups prove both levels: in “Project management” the only Not
Started activity (`A210 Project closeout`) comes first, then the two Completed
activities in **name** order (`Mobilization` before `Project kickoff`). In
“Civil works” the Not Started activities come first in name order (`Piling and
foundations`, `Site utilities diversion`, `Steel erection`), then the In
Progress `Earthworks`, then Completed `Site survey…`. “MEP works” orders
`Commissioning` before `MEP first fix`. Empty values such as Remaining Duration
did not affect the ordering.

The dialog measured 520×465 at 1280×720, inside the viewport, with three labelled
sort rows and the group selector. The toolbar afterwards showed `Sort by
Status`, and the Gantt row order matched the table in every state.

## Verification

- `npx tsc --noEmit` — passed.
- Web unit tests — **629 passed, 0 failed**; multi-level ordering, WBS in-group application, validation,
  deduplication, primary mirroring and direction-toggle tests added in
  `workspace-filter-sort.test.ts`; three-row rendering and ordered form reading
  added in `workspace-dialogs.test.ts`.
- Preview resolver tests — 14 passed, 0 failed.
- `npm run build` — passed.
- `cmp apps/web/styles.css apps/web/public/styles.css` — identical.
- Targeted real-runtime capture — 4 screenshots, three table states, table and
  Gantt IDs equal throughout.

## Evidence files

- `docs/workspace/screenshots/visual/59-group-sort-dialog-en-1280.png` — dialog
  with group selector and three sort rows.
- `60-group-sort-multilevel-en-1280.png` — Status ↓ / Name ↑ applied; toolbar
  shows the primary field.
- `61-group-sort-restored-en-1280.png` — WBS order restored.

## Not claimed

- No grouping categories other than WBS, no grouping bands with titles/colours,
  no alphabetical band sorting, hide-if-empty, grand totals or summaries-only.
- No unbounded Add/Delete sort rows; three levels is the implemented bound.
- Grouping and sorting are not yet saved into the layout metadata, so a reload
  starts from the WBS default.
- No merge to `main`, no Production deployment, no change to PR #1716.
