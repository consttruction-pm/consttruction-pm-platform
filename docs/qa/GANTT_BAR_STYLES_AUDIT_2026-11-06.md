# Gantt Bar Styles — Chapter 7 audit and live evidence

**Date:** 2026-11-06
**Branch:** `codex/jalal/cubi-shell-v26-20261104`
**Reference:** supplied `p6-professional-help.pdf` (`G57535-02`, October 9 2026), Chapter 7 “Gantt Chart”, PDF page 334 (help pages 11–12 of 48): “Add a bar to the Gantt Chart”, “Change a bar in the Gantt Chart”, “Position a bar in the Gantt Chart”
**Surface:** authenticated live workspace, project `preview-rps-01`, Chrome at 1280×720
**Code:** `workspace-presentation.ts`, `workspace-dialogs.ts`, `workspace-desktop-shell.ts`, `workspace-view.ts`, `styles.css` / `public/styles.css`

## What the reference documents

- **Add a bar** — View > Bars, click Add, mark Display, name the bar, choose
  the timescale it represents, attach a filter, configure the Bar Style tab
  (with a live Preview column), select grouping/necking on Bar Settings, set the
  label and position on Bar Labels, then Apply.
- **Change a bar** — open View > Bars, select the bar, toggle Display, rename
  it, change its timescale/filter, reconfigure Bar Style, Bar Settings and Bar
  Labels, then OK or Apply.
- **Position a bar** — on Bar Style > Options choose a row. Bars are drawn in
  dialog order and may be stacked or share a row.
- **Background lines** — Options > Sight Lines adds horizontal lines before
  summaries or at row intervals and vertical major/minor lines.
- **Apply settings from another layout** — Copy From another layout.

## Implemented in this increment

| Reference capability | Status | Implementation / evidence | Remaining gap |
| --- | --- | --- | --- |
| View > Bars / Layout Options > Bars | Implemented | The command opens the Bar Styles dialog from the View menu and the Gantt “Bar Styles” tab in the live shell | — |
| Independent settings per bar type | Implemented | Seven real types — Task, Critical, Summary, Milestone, Progress, Actual, Baseline. Each carries Display, Filter, Row (1–3), Height, Pattern, Start/Body/Finish shape, Start/Body/Finish/Border colour, Label and Label position | The reference allows user-defined bars named and added one by one; CUBI has a fixed seven-type set. Add / Delete / Copy From are not offered |
| Show / hide a bar type | Implemented | The Show checkbox is persisted; the renderer omits hidden types. Actual and Baseline are disabled with an explicit note when no dates exist | — |
| Filter attached to a bar | Implemented | Nine real filters: All, Task, Critical, Non-critical, Milestone, Summary, In Progress, Completed, Not Started. The renderer applies the chosen filter per bar type | P6 can bind a saved custom filter to a bar; CUBI offers the fixed nine |
| Bar style: colours, patterns, shapes | Implemented | Solid, striped, hatched and outline patterns; bar, line, triangle-up, triangle-down, diamond, circle and none for start/body/finish. Colour inputs drive CSS variables consumed by the renderer | No gradient/pattern bitmap editor, no per-corner shapes, no “necking” |
| Bar labels | Implemented | Field choices none, Activity ID, Activity name, Duration, Progress; positions inside-left/centre/right, above, below and right. Summary bars read the derived WBS values | P6 exposes many more label fields and multi-line labels |
| Position a bar in a row | Partial | Row 1–3 is persisted and used when layers stack; layers that do not fit the fixed activity-row height are scaled together so bars stay one-per-row | No arbitrary stacking order beyond three rows, no “same row, first visible wins” semantics |
| Live preview | Partial | Changes are applied by OK and visible immediately after the dialog closes; the dialog header explains that bar geometry still comes from the saved schedule dates | No inline Preview column inside the dialog; no Apply-without-closing |
| Restore defaults | Partial | “Reset to defaults” restores the documented palette and shapes | No separate per-bar “Default” button |
| Persistence | Implemented | The whole bar style set is stored in the project layout presentation metadata and restored after reload | — |
| Bar settings / sight lines | Not implemented | — | Grouping/necking and horizontal/vertical sight lines need layout-level renderer work that is not in this increment |

## Live capture

Tool: `apps/web/e2e/capture-bars.mjs` against `http://127.0.0.1:4174`.
Raw record: `docs/workspace/evidence/bars-2026-11-06.json`
(`gitHead` at capture time `1bdcc5f2`; the code audited here is the working tree
that this commit records).

All numbers below are read from the rendered DOM after the dialog was
submitted, not from the form:

| State | Task bar | Summary bar |
| --- | --- | --- |
| Defaults | bar, solid, 13 px computed, `rgb(238, 243, 248)`, label “A110” right | bar, solid, 10 px, `rgb(23, 50, 77)`, no label, triangle-down endpoints |
| Customized | `#c0392b`, striped, diamond body, circle start, triangle-up finish, 18 px requested → 14 px computed in the 22 px row, label “Mobilization” inside-centre | `#0b5fa5`, hatched, 16 px, label “Riverside Pump Station Upgrade” right, diamond endpoints |
| After reload | identical to customized | identical to customized |
| Restored | bar, solid, 13 px, default background, “A110” right | bar, solid, 10 px, default background, triangle-down endpoints |

The dialog measured 780×619 at 1280×720 and stayed inside the viewport, with
all seven sections present. Counts stayed at 6 task, 7 critical and 7 summary
bars throughout, so styling did not add or drop any schedule row.

## Verification

- `npx tsc --noEmit` — passed.
- Web unit tests — **626 passed, 0 failed**; the added test asserts that a WBS
  summary consumes the persisted summary style (`is-pattern-hatched`,
  `height:16px`, `--cp-bar-body:#0b5fa5`, diamond endpoints, right label).
- Preview resolver tests — 14 passed, 0 failed.
- `npm run build` — passed.
- `cmp apps/web/styles.css apps/web/public/styles.css` — identical.
- Targeted real-runtime capture — 5 screenshots; persistence proved by reload;
  restore proved the defaults return.

## Evidence files

- `docs/workspace/screenshots/visual/55-bars-dialog-en-1280.png` — Bar Styles
  dialog with seven sections and the Task editor open.
- `56-bars-baseline-en-1280.png` — default bars in the Gantt.
- `57-bars-customized-en-1280.png` — task and summary bars after the custom
  style was submitted.
- `58-bars-restored-en-1280.png` — defaults restored.

## Not claimed

- No Add/Delete/Copy From bar definitions, no per-bar timescale, no named
  custom bars, no Bar Settings grouping/necking and no Sight Lines tab.
- No inline Preview column or Apply-without-closing in the dialog.
- Summary geometry remains derived from persisted child activities; the bar
  style changes appearance only and never re-dates a bar.
- No merge to `main`, no Production deployment, no change to PR #1716.
