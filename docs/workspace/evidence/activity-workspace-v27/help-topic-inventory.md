# V27 Help Topic Inventory — Activities Workspace

- Issue: #2047 · PR: #2048 · Branch: `feat/2047-activity-workspace-v26`
- Tested code head: `b71cd61f46ebe358d1b15eee21068977b03493cf`
- Evidence date: 2026-11-18
- Environment: Hasan's Qoder Desktop (Windows 10.0.17763), local full-stack preview only

## 1. Source access result

| Source | Attempt | Result |
|---|---|---|
| Complete desktop HTML Help TOC — `https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm` | Re-fetched 2026-11-18 | **HTTP 403 Forbidden**. No topic content returned. |
| Version 26 Professional Help PDF (815 pages) | Repository and workspace search | **MISSING**. No PDF is present in the repository or the working directory. |
| Version 26 User Guide HTML index | Recorded 2026-10-30 in `docs/workspace/reference/oracle-p6-reference-index.md` | Not re-fetched; same host family. |
| Existing topic crosswalk | `docs/workspace/architecture/v26-window-traceability-and-acceptance-matrix.md` | Contains **84 distinct** official Help topic files as citations from earlier verified crosswalks. |

Consequence: a fresh page-by-page Help audit cannot be performed today. This inventory
therefore records the topical coverage that the project already holds and marks
every Help-origin row honestly. No topic URL, option name, dialog field or default
is invented in this document. Nothing below is labelled inspected when it was not.

Status vocabulary (Persian, per the binding standard): **مطابق و تأییدشده**،
**پیاده‌سازی‌شده ولی آزمون‌نشده**، **ناقص**، **غایب**، **محدودیت مستند و مشخص**،
plus **VERIFY** and **BLOCKED** where the reference itself is unavailable.

## 2. Topic areas and inspection status

| # | Help area (topic family) | Representative topic files held in the crosswalk | Inspection status (2026-11-18) | CUBI surface |
|---:|---|---|---|---|
| 1 | Welcome / workspace basics / main windows | `welcome.htm`, `using_main_windows.htm`, `single_project_mode_vs_multi-project_mode.htm` | Inspected previously; not re-verified (403) | Desktop shell, window tabs, status bar |
| 2 | Menus, toolbars and icons | `49093.htm`–`49100.htm`, `standard_toolbar.htm`, `project_toolbar.htm`, `layout_toolbar.htm`, `edit_toolbar.htm`, `display_toolbar.htm`, `find_toolbar.htm`, `bottom_layout_toolbar.htm` | Inspected previously; not re-verified (403) | 8 menus, 118 commands, 57 toolbar buttons, 11 declared families |
| 3 | Shortcut menus / multiple selection / hot keys | `use_shortcut_menus.htm`, `select_multiple_items.htm` | Inspected previously; not re-verified (403) | 11 context-menu kinds; keyboard registry |
| 4 | Activity Table / columns | `activitytable.htm`, `define_activity_table_columns.htm` | Title-level only; page previously timed out | Activity Grid, Columns dialog |
| 5 | Activity Details / customization | `activity_details.htm`, `customize_activity_details.htm` | `activity_details.htm` inspected previously; `customize_activity_details.htm` returned 403 earlier; also 403 today | 17 Details tabs, Customize Tabs |
| 6 | Layout lifecycle | `create_a_new_activity_layout.htm`, `open_a_layout.htm`, `save_a_layout_in_the_activities_or_rsrc_assignments_window.htm`, `delete_a_layout.htm`, `customizing_activity_layouts.htm` | Inspected previously; not re-verified (403) | Layout selector, Save / New / Reset |
| 7 | Timescale, zoom and bar options | `change_a_layout_s_timescale_format_50.htm`, `zoom_in_and_out_of_a_timescaled_layout.htm`, `change_a_gantt_chart_bar_s_style.htm`, `change_a_gantt_chart_bar_s_settings.htm`, `change_a_gantt_chart_bars_label_layouts.htm` | Inspected previously; not re-verified (403) | Timescale, Bar Styles, Zoom / Fit |
| 8 | Gantt background, data date, progress line, relationships | `change_the_background_lines_in_the_gantt_chart.htm`, `customize_the_data_date_line.htm`, `applying_a_progress_line_to_the_gantt_chart.htm`, `show_or_hide_relationship_lines_in_the_gantt_chart.htm`, `create_relationships_in_the_gantt_chart.htm`, `edit_relationships_in_the_gantt_chart.htm` | Inspected previously; not re-verified (403) | Gantt overlays, dependency links |
| 9 | Filters | `filters_dialog_box.htm`, `create_a_filter.htm`, `create_a_lookahead_filter.htm`, `filter_by_project_status.htm` | Inspected previously; not re-verified (403) | Filters dialog, 7 built-in filters, saved filters |
| 10 | Grouping and sorting | `group_activities_by_field.htm`, `grouping_activities_by_wbs_path.htm`, `grouping_by_hierarchy.htm`, `sort_activities.htm`, `format_grouping_bands.htm`, `change_group_row_fonts_and_colors.htm`, `collapse_or_expand_grouped_data.htm`, `collapse_or_expand_all_groups_in_a_layout.htm` | Inspected previously; not re-verified (403) | Group and Sort, WBS bands, expand/collapse |
| 11 | Table font, row height, colors | `change_activity_table_font_color_and_row_height.htm` | Inspected previously; not re-verified (403) | Table Font and Row dialog |
| 12 | Activity usage profile / spreadsheet | `the_activity_usage_profile.htm`, `define_the_activity_usage_profile.htm`, `display_the_activity_usage_profile.htm`, `the_activity_usage_spreadsheet.htm`, `display_the_activity_usage_spreadsheet.htm` | Inspected previously; not re-verified (403) | Bottom layout: Usage Profile / Spreadsheet |
| 13 | Activity network and Trace Logic | `activity_network.htm`, `move_around_in_the_activity_network.htm`, `view_activity_network_activity_details.htm`, `trace_logic.htm`, `move_around_in_trace_logic.htm`, `set_trace_logic_preferences.htm` | Inspected previously; not re-verified (403) | Activity Network, Trace Logic |
| 14 | Relationships | `add_predecessor_relationships.htm`, `linkingactivitieswithrelationships.htm` | Inspected previously; not re-verified (403) | Predecessors / Successors / Relationships tabs |
| 15 | Progress and updates | `update_progress_for_individual_activities_manually.htm`, `update_progress_for_all_activities.htm` | Inspected previously; not re-verified (403) | Progress window, Update Progress, Update History |
| 16 | Calendars | `edit_a_project_calendar.htm` | Inspected previously; not re-verified (403) | Calendar (CUBI) tab, Jalali/Gregorian calendars |
| 17 | WBS | `view_the_wbs.htm`, `display_work_breakdown_structure_details.htm`, `assign_wbs_weighted_milestones.htm`, `using_weighted_milestones_in_the_wbs.htm`, `wbs_status_types.htm`, `add_a_project_to_the_eps_hierarchy.htm`, `working_with_eps.htm`, `projects.htm`, `open_a_project.htm`, `copy_and_paste_a_work_breakdown_structure_element.htm`, `cut_and_paste_a_work_breakdown_structure_element.htm`, `delete_a_work_breakdown_structure_element.htm` | Inspected previously; not re-verified (403) | WBS window, WBS bands, WBS Details |
| 18 | Baselines | `add_new_baseline_dialog_box.htm`, `assign_baselines_dialog_box.htm` | Inspected previously; not re-verified (403) | Baselines, Compare Baselines |
| 19 | User-defined fields | `user_defined_fields.htm` | Inspected previously; not re-verified (403) | UDFs tab, UDF Values dialog |
| 20 | Project Details | `general_tab_-_project_details.htm` | Inspected previously; not re-verified (403) | Project Details, Project Status |
| 21 | Activity Codes | No dedicated topic file in the 84-file crosswalk | **MISSING / VERIFY** | Codes tab (read-only, contract gap) |
| 22 | Notebook topics | No dedicated topic file in the 84-file crosswalk | **MISSING / VERIFY** | Notebook tab (contract gap) |
| 23 | Steps | No dedicated topic file in the 84-file crosswalk | **MISSING / VERIFY** | Steps tab (read-only) |
| 24 | Documents / WPs & Docs | No dedicated topic file in the 84-file crosswalk | **MISSING / VERIFY** | WPs & Docs tab (read-only, link gap) |
| 25 | Issues, Risks, Thresholds | No dedicated topic file in the 84-file crosswalk | **MISSING / VERIFY** | Issues / Risks tabs and windows |
| 26 | Expenses / costs | No dedicated topic file in the 84-file crosswalk | **MISSING / VERIFY** | Expenses tab, cost windows |
| 27 | Reports, Admin, Enterprise | `49097.htm` (Enterprise menu), `49099.htm` (Admin menu), reporting guide (separate PDF) | Menu pages inspected previously; reporting guide not available | Reports, Administration windows |

## 3. Numeric summary

| Measure | Value |
|---|---:|
| Distinct Help topic files cited in the project crosswalk | 84 |
| Topic pages re-fetched today | 0 (403) |
| PDF pages inspected today | 0 (PDF missing) |
| Topic areas with a running CUBI surface | 20 |
| Topic areas with no authoritative Help citation | 7 (codes, notebook, steps, documents, issues/risks/thresholds, expenses, reports/admin detail) |

## 4. What this means for acceptance

- Menu, toolbar, layout, Gantt, grouping, filtering, WBS, baseline, calendar,
  usage and network behavior can be evaluated against the previously recorded
  crosswalk; they are **not** re-certified by today's blocked fetch.
- Activity Codes, Notebook, Steps, Documents, Issues/Risks/Thresholds, Expenses
  and detailed Reports/Admin topics remain **VERIFY** until the HTML Help host is
  reachable or the supplied PDF is added to the evidence set.
- No parity percentage is claimed. `final-acceptance-report.md` carries the
  resulting statuses per area.
