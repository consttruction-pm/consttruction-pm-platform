# Engineering — Gantt Chart, Relationships, Trace Logic, Constraints and Calendars

Section 4 of the Help traceability workstream.
Verified: 2026-11-22 · Canonical rows: `docs/traceability/engineering-v26.json`
(`ENG-WS-GANTT`, `ENG-WS-GANTT-BARS`, `ENG-WS-RELATIONSHIPS`,
`ENG-WS-GANTT-RELATIONSHIPS`, `ENG-WS-TRACE-LOGIC`, `ENG-WS-CALENDARS`;
constraints have no canonical row and are recorded as
`ENG-WS-CONSTRAINTS`).
Help baseline: P6 Professional V26 HTML Help (`G48902-01`) and User Guide
(`G57529-01`). All 52 cited Help URLs returned HTTP 200 and are listed in the
official TOC with a matching title; all 33 cited User Guide URLs returned
HTTP 200 and are listed in the User Guide TOC with a matching title
(see `OFFICIAL_HELP_BASELINE.md` and
`evidence/section-04-gantt-relationships-calendars-links.json`, which records
`help_ok` 52/52, `user_guide_ok` 33/33, `failures` 0).

## 1. Scope

This section covers the Gantt chart and relationship surfaces of the
Activities window (`/app/activities/`), the Trace Logic bottom layout, the
activity constraint editor on the Activity Details Status tab, and the
Calendars window (`/app/calendars/`). It documents:

- Gantt display, layout, zoom, pan, timescale format, fit, row synchronization,
  bars, bar styles, labels, bar definitions, positions, filters, necking,
  relationship lines, drawing and editing links, the Data Date line, the
  progress line, sight lines, the legend and non-working shading.
- Relationship types, creation, change, removal, lag semantics, lag calendar,
  external relationships and revision-guarded writes.
- Trace Logic selection, navigation, depth preferences, cycles and missing
  references.
- Constraint types, entry, unsupported activity types and the scheduling-input
  boundary.
- Calendar pools, project/global/resource calendars, creation, editing,
  inheritance, workweek and shifts, month and exception editing, deletion,
  usage, Jalali presentation and revision-guarded writes.

It does **not** restate the activity table, columns, selection or exports
(Section 2), Activity Details tabs other than constraints (Section 3), or
resource and cost windows (Section 5). Row IDs reuse the canonical index where
one exists.

Status semantics:

- **Doc status** — `DOCUMENTED`, `HELP_VERIFIED`, `TEST_SPECIFIED`.
- **Product status** — the observed implementation state in this repository:
  `IMPLEMENTED`, `PARTIAL`, `NOT_IMPLEMENTED`. It is never derived from this
  document. `FUNCTIONALLY_VERIFIED` requires an executed run and is not
  claimed in this section.

`Env` is **Engineering** for every row. `Page` is `/app/activities/` for the
Gantt, relationship, Trace Logic and constraint rows, and `/app/calendars/`
for the calendar rows.

## 2. Traceability matrix

| Row ID | Page | Functional item | Help topic · section | Direct Help URL | User Guide · URL | Expected behavior (from Help) | Inputs and validation | Scenario | Doc status | Product status · evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ENG-WS-GANTT | `/app/activities/` | Gantt chart composition and synchronized table | The Gantt Chart · Customizing Activity Layouts > Gantt Chart | https://docs.oracle.com/cd/G48902_01/client_help/en_US/the_gantt_chart.htm | The Gantt Chart · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/theganttchart-19631a.html | Each activity's duration is a horizontal bar on the chosen timescale; a line connecting bars indicates a relationship; the chart is used with the Activity Table to view activities graphically and in table format, create relationships and track progress. | Bars are drawn only from authoritative start and finish values; row order follows the activity display list; the chart never calculates dates. | ENG-GANTT-01 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-view.test.ts` (interactive board, arrows, axis), `apps/web/src/workspace-gantt.test.ts` |
| ENG-WS-GANTT | `/app/activities/` | Show or hide the Gantt chart and choose the top layout | Display the Gantt Chart · Customizing Activity Layouts > Gantt Chart | https://docs.oracle.com/cd/G48902_01/client_help/en_US/display_the_gantt_chart.htm | Display the Gantt Chart · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/displaytheganttchart-19747a.html | With an activity window active, View > Show on Top or Show on Bottom > Gantt Chart displays it; dragging the split bar fully to the left hides the Activity Table and shows only the Gantt. | The toggle is presentation state; hiding the table or chart changes no schedule value and no selection. | ENG-GANTT-01 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/main.ts` (`view.top-table-gantt`, `view.toggle-gantt`), `apps/web/src/workspace-view.test.ts` |
| ENG-WS-GANTT | `/app/activities/` | Zoom the timescale in and out | Zoom in and out of a timescaled layout · Customizing Activity Layouts > Overview | https://docs.oracle.com/cd/G48902_01/client_help/en_US/zoom_in_and_out_of_a_timescaled_layout.htm | No verified direct section | Zooming in shows a shorter range with smaller intervals (quarter to month to week); zooming out shows a longer range with larger intervals; the top and bottom layouts zoom together. | Zoom changes only resolution and visible range; it never rounds, derives or shifts a schedule date. | ENG-GANTT-02 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · day/week/month/quarter/year scale buttons; `apps/web/src/workspace-gantt.test.ts`, `apps/web/src/workspace-view.test.ts` |
| ENG-WS-GANTT | `/app/activities/` | Pan the chart and change the displayed timeperiod | Move around a Gantt Chart · Customizing Activity Layouts > Gantt Chart | https://docs.oracle.com/cd/G48902_01/client_help/en_US/move_around_a_gantt_chart.htm | Move around a Gantt Chart · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/movearoundaganttchart-19753a.html | Dragging the major time unit moves backward or forward in time; the horizontal scroll bar also changes the displayed timeperiod; dragging the minor time unit expands or contracts the visible area. | Panning changes the visible window only; stored dates and zoom semantics are unchanged. | ENG-GANTT-03 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `PARTIAL` · horizontal scrolling is implemented; dragging the timescale to pan or expand is not · `apps/web/src/workspace-view.ts` |
| ENG-WS-GANTT | `/app/activities/` | Expand or contract the visible area | Expand or contract the visible area of a timescaled layout · Customizing Activity Layouts > Overview | https://docs.oracle.com/cd/G48902_01/client_help/en_US/expand_or_contract_the_visible_area_of_a_timescaled_layout.htm | No verified direct section | Dragging the minor time unit to the right expands the timescale and dragging it to the left contracts it. | The operation changes the visible span, not the data range or dates. | ENG-GANTT-03 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `NOT_IMPLEMENTED` · the chart width is fixed per scale (`GANTT_CONTENT_WIDTH`); no drag handle exists |
| ENG-WS-GANTT | `/app/activities/` | Timescale header format and date intervals | Change a layout's timescale format · Customizing Activity Layouts > Gantt Chart | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_layout_s_timescale_format_50.htm | Change a layout's timescale format · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/changealayoutstimescaleformat-19167a.html | The Timescale dialog selects two or three header lines, a start date, font and colour, primary date or ordinal numbering, the date interval type and format, and applies to every timescaled component in the layout. | Header intervals must be one of the documented combinations; ordinal numbering starts from the chosen start date; a font size outside the accepted range is rejected or clamped. | ENG-GANTT-04 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-dialogs.ts` (Timescale dialog), `apps/web/src/workspace-dialogs.test.ts`, `apps/web/src/workspace-gantt.test.ts` |
| ENG-WS-GANTT | `/app/activities/` | Fit the timeline to the pane | `NO DIRECT P6 HELP EQUIVALENT — CUBI-SPECIFIC REQUIREMENT` | — | — | The Help documents zoom levels but not a one-step "Fit" that chooses the finest scale whose whole timeline fits the visible pane. | A pane that has not been laid out keeps the documented month default; a pane narrower than the year width stays at year. | ENG-GANTT-02 | `DOCUMENTED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `fitGanttScale` in `apps/web/src/workspace-gantt.ts`, `apps/web/src/workspace-gantt.test.ts` |
| ENG-WS-GANTT-BARS | `/app/activities/` | Bar style: shape, colour, pattern, height, row and visibility | Change a Gantt Chart bar's style · Tracking Projects > Working with the Gantt Chart | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_gantt_chart_bars_style.htm | Change a Gantt Chart bar's style · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/changeaganttchartbarsstyle-19951a.html | The Bar Style tab changes the start endpoint, body height and position, finish endpoint, colour and pattern, the summary and collapsed visibility and the bar row. | Shape, colour and pattern values are from the documented lists; a height outside the accepted range is clamped; changing a style never changes a date. | ENG-GANTT-05 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-dialogs.ts` (Bar Styles), `apps/web/src/workspace-dialogs.test.ts`, `apps/web/src/workspace-view.test.ts` |
| ENG-WS-GANTT-BARS | `/app/activities/` | Bar labels and label position | Change a Gantt Chart bar's label · Tracking Projects > Working with the Gantt Chart | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_gantt_chart_bars_label.htm | Change a Gantt Chart bar's label · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/changeaganttchartbarslabel-19949a.html | Labels are added, deleted, and given a position and display value per bar; the chart draws the configured label. | Label position is one of the documented positions; changing a label changes presentation only. | ENG-GANTT-06 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · label field/position/font/colour; `apps/web/src/workspace-dialogs.ts`, `apps/web/src/workspace-view.test.ts` |
| ENG-WS-GANTT-BARS | `/app/activities/` | Labels reaching the plotted edge mirror to the left | Change a Gantt Chart bar's label · Tracking Projects > Working with the Gantt Chart | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_gantt_chart_bars_label.htm | Change a Gantt Chart bar's label · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/changeaganttchartbarslabel-19949a.html | Help documents the chosen label position; it does not describe clipping at the scrollable chart edge. CUBI mirrors a right-side label to the left when the bar finishes near the plotted edge, and moves it inside the finish edge when there is no room. | Mirroring applies only to outside labels (above, below, right); inside labels keep their position. | ENG-GANTT-06 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · documented divergence in §5; `resolveGanttLabelPosition`, `apps/web/src/workspace-gantt.test.ts` |
| ENG-WS-GANTT-BARS | `/app/activities/` | Add a bar definition | Add a bar to the Gantt Chart · Customizing Activity Layouts > Gantt Chart | https://docs.oracle.com/cd/G48902_01/client_help/en_US/add_a_bar_to_the_gantt_chart.htm | Add a bar to the Gantt Chart · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/addabartotheganttchart-19709a.html | Add creates a bar, marks Display, names it, selects its timescale and filter, then configures style, settings and labels; Default restores default bar settings. | A new bar needs a name, a timescale and a filter; the filter determines which activities it represents. | ENG-GANTT-07 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `NOT_IMPLEMENTED` · the bar set is the fixed seven documented kinds; no Add or Default control |
| ENG-WS-GANTT-BARS | `/app/activities/` | Change a bar definition and hide it | Change a bar in the Gantt Chart · Customizing Activity Layouts > Gantt Chart | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_bar_in_the_gantt_chart.htm | Change a bar in the Gantt Chart · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/changeabarintheganttchart-19723a.html | The Display checkbox shows or hides a bar; name, timescale and filter can be changed; style, settings and labels are reconfigured on their tabs. | Hiding a bar keeps its definition; it does not delete the activity or its dates. | ENG-GANTT-07 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · visibility, filter, style and labels per kind; `apps/web/src/workspace-dialogs.ts`, `apps/web/src/workspace-dialogs.test.ts` |
| ENG-WS-GANTT-BARS | `/app/activities/` | Delete a bar definition | Delete a bar from the Gantt Chart · Customizing Activity Layouts > Gantt Chart | https://docs.oracle.com/cd/G48902_01/client_help/en_US/delete_a_bar_from_the_gantt_chart_layout.htm | Delete a bar from the Gantt Chart · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/deleteabarfromtheganttchart-19741a.html | Delete removes the selected bar definition; clearing Display hides it without deleting it. | Deleting a bar never deletes activities; a hidden bar remains defined. | ENG-GANTT-07 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `NOT_IMPLEMENTED` · bar kinds are fixed; Display hides but no Delete exists |
| ENG-WS-GANTT-BARS | `/app/activities/` | Bar row position and stacking | Position a bar in the Gantt Chart · Customizing Activity Layouts > Gantt Chart | https://docs.oracle.com/cd/G48902_01/client_help/en_US/position_a_bar_in_the_gantt_chart.htm | Position a bar in the Gantt Chart · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/positionabarintheganttchart-19757a.html | Bars in the same row can stack or overlap; the row number determines where the bar is drawn relative to other bars. | Row is 1, 2 or 3; overlapping bars remain separate definitions and may hide one another visually. | ENG-GANTT-08 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · Row 1/2/3 per bar; `apps/web/src/workspace-dialogs.ts`, `apps/web/src/workspace-view.test.ts` |
| ENG-WS-GANTT-BARS | `/app/activities/` | Bar filter determines represented activities | Change a Gantt Chart bar's filter · Tracking Projects > Working with the Gantt Chart | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_gantt_chart_bars_filter.htm | Change a Gantt Chart bar's filter · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/changeaganttchartbarsfilter-19663a.html | The filter attached to a bar selects the activities it represents, so a critical bar can show only critical activities and a milestone bar only milestones. | Only activities matching the stored facts receive the bar; the filter changes drawing, not the activity record. | ENG-GANTT-08 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · bar kinds use task/critical/summary/milestone/all filters; `apps/web/src/workspace-view.ts`, `apps/web/src/workspace-view.test.ts` |
| ENG-WS-GANTT-BARS | `/app/activities/` | Bar settings, grouping and non-working necking | Change a Gantt Chart bar's settings · Tracking Projects > Working with the Gantt Chart | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_gantt_chart_bar_s_settings.htm | Change a Gantt Chart bar's settings · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/changeaganttchartbarssettings-19729a.html | Bar Settings selects grouping and necking options, including whether calendar non-work time necks the bar. | Necking is applied from the persisted calendar facts; without loaded calendar facts no divider is invented. | ENG-GANTT-09 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-dialogs.ts`, `apps/web/src/workspace-view.test.ts` |
| ENG-WS-GANTT-BARS | `/app/activities/` | Per-bar timescale | Change a Gantt Chart bar's timescale · Tracking Projects > Working with the Gantt Chart | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_gantt_chart_bars_timescale.htm | Change a Gantt Chart bar's timescale · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/changeaganttchartbarstimescale-19955a.html | A bar definition can be tied to its own timescale so different bars summarise different date ranges. | The per-bar timescale is a definition attribute; it never recalculates dates. | ENG-GANTT-09 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `NOT_IMPLEMENTED` · every bar uses the layout timescale; the bar editor has no timescale field |
| ENG-WS-GANTT-BARS | `/app/activities/` | Actual and baseline bar layers | Change a Gantt Chart bar's style · Tracking Projects > Working with the Gantt Chart | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_gantt_chart_bars_style.htm | Change a Gantt Chart bar's style · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/changeaganttchartbarsstyle-19951a.html | Actual bars draw from the stored actual dates and baseline bars from the stored baseline dates; each is its own bar definition with its own filter, row, shape and colour. | A layer draws only where the underlying stored dates exist; absence leaves the layer empty and is stated, never fabricated. | ENG-GANTT-17 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `GANTT_BAR_KINDS` and `presentationDataAvailability`; `apps/web/src/workspace-presentation.ts`, `apps/web/src/workspace-view.ts` |
| ENG-WS-GANTT-BARS | `/app/activities/` | Critical bar layer and its definition | Define critical activities · Managing Projects > Scheduling Projects | https://docs.oracle.com/cd/G48902_01/client_help/en_US/define_critical_activities.htm | No verified direct section | Activities are flagged critical at schedule time by the chosen method — Total Float less than or equal to a stated float, or Longest Path — and the critical bar filter draws exactly those flagged activities. | The chart draws the stored critical flag; it never derives criticality from the displayed bars. | ENG-GANTT-18 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `PARTIAL` · the critical bar and filter read the stored flag (`GANTT_BAR_FILTERS`, `PRIMARY_PRECEDENCE`); no schedule-option surface chooses Total Float versus Longest Path · `apps/web/src/workspace-presentation.ts`, `apps/web/src/workspace-view.ts` |
| ENG-WS-GANTT-RELATIONSHIPS | `/app/activities/` | Show or hide relationship lines | Show or hide relationship lines in the Gantt Chart · Customizing Activity Layouts > Gantt Chart | https://docs.oracle.com/cd/G48902_01/client_help/en_US/show_or_hide_relationship_lines_in_the_gantt_chart.htm | No verified direct section | The Show Relationships checkbox in Bar Chart Options > General displays or hides dependency lines; the Top Layout toolbar also toggles them. | The toggle changes drawing only; it never deletes a relationship. | ENG-GANTT-10 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · Layout Options and chart control; `apps/web/src/workspace-view.test.ts` |
| ENG-WS-GANTT-RELATIONSHIPS | `/app/activities/` | Relationship line edge semantics | View activity relationships in the Gantt Chart · Developing Projects > Viewing activity relationships | https://docs.oracle.com/cd/G48902_01/client_help/en_US/view_activity_relationships_in_the_gantt_chart.htm | View activity relationships in the Gantt Chart · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/viewactivityrelationshipsintheganttchart-19571a.html | A line begins and ends on specific bar edges: FS right-to-left, FF right-to-right, SF left-to-right and SS left-to-left; those edges identify the stored type. | The drawn edge must match the persisted type; the chart does not convert a type for display convenience. | ENG-GANTT-10 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `createGanttLinkGeometry` and `relationshipTypeFromEdges`; `apps/web/src/workspace-gantt.test.ts` |
| ENG-WS-GANTT-RELATIONSHIPS | `/app/activities/` | Draw a relationship on the chart | Create relationships in the Gantt Chart · Developing Projects > Linking Activities with Relationships | https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_relationships_in_the_gantt_chart.htm | No verified direct section | Dragging from a predecessor edge to a successor edge creates FS (finish to start), FF (finish to finish), SF (start to finish) or SS (start to start); a hint states the type before release. | Both endpoints must be activities, must differ, and must not create a duplicate or a cycle; comments can be added in the relationship tabs. | ENG-GANTT-11 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · drag preview and type hint; `apps/web/src/workspace-view.ts`, `apps/web/src/workspace-view.test.ts` |
| ENG-WS-GANTT-RELATIONSHIPS | `/app/activities/` | Edit a relationship from its line | Edit relationships in the Gantt Chart · Developing Projects > Linking Activities with Relationships | https://docs.oracle.com/cd/G48902_01/client_help/en_US/edit_relationships_in_the_gantt_chart.htm | No verified direct section | Double-clicking a relationship line opens its editor, where a different type and a new lag can be saved. | The edit keeps both endpoints unless changed, requires a current revision and rejects a self-link. | ENG-GANTT-12 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · relationship editor reachable from the link hit area and the register; `apps/web/src/main.ts`, `apps/web/src/workspace-view.test.ts` |
| ENG-WS-GANTT-RELATIONSHIPS | `/app/activities/` | Delete a relationship from its line | Delete relationships in the Gantt Chart · Developing Projects > Linking Activities with Relationships | https://docs.oracle.com/cd/G48902_01/client_help/en_US/delete_relationships_in_the_gantt_chart.htm | No verified direct section | Double-clicking the line and choosing Delete removes the relationship after confirmation. | Deletion removes only the link, not either activity; a stale revision is rejected. | ENG-GANTT-12 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · Delete in the relationship register with confirmation; `apps/web/src/main.ts` |
| ENG-WS-GANTT | `/app/activities/` | Data Date line style, thickness, colour and visibility | Customize the data date line · Customizing Activity Layouts > Gantt Chart | https://docs.oracle.com/cd/G48902_01/client_help/en_US/customize_the_data_date_line.htm | Customize the data date line · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/customizethedatadateline-20041a.html | The Data Date tab selects a solid, dashed or dotted style, a thickness from 1 to 10 and a colour; a non-solid style forced above 1 becomes solid. | The line is drawn only when an authoritative Data Date exists; thickness and colour are presentation values. | ENG-GANTT-13 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-dialogs.ts`, `apps/web/src/workspace-view.test.ts` |
| ENG-WS-GANTT | `/app/activities/` | Data Date meaning for progress | Using the data date · Managing Projects > Scheduling Projects | https://docs.oracle.com/cd/G48902_01/client_help/en_US/using_the_data_date.htm | No verified direct section | The Data Date is the last date progress was recorded; activities are scheduled from it; work on the Data Date itself is not included because it starts the period. | Progress points left of the date are behind, on the date are on schedule and right of it are ahead; the chart does not infer a Data Date. | ENG-GANTT-13 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `progressPointRelation`; `apps/web/src/workspace-gantt.test.ts` |
| ENG-WS-GANTT | `/app/activities/` | Progress line | Apply a Progress Line to the Gantt Chart · Customizing Activity Layouts > Gantt Chart | https://docs.oracle.com/cd/G48902_01/client_help/en_US/applying_a_progress_line_to_the_gantt_chart.htm | No verified direct section | The Progress Line tab controls whether the line is drawn as a variance line or a progress point line, and sets thickness and colour; in the Activities window it uses remaining duration or percent complete. | The line joins the persisted progress points of drawn activities; it never writes progress. | ENG-GANTT-14 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · progress point line; `apps/web/src/workspace-dialogs.ts`, `apps/web/src/workspace-view.test.ts` |
| ENG-WS-GANTT | `/app/activities/` | Background and sight lines | Change the background lines in the Gantt Chart · Customizing Activity Layouts > Gantt Chart | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_the_background_lines_in_the_gantt_chart.htm | Change the background lines in the Gantt Chart · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/changethebackgroundlinesintheganttchart-19739a.html | Sight Lines shows a major horizontal line before every summary, minor horizontal lines at a row interval and minor vertical lines at a time interval. | An interval of 0 turns that line family off; the lines are drawn behind bars and never alter them. | ENG-GANTT-15 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-dialogs.ts`, `apps/web/src/workspace-view.test.ts` |
| ENG-WS-GANTT | `/app/activities/` | Legend | Show or hide the Gantt Chart legend · Customizing Activity Layouts > Gantt Chart | https://docs.oracle.com/cd/G48902_01/client_help/en_US/show_or_hide_the_gantt_chart_legend.htm | Show or hide the Gantt Chart legend · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/showorhidetheganttchartlegend-19761a.html | The Show Legend checkbox displays or hides the legend, and the legend can be positioned; only bars currently shown appear in it. | The legend is presentation only and never changes bar visibility. | ENG-GANTT-15 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · legend position and visibility; `apps/web/src/workspace-dialogs.ts`, `apps/web/src/workspace-view.test.ts` |
| ENG-WS-GANTT | `/app/activities/` | Non-working shading from the project calendar | `NO DIRECT P6 HELP EQUIVALENT — CUBI-SPECIFIC REQUIREMENT` | — | — | Help defines non-working days in calendars but does not document a Gantt background shade for them. CUBI shades contiguous weekend and holiday bands from the selected project's persisted calendar snapshot, and overlays persisted exception dates projected by the Shared Calculation Core through `GET /api/projects/{id}/p6/calendars/{id}/{version}/day-facts` (`p6-calendar-day-facts.v1`). A nonwork or stored-holiday exception draws a holiday band; a total/detailed-work-hours exception removes the weekend band on that date. | Weekdays and holidays come only from the version-bound calendar snapshot; exception dates come only from that calendar's own plus inherited `calendar_exception` rows; an unreadable snapshot, an empty workweek or a failed day-facts projection produces no shading rather than shading the whole chart. | ENG-GANTT-16 | `DOCUMENTED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `createGanttNonWorkingBands` with `workingDates`/`nonWorkingDates`; `P6CalendarDayFactsAPI` (`src/construction_pm/p6_calendar_day_facts_api.py`); `apps/web/src/workspace-gantt.test.ts`, `apps/web/src/workspace-view.test.ts`, `tests/test_p6_calendar_day_facts_api.py`, `tests/test_project_lifecycle_http_routes.py`, `apps/web/e2e/gantt-calendar-exceptions-v26.mjs` |

### Relationship register (`/app/activities/`, logic panel)

| Row ID | Page | Functional item | Help topic · section | Direct Help URL | User Guide · URL | Expected behavior (from Help) | Inputs and validation | Scenario | Doc status | Product status · evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ENG-WS-RELATIONSHIPS | `/app/activities/` | The four relationship types | Relationships · Developing Projects > Linking Activities with Relationships | https://docs.oracle.com/cd/G48902_01/client_help/en_US/relationships.htm | Relationships · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/relationships-19487a.html | A relationship links another activity's start or finish to this activity's start or finish; the types are finish to start, finish to finish, start to start and start to finish; finish to start is the default. | Type is one of FS, SS, FF, SF; every relationship has a predecessor and a successor; an activity may have many relationships. | ENG-REL-01 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · type selector and stored type; `apps/web/src/workspace-view.test.ts`, `tests/test_relationship_master_repository.py` |
| ENG-WS-RELATIONSHIPS | `/app/activities/` | Add a relationship | Adding relationships between activities · Developing Projects > Linking Activities with Relationships | https://docs.oracle.com/cd/G48902_01/client_help/en_US/adding_relationships_between_activities.htm | Linking Activities with Relationships · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/linkingactivitieswithrelationships-20867a.html | Relationships can be drawn on the Gantt, or added from the Predecessors, Successors and Relationships tabs; relationship lines graphically illustrate links. | Both endpoints must exist in the loaded scope; a self-link, a duplicate and a cycle are rejected. | ENG-REL-01 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · register create form plus Gantt drawing; `apps/web/src/workspace-view.test.ts`, `tests/test_p6_relationship_api.py` |
| ENG-WS-RELATIONSHIPS | `/app/activities/` | Change a predecessor relationship | Change predecessor relationships · Developing Projects > Linking Activities with Relationships | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_predecessor_relationships.htm | No verified direct section | In the Predecessors or Relationships tab, a relationship's type and lag can be changed; a predecessor can also be assigned. | A changed type must be a documented type; lag keeps its unit; a stale record revision is rejected. | ENG-REL-02 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · edit form; `apps/web/src/workspace-view.test.ts`, `tests/test_p6_relationship_api.py` |
| ENG-WS-RELATIONSHIPS | `/app/activities/` | Change a successor relationship | Change successor relationships · Developing Projects > Linking Activities with Relationships | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_successor_relationships.htm | No verified direct section | The Successors or Relationships tab changes the successor relation's type and lag and can assign another successor. | Same type, lag-unit and revision rules as predecessors. | ENG-REL-02 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · the register is successor-agnostic; `apps/web/src/workspace-view.ts` |
| ENG-WS-RELATIONSHIPS | `/app/activities/` | Remove a predecessor relationship | Remove predecessor relationships · Developing Projects > Linking Activities with Relationships | https://docs.oracle.com/cd/G48902_01/client_help/en_US/remove_predecessor_relationships.htm | No verified direct section | Selecting a predecessor and choosing Remove, then Yes, deletes the relationship after optional Go To inspection. | Removal deletes only the link; a stale revision is rejected and the link remains. | ENG-REL-03 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · delete with confirmation; `apps/web/src/main.ts`, `tests/test_relationship_master_repository.py` |
| ENG-WS-RELATIONSHIPS | `/app/activities/` | Remove a successor relationship | Remove successor relationships · Developing Projects > Linking Activities with Relationships | https://docs.oracle.com/cd/G48902_01/client_help/en_US/remove_successor_relationships.htm | No verified direct section | The successor relationship is removed the same way, without deleting either activity. | Same revision and confirmation rules. | ENG-REL-03 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · same delete surface |
| ENG-WS-RELATIONSHIPS | `/app/activities/` | Calendar used for relationship lag | Choose a calendar for relationship lag · Managing Projects > Scheduling Projects | https://docs.oracle.com/cd/G48902_01/client_help/en_US/choose_a_calendar_for_relationship_lag.htm | No verified direct section | The scheduling options choose a calendar for relationship lag; a lag entered in a unit other than hours is converted using the predecessor activity's calendar. | The lag calendar is a scheduling input; changing it does not rewrite the stored lag value or unit. | ENG-REL-04 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `PARTIAL` · the stored assignment kind exists in the backend but no scheduling-option or per-relationship selector is exposed · `tests/test_calendar_master_repository.py` |
| ENG-WS-RELATIONSHIPS | `/app/activities/` | External relationships | Relationships · Developing Projects > Linking Activities with Relationships | https://docs.oracle.com/cd/G48902_01/client_help/en_US/relationships.htm | Relationships · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/relationships-19487a.html | A relationship between activities in different projects is an external relationship. | The successor or predecessor may live in another project when cross-project linking is enabled. | ENG-REL-04 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `NOT_IMPLEMENTED` · the create form offers only activities already loaded for the open project |
| ENG-WS-RELATIONSHIPS | `/app/activities/` | Revision-guarded relationship writes | `NO DIRECT P6 HELP EQUIVALENT — CUBI-SPECIFIC REQUIREMENT` | — | — | Help describes the relationship edit but not the CUBI optimistic-concurrency contract. CUBI sends the expected record revision and rejects a stale write, a cross-scope write and a duplicate or cycle. | A missing or stale revision, a self-link, a duplicate pair and a cycle each fail with a distinct error code and leave stored logic unchanged. | ENG-REL-05 | `DOCUMENTED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `REVISION_CONFLICT`, `SELF_RELATIONSHIP`, `RELATIONSHIP_CYCLE`; `tests/test_p6_relationship_api.py`, `tests/test_project_lifecycle_http_routes.py` |

### Trace Logic bottom layout (`/app/activities/`)

| Row ID | Page | Functional item | Help topic · section | Direct Help URL | User Guide · URL | Expected behavior (from Help) | Inputs and validation | Scenario | Doc status | Product status · evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ENG-WS-TRACE-LOGIC | `/app/activities/` | Trace Logic analysis of predecessors and successors | Trace Logic · Customizing Activity Layouts > Trace Logic | https://docs.oracle.com/cd/G48902_01/client_help/en_US/trace_logic.htm | Trace Logic · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/tracelogic-19645a.html | Trace Logic steps forward and backward through relationships for a selected activity; a red border marks a critical activity and a line connecting boxes marks a relationship; it is used to examine delays, obsolete constraints, wrong link types and negative float. | The chain uses the selected activity and the persisted relationships; criticality comes from the stored activity facts. | ENG-TRACE-01 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-trace-logic.ts`, `apps/web/src/workspace-trace-logic.test.ts` |
| ENG-WS-TRACE-LOGIC | `/app/activities/` | Display Trace Logic in the bottom layout | Display Trace Logic · Customizing Activity Layouts > Trace Logic | https://docs.oracle.com/cd/G48902_01/client_help/en_US/display_trace_logic.htm | Display Trace Logic · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/displaytracelogic-19643a.html | With the Activities window active, View > Show on Bottom > Trace Logic displays it; the bottom layout toolbar and Layout Options do the same. | Showing or hiding the view changes only the layout, not the selection or the schedule. | ENG-TRACE-02 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · bottom layout surface; `apps/web/src/workspace-view.test.ts` |
| ENG-WS-TRACE-LOGIC | `/app/activities/` | Move around Trace Logic by selecting activities | Move around in Trace Logic · Customizing Activity Layouts > Trace Logic | https://docs.oracle.com/cd/G48902_01/client_help/en_US/move_around_in_trace_logic.htm | Move around in Trace Logic · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/movearoundintracelogic-19835a.html | Clicking an activity in the Activity Table, Gantt, Activity Usage Spreadsheet, Activity Network or Trace Logic recentres the chain on that activity. | A clicked activity must be loaded; with no selection the view explains that a selection is required. | ENG-TRACE-02 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `data-trace-goto` navigation; `apps/web/src/workspace-trace-logic.test.ts` |
| ENG-WS-TRACE-LOGIC | `/app/activities/` | Predecessor and successor depth preferences | Set Trace Logic preferences · Customizing Activity Layouts > Trace Logic | https://docs.oracle.com/cd/G48902_01/client_help/en_US/set_trace_logic_preferences.htm | Set Trace Logic preferences · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/settracelogicpreferences-19837a.html | Bottom Layout Options sets the number of predecessors and the number of successors separately. | The two depths apply independently; an invalid stored value falls back to the default; Apply previews without closing. | ENG-TRACE-03 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · depths 1–5, default 2, per-direction keys and legacy key; `apps/web/src/workspace-trace-logic.test.ts` |
| ENG-WS-TRACE-LOGIC | `/app/activities/` | View relationships in Trace Logic | View activity relationships in Trace logic · Developing Projects > Viewing activity relationships | https://docs.oracle.com/cd/G48902_01/client_help/en_US/view_activity_relationships_in_trace_logic.htm | View activity relationships in Trace logic · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/viewactivityrelationshipsintracelogic-19573a.html | The selected activity appears with a blue border; predecessors are to its left and successors to its right, with the relation and lag on each row. | Only stored relationships are drawn; an endpoint that is not loaded is counted and omitted, and a cycle stops the branch with an explicit notice. | ENG-TRACE-04 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · left/right groups, cycle notice, missing-reference count; `apps/web/src/workspace-trace-logic.test.ts` |

### Activity constraints (Activity Details, `/app/activities/`)

| Row ID | Page | Functional item | Help topic · section | Direct Help URL | User Guide · URL | Expected behavior (from Help) | Inputs and validation | Scenario | Doc status | Product status · evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ENG-WS-CONSTRAINTS | `/app/activities/` | Constraint types | Types of constraints · Managing Projects > Scheduling Projects | https://docs.oracle.com/cd/G48902_01/client_help/en_US/types_of_constraints.htm | No verified direct section | Primary and secondary constraints model date dependence. Hard constraints (Mandatory Start, Mandatory Finish) prevent movement; soft constraints (Start On, Start On or Before, Start On or After, Finish On, Finish On or Before, Finish On or After) allow movement but can distort float. | Type is one of the documented constraint types; a constraint date is required for the date-bound types. | ENG-CON-01 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `PARTIAL` · six stored types: Start/Finish No Earlier/No Later Than and Mandatory Start/Finish; Start On, Finish On and As Late As Possible are absent · `apps/web/src/workspace-constraints.ts` |
| ENG-WS-CONSTRAINTS | `/app/activities/` | Enter and remove an activity constraint | Enter activity constraints · Managing Projects > Scheduling Projects | https://docs.oracle.com/cd/G48902_01/client_help/en_US/enter_activity_constraints.htm | No verified direct section | In Activity Details > Status, a Primary constraint type and date are selected, optionally with a Secondary type and date; the Secondary list is filtered by the Primary selection; constraints cannot be applied to Level of Effort or WBS Summary activities. | The activity must be selected; a type and date are required; a duplicate type and unsupported activity type are rejected; removal deletes only that constraint. | ENG-CON-01 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `PARTIAL` · add/remove uses one type plus date per row, not the Primary/Secondary field pair; `apps/web/src/workspace-constraints.test.ts`, `apps/web/src/workspace-activity-details.test.ts` |
| ENG-WS-CONSTRAINTS | `/app/activities/` | Reject constraints on derived activity types | Enter activity constraints · Managing Projects > Scheduling Projects | https://docs.oracle.com/cd/G48902_01/client_help/en_US/enter_activity_constraints.htm | No verified direct section | The constraint editor is not available for Level of Effort or WBS Summary activity types. | A write against an unsupported activity type is rejected and no constraint row is stored. | ENG-CON-02 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `CONSTRAINT_ACTIVITY_TYPE_UNSUPPORTED`; `tests/test_p6_constraint_api.py` |
| ENG-WS-CONSTRAINTS | `/app/activities/` | A constraint is a scheduling input, not a local calculation | `NO DIRECT P6 HELP EQUIVALENT — CUBI-SPECIFIC REQUIREMENT` | — | — | Help explains that constraints affect scheduling; CUBI additionally states that the pane persists the input and never derives early/late dates, float, criticality or feasibility. Stored dates change only after the shared scheduler publishes new results. | Saving or removing a constraint changes only the constraint record; no date, float or critical flag is recomputed in the browser. | ENG-CON-03 | `DOCUMENTED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-constraints.ts`, `apps/web/src/workspace-activity-details.ts` |

### Calendars window (`/app/calendars/`)

| Row ID | Page | Functional item | Help topic · section | Direct Help URL | User Guide · URL | Expected behavior (from Help) | Inputs and validation | Scenario | Doc status | Product status · evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ENG-WS-CALENDARS | `/app/calendars/` | Calendar pools and purpose | Calendars · Structuring Projects > Defining Calendars | https://docs.oracle.com/cd/G48902_01/client_help/en_US/calendars.htm | Calendars · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/calendars-18855a.html | Global, project and resource calendar pools exist. A calendar defines workhours per day, default hours per time period, holidays and non-working days; calendars drive scheduling, tracking and leveling; project and resource calendars can inherit from a global calendar. | Each calendar has a pool, a name and a definition; assigning a calendar never rewrites its definition. | ENG-CAL-01 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · register with `global`, `project` and `resource` types; `apps/web/src/workspace-view.test.ts`, `apps/web/src/workspace-calendars.test.ts` |
| ENG-WS-CALENDARS | `/app/calendars/` | Create a project calendar from a base | Create a project calendar · Structuring Projects > Defining Calendars > Project Calendars | https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_a_project_calendar.htm | Project Calendars · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/projectcalendars-20938a.html | The new calendar is created by selecting a calendar to copy, naming it and then modifying it. | A base calendar must be selected, a name is required, and the new reference must not already exist. | ENG-CAL-02 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · New dialog copies the base definition, work hours and exceptions; `apps/web/src/workspace-calendars.test.ts` |
| ENG-WS-CALENDARS | `/app/calendars/` | Edit workweek, non-work days, month and standard days | Edit a project calendar · Structuring Projects > Defining Calendars > Project Calendars | https://docs.oracle.com/cd/G48902_01/client_help/en_US/edit_a_project_calendar.htm | Edit a project calendar · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/editaprojectcalendar-20757a.html | The calendar month uses arrow buttons; clicking a date and Nonwork marks it non-working; clicking a date and choosing Total work hours/day or Detailed work hours/day sets the day's hours; Standard restores the default; Time Periods sets default hours per period. | Dates navigate real calendar months; a non-work mark needs no hours; detailed hours must not overlap and must be ordered; Standard applies the default hours for that weekday. | ENG-CAL-03 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · Month tab and Calendar Month grid; `apps/web/src/workspace-calendars.test.ts`, `apps/web/src/workspace-view.test.ts` |
| ENG-WS-CALENDARS | `/app/calendars/` | Workweek, working-day flags and split shifts | Edit a project calendar · Structuring Projects > Defining Calendars > Project Calendars | https://docs.oracle.com/cd/G48902_01/client_help/en_US/edit_a_project_calendar.htm | Edit a project calendar · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/editaprojectcalendar-20757a.html | Each weekday can be a working or non-working day and carries its working hours; detailed hours define which hours of the day are work. | A shift list must be ordered, non-overlapping and non-empty; an invalid shift is refused before any write; a working-day calendar stores one hours-per-day factor. | ENG-CAL-04 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · Workweek tab and `parseWorkdayShifts`; `apps/web/src/workspace-calendars.test.ts` |
| ENG-WS-CALENDARS | `/app/calendars/` | Calendar inheritance from a global calendar | Edit a project calendar · Structuring Projects > Defining Calendars > Project Calendars | https://docs.oracle.com/cd/G48902_01/client_help/en_US/edit_a_project_calendar.htm | Edit a project calendar · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/editaprojectcalendar-20757a.html | The Inherit Holidays and Exceptions from Global Calendar field bases the calendar on a global calendar, so later changes to that global calendar affect it. | The base must exist, have the same kind, and must not be the calendar itself or create an inheritance cycle. | ENG-CAL-03 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · set, preserve and clear base; `CALENDAR_BASE_SELF_REFERENCE`, `CALENDAR_BASE_CYCLE`, `BASE_CALENDAR_KIND_MISMATCH`; `tests/test_p6_calendar_api.py`, `apps/web/src/workspace-calendars.test.ts` |
| ENG-WS-CALENDARS | `/app/calendars/` | Delete a calendar | Delete a project calendar · Structuring Projects > Defining Calendars > Project Calendars | https://docs.oracle.com/cd/G48902_01/client_help/en_US/delete_a_project_calendar.htm | Delete a project calendar · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/deleteaprojectcalendar-20722a.html | Deleting removes the calendar after confirmation. | A stale revision is rejected; the delete removes the master, snapshot, work hours and exceptions together; a denied write changes nothing. | ENG-CAL-07 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `deleteCalendar` and backend cleanup; `apps/web/src/workspace-calendars.test.ts`, `tests/test_p6_calendar_api.py` |
| ENG-WS-CALENDARS | `/app/calendars/` | Global calendars | Global Calendars · Structuring Projects > Defining Calendars | https://docs.oracle.com/cd/G48902_01/client_help/en_US/globalcalendars.htm | Global Calendars · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/globalcalendars-20816a.html | Global calendars apply to all projects and can be inherited by project and resource calendars; they are created, edited and deleted in the global pool. | A global calendar follows the same definition, inheritance and revision rules as a project calendar. | ENG-CAL-07 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `global` type in the same register; `apps/web/src/workspace-calendars.ts` |
| ENG-WS-CALENDARS | `/app/calendars/` | Resource calendars | Resource Calendars · Structuring Projects > Defining Calendars | https://docs.oracle.com/cd/G48902_01/client_help/en_US/resourcecalendars.htm | No verified direct section | Resource calendars form a separate pool; shared and personal resource calendars exist and can be assigned to resources. | Resource calendar definitions obey the same work-time and revision rules; assigning one does not modify the resource record here. | ENG-CAL-07 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `PARTIAL` · `resource` calendars can be created and read; there is no resource-master or personal/shared conversion surface · `apps/web/src/workspace-calendars.ts` |
| ENG-WS-CALENDARS | `/app/calendars/` | Default hours per time period | Defining default hours per time period in calendars · Structuring Projects > Defining Calendars | https://docs.oracle.com/cd/G48902_01/client_help/en_US/defining_default_hours_per_time_period_in_calendars.htm | Defining default hours per time period in calendars · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/definingdefaulthourspertimeperiodincalendars-20063a.html | Hours per day, week, month and year are conversion factors used to display units and durations in other time increments and to store them in hours. | The values come from the calendar definition; they are not derived from a schedule date or from the workweek in this window. | ENG-CAL-08 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `PARTIAL` · factors are displayed read-only on the General tab; no editor |
| ENG-WS-CALENDARS | `/app/calendars/` | Assign a calendar to an activity | Assign a calendar to an activity · Developing Projects > Adding Activities to a Project | https://docs.oracle.com/cd/G48902_01/client_help/en_US/assign_a_calendar_to_an_activity.htm | Assign a calendar to an activity · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/assignacalendartoanactivity-19503a.html | The Activity Calendar field on Activity Details > General selects the calendar used by the activity. | The calendar must exist in the project or global pool; assigning it changes the activity input, not the calendar definition. | ENG-CAL-08 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `PARTIAL` · the field is displayed read-only from the activity record; no assignment dialog · `apps/web/src/workspace-activity-details.ts` |
| ENG-WS-CALENDARS | `/app/calendars/` | Project default activity calendar | Set the project default activity calendar · Working with the EPS | https://docs.oracle.com/cd/G48902_01/client_help/en_US/set_the_project_default_activity_calendar.htm | No verified direct section | The project Defaults tab selects the calendar used for new activities; changing it does not affect existing activities. | The default is used only for new activities and must reference a stored calendar. | ENG-CAL-08 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `PARTIAL` · project settings store `primary_calendar_id`, but the activity create request carries no calendar, so new activities are not proven to inherit it · `apps/web/src/main.ts` |
| ENG-WS-CALENDARS | `/app/calendars/` | View project calendar assignments (Used By) | View project calendar assignments · Structuring Projects > Defining Calendars > Project Calendars | https://docs.oracle.com/cd/G48902_01/client_help/en_US/view_project_calendar_assignments.htm | View project calendar assignments · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/viewprojectcalendarassignments-21132a.html | Used By lists the activities and other records that reference the selected project calendar. | The list must reflect stored references only; a versioned reference matches the exact calendar version. | ENG-CAL-05 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · Used By tab with counts and details; `apps/web/src/workspace-calendars.test.ts` |
| ENG-WS-CALENDARS | `/app/calendars/` | View resource calendar assignments (Used By) | View resource calendar assignments · Structuring Projects > Defining Calendars | https://docs.oracle.com/cd/G48902_01/client_help/en_US/view_resource_calendar_assignments.htm | View resource calendar assignments · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/viewresourcecalendarassignments-21133a.html | Used By also reports resource masters and resource assignments that reference the calendar. | A resource master stores an id without a version and is matched by id; a resource assignment stores id and version and is matched exactly. | ENG-CAL-05 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · usage kinds include `resource_calendar_assignment` and `resource_assignment_calendar`; `tests/test_calendar_usage_api.py` |
| ENG-WS-CALENDARS | `/app/calendars/` | Calendar exceptions and holidays | Edit a project calendar · Structuring Projects > Defining Calendars > Project Calendars | https://docs.oracle.com/cd/G48902_01/client_help/en_US/edit_a_project_calendar.htm | Edit a project calendar · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/editaprojectcalendar-20757a.html | Exceptions mark a date non-working, give it total work hours or detailed work hours, or reset it to standard; they can be added, changed and removed. Persisted rows (including inherited ones) are projected into the Activities Gantt non-working bands through the Shared Core day-facts endpoint. | Date must be a real calendar date; total hours must be a non-negative number; detailed hours need a start before the finish; editing raises the exception revision and a stale edit is rejected; only local and inherited exceptions of the exact calendar version affect that calendar's projection. | ENG-CAL-06 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · four modes; one detailed interval per exception is a documented divergence · `apps/web/src/workspace-calendars.test.ts`, `tests/test_p6_calendar_api.py`, `tests/test_p6_calendar_day_facts_api.py` |
| ENG-WS-CALENDARS | `/app/calendars/` | Jalali calendar display and entry | `NO DIRECT P6 HELP EQUIVALENT — CUBI-SPECIFIC REQUIREMENT` | — | — | Help documents the calendar month and exception dialog but not a Jalali display calendar. CUBI stores every date as canonical ISO Gregorian and presents Jalali values for entry and display when the calendar system is Jalali. | A Jalali date entry must parse to a real day; conversion must not shift the stored day across a UTC boundary; the stored record keeps the canonical Gregorian date. | ENG-CAL-06 | `DOCUMENTED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `workspace-calendar-display.ts`, `workspace-jalali-entry.ts`, `apps/web/src/workspace-calendars.test.ts` |
| ENG-WS-CALENDARS | `/app/calendars/` | Revision-guarded calendar writes | `NO DIRECT P6 HELP EQUIVALENT — CUBI-SPECIFIC REQUIREMENT` | — | — | Help describes the calendar dialog but not the CUBI optimistic-concurrency contract. CUBI sends the expected record revision on update and delete and rejects a stale write; work-hour and exception edits use their stored revisions. | A missing or stale revision fails with a conflict code, the dialog reports the failure and the stored record is unchanged. | ENG-CAL-07 | `DOCUMENTED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `REVISION_CONFLICT`, `EXCEPTION_REVISION_CONFLICT`, `expected_revision`; `apps/web/src/workspace-calendars.test.ts`, `tests/test_p6_calendar_api.py` |

## 3. Page specifications

### Activities window — Gantt chart (`/app/activities/`)

- **Purpose** — draw the persisted schedule as bars and dependency lines beside the activity table, so plan logic and progress can be inspected without recalculating anything.
- **Entry conditions** — an authenticated project session with at least one activity loaded; the Gantt panel visible in the top layout.
- **Permissions** — every project role may read; relationship and date-affecting actions are limited to the write-capable roles enforced by the API (`planner`, `project_admin`).
- **Structure** — chart toolbar (scale Day/Week/Month/Quarter/Year, dependency-line toggle, Fit), timescale axis, bar rows synchronized one-to-one with the table display rows, link SVG layer, progress layer, Data Date line, non-working band layer.
- **Fields** — none are edited on the chart itself; bar and layout options are edited in the Timescale, Bar Styles and Layout Options dialogs.
- **Commands** — show/hide Gantt; toggle dependency lines; pick scale; Fit; drag from a bar edge to create a relationship; open the relationship editor from a line; open Layout Options, Timescale and Bar Styles.
- **Filters** — each bar kind carries a filter (task, critical, summary, milestone, all); the activity table filter also removes rows and their bars.
- **Sorting / grouping** — row order is the table order, including grouping bands; Gantt rows use the same pitch and WBS band height.
- **Search** — inherited from the activity table; a filtered-out activity draws no bar and any relationship touching it is omitted.
- **Dialogs** — Layout Options (scale, relationship lines, progress line, Data Date line, baseline), Timescale (header lines, interval, primary/ordinal dates, week-of-year, fonts and colours), Bar Styles (per-kind style, filter, row, label, necking, chart options).
- **Validation** — bar height, font size and thickness are bounded; a colour must be a valid hex value; an interval/font/line value outside the accepted range is clamped or rejected.
- **Save / cancel** — dialog Apply previews, OK commits the saved presentation; Cancel leaves the stored layout unchanged. No schedule date is written from the Gantt.
- **Dependencies** — the authoritative activity read model, relationship read model, project calendar snapshot and its day-facts projection (`p6-calendar-day-facts.v1`, which folds in local and inherited `calendar_exception` rows), Data Date, saved layout presentation.
- **Expected results** — bars and links appear at the dates and edges of the stored facts; hiding a layer or changing a style leaves those facts intact.
- **Error scenarios** — missing dates produce no bar; missing calendar facts or a failed day-facts projection produce no shading; a relationship write can return a conflict, cycle or scope error, shown in the relationship notice.
- **Help references** — rows above under `ENG-WS-GANTT` and `ENG-WS-GANTT-BARS`.
- **Acceptance criteria** — `ENG-GANTT-01` … `ENG-GANTT-18`.

### Activities window — Trace Logic (`/app/activities/`)

- **Purpose** — show the predecessor and successor chain of the selected activity as a navigable projection of stored logic.
- **Entry conditions** — an activity is selected and the bottom layout is Trace Logic.
- **Permissions** — all project roles may read.
- **Structure** — heading, selected activity, independent predecessor and successor depth selectors, predecessor group, successor group, notices.
- **Fields** — depth 1–5 per direction; the default is 2; a legacy single-depth value is honoured until either direction is changed.
- **Commands** — select an activity; click a row to navigate; change either depth.
- **Filters** — none.
- **Sorting / grouping** — level order, then stored relationship order; predecessors and successors are separate groups.
- **Search** — not applicable.
- **Dialogs** — none; depth preference is stored per user (`cubi:workspace:trace-logic-predecessor-depth`, `…-successor-depth`, legacy `cubi:workspace:trace-logic-depth`).
- **Validation** — depth is clamped to 1–5; a corrupt stored value falls back to 2.
- **Save / cancel** — depth changes persist immediately; there is no cancel.
- **Dependencies** — loaded activities and relationships; no scheduling service is called.
- **Expected results** — direct neighbours at level 1, deeper levels up to the chosen depth; each row shows type and signed lag; a repeated ancestor stops the branch with a cycle notice; missing endpoints are counted and omitted.
- **Error scenarios** — no selection shows an instruction; no relationships within depth shows an empty explanation; a cycle or missing endpoint is reported, never invented as a row.
- **Help references** — `trace_logic.htm`, `display_trace_logic.htm`, `move_around_in_trace_logic.htm`, `set_trace_logic_preferences.htm`, `view_activity_relationships_in_trace_logic.htm`.
- **Acceptance criteria** — `ENG-TRACE-01` … `ENG-TRACE-04`.

### Activities window — Relationships editor (`/app/activities/`)

- **Purpose** — create, change and remove the project logic that the Gantt draws and the scheduler reads.
- **Entry conditions** — at least two activities loaded.
- **Permissions** — read for all project roles; create/change/remove for write-capable roles.
- **Structure** — relationship list (predecessor → successor, type, lag, Delete, Edit disclosure) and a create form.
- **Fields** — predecessor, successor, type (FS/SS/FF/SF), lag value (signed decimal), lag unit (working-day, working-hour).
- **Commands** — create, edit, delete.
- **Filters** — none in the editor.
- **Sorting / grouping** — stored list order.
- **Search** — not applicable.
- **Dialogs** — inline create and edit forms.
- **Validation** — endpoints must differ; type must be one of the four; lag must be a signed decimal; unit must be day or hour; duplicate, self-link and cycle are rejected; a stale revision conflicts.
- **Save / cancel** — submit writes through the relationship API and reloads the workspace; collapsing the edit form cancels.
- **Dependencies** — relationship API and the loaded activity list.
- **Expected results** — the new or changed link appears in the list, the Gantt and Trace Logic after reload.
- **Error scenarios** — `SELF_RELATIONSHIP`, `RELATIONSHIP_CYCLE`, `REVISION_CONFLICT`, `CROSS_SCOPE_ACCESS`, missing endpoints.
- **Help references** — rows above under `ENG-WS-RELATIONSHIPS`.
- **Acceptance criteria** — `ENG-REL-01` … `ENG-REL-05`.

### Activity Details — Constraints (`/app/activities/`)

- **Purpose** — record date constraints as scheduling inputs without deriving dates locally.
- **Entry conditions** — an activity selected; Status tab open.
- **Permissions** — read for all project roles; add/remove for `planner` and `project_admin`.
- **Structure** — Constraints section with stored type/date/revision rows and an add form (type, date).
- **Fields** — constraint type, constraint date.
- **Commands** — add, remove.
- **Validation** — type must be a stored type; date must be ISO; duplicate type, unsupported activity type and stale revision are rejected.
- **Save / cancel** — write through the constraint API; the pane reloads the authoritative list.
- **Dependencies** — constraint API and scheduling core.
- **Expected results** — the constraint is stored and shown with its revision; no date or float changes in the pane.
- **Error scenarios** — `INVALID_CONSTRAINT_TYPE`, `INVALID_CONSTRAINT_DATE`, `DUPLICATE_CONSTRAINT_TYPE`, `CONSTRAINT_ACTIVITY_TYPE_UNSUPPORTED`, `REVISION_CONFLICT`.
- **Help references** — `types_of_constraints.htm`, `enter_activity_constraints.htm`.
- **Acceptance criteria** — `ENG-CON-01` … `ENG-CON-03`.

### Calendars window (`/app/calendars/`)

- **Purpose** — maintain the calendar definitions that schedule, track and level the project.
- **Entry conditions** — authenticated project with a calendar catalogue (or an explicit empty state).
- **Permissions** — read for all project roles; create, edit, copy and delete are API-authorized writes.
- **Structure** — toolbar (New, Copy, Delete, Refresh), Available Calendars register, Calendar Details with General, Workweek, Calendar Month, Exceptions and Used By tabs.
- **Fields** — General: name, type (`global`/`project`/`resource`), base calendar, read-only id/version/kind/revision/system and hours-per-period factors. Workweek: weekday working flag, hours, split shifts. Month: date selection, Nonwork, Standard, month navigation, weekday-heading apply. Exceptions: date, mode, total hours or start/finish. Used By: read-only references.
- **Commands** — select, New (from base), Copy, Delete, Refresh, Edit/Save/Cancel, Save day, month navigation, Nonwork/Standard, add/edit/remove exception.
- **Filters** — none; the register lists the project calendar catalogue.
- **Sorting / grouping** — catalogue order from the read model; weekday order Monday–Sunday.
- **Search** — not applicable.
- **Dialogs** — New calendar (base, id, version, name, type, date system), Copy (target id/version), Delete confirmation.
- **Validation** — id/version/name/base required; type one of the three; kind `working-day` or `working-time`; base must exist, match kind and not self or cycle; shift lists ordered and non-overlapping; exception date/mode/hours valid; revision required on write.
- **Save / cancel** — edit buffers General fields until Save; Cancel restores; workweek and exception writes persist immediately and reload their lists; delete removes children in one transaction.
- **Dependencies** — calendar API, calendar snapshot, work-hours read, exceptions read, usage read, Jalali conversion for display.
- **Expected results** — saved values appear in the authoritative lists; schedules that depend on the calendar become stale until the scheduler runs again.
- **Error scenarios** — `CALENDAR_NAME_REQUIRED`, `INVALID_CALENDAR_TYPE`, `CALENDAR_REFERENCE_REQUIRED`, `CALENDAR_BASE_REQUIRED`, `CALENDAR_TARGET_ALREADY_SELECTED`, `CALENDAR_BASE_SELF_REFERENCE`, `CALENDAR_BASE_CYCLE`, `CALENDAR_SNAPSHOT_KIND_CONFLICT`, `REVISION_CONFLICT`, `CALENDAR_EXCEPTION_INVALID`, `EXCEPTION_REVISION_CONFLICT`, `INVALID_EXCEPTION_DATE`, `WEEKDAY_REQUIRED`.
- **Help references** — rows above under `ENG-WS-CALENDARS`.
- **Acceptance criteria** — `ENG-CAL-01` … `ENG-CAL-08`.

## 4. Acceptance scenarios

### Gantt chart

#### ENG-GANTT-01 — Gantt composition, layout toggle and synchronized rows

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Gantt chart and activity table |
| Feature | Display the Gantt, choose the top layout, hide the table, keep rows synchronized |
| Preconditions | Planner session; project `PRJ-1` with activities `A100` (2026-01-05 → 2026-01-12) and `A110` (2026-01-13 → 2026-01-20) and no relationships |
| Test data | Gantt visible; top layout `table-gantt`; then `table-only` |
| User action | Open Activities → confirm two bars aligned with two table rows → switch to Gantt-only → switch back |
| Expected result | Each bar starts and ends at its stored date; one Gantt row per display row; hiding the table leaves the same bars and selection; no date changes |
| Negative scenario | With no scheduled activities, the chart shows an explicit "no scheduled activities" state and no invented bars |
| Permission scenario | Viewer sees the same chart and can toggle presentation |
| Persistence scenario | Reload keeps the chosen layout; dates remain identical |
| Related Help | The Gantt Chart — https://docs.oracle.com/cd/G48902_01/client_help/en_US/the_gantt_chart.htm; Display the Gantt Chart — https://docs.oracle.com/cd/G48902_01/client_help/en_US/display_the_gantt_chart.htm |

#### ENG-GANTT-02 — Zoom levels and Fit

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Gantt toolbar and Layout Options |
| Feature | Day/Week/Month/Quarter/Year scale and Fit |
| Preconditions | Activities spanning 2025-01-01 to 2027-12-31 |
| Test data | Scale sequence day → week → month → quarter → year; pane width 900 px |
| User action | Click each scale; then click Fit |
| Expected result | The axis ticks change from daily to yearly; the same date range stays visible; Fit selects the finest scale whose full width fits (month at 900 px) |
| Negative scenario | An unknown scale value is ignored; a zero-width pane keeps month |
| Permission scenario | Viewer may change scale |
| Persistence scenario | The selected scale survives reload; Fit does not change stored dates |
| Related Help | Zoom in and out of a timescaled layout — https://docs.oracle.com/cd/G48902_01/client_help/en_US/zoom_in_and_out_of_a_timescaled_layout.htm |

#### ENG-GANTT-03 — Panning and the timescale drag gap

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Gantt chart |
| Feature | Horizontal scroll and documented timescale drag |
| Preconditions | Timeline wider than the pane |
| Test data | Scroll to the right by 400 px |
| User action | Use the horizontal scroll bar; then attempt to drag the major and minor timescale |
| Expected result | Scrolling changes the visible timeperiod and keeps bar positions correct; dragging the timescale is not implemented (documented gap) |
| Negative scenario | Scroll to an empty period shows the axis and no bars, not a fabricated range |
| Permission scenario | Viewer may scroll |
| Persistence scenario | Scrolling does not persist a new data range; reload returns to the saved view |
| Related Help | Move around a Gantt Chart — https://docs.oracle.com/cd/G48902_01/client_help/en_US/move_around_a_gantt_chart.htm |

#### ENG-GANTT-04 — Timescale header format

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Timescale dialog |
| Feature | Header lines, date interval, primary/ordinal dates, week-of-year, font and colour |
| Preconditions | Saved layout with default timescale |
| Test data | 3 lines; interval `week-day`; ordinal format; ordinal start `2026-01-05`; ordinal interval `day`; font size 13; colours `#102030` / `#e0e6ee` |
| User action | Open Timescale → set values → OK → reload |
| Expected result | Three header lines appear; ticks use ordinal numbers from the chosen start; the week-of-year type shows ISO week labels; fonts and colours persist |
| Negative scenario | Font size 99 is clamped; an invalid colour is rejected or falls back |
| Permission scenario | Viewer may change layout presentation |
| Persistence scenario | The header format survives reload and does not reset the toolbar zoom |
| Related Help | Change a layout's timescale format — https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_layout_s_timescale_format_50.htm |

#### ENG-GANTT-05 — Bars and milestones from authoritative dates

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Gantt chart |
| Feature | Bar geometry, zero-duration milestone, missing dates |
| Preconditions | Activities with dates, one with identical start/finish, one without dates |
| Test data | `A100` 2026-01-05 → 2026-01-12; `M100` 2026-01-10 → 2026-01-10; `A120` no dates |
| User action | Render the chart |
| Expected result | `A100` bar spans its dates; `M100` is a point milestone; `A120` has no bar; progress fill matches stored percent; critical bars use the critical style |
| Negative scenario | An unparseable date produces no geometry instead of a bar at zero |
| Permission scenario | Viewer sees the same geometry |
| Persistence scenario | Reload produces identical geometry |
| Related Help | The Gantt Chart — https://docs.oracle.com/cd/G48902_01/client_help/en_US/the_gantt_chart.htm |

#### ENG-GANTT-06 — Bar styles and labels

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Bar Styles dialog |
| Feature | Shape, colour, pattern, height, row, visibility, label and label position |
| Preconditions | Task and critical bars visible |
| Test data | Task body `#00aa00`, pattern dotted, height 12, row 1; label `finish-id-name`, position right, font 12, colour `#112233` |
| User action | Change each value → Apply → OK → reload |
| Expected result | Only the task bar changes; dates and progress are unchanged; the label draws at the chosen side; a bar finishing near the right edge mirrors its label to the left |
| Negative scenario | Height 0 is clamped to the minimum; an invalid colour is rejected |
| Permission scenario | Viewer may change style without changing data |
| Persistence scenario | Style and label settings survive reload |
| Related Help | Change a Gantt Chart bar's style — https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_gantt_chart_bars_style.htm; label — https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_gantt_chart_bars_label.htm |

#### ENG-GANTT-07 — Change, hide, filter and position bars; add/delete gap

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Bar Styles dialog |
| Feature | Display checkbox, filter, row, and missing Add/Delete definitions |
| Preconditions | Project with unscheduled, milestone and critical activities |
| Test data | Set milestone bar filter `milestone`, row 2; clear the actual bar Display; attempt Add and Delete |
| User action | Apply the changes; look for Add/Delete |
| Expected result | Only milestones receive the milestone bar; the actual bar disappears; no Add or Delete control exists (documented gap); no activity is deleted |
| Negative scenario | Hiding every bar leaves the chart empty but the table and data intact |
| Permission scenario | Viewer may hide bars |
| Persistence scenario | Hidden/filtered bars stay so after reload |
| Related Help | Change a bar in the Gantt Chart — https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_bar_in_the_gantt_chart.htm; Add a bar — https://docs.oracle.com/cd/G48902_01/client_help/en_US/add_a_bar_to_the_gantt_chart.htm |

#### ENG-GANTT-08 — Bar row stacking and necking

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Bar Styles dialog and chart |
| Feature | Row 1/2/3 and calendar non-work necking |
| Preconditions | Project calendar with Saturday/Sunday non-working; task and actual bars |
| Test data | Task row 1; actual row 2; necking on for task |
| User action | Apply and inspect a bar spanning a weekend |
| Expected result | Bars occupy separate vertical rows; black dividers mark calendar non-working boundaries on the necked bar; no divider appears without calendar facts |
| Negative scenario | Row value outside 1–3 is rejected or clamped |
| Permission scenario | Viewer may change presentation |
| Persistence scenario | Row and necking settings survive reload |
| Related Help | Position a bar in the Gantt Chart — https://docs.oracle.com/cd/G48902_01/client_help/en_US/position_a_bar_in_the_gantt_chart.htm; Change a Gantt Chart bar's settings — https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_gantt_chart_bar_s_settings.htm |

#### ENG-GANTT-09 — Per-bar timescale gap

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Bar Styles dialog |
| Feature | Per-bar timescale |
| Preconditions | Layout timescale week |
| Test data | Look for a Timescale field in each bar editor |
| User action | Inspect the bar editor |
| Expected result | No per-bar timescale field exists; every bar uses the layout timescale (documented gap) |
| Negative scenario | Changing the layout timescale changes all bars together |
| Permission scenario | Not applicable |
| Persistence scenario | The gap is stable across reload |
| Related Help | Change a Gantt Chart bar's timescale — https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_gantt_chart_bars_timescale.htm |

#### ENG-GANTT-10 — Relationship lines toggle and edge semantics

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Gantt chart |
| Feature | Dependency-line visibility and edge-to-type mapping |
| Preconditions | `A100` → `A110` FS; `A120` → `A130` SS; `A140` → `A150` FF; `A160` → `A170` SF |
| Test data | Toggle lines off, then on |
| User action | Inspect each line endpoint |
| Expected result | Lines appear only when enabled; FS leaves the predecessor's right edge and enters the successor's left; SS left-to-left; FF right-to-right; SF left-to-right; critical links use the critical arrow |
| Negative scenario | A relationship whose endpoint is filtered out draws no line and no placeholder |
| Permission scenario | Viewer may toggle lines |
| Persistence scenario | The toggle survives reload and never deletes a relationship |
| Related Help | Show or hide relationship lines — https://docs.oracle.com/cd/G48902_01/client_help/en_US/show_or_hide_relationship_lines_in_the_gantt_chart.htm; View activity relationships in the Gantt Chart — https://docs.oracle.com/cd/G48902_01/client_help/en_US/view_activity_relationships_in_the_gantt_chart.htm |

#### ENG-GANTT-11 — Draw a relationship

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Gantt chart |
| Feature | Drag-to-link with type hint |
| Preconditions | Planner; two unrelated activities `A100`, `A110` |
| Test data | Draw finish→start; draw start→start |
| User action | Drag from the predecessor edge to the successor edge; release |
| Expected result | A hint names FS then SS while dragging; release stores the matching type; the line appears after reload |
| Negative scenario | Dropping on the same activity is refused; a duplicate pair is refused; a cycle is refused |
| Permission scenario | Viewer cannot draw (no write capability) |
| Persistence scenario | The created link survives reload and appears in the relationship list |
| Related Help | Create relationships in the Gantt Chart — https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_relationships_in_the_gantt_chart.htm |

#### ENG-GANTT-12 — Edit and delete a relationship from its line

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Gantt chart and relationship editor |
| Feature | Double-click edit and delete |
| Preconditions | Stored FS link with revision 1 |
| Test data | Change to SS, lag 2 working-days; then delete with revision 1 |
| User action | Double-click the line → edit → save; double-click again → delete → confirm |
| Expected result | The first save stores SS/lag and raises the revision; the delete removes the link and its line; both activities remain |
| Negative scenario | A stale revision is reported and the link is unchanged |
| Permission scenario | Viewer cannot edit or delete |
| Persistence scenario | Reload shows the edited type then no link after deletion |
| Related Help | Edit relationships in the Gantt Chart — https://docs.oracle.com/cd/G48902_01/client_help/en_US/edit_relationships_in_the_gantt_chart.htm; Delete relationships in the Gantt Chart — https://docs.oracle.com/cd/G48902_01/client_help/en_US/delete_relationships_in_the_gantt_chart.htm |

#### ENG-GANTT-13 — Data Date line and progress classification

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Gantt chart and Bar Styles |
| Feature | Data Date line style and behind/on/ahead |
| Preconditions | Project Data Date 2026-01-15; three activities with progress points before, on and after it |
| Test data | Line dashed, thickness 2, colour `#003366` |
| User action | Apply the line options; inspect progress points |
| Expected result | A dashed line marks 2026-01-15; the three points classify as behind, on and ahead within a half-day tolerance |
| Negative scenario | With no authoritative Data Date, no line is drawn and the dialog explains why |
| Permission scenario | Viewer may change the line style |
| Persistence scenario | Line style survives reload; classification uses the stored date |
| Related Help | Customize the data date line — https://docs.oracle.com/cd/G48902_01/client_help/en_US/customize_the_data_date_line.htm; Using the data date — https://docs.oracle.com/cd/G48902_01/client_help/en_US/using_the_data_date.htm |

#### ENG-GANTT-14 — Progress line

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Bar Styles dialog |
| Feature | Progress point line |
| Preconditions | Activities with stored percent complete; Data Date present |
| Test data | Show progress line, thickness 2, colour `#7030a0` |
| User action | Enable and apply |
| Expected result | A polyline joins the stored progress points; points before the Data Date sit left, after it sit right; no progress value changes |
| Negative scenario | With fewer than two drawable points no line is drawn |
| Permission scenario | Viewer may enable the line |
| Persistence scenario | Visibility and colour survive reload |
| Related Help | Apply a Progress Line to the Gantt Chart — https://docs.oracle.com/cd/G48902_01/client_help/en_US/applying_a_progress_line_to_the_gantt_chart.htm |

#### ENG-GANTT-15 — Sight lines and legend

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Bar Styles dialog and chart |
| Feature | Major/minor background lines and legend |
| Preconditions | A WBS summary and several activities |
| Test data | Major line before summaries; minor horizontal every 3 rows; minor vertical on; legend visible above the chart |
| User action | Apply and inspect |
| Expected result | Lines draw behind bars at the configured intervals; the legend lists only visible bar styles at the chosen position; bars remain readable |
| Negative scenario | Interval 0 disables that line family; hiding a bar removes it from the legend |
| Permission scenario | Viewer may change presentation |
| Persistence scenario | All values survive reload |
| Related Help | Change the background lines in the Gantt Chart — https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_the_background_lines_in_the_gantt_chart.htm; Show or hide the Gantt Chart legend — https://docs.oracle.com/cd/G48902_01/client_help/en_US/show_or_hide_the_gantt_chart_legend.htm |

#### ENG-GANTT-16 — Non-working shading

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Gantt chart |
| Feature | Weekend and holiday bands from the project calendar, including persisted exceptions |
| Preconditions | Project calendar works Saturday–Wednesday, holidays 2026-01-01 and 2026-01-02; chart spans the week; one persisted nonwork exception inside the visible range and one total-work-hours exception on a weekend day |
| Test data | Range 2025-12-28 → 2026-01-10 |
| User action | Render the chart; add and remove the exceptions (own or inherited) through the calendar API; then load a project with no calendar snapshot |
| Expected result | Thursday/Friday and the two holidays shade as contiguous bands; the nonwork exception also shades while stored; the total-work-hours exception removes that weekend day's band; removing the rows restores the snapshot-only bands; the no-snapshot project draws no shading at all |
| Negative scenario | A calendar with no working weekday produces no bands rather than shading everything; a failed or unavailable day-facts projection leaves the snapshot bands intact and shades no exception date |
| Permission scenario | Viewer sees the same shading |
| Persistence scenario | Reload with the same calendar version yields identical bands; an exception added under another calendar version does not alter this chart |
| Related Help | CUBI-specific requirement (calendar facts source) — no direct P6 Gantt shading topic |

#### ENG-GANTT-17 — Actual and baseline bars

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Gantt chart and Bar Styles |
| Feature | Actual and baseline bar layers |
| Preconditions | One project with actual dates and a stored baseline; one without |
| Test data | Show actual and baseline bars |
| User action | Inspect both projects and the bar editor |
| Expected result | Actual bars draw only from stored actual dates; baseline bars only from stored baseline dates; where the facts are absent the bars do not draw and the editor says why |
| Negative scenario | No fabricated actual or baseline bar is drawn |
| Permission scenario | Viewer sees the same layers |
| Persistence scenario | Visibility survives reload |
| Related Help | Change a Gantt Chart bar's style — https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_gantt_chart_bars_style.htm |

#### ENG-GANTT-18 — Critical path presentation

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Gantt chart and Bar Styles |
| Feature | Critical bar style and filter |
| Preconditions | Activities flagged critical and non-critical |
| Test data | Critical bar filter `critical`; task bar filter `task` |
| User action | Render and inspect |
| Expected result | Only critical activities receive the critical bar; the critical style is independent of the task style; no second "show critical path" toggle is added |
| Negative scenario | An activity without the critical fact is never drawn as critical |
| Permission scenario | Viewer sees the stored criticality |
| Persistence scenario | Criticality comes from the stored schedule, not from the layout |
| Related Help | Change a Gantt Chart bar's filter — https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_gantt_chart_bars_filter.htm |

### Relationships

#### ENG-REL-01 — Create the four relationship types

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — relationship editor |
| Feature | Type, endpoints and lag entry |
| Preconditions | Planner; activities `A100`, `A110`, `A120` |
| Test data | FS with lag 0; SS with lag 2 working-days; FF with lag -1 working-hour; SF with lag 1.5 working-days |
| User action | Create each link through the register |
| Expected result | Each link stores its exact type and signed lag/unit and appears with both endpoints; FS remains the default for a new form |
| Negative scenario | Same predecessor and successor is rejected with "two different activities"; an invalid type or lag format is not submitted |
| Permission scenario | Viewer sees links but the submit control is not authorized by the API |
| Persistence scenario | All four links survive reload with type and lag intact |
| Related Help | Relationships — https://docs.oracle.com/cd/G48902_01/client_help/en_US/relationships.htm; Adding relationships between activities — https://docs.oracle.com/cd/G48902_01/client_help/en_US/adding_relationships_between_activities.htm |

#### ENG-REL-02 — Change type and lag

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — relationship editor |
| Feature | Edit an existing predecessor or successor relation |
| Preconditions | Stored FS link, revision 2 |
| Test data | Change to FF and lag 3 working-days |
| User action | Open Edit → change type and lag → save |
| Expected result | The stored type becomes FF, lag 3, revision 3; both endpoints are unchanged |
| Negative scenario | Saving with revision 1 returns `REVISION_CONFLICT` and the link remains FS |
| Permission scenario | Viewer cannot submit the edit |
| Persistence scenario | Reload shows FF/3 |
| Related Help | Change predecessor relationships — https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_predecessor_relationships.htm; Change successor relationships — https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_successor_relationships.htm |

#### ENG-REL-03 — Remove a relationship

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — relationship editor |
| Feature | Delete a predecessor or successor link |
| Preconditions | Stored link, revision 1; both activities otherwise unscheduled |
| Test data | Confirm delete |
| User action | Delete → confirm |
| Expected result | The link disappears from the list, Gantt and Trace Logic; both activities remain |
| Negative scenario | Cancelling keeps the link; a stale revision is rejected |
| Permission scenario | Viewer cannot delete |
| Persistence scenario | Reload confirms the link is gone |
| Related Help | Remove predecessor relationships — https://docs.oracle.com/cd/G48902_01/client_help/en_US/remove_predecessor_relationships.htm; Remove successor relationships — https://docs.oracle.com/cd/G48902_01/client_help/en_US/remove_successor_relationships.htm |

#### ENG-REL-04 — Lag calendar and external-link gaps

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — relationship editor and scheduling options |
| Feature | Lag calendar and cross-project relationships |
| Preconditions | Stored lag in working-days; one project open |
| Test data | Look for a lag-calendar selector and a cross-project activity picker |
| User action | Inspect both surfaces |
| Expected result | Neither selector exists: lag uses the backend assignment contract but the UI offers no choice, and endpoints are limited to loaded activities (documented gaps) |
| Negative scenario | An attempt to enter an unloaded activity id is not offered and cannot be submitted |
| Permission scenario | Not applicable |
| Persistence scenario | Existing stored lag remains readable with its unit |
| Related Help | Choose a calendar for relationship lag — https://docs.oracle.com/cd/G48902_01/client_help/en_US/choose_a_calendar_for_relationship_lag.htm; Relationships (external) — https://docs.oracle.com/cd/G48902_01/client_help/en_US/relationships.htm |

#### ENG-REL-05 — Revision, self-link and cycle rejection

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — relationship API |
| Feature | Concurrency and dependency validation |
| Preconditions | Planner; links A→B and B→C |
| Test data | Attempt C→A; attempt A→A; attempt a duplicate A→B; update B→C with a stale revision |
| User action | Submit each attempt |
| Expected result | C→A fails with `RELATIONSHIP_CYCLE`; A→A with `SELF_RELATIONSHIP`; duplicate is refused; stale update returns `REVISION_CONFLICT`; stored links are unchanged |
| Negative scenario | A cross-scope relationship id returns a scope denial |
| Permission scenario | Viewer write attempt is denied |
| Persistence scenario | Failed writes leave the list identical after reload |
| Related Help | CUBI-specific revision and cycle contract (relationship edit topic) — https://docs.oracle.com/cd/G48902_01/client_help/en_US/relationships.htm |

### Trace Logic

#### ENG-TRACE-01 — Chain projection and row content

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Trace Logic |
| Feature | Predecessors left, successors right, type and lag per row |
| Preconditions | `A100` FS→ `A110`; `A110` SS+2d→ `A120`; `A110` FF→ `A130` |
| Test data | Select `A110`; depth 1 |
| User action | Open Trace Logic |
| Expected result | `A100` appears under Predecessors as FS; `A120` and `A130` under Successors with SS+2d and FF; selected id is shown once |
| Negative scenario | An activity with no links shows both groups empty and an explanation |
| Permission scenario | Viewer sees the same chain |
| Persistence scenario | Reload with the same selection shows the same rows |
| Related Help | Trace Logic — https://docs.oracle.com/cd/G48902_01/client_help/en_US/trace_logic.htm; View activity relationships in Trace logic — https://docs.oracle.com/cd/G48902_01/client_help/en_US/view_activity_relationships_in_trace_logic.htm |

#### ENG-TRACE-02 — Display, navigation and depth controls

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Trace Logic |
| Feature | Bottom layout display, click navigation, independent depths |
| Preconditions | Chain of three levels; depths stored as predecessor 2, successor 1 |
| Test data | Change predecessor depth to 5; click a successor row |
| User action | Show Trace Logic → change depths → click a row |
| Expected result | The predecessor group grows to five levels while successors stay at one; clicking a row recentres the chain; both selectors remain visible |
| Negative scenario | A depth of 0 or 9 is clamped to 1 or 5 |
| Permission scenario | Viewer may change depth |
| Persistence scenario | Depths survive reload; a legacy single-depth value seeds both sides until changed |
| Related Help | Display Trace Logic — https://docs.oracle.com/cd/G48902_01/client_help/en_US/display_trace_logic.htm; Move around in Trace Logic — https://docs.oracle.com/cd/G48902_01/client_help/en_US/move_around_in_trace_logic.htm; Set Trace Logic preferences — https://docs.oracle.com/cd/G48902_01/client_help/en_US/set_trace_logic_preferences.htm |

#### ENG-TRACE-03 — Cycles, diamonds and missing endpoints

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Trace Logic |
| Feature | Degraded-chain reporting |
| Preconditions | A→B→C→A cycle; a diamond A→B, A→C, B→D, C→D; a link to unloaded `X999` |
| Test data | Select A with depth 5 |
| User action | Inspect notices and rows |
| Expected result | The cycle branch stops at the repeated activity with a cycle notice; D appears once, not as a cycle; the unloaded endpoint is counted in a missing-reference notice and never drawn as a row |
| Negative scenario | The view never loops or invents a placeholder activity |
| Permission scenario | Viewer sees the same notices |
| Persistence scenario | Reload produces the same notices |
| Related Help | Trace Logic — https://docs.oracle.com/cd/G48902_01/client_help/en_US/trace_logic.htm |

#### ENG-TRACE-04 — No local date recalculation

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Trace Logic |
| Feature | Read-only projection |
| Preconditions | Activity with stored dates and float |
| Test data | Record dates before opening Trace Logic |
| User action | Open and navigate Trace Logic |
| Expected result | Dates and float are identical before and after; the view states that dates are not recalculated |
| Negative scenario | A cycle or missing link changes no stored value |
| Permission scenario | Read-only for every role |
| Persistence scenario | Reload shows identical dates |
| Related Help | Trace Logic — https://docs.oracle.com/cd/G48902_01/client_help/en_US/trace_logic.htm |

### Constraints

#### ENG-CON-01 — Add, read and remove constraints

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Activity Details Status tab |
| Feature | Constraint add and remove |
| Preconditions | Planner; activity `A100` with no constraints |
| Test data | START_NO_EARLIER_THAN on 2026-12-01; MANDATORY_FINISH on 2026-12-20 |
| User action | Add both; reload; remove the first |
| Expected result | Both appear with dates and revisions; removal deletes only that row; dates and float are unchanged |
| Negative scenario | A blank date or invalid type is rejected locally |
| Permission scenario | Viewer sees the rows without the add form or Remove |
| Persistence scenario | The remaining constraint survives reload |
| Related Help | Types of constraints — https://docs.oracle.com/cd/G48902_01/client_help/en_US/types_of_constraints.htm; Enter activity constraints — https://docs.oracle.com/cd/G48902_01/client_help/en_US/enter_activity_constraints.htm |

#### ENG-CON-02 — Constraint validation and supported types

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — constraint API and Status tab |
| Feature | Type coverage, duplicates and unsupported activity types |
| Preconditions | Planner; Task activity and a Level of Effort activity |
| Test data | Add START_NO_EARLIER_THAN twice; add to LOE; request START_ON if offered |
| User action | Submit each attempt |
| Expected result | Duplicate fails with `DUPLICATE_CONSTRAINT_TYPE`; LOE fails with `CONSTRAINT_ACTIVITY_TYPE_UNSUPPORTED`; START_ON, FINISH_ON and AS_LATE_AS_POSSIBLE are not offered (documented gap) |
| Negative scenario | Invalid date format fails with `INVALID_CONSTRAINT_DATE` |
| Permission scenario | Viewer write attempt is denied |
| Persistence scenario | Failed writes leave the constraint list unchanged |
| Related Help | Types of constraints — https://docs.oracle.com/cd/G48902_01/client_help/en_US/types_of_constraints.htm; Enter activity constraints — https://docs.oracle.com/cd/G48902_01/client_help/en_US/enter_activity_constraints.htm |

#### ENG-CON-03 — Constraint is an input, not a calculation

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` — Activity Details |
| Feature | No local CPM or float derivation |
| Preconditions | Activity with stored dates, total float and critical flag |
| Test data | Save a MANDATORY_FINISH constraint |
| User action | Compare dates/float before and after; run the scheduler separately |
| Expected result | The constraint record changes; no date, float or critical flag changes in the pane; only a scheduler run can publish new dates |
| Negative scenario | A rejected constraint write changes nothing |
| Permission scenario | Viewer cannot write |
| Persistence scenario | The constraint survives reload with the original dates until rescheduling |
| Related Help | CUBI-specific scheduling-input boundary (Types of constraints) — https://docs.oracle.com/cd/G48902_01/client_help/en_US/types_of_constraints.htm |

### Calendars

#### ENG-CAL-01 — Register, selection and tabs

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/calendars/` |
| Feature | Catalogue, selection and five detail tabs |
| Preconditions | Project with a project calendar and a global calendar |
| Test data | Select each row; open General, Workweek, Calendar Month, Exceptions, Used By |
| User action | Inspect the register and tabs |
| Expected result | The register lists only authenticated project calendars with type/version/revision; each tab reads its own data; an unavailable catalogue shows an explicit state |
| Negative scenario | An empty catalogue shows "no calendar records" and disables New only when no base exists |
| Permission scenario | Viewer can read every tab |
| Persistence scenario | Reload returns to the catalogue with no stale selection |
| Related Help | Calendars — https://docs.oracle.com/cd/G48902_01/client_help/en_US/calendars.htm |

#### ENG-CAL-02 — Create a calendar from a base

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/calendars/` — New dialog |
| Feature | Base, id, version, name, type and date system |
| Preconditions | Base calendar `CAL-BASE/1` with snapshot, work hours and exceptions |
| Test data | `CAL-NEW`, version `1`, name "Site calendar", type project, system gregorian |
| User action | New → fill → Create |
| Expected result | The new master, snapshot, work-hour rules and exceptions are created in one transaction; the new calendar appears and is usable |
| Negative scenario | Missing base, id, version or name is refused; an existing reference is refused |
| Permission scenario | Viewer creation is denied and nothing is written |
| Persistence scenario | Reload shows the copy with the same definition |
| Related Help | Create a project calendar — https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_a_project_calendar.htm |

#### ENG-CAL-03 — General edit and inheritance

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/calendars/` — General tab |
| Feature | Name, type, base calendar, revision |
| Preconditions | Project calendar revision 3 inherited from `CAL-G/1` |
| Test data | Rename; change base to `CAL-G/2`; then choose "Do not inherit" |
| User action | Edit → Save after each change |
| Expected result | Name and base update with a new revision; clearing the base removes inheritance; the hint reflects the current base |
| Negative scenario | Blank name → `CALENDAR_NAME_REQUIRED`; self base → `CALENDAR_BASE_SELF_REFERENCE`; cycle → `CALENDAR_BASE_CYCLE`; kind change with a snapshot → `CALENDAR_SNAPSHOT_KIND_CONFLICT`; stale revision → `REVISION_CONFLICT` |
| Permission scenario | Viewer sees read-only fields |
| Persistence scenario | Reload shows the last successful base state |
| Related Help | Edit a project calendar — https://docs.oracle.com/cd/G48902_01/client_help/en_US/edit_a_project_calendar.htm; Project Calendars — https://docs.oracle.com/cd/G48902_01/client_help/en_US/projectcalendars.htm |

#### ENG-CAL-04 — Workweek, shifts and month editing

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/calendars/` — Workweek and Calendar Month |
| Feature | Working-day flag, hours, split shifts, Nonwork/Standard |
| Preconditions | Working-time calendar, Monday–Friday working |
| Test data | Friday off; Monday 08:00-12:00, 13:00-17:00; mark 2026-01-20 Nonwork then Standard |
| User action | Save each day and the month actions |
| Expected result | Flags/hours persist as work-hour rules; Friday stops being working; Monday shows both shifts and 8 hours; the month day changes state and returns to standard |
| Negative scenario | Overlapping shifts or start ≥ finish are refused before a write; a working-day calendar keeps hours read-only |
| Permission scenario | Viewer writes are denied |
| Persistence scenario | Reload shows the same flags, shifts and month state |
| Related Help | Edit a project calendar — https://docs.oracle.com/cd/G48902_01/client_help/en_US/edit_a_project_calendar.htm |

#### ENG-CAL-05 — Used By references

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/calendars/` — Used By tab |
| Feature | Project and resource references |
| Preconditions | Calendar version referenced by an activity and a resource assignment; resource master references the id only |
| Test data | Open Used By |
| User action | Read the list and counts |
| Expected result | Activity and relationship-lag references match id and version; resource masters match by id and show a null version; totals equal the listed rows |
| Negative scenario | A drifted usage payload is rejected rather than shown as an empty list |
| Permission scenario | Viewer may read |
| Persistence scenario | Reload produces the same references |
| Related Help | View project calendar assignments — https://docs.oracle.com/cd/G48902_01/client_help/en_US/view_project_calendar_assignments.htm; View resource calendar assignments — https://docs.oracle.com/cd/G48902_01/client_help/en_US/view_resource_calendar_assignments.htm |

#### ENG-CAL-06 — Exceptions and Jalali dates

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/calendars/` — Exceptions tab |
| Feature | Four modes, edit, remove, Jalali entry |
| Preconditions | Gregorian calendar; a Jalali calendar |
| Test data | Nonworking 2026-01-01; total 6 h on 2026-01-02; detailed 09:00–12:00 on 2026-01-03; edit the total to 7 h |
| User action | Add each; edit; remove one; enter a Jalali date |
| Expected result | Each mode stores its fields; edit keeps the date and raises the revision; removal deletes only that date; Jalali input keeps the canonical Gregorian date |
| Negative scenario | Invalid date, unknown mode, negative total or start ≥ finish is refused; stale exception revision → `EXCEPTION_REVISION_CONFLICT` |
| Permission scenario | Viewer writes are denied |
| Persistence scenario | Reload shows the remaining exceptions with revisions |
| Related Help | Edit a project calendar — https://docs.oracle.com/cd/G48902_01/client_help/en_US/edit_a_project_calendar.htm |

#### ENG-CAL-07 — Copy, delete and pools

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/calendars/` — toolbar and dialogs |
| Feature | Copy, delete, global and resource calendars |
| Preconditions | Project calendar with children; a global calendar; a resource calendar |
| Test data | Copy to `CAL-COPY/1`; delete the project calendar at revision 3 |
| User action | Copy; delete; inspect pools |
| Expected result | Copy reproduces snapshot, work hours and exceptions under the new reference; delete removes master, snapshot, work hours and exceptions; global and resource calendars are listed in their pools |
| Negative scenario | Copy to itself → `CALENDAR_TARGET_ALREADY_SELECTED`; stale delete → `REVISION_CONFLICT`; viewer delete → denied |
| Permission scenario | Viewer cannot copy or delete |
| Persistence scenario | Reload shows the copy and no deleted calendar |
| Related Help | Create a project calendar — https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_a_project_calendar.htm; Delete a project calendar — https://docs.oracle.com/cd/G48902_01/client_help/en_US/delete_a_project_calendar.htm; Global Calendars — https://docs.oracle.com/cd/G48902_01/client_help/en_US/globalcalendars.htm; Resource Calendars — https://docs.oracle.com/cd/G48902_01/client_help/en_US/resourcecalendars.htm |

#### ENG-CAL-08 — Factors, activity assignment and default gaps

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/calendars/` and `/app/activities/` |
| Feature | Hours per period, activity calendar, project default |
| Preconditions | Calendar with factors; project with `primary_calendar_id`; activity with a `calendar_id` |
| Test data | Inspect General factors; inspect Activity Details General; create an activity |
| User action | Attempt to edit each |
| Expected result | Factors are read-only; the activity calendar is read-only; the project default is stored but the create request carries no calendar (documented gaps); no value is guessed |
| Negative scenario | Editing is unavailable rather than silently writing an unrelated field |
| Permission scenario | Viewer sees the same read-only values |
| Persistence scenario | Existing values remain unchanged across reload |
| Related Help | Defining default hours per time period — https://docs.oracle.com/cd/G48902_01/client_help/en_US/defining_default_hours_per_time_period_in_calendars.htm; Assign a calendar to an activity — https://docs.oracle.com/cd/G48902_01/client_help/en_US/assign_a_calendar_to_an_activity.htm; Set the project default activity calendar — https://docs.oracle.com/cd/G48902_01/client_help/en_US/set_the_project_default_activity_calendar.htm |

## 5. Documented divergences and gaps

These are recorded, not asserted as defects. No product file is changed by
this workstream.

| # | Area | Help behavior | CUBI behavior | Classification |
| --- | --- | --- | --- | --- |
| 1 | Gantt pan | Dragging the major time unit pans; dragging the minor unit expands or contracts | Horizontal scroll pans; no timescale drag | `PARTIAL` presentation gap |
| 2 | Bar definitions | Add and Delete bar definitions | Fixed seven bar kinds; Display hides, but no Add/Delete | `NOT_IMPLEMENTED` gap |
| 3 | Per-bar timescale | Each bar can have its own timescale | All bars use the layout timescale | `NOT_IMPLEMENTED` gap |
| 4 | Bar label clipping | Help defines label position only | CUBI mirrors edge labels to the left | `IMPLEMENTED` adaptation; divergence recorded |
| 5 | Non-working shading | No Gantt topic documents weekend/holiday shading | Shading from the persisted calendar snapshot plus Shared Core-projected exception dates | CUBI-specific requirement |
| 6 | Relationship comments | Comments can be entered on a relationship | The editor stores type, lag and endpoints only | `NOT_IMPLEMENTED` gap |
| 7 | External relationships | Cross-project links are supported | Only loaded project activities can be linked | `NOT_IMPLEMENTED` gap |
| 8 | Lag calendar | A scheduling calendar for lag can be chosen | Assignment kind exists in the backend; no UI selector | `PARTIAL` gap |
| 9 | Constraint types | Start On, Start On or Before/After, Finish On, Finish On or Before/After, Mandatory, As Late As Possible | Six types: Start/Finish No Earlier/No Later Than and Mandatory Start/Finish | `PARTIAL` gap; Start On, Finish On and As Late As Possible absent |
| 10 | Primary/Secondary constraints | Two constrained fields with a filtered Secondary list | One constraint per type, multiple stored rows | `PARTIAL` model difference |
| 11 | Calendar factors | Hours per time period are editable and drive conversion | Displayed read-only | `PARTIAL` gap |
| 12 | Activity-level calendar | Activity Calendar can be assigned | Displayed read-only; only the project primary calendar is stored | `PARTIAL` gap |
| 13 | Project default calendar | Applies to new activities | Stored on the project, but the activity create request carries no calendar | `PARTIAL` gap; inheritance not proven |
| 14 | Resource calendars | Shared and personal pools with conversion | `resource` calendars exist; no resource-master assignment or conversion UI | `PARTIAL` gap |
| 15 | Detailed exception hours | Detailed work hours can describe a day's work | One detailed interval per exception | `PARTIAL` limitation |
| 16 | Jalali dates | Help does not describe a Jalali display calendar | Canonical ISO storage with Jalali entry/display | CUBI-specific requirement |
| 17 | Revision concurrency | Help describes the dialog, not optimistic concurrency | Every calendar, exception and relationship write carries an expected revision | CUBI-specific requirement |

## 6. Verification and evidence

| Check | Result |
| --- | --- |
| Official Help TOC | `https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm` parsed; every cited Help URL is a TOC member |
| Help URL/title check | 52/52 cited Help URLs returned HTTP 200, are TOC members and matched their TOC title; report in `evidence/section-04-gantt-relationships-calendars-links.json` |
| User Guide check | 33/33 cited User Guide URLs returned HTTP 200, are User Guide TOC members and matched their title; topics without a verified direct section are marked "No verified direct section" |
| Existing product tests cited | `workspace-gantt.test.ts`, `workspace-view.test.ts`, `workspace-dialogs.test.ts`, `workspace-trace-logic.test.ts`, `workspace-constraints.test.ts`, `workspace-activity-details.test.ts`, `workspace-calendars.test.ts`, `workspace-calendar-display.test.ts`, `calendar-holidays.test.ts`, `tests/test_relationship_validation.py`, `tests/test_relationship_master_repository.py`, `tests/test_p6_relationship_api.py`, `tests/test_project_lifecycle_http_routes.py`, `tests/test_activity_constraint_validation.py`, `tests/test_secondary_constraint_validation.py`, `tests/test_constraint_master_repository.py`, `tests/test_p6_constraint_api.py`, `tests/test_calendar_master_repository.py`, `tests/test_calendar_exception_kernel.py`, `tests/test_calendar_usage_api.py`, `tests/test_p6_calendar_api.py` |
| Executed acceptance run | None claimed. Every scenario is `TEST_SPECIFIED` until Agent 1's suite or an observed runtime result proves it. |

## 7. Gaps carried forward

- Sections 5–18 remain `NOT_STARTED`.
- The Gantt/relationship/calendar gaps in §5 are recorded for Agent 1 to scope.
  None is asserted as a defect because the CUBI requirement for each is not
  established by an accepted specification.
- No GitHub defect Issue is opened by this section. If Agent 1 confirms that a
  missing control is required, the affected row and scenario are the repro.
