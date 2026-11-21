# Engineering AI Workbench — Help Matrix

Binding sources:

- P6 Professional V26 HTML Help TOC:
  <https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm>
- P6 Professional V26 User Guide:
  <https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/index.html>
- P6 EPPM V26 HTML Help (Enterprise/approval semantics):
  <https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm>

No Oracle/Primavera/P6 brand is displayed in CUBI. Each studio now has one
verified studio-level reference (see `HELP_CROSSWALK.md`); the per-control URLs
below stay `HELP_REFERENCE_PENDING` until that exact control's page is opened
and recorded.

| Studio | Region / control | Behavior | Help topic | Exact URL | Origin | API | Permission | Test ID | Status |
|---|---|---|---|---|---|---|---|---|---|
| Import | Source identity | File name/type/size/format/version/checksum/scan/parse | Import and Export Projects | PENDING | Inherited | staging preview | project write | `aw-import-source` | HELP_REFERENCE_PENDING |
| Import | Inventory | Counts per entity; valid/invalid/duplicate/orphan/unsupported | Project Structure; WBS; Activity Data | PENDING | Inherited | staging preview | project read | `aw-import-inventory` | HELP_REFERENCE_PENDING |
| Import | Mapping | Source→target, auto/manual, date/duration/unit/currency/calendar/code/resource/ID | Data Mapping | PENDING | Inherited | staging mapping | project write | `aw-import-mapping` | HELP_REFERENCE_PENDING |
| Import | Validation | Duplicate IDs, cycles, dangling logic, lags, dates, calendars, resources, baselines, loss | Import Data; Relationships; Calendars | PENDING | Inherited | staging validation | project read | `aw-import-validation` | HELP_REFERENCE_PENDING |
| Import | Schedule Preview | WBS/Gantt/grid/details, float, critical, baseline, source-vs-recalculated | Gantt Chart; Activity Table; Critical Path | PENDING | Inherited | staging snapshot + core | project read | `aw-import-preview` | HELP_REFERENCE_PENDING |
| Import | Options | Create/update/merge, IDs, datasets, conflicts, calendar, timezone | Import Data; Project Structure | PENDING | Inherited | staging plan | project write | `aw-import-options` | HELP_REFERENCE_PENDING |
| Import | Final Review | Counts, digest, target revision, permissions, apply/verify | Import Data | PENDING | Inherited | staging apply | project write + execute | `aw-import-review` | HELP_REFERENCE_PENDING |
| Scenario | Brief | Request, revision, data date, objective, constraints, assumptions | Schedule Calculation; Layouts | PENDING | Inherited | command plan | project read | `aw-scenario-brief` | HELP_REFERENCE_PENDING |
| Scenario | Selector | Baseline/current/scenarios; create/duplicate/rename/archive/pin/recommend/compare | Baselines; Layouts | PENDING | CUBI Extension (scenario lifecycle) + inherited baseline semantics | scenario service | project read/write | `aw-scenario-selector` | BLOCKED |
| Scenario | Gantt | Scales, zoom, fit, row height, bars, progress, milestones, summaries, constraints, float, critical, data date, FS/SS/FF/SF, lags | Gantt Chart; Activity Details; Relationships; Critical Path; Total Float | PENDING | Inherited | schedule read + scenario | project read | `aw-scenario-gantt` | BLOCKED |
| Scenario | Grid | Activity columns, freeze, sort, filter, group, multi-select, context menu, keyboard | Activity Table; Filters; Group and Sort; Columns | PENDING | Inherited | scenario read | project read | `aw-scenario-grid` | BLOCKED |
| Scenario | Comparison | Side-by-side, overlay, variance table, old/new values | Schedule Comparison (CUBI extension) | PENDING | CUBI Extension | comparison | project read | `aw-scenario-compare` | BLOCKED |
| Scenario | Inspector | General/dates/durations/logic/resources/costs/constraints/calendars/progress/changes/evidence/validation | Activity Details | PENDING | Inherited | scenario read | project read | `aw-scenario-inspector` | BLOCKED |
| Scenario | Impact | Finish, float, resources, cost, risk; each with evidence | Project Statistics; Schedule Performance | PENDING | Inherited + derived | scheduling core | project read | `aw-scenario-impact` | BLOCKED |
| Scenario | Controls | Run, recalculate, validate, compare, save draft, export, request approval, discard | Schedule Calculation; Export | PENDING | Inherited + CUBI extension | scenario service | project write | `aw-scenario-controls` | BLOCKED |
| Risk | Register/Matrix/Response | Real risk rows, 3×3/5×5 matrix, response and residual rating | Risk register (EPPM) | PENDING | Inherited (EPPM) | risk API | project read/write | `aw-risk-register` | HELP_REFERENCE_PENDING |
| Risk | Quantitative | EMV/PERT/Monte Carlo only with valid inputs; seed and assumptions recorded | Risk analysis (EPPM) | PENDING | Inherited where present; otherwise CUBI extension | risk analysis service | project read | `aw-risk-quant` | HELP_REFERENCE_PENDING |
| Analysis | KPI/Forecast | Facts, derived metrics, forecasts separated; drill-down | Project Statistics; Earned Value; Reports | PENDING | Inherited | project read models | project read | `aw-analysis-kpi` | HELP_REFERENCE_PENDING |
| Decision | Proposal/Approval | Exact proposal/version/revision binding; approve/reject/partial/defer | Approvals; Workflows; Change Management (EPPM) | PENDING | Inherited (EPPM) | approval service | approve | `aw-decision-proposal` | HELP_REFERENCE_PENDING |

A row may move to `VERIFIED` only after the exact topic URL, the fields and the
permission behavior have been opened and recorded. TOC presence alone is not
verification.
