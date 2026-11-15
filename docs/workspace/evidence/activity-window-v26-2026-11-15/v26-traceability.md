# Activity Window — Version 26 Traceability

Tested code: `bbacdaa0094d8dccc647ff08c1cf75db59875901` (main).
Captured: 2026-11-15, managed Python preview runtime (fresh SQLite per suite), headless Chrome.
Product under test is CUBI; Oracle/Primavera names below appear only as the reference
documentation being traced against.

## 1. Authority and provenance

| Reference | Location | Status |
| --- | --- | --- |
| Version 26 HTML Help (complete desktop help) | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm | Fetched 2026-11-15; every topic title below read from the fetched page |
| Version 26 Professional User Guide (PDF) | https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/p6_pro_user.pdf | Fetched 2026-11-15; **303 pages**, PDF metadata “Microsoft Word 2024”, creation 2026-05-29 |
| Supplied 815-page Version 26 PDF named in the instruction | not present in `/mnt`, `/mnt/session`, or the repository | **MISSING / VERIFY** |

The 815-page PDF the instruction refers to is not mounted in this environment. No page
number below is attributed to it. Every “Guide page” value is a real page in the retrieved
303-page official guide, verified by extracting the page text and its printed table of
contents. A later pass must re-key these references to the 815-page file once it is supplied;
until then the 815-page bookkeeping stays **MISSING / VERIFY** and must not be reported as
complete.

## 2. Activity Details — the sixteen desktop tabs

The contract in `apps/web/src/workspace-activity-details.ts:71` renders sixteen desktop tabs
in this order, followed by a CUBI-only Calendar tab. The Version 26 parent topic
([Activity Details](https://docs.oracle.com/cd/G48902_01/client_help/en_US/activity_details.htm))
lists its tabs; `Customize Activity Details` is the documented add/remove/reorder path
([topic](https://docs.oracle.com/cd/G48902_01/client_help/en_US/customize_activity_details.htm)).

| # | CUBI tab | Version 26 Help topic (title — URL) | Guide page | CUBI surface |
| --- | --- | --- | --- | --- |
| 1 | General | General tab - Activity Details — `general_tab_-_activity_details.htm` | 111, 114 | read; editable general fields submit through the activity master |
| 2 | Status | Status tab - Activity Details — `status_tab_-_activity_details.htm` | 115, 116 | read; dates/percent complete through the activity master |
| 3 | Resources | Resources tab - Activity Details — `resources_tab_-_activity_details.htm` | 117 | read + write (`/p6/resource-assignments`) |
| 4 | Predecessors | Predecessors tab - Activity Details — `predecessors_tab_-_activity_details.htm` | 123 | read; edits through the relationship routes |
| 5 | Successors | Successors tab - Activity Details — `successors_tab_-_activity_details.htm` | 124 | read; edits through the relationship routes |
| 6 | Relationships | Relationships tab - Activity Details — `relationships_tab_-_activity_details.htm` | 126 | read |
| 7 | Codes | Codes tab - Activity Details — `codes_tab_-_activity_details.htm` | 82 | read |
| 8 | Notebook | Notebook tab - Activity Details — `notebook_tab_-_activity_details.htm` | 155 | browser-local comments rail |
| 9 | Steps | Steps tab - Activity Details — `steps_tab_-_activity_details.htm` | 150, 151 | read |
| 10 | WPs & Docs | WPs & Docs tab - Activity Details — `19419.htm` | 216, 219 | read |
| 11 | Expenses | Expenses tab - Activity Details — `expenses_tab_-_activity_details.htm` | 143 | read + write (`/p6/expenses`) |
| 12 | Issues | **CUBI extension** — mapped to Issues — `issues.htm` | 205 | read + write (`/p6/issues`) |
| 13 | Risks | Risks tab - Activity Details (P6 Professional Only) — `48816.htm` | 210 | read-only project register |
| 14 | Summary | listed in Activity Details (no standalone topic) — `activity_details.htm` | 120 | read |
| 15 | UDFs | listed in Activity Details (no standalone topic) — `activity_details.htm` | 86 | read + typed write (UDF PUT) |
| 16 | Update History | Update History tab - Activity Details — `103015.htm` | — (no guide section) | read |
| + | Calendar (CUBI) | **CUBI extension** — mapped to Calendars — `calendars.htm` | 89 | read |

Parity statement, stated precisely:

- The Version 26 Professional help lists sixteen tab topics including **Feedback** and
  **Update History**. Tasks and Discussion are marked P6 EPPM Only.
- CUBI renders fifteen of those sixteen (`Feedback` is the one absence) and adds `Issues`
  and `Calendar`. `Issues` is therefore a CUBI extension beyond the Oracle tab list, not a
  parity claim; `Feedback` is deferred because CUBI has no EPPM team-collaboration service,
  and an always-empty tab would violate the no-fabrication rule. This matches
  `docs/workspace/architecture/workspace-window-inventory.md:80` and the ACT-014 note in the
  traceability matrix.
- `Summary` and `UDFs` have no standalone help topic in this Version 26 build; the tabs are
  authoritative on the parent topic and in the guide (pp. 120 and 86). That is recorded as a
  documentation limitation, not as a CUBI gap.

Browser proof: `activity-details-v26.mjs` renders all seventeen tabs in contract order with
Calendar last, every data tab settles into idle/loading/loaded/empty/error/unauthorized
states, three write paths round-trip, and removing a tab in Customize survives a reload.
`context-menus-v26.mjs` opens the same Customize dialog from the details context menu and
checks the full V26 control set (Available/Display columns, add, add-all, remove,
remove-all, up, down, default, apply, cancel) in English and Persian RTL.

## 3. Menus, toolbars and rails

| Surface | Version 26 Help topic (title — URL) | Guide page | CUBI implementation and proof |
| --- | --- | --- | --- |
| Application menu bar | Menu bar — `menu_bar.htm`; File `49093.htm`, Edit `49094.htm`, View `49095.htm`, Project `49096.htm` | 34 (active-window enablement) | `workspace-desktop-shell.ts`; six-cell suite `toolbars-v26.mjs` measures exactly one menu bar, eight triggers, 24 px bars, 11.5 px labels, no parallel command shell |
| Main toolbar families | Standard Toolbar — `standard_toolbar.htm`, Project Toolbar — `project_toolbar.htm` | 34 | one `.cp-toolbar`, 10 families in reference order, every button has an icon, no duplicate command, min target 25×24 px |
| Layout toolbar | Layout Toolbar — `layout_toolbar.htm` | 36 | layout selector and Columns/Timescale/Filter/Group and Sort entry points; `toolbars-v26.mjs` asserts the layout trigger and the Classic Schedule Layout selector round-trip |
| Tool rails and customization | Toolbar and icon reference (TOC `menu,toolbar,andiconreference.htm`, individual pages) | 34 | `toolbar-rails-v26.mjs`: both rails, eighteen right-rail families, Add or Remove Buttons, Customize dialog, drag between families/rails/dock, custom toolbars, persisted per-user config, permissions, RTL |
| Shortcut menus | Use shortcut menus — `use_shortcut_menus.htm` | 39 | `context-menus-v26.mjs`: 92 checks across table row/cell/header/empty area, WBS band, Gantt bar/link/timescale/empty board, details pane, dismissal and focus restore, RTL |

The toolbar suite previously measured every `<button>` inside a rail, including the family
drag handles that Version 26 renders as a small grip. That selector was stale after the rail
family headers landed; it is now scoped to `[data-tool-rail-button]` and skips the grip glyph,
so the 16 px assertion applies to command icons only. This is a test-scope correction, not a
lowered threshold.

## 4. Table, columns, filters, grouping and sorting

| Capability | Version 26 Help topic (title — URL) | Guide page | Proof |
| --- | --- | --- | --- |
| Activity Table | Activity Table — `activitytable.htm`, The Activity Table — `the_activity_table.htm` | 225 | `activity-details-v26.mjs` grid assertions; `activity-grid-keyboard-v26.mjs` |
| Columns dialog | Define Activity Table columns — `define_activity_table_columns.htm`; Customize activity column titles — `customize_activity_column_titles.htm` | 225, 226 | `activity-columns-v26.mjs`: 11 scenarios (filter, draft transfer, edit, default staging, copy from, other project, viewer read-only, RTL, 1920) |
| Sorting and grouping | Sort activities — `sort_activities.htm`; Group activities by field — `group_activities_by_field.htm`; Group activities by WBS path — `group_activities_by_wbs_path.htm` | 227, 277, 279, 280 | `activity-group-sort-v26.mjs` |
| Table font and row height | Change Activity Table font, color, and row height — `change_activity_table_font_color_and_row_height.htm` | 227 | `activity-table-font-v26.mjs` |
| Filters | Filter a tracking layout — `filter_a_layout.htm`; Create a filter — `create_a_filter.htm`; Apply a filter — `apply_a_filter.htm`; Filtering data — `filtering_data.htm` | 283, 285, 286 | `activity-filters-v26.mjs`: 14 scenarios — categories, All/Any, Replace/Highlight, typed rows with High value, relative CD/CS/CF ranges, live preview count, apply, reload, Persian RTL |

## 5. WBS

| Capability | Version 26 Help topic (title — URL) | Guide page | Proof |
| --- | --- | --- | --- |
| WBS window, table and chart | Work Breakdown Structure — `work_breakdown_structure.htm`; View the WBS — `view_the_wbs.htm`; Change the WBS table display — `change_the_work_breakdown_structure_table_display.htm` | 74, 75, 77, 78 | `wbs-hierarchy-v26.mjs`: 19 checks comparing table, chart and `GET /api/projects/{id}/p6/wbs`; a node created through the API appears in both layouts after reload |
| Expand/collapse by band | Grouping by hierarchy (TOC `grouping_by_hierarchy.htm`) | 277 | `activity-wbs-collapse-v26.mjs` — selected branch, all depths, persisted state |
| Band formatting | Format grouping bands — `format_grouping_bands.htm` | 281 | `activity-wbs-band-v26.mjs`: six scenarios incl. reload, reset, RTL, 1920 |
| WBS copy/cut/paste and delete protection | Copy and paste a WBS element, Delete a WBS element (TOC) | 78, 79 | `wbs-cut-copy-paste-v26.mjs` |
| Weighted milestones and status | Assign WBS weighted milestones — `assign_wbs_weighted_milestones.htm`; WBS status types | 75, 76 | `wbs-status-milestones-v26.mjs` |

## 6. Gantt chart

| Capability | Version 26 Help topic (title — URL) | Guide page | Proof |
| --- | --- | --- | --- |
| Gantt chart and timescale | Gantt Chart — `ganttchart.htm`; The Gantt Chart — `the_gantt_chart.htm`; Change a layout's timescale format — `change_a_layout_s_timescale_format_50.htm` | 228, 229 | `gantt-options-v26.mjs`, `gantt-scroll-sync-v26.mjs`, `gantt-fit-v26.mjs` |
| Bars, bar styles and labels | Add a bar to the Gantt Chart — `add_a_bar_to_the_gantt_chart.htm`; Change a Gantt Chart bar's style — `change_a_gantt_chart_bars_style.htm`; Change a Gantt Chart bar's label — `change_a_gantt_chart_bars_label.htm` | 230, 234, 235 | `gantt-bar-styles-v26.mjs`: eight scenarios incl. milestone shape, reload, RTL, 1280, 1920 |
| Overlays: data date, progress line, baseline, critical | Customize the data date line (TOC); Apply a Progress Line to the Gantt Chart — `applying_a_progress_line_to_the_gantt_chart.htm`; Define critical activities — `define_critical_activities.htm` | 233, 240, 195 | `activity-gantt-overlays-v26.mjs` |
| Relationship arrows and drag gestures | View/Create/Edit relationships in the Gantt (TOC: `view_activity_relationships_in_the_gantt_chart.htm`, `create_relationships_in_the_gantt_chart.htm`, `edit_relationships_in_the_gantt_chart.htm`) | 126, 127 | `activity-relationships-v26.mjs`: 11 scenarios — FS/SS/FF/SF creation and edit by drag, lag badge, arrow context menu delete with confirmation, hidden-layer inertness, RTL and 1920 |

The relationship suite now scrolls both bar ends into the visible Gantt band before a drag.
At 1280×720 the lower rows are legitimately clipped by the pane’s own scroll container, so a
pointer at the clip edge is ignored by the browser; the gesture was measuring a point outside
the scrollable viewport, not exposing a product defect.

## 7. Other Activity window views

| View | Version 26 Help topic | Guide page | Proof |
| --- | --- | --- | --- |
| Activity Network | Activity Network — `activitynetwork.htm` | 241 | `activity-network-v26.mjs` |
| Trace Logic | Trace Logic — `tracelogic.htm` | 246 | `activity-trace-logic-v26.mjs` |
| Activity Usage Profile / Spreadsheet | Activity Usage Profile — `activityusageprofile.htm`; Activity Usage Spreadsheet — `activityusagespreadsheet.htm` | 248 | `activity-usage-v26.mjs` |
| Baseline columns and bars | Baselines — `baselines.htm`; Assign baselines to projects — `assign_baselines_to_projects.htm` | 161, 163 | `activity-baseline-v26.mjs` |
| UDF values on activities | User-defined fields — guide p.86 (no per-tab help topic) | 86, 87 | `activity-udf-values-v26.mjs` |
| Selection, scope and counts | Select multiple items — guide p.39; Create a filter — `create_a_filter.htm` | 39, 285 | `activity-multi-select-v26.mjs`, `activity-scope-v26.mjs` |
| Grid keyboard and roving focus | Using shortcut keys (TOC) | 39 | `activity-grid-keyboard-v26.mjs` |

## 8. Known gaps and divergences

1. **815-page supplied PDF is missing.** Page references above belong to the 303-page
   official guide. Re-keying is pending the file; status **MISSING / VERIFY**.
2. **Feedback tab** (P6 Professional) is not offered. It depends on EPPM team collaboration
   that CUBI does not run. Deferred in the window inventory, not silently dropped.
3. **Issues tab** is a CUBI extension beyond the Version 26 tab list. It is backed by the
   project issue register and has full write validation; it must not be counted as Oracle
   parity.
4. **Summary and UDFs tabs** have no standalone help topic in this Version 26 build; the
   parent topic and the guide are the authority.
5. **Update History** has a help topic but no guide section.
6. **Notebook** defers to the browser-local comments rail; it does not write P6 notebook
   topics.
7. **Risks** is a project register read surface; there is no per-activity risk foreign key.
8. **Toolbars.** Tooltips are native `title` attributes rather than the Version 26 hint
   window; toolbar visibility persists per user in localStorage rather than inside a saved
   layout. Both are recorded in the WS-003 matrix row.
9. **Activity delete/cut/copy/paste/fill-down/renumber/dissolve** remain disabled with a
   localized reason in the runtime that does not expose those routes; the menus show the
   V26 commands but do not invent effects.

## 9. Reproduce

```bash
cd /data/work/repo
PYTHONPATH=src python3 -m construction_pm.preview \
  --web-root apps/web --database /tmp/activity.sqlite --port 4193 --reset

cd apps/web
CUBI_PREVIEW_URL=http://127.0.0.1:4193 \
CUBI_EVIDENCE_DATE=2026-11-15 \
CUBI_TESTED_CODE_SHA=$(git rev-parse HEAD) \
CUBI_CHROME_NO_SANDBOX=1 \
node e2e/activity-details-v26.mjs
```

Each suite writes its own bundle under `docs/workspace/evidence/<suite>-2026-11-15/`; the
run summary and counts are recorded in `summary.md` and `evidence.json` in this directory.
