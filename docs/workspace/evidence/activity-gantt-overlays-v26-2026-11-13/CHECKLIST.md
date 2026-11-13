# ACT-011 — Data Date and Gantt overlay acceptance (2026-11-13)

Contract: `cubi-activity-gantt-overlays-v26.v1`
Tested code: `10659a0281588f25a95ff50cd092a197c5e7d55b`
Suite: `apps/web/e2e/activity-gantt-overlays-v26.mjs`
Report: `activity-gantt-overlays-v26.json` (7/7 scenarios, 0 exceptions, 0 console errors, 0 failing API responses)
Screenshots: `01`–`07`

## Help topics

- [Customize the data date line](https://docs.oracle.com/cd/G48902_01/client_help/en_US/customize_the_data_date_line.htm) — View > Bars > Options > Data Date; style can be solid, dashed or dotted; thickness 1–10 px is a solid-line option and a non-solid style becomes solid when thickness exceeds 1; the colour comes from the palette.
- [Apply a Progress Line to the Gantt Chart](https://docs.oracle.com/cd/G48902_01/client_help/en_US/applying_a_progress_line_to_the_gantt_chart.htm) — a progress point line joins each activity's % complete or remaining duration; a point left of the Data Date is behind schedule, on the date is on schedule, and right of the date is ahead.
- [Progress Line tab - Bar Chart Options dialog box](https://docs.oracle.com/cd/G48902_01/client_help/en_US/progress_line_tab_-_bar_chart_options_dialog_box.htm) — the size (1–10), colour and basis of the progress line.

## Environment

- `python3 -m construction_pm.preview --web-root apps/web --host 127.0.0.1 --port 4201 --database /tmp/overlays-e2e.db --reset`
- Fixture: Riverside Pump Station Upgrade (`preview-rps-01`), revision 7, `schedule_options.data_date = "2026-10-12"`, 7 WBS bands and 14 activities.
- Viewports: en/LTR 1366×768 and 1920×1080, fa/RTL 1280×720; the Gantt is set to the Day timescale for exact positioning.

## Scenarios

| # | Proof | Result |
|---|---|---|
| 01 | Without any browser-local setup the status bar reads `Data Date: 2026-10-12`, the Activity Details General tab shows `DATA DATE 2026-10-12`, and the Gantt draws one `data-gantt-data-date="2026-10-12"` line labelled **Data Date**. On the Day timescale the line's 28.8 % position equals the position the drawn ticks assign to 12 Oct 2026 (28.8 %) within 0.6 %, the line is contained by the Gantt body and spans 208 px of it, its default colour is `#c00000`, and seven critical bars are drawn. | pass |
| 02 | The Bars dialog's Data Date fieldset is enabled, its note names the authoritative date, and enabling the progress point line draws 14 points against the same date: 4 behind, 0 on and 10 ahead; all 14 are classified, the stroke is 2 px `#ff8800`, and no schedule API request is issued. | pass |
| 03 | A dashed 4 px `#00aa55` Data Date line renders dashed at 1 px with the stored colour, matching the Help rule that non-solid styles stay 1 px; switching to solid 4 px `#112233` renders a 4 px solid line in that colour. | pass |
| 04 | Save Layout publishes `metadata.presentation.gantt.dataDateLine {visible:true, style:"solid", thickness:3, color:"#112233"}` and `progressLine {visible:true, thickness:2, color:"#ff8800"}` at revision 2. A full page reload without any browser-local hint restores the 3 px dark line and the 14-point progress line, still classified against 2026-10-12, with no schedule write. | pass |
| 05 | With no `p6_baseline` or `p6_baseline_activity` rows, the baseline bar editor explains that no baseline dates are loaded and zero baseline bars are drawn; nothing is synthesised. | pass |
| 06 | Persian RTL at 1280×720: `dir=rtl`, the line label is `تاریخ داده`, the position still equals 28.8 % for 12 Oct, the line stays inside the body, the 14-point progress line is present, and horizontal overflow is 0 px. | pass |
| 07 | English at 1920×1080 keeps the same line position and containment, the 14 points and seven critical bars, with 0 px overflow. | pass |

## Defects found and fixed in this slice

1. **The Data Date was hard-coded away in the browser.** `apps/web/src/main.ts` rendered `dataDate: "—"` in the status bar, passed `null` to the Gantt, `"—"` to Activity Details and `null` to the filter date context even though `GET /api/projects/{id}/p6/schedule/settings` already published `"2026-10-12"`. A new `loadActiveProjectDataDate` reads the existing `loadScheduleDataDate` transport adapter once per opened project, keeps the value keyed by project id (a failed or malformed read leaves it unset), and re-renders preserving drafts. All four consumers now receive the server value; the Bars dialog's Data Date fieldset, the rendered line and the `CD` filter token all become live from it.
2. **The progress line could not be read against the date.** `apps/web/src/workspace-view.ts` joined the saved progress points only. It now classifies every point through the new `progressPointRelation` helper in `apps/web/src/workspace-gantt.ts` (left = behind, within half a day = on, right = ahead) and exposes the counts and the date on the SVG; the Bars dialog note now states the P6 positional rule instead of claiming the model has no date.
3. **The Bars dialog note was stale.** It now prints the authoritative date it will use.

## Boundaries

- All overlay settings are presentation metadata: scenarios 02–04 assert that no non-GET `/api/projects/{project}/p6/schedule/…` or `/activities/…` request is made while enabling lines, changing styles or restoring them. The only write is the explicit Save Layout.
- The line derives its position from the same `createGanttScale` mapping as the axis ticks; the suite interpolates the expected position from the drawn ticks, so a different source date or a different scale would fail the comparison.
- Progress points use the persisted `percentComplete` of each bar; no progress value is inferred.

## Known limits

- The project has no baseline snapshot or baseline activity dates, so baseline bars cannot be drawn; the editor reports that state and the browser asserts zero baseline bars. Baseline projection is not part of this slice.
- The progress line is a single configured colour; P6's ahead/behind meaning is positional (scenario 02 records the classification) rather than colour-coded, and the dialog states that rule.
- A non-solid Data Date style stays 1 px; the dialog documents that, matching the Help text that thickness only applies to a solid line.
