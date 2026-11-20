# V27 Visual Fidelity Matrix — Activities Workspace

- Tested head: `b71cd61f46ebe358d1b15eee21068977b03493cf`
- Viewports re-measured: 1280×720, 1366×768, 1920×1080 and 844×390 landscape phone
- Reference: structural/behavioral crosswalk. Vendor screenshots and figures are
  not stored or reproduced (copyright boundary in `docs/workspace/reference/v26-source-register.md` §5).
  Pixel-level parity with vendor captures is therefore **not claimed**.

Statuses: **مطابق و تأییدشده** · **پیاده‌سازی‌شده ولی آزمون‌نشده** · **ناقص** · **غایب** · **محدودیت مستند و مشخص**

## 1. Shell geometry and regions

| Surface | Expected region behavior | Measured result | Status |
|---|---|---|---|
| Application header | Product identity, project context, home, language, sign-out | Present in EN and FA; no vendor branding | **مطابق و تأییدشده** |
| Menu bar | Single row, access keys, localized labels | 8 menus, fits all tested widths | **مطابق و تأییدشده** |
| Toolbars | Horizontal command families with overflow control; window-aware enablement | 57 buttons, 53 distinct icons, overflow control visible at 1280 | **مطابق و تأییدشده** |
| Window tab strip | Project tab + window tabs, dirty marker, close control | Verified incl. reorder, reload restore, RTL at 1280 | **مطابق و تأییدشده** |
| Layout name / revision chip | Layout name and revision visible | `Classic Schedule Layout · rN` | **مطابق و تأییدشده** |
| Activity Grid | Top pane, header actions, table scroller | Table/Gantt split preserved; no document-level scroll | **مطابق و تأییدشده** |
| Gantt chart | Time-scaled pane, dependency links, data date | Rendered from stored schedule facts; synchronized scrolling | **مطابق و تأییدشده** |
| Activity Details | Bottom pane with 17 tabs | Fits inside 720px viewport; details bottom 660px at 1280×720 | **مطابق و تأییدشده** |
| Status bar | Localization, environment, signed-in user | Present, preview banner clearly states demo/non-production | **مطابق و تأییدشده** |
| Left / right rails | P6-style command rails | Present and responsive | **مطابق و تأییدشده** |

## 2. Responsive acceptance (V27)

| Scenario | Assertion | Result |
|---|---|---|
| 01 1280×720 | No vertical document scroller; workspace reachable | PASS |
| 02 1366×768 | Split geometry, details visible | PASS |
| 03 1920×1080 | No overflow, panes intact | PASS |
| 04 844×390 landscape | Workspace reachable through its own scroller | PASS |
| 05 Menus | Every menu inside viewport; Escape restores trigger | PASS |
| 06 Application keys | Ctrl+A works from body; text-field chords not stolen | PASS |
| 07 Full Screen | Native transition | Environment-limited in headless; see `deviation-register.md` D-V27-03 |
| 08 Table/Gantt splitter | Drag, clamp, persist, reset to 50% | PASS |
| 09 Details splitter | Pointer + keyboard, reset to 70 | PASS |
| 10 Persian RTL | Same geometry inside 1280×720 | PASS |
| 11 Integrity | No schedule write during responsive work | PASS |

Evidence: `docs/workspace/evidence/workspace-responsive-v26-2026-11-18/` (JSON + 10 screenshots),
`workspace-responsive-v26` 11/11 at `b71cd61f4`.

At 1280×720 the document scroll width equals 1280 in both LTR and RTL, proving the
previous 19px vertical overflow (R1) is closed.

## 3. Visual tokens and states

| Element | Visual rule | Evidence | Status |
|---|---|---|---|
| Themes | 6 named skins (Classic, Modern 3D, Graphite, Arctic, Copper, Midnight) | View menu; `capture-theme` evidence; shell tests | **پیاده‌سازی‌شده ولی آزمون‌نشده** per-theme screenshot grid |
| Critical path | Critical bars and rows use the critical color token | `activity-gantt-overlays-v26` | **مطابق و تأییدشده** |
| Progress | Progress fill proportional to stored percent | `activity-gantt-overlays-v26` | **مطابق و تأییدشده** |
| Completed | Completed activities render their stored 100% state | `activities-v26-scenarios` 18/18 | **مطابق و تأییدشده** |
| Milestones | Start/finish milestones use distinct bar shape | `activity-gantt-overlays-v26`, fixtures A155 | **مطابق و تأییدشده** |
| Summary bands | WBS summary bars span children | `activity-wbs-band-v26` | **مطابق و تأییدشده** |
| Dependency links | FS/SS/FF/SF arrows and labels | `activity-relationships-v26` | **مطابق و تأییدشده** |
| Data date | Vertical data-date line with label | `activity-gantt-overlays-v26` | **مطابق و تأییدشده** |
| Non-working time | Weekend and holiday shading incl. Jalali holiday | `calendars-jalali-v26`; visual cell shows 11 non-working columns, 1 holiday | **مطابق و تأییدشده** |
| Selection / focus | Row selection, roving focus, keyboard focus ring | `activity-grid-keyboard-v26`, `activity-multi-select-v26` | **مطابق و تأییدشده** |
| Disabled state | Disabled commands carry a localized reason | 10 toolbar buttons + menu matchers in reference state | **مطابق و تأییدشده** |
| Density | Table font and row-height controls persist | `activity-table-font-v26` | **مطابق و تأییدشده** |
| RTL mirroring | Labels, tab order, rails, tables mirror | `activity-details`, `activity-columns`, responsive 10 | **مطابق و تأییدشده** |
| Logo / branding | CUBI only; no vendor marks | Source review of shell | **مطابق و تأییدشده** |

## 4. Visual acceptance cells executed

`workspace-visual-acceptance-v26` captured 6 cells (EN/FA × 1280×720, 1366×768,
1920×1080) and wrote 24 screenshots plus the canonical visual set. Each cell
asserts: no document overflow, table/Gantt row alignment, no clipped labels,
non-working shading, dialog inside viewport, resize stability and window switch.
Result: **PASS 6 visual cells**, zero exceptions, zero 5xx.

Note: the suite recorded `testedCodeSha` as `f349d474` because it ran before the
V27 commit; the executable working tree was identical to `b71cd61f4` apart from
documentation/evidence files. The re-run suites at `b71cd61f4` are listed in
`test-coverage-matrix.md`.

## 5. Not claimed

- Pixel-for-pixel identity with vendor screenshots (no lawful screenshot set held).
- Vendor icon artwork; CUBI uses its own icon set (53 distinct toolbar icons).
- Exact vendor chrome spacing, fonts and gradients.
