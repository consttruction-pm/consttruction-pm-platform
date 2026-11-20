# CUBI Engineering — page, field and Help matrix

**Generated from:** `docs/traceability/engineering-v26.json` and `scripts/generate_master_page_matrices.py`
**Rows:** 67 · **Machine-readable twin:** `ENGINEERING_PAGE_FIELD_HELP_MATRIX.json`

Status vocabulary: `VERIFIED`, `WIRED_WRITE`, `WIRED_READ`, `SHELL_ONLY`, `MISSING`, `NOT_AUDITED`, `BLOCKED_EXTERNAL`.
Only `VERIFIED` rows carry an observed browser proof; every other row is backed by source, unit/contract tests or API evidence, not by a screenshot.

## Page and Help matrix

| Page ID | Page | Surface | Help topic | Direct HTML URL | Status | Evidence |
|---|---|---|---|---|---|---|
| ENG-PUB-HOME | / | Home page | Working with Projects | [Working with Projects](https://docs.oracle.com/cd/G48902_01/client_help/en_US/workingwithprojects.htm) | VERIFIED | apps/web/index.html |
| ENG-PUB-PLATFORM | /platform/ | Platform overview | — | — | VERIFIED | apps/web/public/platform/index.html |
| ENG-PUB-FEATURES | /features/ | Feature index | Define Activity Table columns | [Define Activity Table columns](https://docs.oracle.com/cd/G48902_01/client_help/en_US/define_activity_table_columns.htm) | VERIFIED | apps/web/public/features/index.html |
| ENG-PUB-FEATURES-SCHEDULING | /features/scheduling/ | Scheduling feature page | Scheduling Projects | [Scheduling Projects](https://docs.oracle.com/cd/G48902_01/client_help/en_US/schedulingprojects.htm) | WIRED_WRITE | apps/web/public/features/scheduling/index.html |
| ENG-PUB-FEATURES-PROJECT-CONTROLS | /features/project-controls/ | Project controls feature page | Tracking | [Tracking](https://docs.oracle.com/cd/G48902_01/client_help/en_US/tracking.htm) | WIRED_WRITE | apps/web/public/features/project-controls/index.html |
| ENG-PUB-FEATURES-RESOURCES | /features/resources/ | Resources feature page | Resources | [Resources](https://docs.oracle.com/cd/G48902_01/client_help/en_US/resources.htm) | WIRED_WRITE | apps/web/public/features/resources/index.html |
| ENG-PUB-FEATURES-COST | /features/cost/ | Cost feature page | Expenses | [Expenses](https://docs.oracle.com/cd/G48902_01/client_help/en_US/expenses.htm) | WIRED_READ | apps/web/public/features/cost/index.html |
| ENG-PUB-FEATURES-DOCUMENTS | /features/documents/ | Documents feature page | Work Products and Documents | [Work Products and Documents](https://docs.oracle.com/cd/G48902_01/client_help/en_US/work_products_and_documents.htm) | WIRED_READ | apps/web/public/features/documents/index.html |
| ENG-PUB-FEATURES-RISKS | /features/risks/ | Risks feature page | Risks (P6 Professional Only) | [Risks (P6 Professional Only)](https://docs.oracle.com/cd/G48902_01/client_help/en_US/risks.htm) | WIRED_READ | apps/web/public/features/risks/index.html |
| ENG-PUB-FEATURES-REPORTING | /features/reporting/ | Reporting feature page | Print budget reports | [Print budget reports](https://docs.oracle.com/cd/G48902_01/client_help/en_US/print_budget_reports.htm) | WIRED_READ | apps/web/public/features/reporting/index.html |
| ENG-PUB-FEATURES-AI-ASSISTANT | /features/ai-assistant/ | AI assistant feature page | — | — | VERIFIED | apps/web/public/features/ai-assistant/index.html |
| ENG-PUB-SOLUTIONS | /solutions/ | Solutions page | — | — | VERIFIED | apps/web/public/solutions/index.html |
| ENG-PUB-INTEGRATIONS | /integrations/ | Integrations page | Importing and exporting data - Future period bucket planning FAQ | [Importing and exporting data - Future period bucket planning FAQ](https://docs.oracle.com/cd/G48902_01/client_help/en_US/48617.htm) | WIRED_READ | apps/web/public/integrations/index.html |
| ENG-PUB-PRICING | /pricing/ | Pricing page | — | — | VERIFIED | apps/web/public/pricing/index.html |
| ENG-PUB-RESOURCES | /resources/ | Resources page | — | — | VERIFIED | apps/web/public/resources/index.html |
| ENG-PUB-DOCUMENTATION | /documentation/ | Documentation page | — | — | VERIFIED | apps/web/public/documentation/index.html |
| ENG-PUB-HELP | /help/ | Help center | — | — | VERIFIED | apps/web/public/help/index.html |
| ENG-PUB-FAQ | /faq/ | FAQ page | — | — | VERIFIED | apps/web/public/faq/index.html |
| ENG-PUB-ABOUT | /about/ | About page | — | — | VERIFIED | apps/web/public/about/index.html |
| ENG-PUB-SECURITY | /security/ | Security page | Setting up user security (P6 Professional Only) | [Setting up user security (P6 Professional Only)](https://docs.oracle.com/cd/G48902_01/client_help/en_US/setting_up_user_security.htm) | WIRED_READ | apps/web/public/security/index.html |
| ENG-PUB-PAYMENTS | /payments/ | Payments page | — | — | VERIFIED | apps/web/public/payments/index.html |
| ENG-PUB-CONTACT | /contact/ | Contact page | — | — | VERIFIED | apps/web/public/contact/index.html |
| ENG-PUB-GET-STARTED | /get-started/ | Get started page | — | — | VERIFIED | apps/web/public/get-started/index.html |
| ENG-PUB-PRIVACY | /privacy/ | Privacy policy | — | — | VERIFIED | apps/web/public/privacy/index.html |
| ENG-PUB-TERMS | /terms/ | Terms of service | — | — | VERIFIED | apps/web/public/terms/index.html |
| ENG-WS-SHELL | /app/ | Workspace shell and main windows | Using main windows | [Using main windows](https://docs.oracle.com/cd/G48902_01/client_help/en_US/using_main_windows.htm) | VERIFIED | apps/web/src/workspace-desktop-shell.test.ts |
| ENG-WS-MENUS | /app/ | Menu bar and commands | Working with Toolbars and Menus | [Working with Toolbars and Menus](https://docs.oracle.com/cd/G48902_01/client_help/en_US/workingwithtoolbarsandmenus.htm) | VERIFIED | apps/web/src/workspace-view.test.ts |
| ENG-WS-TOOLBARS | /app/ | Toolbars | Customizing Toolbars | [Customizing Toolbars](https://docs.oracle.com/cd/G48902_01/client_help/en_US/customizingtoolbars.htm) | WIRED_READ | apps/web/src/workspace-visual-demo.test.ts |
| ENG-WS-SELECTION | /app/activities/ | Multi-selection | Select multiple items | [Select multiple items](https://docs.oracle.com/cd/G48902_01/client_help/en_US/select_multiple_items.htm) | VERIFIED | apps/web/src/workspace-activity-scope.test.ts |
| ENG-WS-CONTEXT-MENUS | /app/ | Shortcut menus | Use shortcut menus | [Use shortcut menus](https://docs.oracle.com/cd/G48902_01/client_help/en_US/use_shortcut_menus.htm) | WIRED_READ | apps/web/src/workspace-view.test.ts |
| ENG-WS-LAYOUTS | /app/activities/ | Activity layouts | Customizing Activity Layouts | [Customizing Activity Layouts](https://docs.oracle.com/cd/G48902_01/client_help/en_US/customizingactivitylayouts.htm) | WIRED_WRITE | apps/web/src/p6-layout-persistence-adapter.test.ts |
| ENG-WS-ACTIVITY-TABLE | /app/activities/ | Activity table | Define Activity Table columns | [Define Activity Table columns](https://docs.oracle.com/cd/G48902_01/client_help/en_US/define_activity_table_columns.htm) | VERIFIED | apps/web/src/p6-columns-dialog.test.ts |
| ENG-WS-GROUPING | /app/activities/ | Grouping and sorting | Grouping activities by field | [Grouping activities by field](https://docs.oracle.com/cd/G48902_01/client_help/en_US/grouping_activities_by_field.htm) | WIRED_WRITE | apps/web/src/workspace-view.test.ts |
| ENG-WS-FILTERS | /app/activities/ | Filters | Create a filter | [Create a filter](https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_a_filter.htm) | WIRED_WRITE | apps/web/src/workspace-activity-filters.test.ts |
| ENG-WS-GANTT | /app/activities/ | Gantt chart | The Gantt Chart | [The Gantt Chart](https://docs.oracle.com/cd/G48902_01/client_help/en_US/the_gantt_chart.htm) | VERIFIED | apps/web/src/workspace-view.test.ts |
| ENG-WS-GANTT-BARS | /app/activities/ | Gantt bar styles | Change a Gantt Chart bar's style | [Change a Gantt Chart bar's style](https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_gantt_chart_bars_style.htm) | VERIFIED | apps/web/src/workspace-view.test.ts |
| ENG-WS-DATA-DATE | /app/activities/ | Data Date and progress line | Using the data date | [Using the data date](https://docs.oracle.com/cd/G48902_01/client_help/en_US/using_the_data_date.htm) | VERIFIED | apps/web/src/workspace-view.test.ts |
| ENG-WS-RELATIONSHIPS | /app/activities/ | Relationships | Linking Activities with Relationships | [Linking Activities with Relationships](https://docs.oracle.com/cd/G48902_01/client_help/en_US/linkingactivitieswithrelationships.htm) | VERIFIED | apps/web/src/p6-api.test.ts |
| ENG-WS-GANTT-RELATIONSHIPS | /app/activities/ | Relationships in Gantt | Create relationships in the Gantt Chart | [Create relationships in the Gantt Chart](https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_relationships_in_the_gantt_chart.htm) | WIRED_WRITE | apps/web/src/workspace-view.test.ts |
| ENG-WS-NETWORK | /app/activities/ | Activity Network | Activity Network | [Activity Network](https://docs.oracle.com/cd/G48902_01/client_help/en_US/activitynetwork.htm) | VERIFIED | apps/web/src/workspace-view.test.ts |
| ENG-WS-DETAILS | /app/activities/ | Activity Details | Customize Activity Details | [Customize Activity Details](https://docs.oracle.com/cd/G48902_01/client_help/en_US/customize_activity_details.htm) | VERIFIED | apps/web/src/workspace-activity-details.test.ts |
| ENG-WS-USAGE-PROFILE | /app/activities/ | Activity usage profile and spreadsheet | The Activity Usage Profile | [The Activity Usage Profile](https://docs.oracle.com/cd/G48902_01/client_help/en_US/the_activity_usage_profile.htm) | WIRED_READ | apps/web/src/workspace-activity-usage.test.ts |
| ENG-WS-TRACE-LOGIC | /app/activities/ | Trace Logic | Trace Logic | [Trace Logic](https://docs.oracle.com/cd/G48902_01/client_help/en_US/tracelogic.htm) | WIRED_WRITE | apps/web/src/workspace-view.test.ts |
| ENG-WS-WBS | /app/wbs/ | WBS table and chart | Defining the WBS | [Defining the WBS](https://docs.oracle.com/cd/G48902_01/client_help/en_US/definingthewbs.htm) | VERIFIED | apps/web/src/p6-activity-wbs-grid.test.ts |
| ENG-WS-PROJECTS | /app/projects/ | Projects and EPS | Managing projects using the EPS | [Managing projects using the EPS](https://docs.oracle.com/cd/G48902_01/client_help/en_US/managing_projects_using_the_eps.htm) | WIRED_WRITE | apps/web/src/workspace-view.test.ts |
| ENG-WS-RESOURCES | /app/resources/ | Resources | Resources | [Resources](https://docs.oracle.com/cd/G48902_01/client_help/en_US/resources.htm) | WIRED_WRITE | apps/web/src/workspace-assignments.test.ts |
| ENG-WS-ROLES | /app/resources/ | Roles | Roles | [Roles](https://docs.oracle.com/cd/G48902_01/client_help/en_US/roles.htm) | WIRED_WRITE | apps/web/src/workspace-assignments.test.ts |
| ENG-WS-RESOURCE-USAGE | /app/resources/ | Resource usage profile | The Resource Usage Profile | [The Resource Usage Profile](https://docs.oracle.com/cd/G48902_01/client_help/en_US/the_resource_usage_profile.htm) | WIRED_READ | apps/web/src/p6-capacity-panel.test.ts |
| ENG-WS-CALENDARS | /app/calendars/ | Calendars | Defining Calendars | [Defining Calendars](https://docs.oracle.com/cd/G48902_01/client_help/en_US/definingcalendars.htm) | WIRED_WRITE | apps/web/src/workspace-administration.test.ts |
| ENG-WS-SCHEDULE | /app/schedule/ | Schedule dialog | Scheduling Projects | [Scheduling Projects](https://docs.oracle.com/cd/G48902_01/client_help/en_US/schedulingprojects.htm) | WIRED_WRITE | apps/web/src/workspace-administration.test.ts |
| ENG-WS-CRITICAL-PATH | /app/schedule/ | Critical path and float | Define critical activities | [Define critical activities](https://docs.oracle.com/cd/G48902_01/client_help/en_US/define_critical_activities.htm) | WIRED_WRITE | apps/web/src/workspace-view.test.ts |
| ENG-WS-LEVELING | /app/schedule/ | Resource leveling | Leveling Resources | [Leveling Resources](https://docs.oracle.com/cd/G48902_01/client_help/en_US/levelingresources.htm) | WIRED_READ | apps/web/src/workspace-administration.test.ts |
| ENG-WS-BASELINES | /app/baselines/ | Baselines | Baselines | [Baselines](https://docs.oracle.com/cd/G48902_01/client_help/en_US/baselines.htm) | WIRED_READ | apps/web/src/workspace-view.test.ts |
| ENG-WS-TRACKING | /app/tracking/ | Tracking | Tracking | [Tracking](https://docs.oracle.com/cd/G48902_01/client_help/en_US/tracking.htm) | WIRED_READ | apps/web/src/workspace-view.test.ts |
| ENG-WS-REPORTS | /app/reports/ | Reports and printing | Print budget reports | [Print budget reports](https://docs.oracle.com/cd/G48902_01/client_help/en_US/print_budget_reports.htm) | WIRED_READ | apps/web/src/p6-report-print-field-selection.test.ts |
| ENG-WS-EXCHANGE | /app/exchange/ | Import and export | Importing and exporting data - Future period bucket planning FAQ | [Importing and exporting data - Future period bucket planning FAQ](https://docs.oracle.com/cd/G48902_01/client_help/en_US/48617.htm) | WIRED_READ | apps/web/src/p6-interchange-panel.test.ts |
| ENG-WS-ADMIN | /app/admin/ | Administration | Administration | [Administration](https://docs.oracle.com/cd/G48902_01/client_help/en_US/administration.htm) | WIRED_READ | apps/web/src/workspace-administration.test.ts |
| ENG-WS-DOCUMENTS | /app/documents/ | Work products and documents | Work Products and Documents | [Work Products and Documents](https://docs.oracle.com/cd/G48902_01/client_help/en_US/work_products_and_documents.htm) | WIRED_READ | apps/web/src/workspace-view.test.ts |
| ENG-WS-RISKS | /app/risks/ | Risks | Risks (P6 Professional Only) | [Risks (P6 Professional Only)](https://docs.oracle.com/cd/G48902_01/client_help/en_US/risks.htm) | WIRED_READ | apps/web/src/workspace-view.test.ts |
| ENG-WS-ISSUES | /app/issues/ | Issues | Issues | [Issues](https://docs.oracle.com/cd/G48902_01/client_help/en_US/issues.htm) | WIRED_READ | apps/web/src/workspace-view.test.ts |
| ENG-WS-EXPENSES | /app/expenses/ | Expenses | Expenses | [Expenses](https://docs.oracle.com/cd/G48902_01/client_help/en_US/expenses.htm) | WIRED_READ | apps/web/src/workspace-view.test.ts |
| ENG-WS-THRESHOLDS | /app/thresholds/ | Thresholds | Thresholds | [Thresholds](https://docs.oracle.com/cd/G48902_01/client_help/en_US/thresholds_topic.htm) | WIRED_READ | apps/web/src/workspace-view.test.ts |
| ENG-WS-PORTFOLIOS | /app/portfolios/ | Portfolios | Portfolios | [Portfolios](https://docs.oracle.com/cd/G48902_01/client_help/en_US/portfolios.htm) | WIRED_READ | apps/web/src/workspace-view.test.ts |
| ENG-WS-OBS | /app/admin/ | OBS | Organizational breakdown structure (OBS) overview | [Organizational breakdown structure (OBS) overview](https://docs.oracle.com/cd/G48902_01/client_help/en_US/organizational_breakdown_structure_(obs)_overview.htm) | WIRED_READ | apps/web/src/workspace-administration.test.ts |
| ENG-WS-UDF | /app/activities/ | User-defined fields | User-defined fields | [User-defined fields](https://docs.oracle.com/cd/G48902_01/client_help/en_US/user_defined_fields.htm) | WIRED_WRITE | apps/web/src/p6-udf-http.test.ts |
| ENG-WS-STEPS | /app/activities/ | Activity steps | Activity steps | [Activity steps](https://docs.oracle.com/cd/G48902_01/client_help/en_US/activity_steps.htm) | WIRED_WRITE | apps/web/src/workspace-activity-steps.test.ts |
| ENG-WS-ACTIVITY-CODES | /app/activities/ | Activity codes | Activity Codes | [Activity Codes](https://docs.oracle.com/cd/G48902_01/client_help/en_US/activitycodes.htm) | WIRED_READ | apps/web/src/workspace-view.test.ts |

## Field-level coverage — Project creation (real form contract)

Source: `docs/workspace/architecture/workspace-form-field-inventory.md`. Persistence and revision guards are exercised by the project lifecycle HTTP tests; the form itself is rendered by the workspace.

| Field | Type | Required | Validation | Source of truth | Surface | Status | Source document |
|---|---|---|---|---|---|---|---|
| Business domain | enum | yes | Construction/Oil & Gas/Infrastructure/Industrial/Energy/Other | User input | Project create form | WIRED_WRITE | workspace-form-field-inventory.md |
| Portfolio | picker | no | Must belong to tenant | Dictionary | Project create form | WIRED_WRITE | workspace-form-field-inventory.md |
| Project name | text | yes | 2–120 chars | User input | Project create form | WIRED_WRITE | workspace-form-field-inventory.md |
| Project ID | text | yes | [A-Z0-9][A-Z0-9_-]{1,39}, unique per tenant | User input | Project create form | WIRED_WRITE | workspace-form-field-inventory.md |
| Description | textarea | no | ≤2000 chars | User input | Project create form | WIRED_WRITE | workspace-form-field-inventory.md |
| Start date | date | yes | Valid in active calendar | User input | Project create form | WIRED_WRITE | workspace-form-field-inventory.md |
| Target finish | date | no | ≥ start | User input | Project create form | WIRED_WRITE | workspace-form-field-inventory.md |
| Date system | enum | yes | gregorian / jalali | User input | Project create form | WIRED_WRITE | workspace-form-field-inventory.md |
| Project calendar | picker | yes | Must exist in tenant | Dictionary | Project create form | WIRED_WRITE | workspace-form-field-inventory.md |
| Responsible organisation | picker | no | Must belong to business domain | Dictionary | Project create form | WIRED_WRITE | workspace-form-field-inventory.md |
| Default duration type | enum | no | Fixed duration / units / units per time | User input | Project create form | WIRED_WRITE | workspace-form-field-inventory.md |
| WBS template | picker | no | Blank or template | Dictionary | Project create form | WIRED_WRITE | workspace-form-field-inventory.md |
| Seed activities | toggle | no | — | User input | Project create form | WIRED_WRITE | workspace-form-field-inventory.md |

## Field-level coverage — the remaining surfaces

Field extraction for the other 66 rows is tracked per window in `v26-complete-window-component-catalog.md` and `workspace-form-field-inventory.md`. The per-field audit rows (Tab, Component, Field ID, Label, API, Permission, Audit, Help topic, Test ID, Screenshot) are **NOT_AUDITED** for those surfaces in this revision and must be filled before any row is promoted to `VERIFIED`. No field was invented to fill this table.
