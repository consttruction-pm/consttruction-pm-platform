# CUBI Visual Workspace Master Audit

Scope: visual shell only. API, persistence, calculation logic and service wiring are out of scope until the visual design is complete.

CUBI must expose the full professional project-controls desktop workspace: complete menu bar, nested menus, toolbars, window tabs, left navigation tree, contextual command bars, layout options and page-specific Details tabs. CUBI additions are additive and must never displace baseline functions. All visible but unwired commands must be marked visual-only/disabled and must not claim success or invent data. Customer-facing UI/help must use CUBI vocabulary and branding only.

## Persistent shell
1. App identity/status strip: CUBI, project, revision, user, connection/sync, language, calendar display, theme.
2. Menu bar: Workspace, Edit, View, Project, Organization, Tools, Administration, Help.
3. Main toolbar groups: Standard, Project, Layout, Schedule, Selection/Navigation, CUBI Tools.
4. Breadcrumb/context: Business Domain > optional Portfolio > Project > active window, revision and Data Date.
5. Window tabs: global and project windows, active/dirty state, close, reorder, keyboard cycling and tab groups.
6. Work area: collapsible left tree, central page, contextual Details pane, adjustable splitters.
7. Layout bar: layout, view, filter, group/sort, columns, timescale and bars.
8. Status bar: project, Data Date, baseline, layout, filter, selected count, user/role, save/sync and help.

## Menu catalogue
- Workspace: New/Open/Close Project, Close All, Save/Save All, Recent Projects, Import/Export, Print Preview, Page Setup, Print, Project Backup/Restore, Workspace Backup/Restore, Recovery, Sign Out, Exit.
- Edit: Undo/Redo/History, Cut/Copy/Paste/Paste Special, Fill Down/Across, Add Project/WBS/Activity/Relationship/Resource/Role/Assignment/Expense/Document/Issue/Risk/Threshold/Form, Edit/Delete/Duplicate, Dissolve Activity, Link/Unlink, Assign Resources/Roles/Codes/Predecessors/Successors/Documents, Renumber IDs, Global Change, Find/Replace, Select All, Preferences.
- View: Layout New/Open/Save/Save As/Import/Export; Show on Top Table/Gantt/Network/Chart/Usage Spreadsheet/Profile; Show on Bottom Details/Usage Profiles/Trace Logic/None; Bottom Layout Options; Columns; Filters; Group and Sort; Timescale; Bars; Bar Chart Options; Progress Line/Spotlight; Attachments; Line Numbers; Critical Path; Check Schedule; Font/Row; Chart Colors/Templates; Arrange/Align Children; Zoom; Expand/Collapse; Toolbars; Tab Groups; Tile; Full Screen; Theme.
- Project: Activities, Additional Activities View, WBS, Resource Assignments, Assign/Maintain Baselines, Expenses, Work Products & Documents, Thresholds, Issues, Risks, Set Default Project, Project Details, Codes, Defaults, Notebook, Calendars, UDFs.
- Organization: Projects/Business Domains, Portfolios, Responsibility Structure, Resources, Roles, Global/Project/Resource Calendars, Workweeks/Hours/Exceptions/Holidays, Project/Activity/Resource/Role Codes, UDFs, Resource Curves/Shifts, Cost Accounts, Funding Sources, Currencies, Financial Periods.
- Tools: Schedule, Level Resources, Apply Actuals, Update Progress, Recalculate Assignment Costs, Summarize, Store Period Performance, Global Change, Monitor Thresholds, Issue Navigator, Reports/Groups/Batches/Designer/Preview/Distribution, Form Builder, Smart Guide, Engineering Assistant, Search, Quality Checks, Import Validation.
- Administration: Users, Teams, Access/Security Profiles, Permissions, Preferences, Categories, Currencies, Financial Periods, System Defaults, Audit Log, Retention/Recovery.
- Help: Workspace Guide, Context Help, Shortcuts, What's New, Documentation Library, About CUBI.

## Page and Details inventory
| Window | Main view | Required Details tabs |
|---|---|---|
| Projects | Business Domain/Portfolio/Project tree + register/table/chart/Gantt | General, Dates, Defaults, Resources, Settings, Codes, Notebook, Budget Log, Spending Plan, Budget Summary, Funding, Baselines, Documents, History, UDFs |
| Activities | Table/Gantt, Activity Network, usage spreadsheets | General, Status, Resources, Predecessors, Successors, Relationships, Codes, Notebook, Steps, WPs & Docs, Expenses, Issues, Risks, Summary, UDFs, Update History |
| WBS | WBS table/chart | General, Status, Resources, Earned Value, WPs & Docs, Notebook, Issues, Risks, UDFs, History |
| Resource Assignments | Assignment table grouped by resource/activity, usage profile | General, Activity, Resource, Units & Costs, Dates, Curves, Notes, History |
| Resources | Resource hierarchy/chart/usage | General, Details, Units & Prices, Roles, Codes, Calendars, Shifts, Curves, UDFs, Notebook, History |
| Roles | Role hierarchy/rates | General, Resources, Price/Unit Rates, Limits, Codes, UDFs, History |
| Calendars | Calendar list + workweek/hour editor | General, Workweek, Work Hours, Exceptions/Holidays, Assignments, Resource Use, History |
| Documents | Document register | General, File Locations, Assignments, WBS Links, Activity Links, Revisions, History |
| Expenses | Expense register | General, Activity, Cost, Dates, Accrual, Category, Documents, History |
| Thresholds | Threshold register/monitor | General, Parameters, WBS/Activity Assignments, Monitoring, History |
| Issues | Issue register | General, Status, Priority, Responsible, Activity/WBS Links, Notebook, Documents, History |
| Risks | Risk register/probability-impact chart | General, Probability & Impact, Response, Owners, Schedule Impact, Cost Impact, WBS/Activity Links, Documents, History |
| Reports | Catalog/groups/batches/run/preview | Definition, Parameters, Data Scope, Preview, Distribution, Run History |
| Tracking | Tracking layouts/profiles | Projects, Layout, Data, Profiles, Variance, History |
| Form Builder (CUBI) | Designer canvas, field palette, properties | Form, Header, Fields, Validation, Conditional Logic, Workflow, Permissions, Library, Version, Preview, History |
| Cost & Financial Control (CUBI) | Cost register/cash flow/forecast | General, Budget, Actual Cost, Commitments, Forecast, Cash Flow, EVM, Funding, Change/Claim Links, Documents, History |
| Progress & Field Control (CUBI) | Period progress/field records | General, Status, Quantities, Physical Progress, Daily Reports, Labour, Equipment, Evidence, Approvals, History |
| Procurement (CUBI) | Procurement register | General, Supplier, Package, Quantities, Dates, Cost, Delivery, Activity/WBS Links, Documents, History |
| Changes & Claims (CUBI) | Notices/change/claims/impact | General, Notice, Change, Entitlement, Schedule Impact, Cost Impact, Decision, Evidence, Correspondence, History |

The Details pane title identifies the object and record. With no selection it shows page-level context. It changes with the active window and selected record, preserves a valid selected tab, and never leaks stale details from another page. Tab order/visibility are configurable per window/layout.

## Contextual command bars
Each page has its own horizontal contextual bar below the global toolbar; the right-edge CUBI Add (+) bar remains separate and never overlays data. Shared commands: Add, Open, Edit, Delete, Duplicate, Copy/Paste, Save/Cancel, Undo/Redo, Refresh, Assign, Link/Unlink, Move, Indent/Outdent, Filter, Group, Sort, Columns, Layout, Export, Print, Details, Help, More. Page-specific commands include baseline/schedule/trace logic for Activities; child/sibling/milestones for WBS; roles/rates/shifts/curves for Resources; usage/spreads for Assignments; workweek/exceptions for Calendars; upload/link/version/launch for Documents; accrual/cash-flow for Expenses/Cost; owner/response/monitor for Issues/Risks/Thresholds; run/preview/distribute for Reports; and field/rule/workflow/preview/version for Form Builder.

## Left navigation
Current Project: Activities, WBS, Resource Assignments, Expenses, Documents, Issues, Risks, Thresholds, Baselines, Cost, Progress, Procurement, Changes & Claims, Forms.
Organization: Projects/Business Domains, Portfolios, Resources, Roles, Calendars, Codes, UDFs, Cost Accounts, Funding Sources, Resource Curves.
Insights: Reports, Tracking, Dashboards, Smart Guide.
Administration: Users, Teams, Security, Preferences, Audit.
Workspace: Recent Windows, Saved Layouts, Form Libraries, Appearance.

## CUBI-only additions
Form Builder has two distinct libraries: Organization Form Library (reusable governed templates) and Project Form Library (project-specific forms and tailored versions). Form headers support JPG/PNG, including transparent PNG. It also includes sections, fields, validation, conditional logic, workflow, approval, preview and version history. Other additive areas: Engineering Intelligence Assistant, daily field reports, labour/equipment, inspections, quality/NCR, safety, punch/closeout, procurement/materials, notices/changes/claims, Theme Manager and contextual Add (+).

## Completion evidence
The shell is complete only after running-app proof that all menus/submenus open and are keyboard accessible; every window opens as a tab; each page has its own Details tabs and contextual bar; table/Gantt/network/chart/profile/spreadsheet options are present; layout dialogs are complete; English/Persian and LTR/RTL are tested; desktop/tablet/mobile layouts are tested; and no control falsely reports execution. A menu catalogue or static placeholder is not proof of completion.

## Internal reference set
Parity source: P6 Professional desktop Version 26 User Guide and Help, including Menu Bar, Project Menu, View Menu, Main Windows and Administration Menu:
- https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/toc.htm
- https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm
- https://docs.oracle.com/cd/F51303_01/client_help/en_US/menu_bar.htm
- https://docs.oracle.com/cd/F51303_01/client_help/en_US/49096.htm
- https://docs.oracle.com/cd/G48902_01/client_help/en_US/49095.htm
- https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/using_main_windows.htm
- https://docs.oracle.com/cd/G48902_01/client_help/en_US/49099.htm


## Multilingual UI and public website requirement (2026-11-02)

Supported language targets: English (en), Persian (fa), German (de), Chinese Simplified (zh), Arabic (ar), French (fr), Japanese (ja), and Korean (ko).

- Arabic is RTL. Persian remains RTL. English, German, French, Japanese, Korean and Simplified Chinese are LTR.
- The authenticated visual workspace language selector must expose all registered languages, preserve the current project, selected object, open page, layout, calendar mode and unsaved drafts when switching, and update document lang/dir, navigation, menus, command bars, Details tabs, dialogs, forms, tables, charts, reports, assistant and status bar.
- Public website must provide translated, indexable route sets for Home, Platform, Solutions, Resources, Contact and Pricing in each published language. Each route must include correct lang/dir, translated title/description/OG metadata, canonical and reciprocal hreflang links, localized navigation/footer and correct language switcher.
- A language may be registered in the workspace before its public website routes are published. Do not advertise an unavailable website route or create a dead link. Do not treat English fallback as completed translation.
- Translation packs use stable translation IDs and are verified/activated through the existing language-pack lifecycle. The visual command shell and generic UI translation helpers must resolve activated pack strings before English fallback.
- Fonts must cover Arabic/Persian shaping, French diacritics, Japanese kana/kanji, Korean Hangul and Chinese glyphs. Layouts must be checked for clipping, wrapping, line height, mixed-direction identifiers, numbers and dates.
- Acceptance: complete translation coverage report for every shipped page and workspace surface; RTL/LTR visual tests; locale-specific SEO route tests; language-switch preservation tests; screenshots for all eight languages at desktop and mobile breakpoints.
