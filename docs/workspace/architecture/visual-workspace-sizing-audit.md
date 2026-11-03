# Visual Workspace Sizing Audit — Conversation Baseline and Git History

Date: 2026-11-03
Branch: `audit/p6-v26-gantt-visual-parity-current`
Scope: shell bands, page/window geometry, split panes, Gantt, Timeline, Details, rails and dialogs.

## 1. Approved geometry recovered from prior instructions

The latest explicit desktop reference geometry is 1100 × 808, recorded in commit `afa534e37d779bdababdb23c73684d6fe749e094` (2026-11-01). It supersedes earlier experimental ratios for the main Activity schedule workspace.

| Region | Approved reference |
|---|---:|
| Reference viewport | 1100 × 808 px |
| Title bar | 23 px |
| Menu bar | 18 px |
| Toolbar | 24 px |
| Layout bar | 20 px |
| Status bar | 14 px |
| Remaining workspace | 709 px |
| Activity header | 18 px |
| Upper schedule region | 433 px |
| Divider/gap | 10 px |
| Lower Activity Details region | 248 px |
| Vertical split | 63.58% / 36.42% |
| Activity table / Gantt split | 53.5% / 46.5% |
| Directory icon rail | 20 px |
| Comments/context rail | 23 px |
| Table/Gantt splitter | 4 px |

The arithmetic is coherent: 23 + 18 + 24 + 20 + 14 + 709 = 808; 18 + 433 + 10 + 248 = 709. At the reference viewport, the upper/lower split is 63.58/36.42. The horizontal split is 53.5% table, 4 px splitter, remaining Gantt. Preserve the frame; scroll overflow rather than compressing it.

Earlier discussion on 2026-10-30 included an experimental 58/42 Activity/Gantt split and Timeline measurements in an assistant response. The user then clarified that the apparent Timeline issue was caused by screen resolution and explicitly instructed: **do not touch Timeline sizing**. Those earlier experimental values are not permission to resize the Timeline. The later 2026-11-01 geometry is the controlling frame for Activity/Gantt.

## 2. Git-history findings — what actually changed and why

### A. 2026-10-30 — initial visual-demo shell
Commit: `5d509c78b039f4e4e9c3b4599e518a0cafe2ca8f`

Introduced the standalone `.cp-vd` visual-demo surface. Its independent CSS geometry is:

| Component | `.cp-vd` CSS |
|---|---:|
| Demo title bar | min-height 36 px |
| Demo menu bar | min-height 30 px |
| Demo toolbar region | max-height 96 px; wraps and scrolls |
| Demo window tabs | min-height 32 px |
| Demo layout bar | min-height 34 px |
| Demo window heading | min-height 34 px |
| Demo Activity Details | fixed 212 px; collapsed 30 px |
| Demo Activity table/Gantt split | 52% / remaining; pane minimums 460 px and 320 px |
| Generic demo dialog | width min(560 px, viewport − 24 px); max-height 86vh |
| Option dialog | width min(520 px, viewport − 28 px) |

This is a separate, larger demo layout, not the compact 1100 × 808 `.cp-p6` frame added later. The two sizing systems coexist. Route selection in `workspace-visual-demo-route.ts` confirms that `/app?project=preview-rps-01` (unless `view=live` is explicitly set) selects the visual demo. The visual-demo renderer emits `.cp-vd`, not `.cp-p6`. Therefore the user's normal preview-project entry uses the 36/30/96/32/34/212 px demo sizing, while the approved compact geometry exists under a different `.cp-p6` root and is not applied to that visual-demo route. This is the principal sizing mismatch, not a hypothetical route concern.

### B. 2026-11-01 — compact P6-proportioned frame
Commit: `afa534e37d779bdababdb23c73684d6fe749e094`

Added the explicit 1100 × 808 geometry in section 1. The commit also fixes the directory rail at 20 px, comments rail at 23 px, and table/Gantt split at 53.5/46.5. The commit's stated intent is to preserve the fixed frame and let overflow scroll instead of compressing it; assistant and tools overlays must not resize the work area.

### C. 2026-11-02 — Project Details placement and Network canvas
Commit: `0420ce79efaddabf6c228dbdce7b3e533532ca94`

Project page was changed to place Project Details below the Project register instead of in a generic right-side inspector:
- upper register: `minmax(250px, 1fr)`
- lower Details: `minmax(176px, 34%)`
- 6 px gap
- removed Details max-height and enabled internal scrolling

This is page-specific, not a change to the global Activity/Gantt frame. The intent was to make Project Details a lower dock. It does not use the 248 px Activity Details reference height; it must be treated as a separate Project-page layout unless the original Project screenshot proves otherwise.

The same commit changed only the Activity Network drawing canvas:
- min-height 360 px → 420 px
- added min-width 1080 px
- overflow hidden → auto

The likely purpose is to prevent the node/link canvas being clipped and allow scrolling. This changes the inner Network canvas, not the outer workspace window. The fixed 1080 px minimum can cause horizontal scrolling on narrower screens and must be checked against the original Network screenshot; it is not a reason to enlarge the whole workspace.

### D. 2026-11-03 — expanded module surfaces
Commit: `ea4e1ce91e3e238524aef13a3e1919883c34abba`

The inspected diff adds module content, controls, dialogs and tests. It does not change the global shell heights, Activity/Gantt split, Details height or Timeline geometry. No global window resize was found in this commit.

## 3. Current discrepancies visible in source

| Surface | Current code | Reference/constraint | Finding |
|---|---:|---:|---|
| `.cp-vd` title/menu/toolbar/tabs/layout | 36 / 30 / up to 96 / 32 / 34 px | `.cp-p6` approved 23 / 18 / 24 / 20 px for title/menu/toolbar/layout | Two competing shell geometries coexist. Confirm the post-login rendered root before changing either. |
| `.cp-vd-details` | 212 px; collapsed 30 px | Activity Details 248 px in 1100 × 808 frame | 36 px shorter if this is intended to be the same Activity Details panel. |
| `.cp-vd-split` | table min 460 px / 52%; Gantt min 320 px | 53.5% / 46.5%, with 4 px divider under `.cp-p6` | Demo split differs from approved frame. |
| `.cp-vd-timeline-lane` / track | 52 px / 52 px | Explicit user instruction: do not change Timeline size | Preserve current Timeline geometry; do not resize it as part of viewport fixes. |
| `.cp-vd-timeline-bar` | 16 px | Timeline must remain unchanged | No Timeline resize was made in the inspected 2026-11-02/03 commits. |
| `.cp-vd-network` | min-height 420 px; min-width 1080 px; scrollable | Network canvas must fit its own content without resizing global frame | Inner-canvas change only; review against screenshot before changing. |
| Generic demo dialogs | 560 px / 86vh; option dialogs 520 px | No universal dialog size was approved | Each dialog needs its own reference measurement; do not force one width on all. |

## 4. Protected sizing rules

1. Do not change Timeline lane, bar, phase-name column, milestone spacing or axis geometry as a side effect of viewport/responsive fixes.
2. Do not change the 1100 × 808 frame's title/menu/toolbar/layout/status heights or 63.58/36.42 and 53.5/46.5 ratios without new explicit instruction and screenshot evidence.
3. Assistant, tools drawer, popovers and dialogs must overlay/dock without reducing the fixed workspace area.
4. Do not solve clipping by shrinking row heights, Gantt bars, columns or Details panels. Use scrolling/overflow.
5. Project Details, Resource Details, Activity Details and other page-specific inspectors must be sized from their own page references; do not blindly reuse Activity Details height on all pages.
6. Dialogs and child windows require their own reference measurements; generic 520/560 px widths are fallbacks, not proof of parity.

## 5. Required verification before dimension changes

- Route-source audit confirms `/app?project=preview-rps-01` selects `.cp-vd` unless `view=live` is set. Browser confirmation at the deployed preview remains pending.
- Capture the same 1100 × 808 viewport and measure every fixed chrome band and each page's split panes.
- Compare against saved 2026-10-30 visual-reference screenshots and the 2026-11-01 1100 × 808 reference.
- Audit all 32 destinations and their dialogs individually; record width/height/min/max/overflow, reason for each fixed/minimum size and source screenshot.
- Only then reconcile duplicate `.cp-vd` and `.cp-p6` geometry. No Timeline dimensions are to be changed during this work.

## Status

This is a source/history sizing audit, not a completed runtime screenshot audit. Route source confirms the visual preview uses `.cp-vd`, so the compact 1100 × 808 `.cp-p6` geometry is not currently governing that route. This duplicate-root mismatch is confirmed in source. Runtime measurement of every page/dialog and final restoration/alignment of the visual-preview geometry remain pending.
