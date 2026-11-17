# ENT-06A — Dashboard & Portlet Registry Backend v1

**Issue:** #2028  
**Implementation branch:** feat/ent06-dashboard-portlet-backend-v1  
**Scope:** isolated CUBI Enterprise backend foundation  
**Status:** implementation candidate; exact-head CI and PostgreSQL evidence pending

This document describes the bounded backend slice only. It is not a claim that the complete P6 EPPM dashboard experience, dashboard designer UI, production HTTP routes, browser workflows, or full Oracle parity are complete.

## 0. Preflight and non-interference record

- Base main SHA: 20778a0394dfad0686e2854a4dd043f3b1189172.
- All eight issue-allowed target paths were absent from the base recursive Git tree.
- Current changed-file lists for all 122 open pull requests (including this PR) were checked. None of the other 121 open PRs touches any of the eight target paths.
- The protected shared security, identity, deployment schema, production composition, workspace UI, portfolio-source and Engineering calculation paths are not part of this change.
- The recursive base Git tree contains no root or nested AGENTS.md. This environment does not provide an actual local repository checkout, so the issue's separate actual-checkout AGENTS inspection remains an explicit pre-merge verification gate; no claim that this local-checkout step was completed is made.


## 1. Delivery boundary and ownership

The dashboard is a presentation/configuration aggregate. It stores dashboard identity, context, owner, sharing, ordered portlet instances, layout, allow-listed filters, lifecycle state and revision. It does not own portfolio facts, project facts, KPIs, formulas, schedules, cost, progress, EVM, resources or risk calculations.

| Concern | Owner / boundary |
|---|---|
| Dashboard definition, layout, sharing, filters, revision and audit | CUBI Enterprise ENT-06 |
| Portfolio Control Snapshot read model | Existing Portfolio Control read boundary; consumes Engineering-owned facts |
| Portfolio Decision read model | Existing Portfolio Decision domain/application/API |
| Project schedule, CPM, activities, WBS, resource assignments, cost, progress, EVM and project risk facts | Engineering |
| Identity, session, tenant and project authorization | Existing shared identity/project-lifecycle services; consumed, not modified |
| Dashboard UI, production route mounting, shell integration and browser acceptance | Explicit later handoff; not in this backend slice |

No second portfolio query, KPI, report, scheduling, cost, progress or EVM engine is introduced.

## 2. Implemented backend contract

### 2.1 Definition

The closed contract is **cubi-enterprise-dashboard.v1**. It rejects unknown fields and carries:

- Tenant, dashboard, owner and context identity.
- enterprise_home or a specific portfolio context.
- Private, explicitly assigned user, explicitly assigned Enterprise role, or combined sharing.
- Active/archived lifecycle state and optimistic revision.
- Ordered portlet instances with stable instance IDs, exact registered type/version, typed configuration and bounded layout placement.
- Typed, allow-listed filter metadata.
- Creation and update timestamps.

The default portlet ceiling is twelve, matching the EPPM dashboard default documented in Help. The layout model is a bounded 12-column grid and is presentation-only.

### 2.2 Governed registry

Only these source contracts are registered in v1:

| Portlet type | Source owner | Read permission | Config | Drill-through reference |
|---|---|---|---|---|
| portfolio-control-snapshot.v1 | Enterprise Portfolio Control read model; Engineering remains authoritative for project facts | project.read | portfolio_id | project_id + project_revision |
| portfolio-decision.v1 | Enterprise Portfolio Decision | project.read | portfolio_id + decision_id | decision_id + source revision |

Registry metadata includes source owner, permission, supported contexts, contract version and drill-through reference shape.

The registry is closed. Unknown portlet types and extra configuration keys fail validation. Arbitrary SQL, user-supplied code, formulas, arbitrary external URLs, custom report execution and new KPI/calculation engines are prohibited.

### 2.3 Persistence and lifecycle

PostgresEnterpriseDashboardRepository uses dedicated tenant-scoped tables:

- enterprise_dashboards
- enterprise_dashboard_idempotency
- enterprise_dashboard_audit

The repository provides create, get, tenant list, optimistic update, revision history, idempotency and append-only audit. It does not commit or roll back; the caller owns the transaction. Dashboard and audit writes occur in the same transaction. The audit table has a database trigger rejecting UPDATE and DELETE, and its foreign key prevents deletion of a dashboard with audit history.

The application service provides:

- Create and list.
- Read dashboard definition.
- Update title, description, portlets and filters.
- Duplicate into a new private dashboard owned by the current actor.
- Assign and revoke explicit user or Enterprise-role shares.
- Archive.
- Read portlet data through existing source boundaries.

The authenticated session is the sole authority for actor and tenant. Caller-supplied owner or tenant fields are rejected. Enterprise viewers can read but cannot mutate. Owners and Enterprise administrators can manage dashboards; Enterprise administrators can manage tenant dashboards.

### 2.4 Source authorization and freshness

A dashboard share grants access to the dashboard definition only. For each portlet read:

1. The existing Portfolio Control Snapshot or Portfolio Decision boundary is called with an AuthorizationContext derived from the current authenticated session.
2. Each affected project ID is separately re-authorized through the existing project lifecycle authorize_project(..., PROJECT_READ) boundary.
3. Tenant, portfolio and source contract identity are checked before returning data.
4. The response preserves source snapshot identity and source revision. Snapshot source revision is represented by the ordered source-reference revision set; a decision uses its persisted decision revision.
5. Snapshot age is explicitly classified as fresh or stale. Missing source records return missing; source contracts without a generated timestamp return unknown.
6. A dashboard share never grants project, activity, document, claim or other source-record access.

No cache is introduced. Drill-through references are emitted as typed IDs and revisions, but no UI navigation or route is mounted in this slice.

### 2.5 Filter contract boundary

Filters are stored and validated against a closed key/operator/value catalogue:

- project_status
- membership_status
- decision_status
- generated_after
- generated_before
- include_stale

They are returned with the dashboard read response. The existing Portfolio Control and Portfolio Decision source contracts do not yet expose a common filter AST. This slice therefore does not pretend to apply source-side filters or recompute KPIs; that integration is deferred until an approved source-query contract exists.

## 3. Oracle Help crosswalk

Official HTML Help is the normative source. Each disposition below is limited to this backend slice.

### 3.1 P6 EPPM Version 26 — primary normative parity

| Source topic | Backend disposition | Evidence / gap |
|---|---|---|
| [EPPM V26 Help TOC](https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm) | Partial | The Dashboards and Portlets sections identify dashboard management, content, access, filters, layout and the portfolio-view portlet family. The backend implements the bounded definition and read-model foundation, not the full UI inventory. |
| [Working with Dashboards](https://docs.oracle.com/cd/G48897_01/p6help/en/6665.htm) | Partial | Private and explicitly shared dashboards are represented. EPPM global dashboards and user-interface-view assignment are not implemented in this slice. The Help notes that module access, privileges and project role continue to govern the displayed data; source reauthorization is retained. |
| [Creating Dashboards](https://docs.oracle.com/cd/G48897_01/p6help/en/7826.htm) | Partial | Create and duplicate use cases are implemented. The context selector, copy-from-existing dialog and Save and Close UI are deferred. |
| [Customizing Dashboards](https://docs.oracle.com/cd/G48897_01/p6help/en/7827.htm) | Partial | Content, layout, access and filters are persisted in one definition. Content/Layout/Access tabs and Save and Close interaction are UI work and are not claimed. |
| [Configuring Dashboard Content](https://docs.oracle.com/cd/G48897_01/p6help/en/7831.htm) | Partial | Registered portlet selection and typed configuration are implemented. The full P6 portlet catalogue, per-portlet options/fields and administrative portlet-count configuration are not implemented. The v1 ceiling is twelve. |
| [Portfolio Analysis Page](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/5989.html) | Partial | The existing Portfolio Control Snapshot is consumed as a read model. Side-by-side project-group comparison, waterline analysis and Portfolio Analysis page UI are not implemented here. P6 Help explicitly distinguishes summarized/published data from live data; source identity and freshness are preserved instead of recalculating. |
| [Portfolio Analysis Settings Area](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/portfolioanalysissettingsarea-9110a.html) | Partial | Typed, allow-listed dashboard filter metadata is stored. Bubble, histogram, pie, side-by-side histogram, stacked histogram and scorecard view settings are not implemented by this backend. |
| [Portfolio View Portlet](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/5959.html) | Partial | A read-only Portfolio Control Snapshot portlet and Portfolio Decision portlet are registered. The P6 portfolio-view chart/scorecard designer, project editing, add/delete, export and chart customization are not implemented. |
| [Creating Portfolios](https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_user/7858.htm) | Not Applicable | Portfolio lifecycle and membership are not dashboard responsibilities. Existing portfolio ownership is reused; no duplicate portfolio CRUD is created. |
| [Assigning Projects to a Portfolio](https://docs.oracle.com/cd/G48897_01/p6help/en/7856.htm) | Not Applicable | Portfolio membership is owned by the portfolio capability, not dashboard presentation. |
| [Opening Projects from Dashboard Portlets](https://docs.oracle.com/cd/G48897_01/p6help/en/43796.htm) | Partial | Typed project drill-through references carry project IDs and revisions, and each source project is re-authorized before portlet data is returned. Opening the project from a rendered UI link is deferred. |
| [Portfolio Reports](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-reports/portfolioreports-63041a.html) | Deferred | No report engine or parallel reporting menu is introduced. Existing reporting contracts remain the source; dashboard report integration is a later capability handoff. |

#### Related EPPM HTML topics inspected from the V26 TOC

| Related topic | Disposition | Traceability |
|---|---|---|
| [Configuring Dashboard Access](https://docs.oracle.com/cd/G48897_01/p6help/en/32010.htm) | Partial | Private/user/role sharing and owner/admin mutation boundaries are persisted. Global dashboard access and UI privilege controls are deferred. |
| [Configuring Dashboard Filters](https://docs.oracle.com/cd/G48897_01/p6help/en/32012.htm) | Partial | Allow-listed filters are persisted. P6 filter-locking and per-user filter overrides are not implemented; the source read contract must be extended before filters are applied to source data. |
| [Configuring Dashboard Layout](https://docs.oracle.com/cd/G48897_01/p6help/en/32008.htm) | Partial | Ordered bounded grid placement is persisted. P6 Narrow/Wide and drag/drop UI are deferred. |
| [Working with Portlets](https://docs.oracle.com/cd/G48897_01/p6help/en/47039.htm) | Partial | Portlet identity, layout and typed read response exist. Expand/collapse, help, refresh, maximize/restore, close, print, toolbars and tooltips are UI behavior and are not claimed. |
| [List of Portlets](https://docs.oracle.com/cd/G48897_01/p6help/en/6667.htm) | Partial | The v1 registry deliberately includes only the two stable portfolio source contracts. Personal, project-performance, resource and custom P6 portlets are not silently represented as implemented. |
| [Customizing Portfolio View Portlets](https://docs.oracle.com/cd/G48897_01/p6help/en/44303.htm) | Partial | Source configuration is typed and closed. Chart/scorecard/histogram-specific customization remains deferred. |
| [Creating Portfolio View Portlets](https://docs.oracle.com/cd/G48897_01/p6help/en/44295.htm) | Partial | A registered source-backed portlet can be added to a dashboard definition. Portfolio-view creation, chart type selection and scorecard configuration are not implemented. |

#### Navigation, screen elements and access notes — EPPM V26

The source-family TOC and each required topic were inspected for the path, page controls and security notes below.

- **Working with Dashboards:** Navigation Menu → Dashboard → Dashboards. The page has dashboard tabs and the Manage Dashboards entry. The screen highlights Customize, Content, Custom Portlets/Add, Layout and Access. Content selects portlets; Layout uses arrows or drag/drop and Narrow/Wide; Access selects common user-account controls. Global dashboard edits require the security privilege; multi-user access is controlled by the Access tab; displayed project facts remain subject to module access, privileges and the actor's project role.
- **Creating Dashboards:** Context selector → Dashboard → Manage Dashboards → Create Dashboard → Copy from Existing Dashboard → New Dashboard → Content → General → Dashboard Title → Save and Close. The context selector, copy dialog and save UI are later UI work.
- **Customizing Dashboards:** Navigation Menu → Dashboard → Dashboards → select dashboard → Customize → Content / Layout / Access → Save and Close. Private dashboards and multi-user dashboards created by the actor can be customized; another user's multi-user dashboard cannot; global dashboards require the relevant security privilege. A read-only viewer may override the owner's filter only when the owner has not restricted it.
- **Configuring Dashboard Content:** Navigation Menu → Dashboard → Dashboards → select dashboard → Customize → Dashboard Details → Content. General includes title, filters and maximum displayed rows; category sections expose portlet checkboxes; Portfolio View and Custom Portlets use Add; expanded portlet sections expose options, fields and lists. P6 says the default dashboard ceiling is twelve unless an administrator changes it.
- **Portfolio Analysis Page:** Navigation Menu → Portfolios → Portfolio Analysis. Screen elements are Compare options (vertical/horizontal), Portfolio Analysis toolbar, Settings bar and Work Area. The page compares two project groups and can apply waterline analysis; its summarized/published values can differ from live values, including earned-value baseline behavior. This reinforces the source-revision/freshness boundary and the decision not to calculate KPIs here.
- **Portfolio Analysis Settings Area:** Filter by accepts a portfolio, project code or project; View selects Bubble Chart, Histogram, Pie Chart, Scorecard, Side-by-Side Histogram or Stacked Histogram; More Settings depends on the chosen view. P6 permits a user filter on private dashboards and dashboards the user owns, and on shared/global dashboards only when the owner has not restricted overrides.
- **Portfolio View Portlet:** Navigation Menu → Dashboard → select dashboard → expand Portfolio View. Screen elements include title, chart, scorecard, Customize, Save/Cancel, Add/Delete, Expand/Collapse, Export Spreadsheet and Open Project. A scorecard must be maximized for all options. P6 allows project changes and What-If additions/deletions and up to fifty Portfolio View portlets in some dashboard contexts; this v1 intentionally remains read-only and applies the general twelve-portlet limit.
- **Creating Portfolios:** Context selector → Portfolios → Manage Portfolios → choose Global / Multiple Users / User group → Context → Add → Manual or By Filter. Manual portfolios move projects from Available Projects to Selected Projects; By Filter defines criteria; multi-user portfolios configure Access from Available Users; then Save. Portfolio lifecycle is outside ENT-06A.
- **Assigning Projects to a Portfolio:** Context selector → Portfolios → Open Portfolio (portfolio type, EPS node or project code) → Navigation Menu → Portfolios → Portfolio Analysis → Assign a project to this portfolio → Select Project → Select. P6 disallows assignment while displaying a scenario; Latest Data must be selected.
- **Opening Projects from Dashboard Portlets:** Navigation Menu → Dashboard → select dashboard → expand portlet → select project. P6 requires OBS access, project ownership, resource assignment or activity ownership; only certain project-related portlets expose project links. The backend re-authorizes every referenced project, while rendered link navigation is deferred.
- **Portfolio Reports:** The V26 Reports Help topic is Portfolio Reports. It describes report content, not a dashboard editor path; reports remain in the existing reporting capability and no parallel report engine is added.

Related EPPM screen topics were also checked: Configuring Dashboard Access uses the Customize page's Access tab and a List of Users control; Configuring Dashboard Filters uses the Filter by control at the top of a dashboard or General on the Content tab; Configuring Dashboard Layout uses the Layout tab with Narrow/Wide and up/down/left/right or drag/drop controls; Working with Portlets documents the dashboard-wide filter and titlebar expand/collapse/help/refresh/maximize/restore/close/print controls, plus toolbars and mouseover tips. The List of Portlets groups Personal Data, Portfolio Views, Project Performance, Resources, Custom Portlets and Project Collaboration. The two Portfolio View Portlet customization/creation topics expose chart/scorecard settings, fields and grouping; these remain outside the read-only v1 source contract.

### 3.2 Primavera Cloud — comparative/additive only

Cloud Help is not used to reduce EPPM behavior. Cloud-only tile semantics are not introduced into the v1 registry without a separate approved contract.

| Source topic | Backend disposition | Evidence / gap |
|---|---|---|
| [Portfolios Overview](https://primavera.oraclecloud.com/help/en/user/90205.htm) | Not Applicable | Budget planning, resource planning, negotiation cycles, measures and investor-map portfolio management are not part of this dashboard backend slice. |
| [Create a Portfolio](https://primavera.oraclecloud.com/help/en/user/81716.htm) | Not Applicable | Portfolio creation remains a separate capability. |
| [Add a Project to a Portfolio](https://primavera.oraclecloud.com/help/en/user/81707_1.htm) | Not Applicable | Project membership and refresh/filter lifecycle are not owned by dashboards. |
| [Monitor a Portfolio Scorecard](https://primavera.oraclecloud.com/help/en/user/100616.htm) | Partial | The existing portfolio snapshot can be displayed read-only. Cloud measure recalculation, approved budget/resource scenario views and configurable scorecard detail windows are not implemented. |
| [Measures Overview](https://primavera.oraclecloud.com/help/en/user/99393.htm) | Not Applicable | No new measure/formula/aggregation engine is introduced. |
| [Set a Threshold for a Portfolio or Strategy Measure](https://primavera.oraclecloud.com/help/en/user/99399.htm) | Not Applicable | Measure threshold rules, indicator colors/icons and calculation methods remain outside ENT-06A. |
| [Manage Dashboards](https://primavera.oraclecloud.com/help/en/user/144444.htm) | Partial | Dashboard create/update/duplicate/archive and share persistence are implemented. Cloud workspace tabs, assignment UI, organize UI and owning-workspace transfer are not implemented. |
| [Add a Dashboard](https://primavera.oraclecloud.com/help/en/user/91076.htm) | Partial | A dashboard must contain at least one registered portlet. Name/title/description, context and layout are persisted. Drag/drop editor, Viewer checkbox and chart creation are deferred. |
| [Add a Tile to a Dashboard](https://primavera.oraclecloud.com/help/en/user/91079.htm) | Partial | The bounded portlet registry and layout contract provide the backend equivalent of selecting a supported tile. External URL tiles and arbitrary embedded content are explicitly excluded. |
| [View a Dashboard](https://primavera.oraclecloud.com/help/en/user/102753_2.htm) | Partial | The backend returns authorized read-only data, source identity/revision and freshness. Maximize/minimize, refresh button, multi-level chart drill-down and object-page navigation require the later UI/API handoff. |
| [Working with Portfolio Dashboard Tile Types](https://primavera.oraclecloud.com/help/en/user/99151.htm) | Not Applicable for Cloud-only types | Map Viewer, Gantt, Photo, Text, External Content, Cloud Chart, List, Count and Measure tile semantics are not registered. No external URL, map, formula or duplicate chart engine is introduced. |
| [Analyze Portfolio Performance Using the Investor Map](https://primavera.oraclecloud.com/help/en/user/102917.htm) | Not Applicable | Investor Map bubble axes, size/color, reference lines, quadrants and portfolio view semantics are outside this v1 backend registry. |

#### Navigation, screen elements and access notes — Primavera Cloud

- **Portfolios Overview:** Object selector → Portfolios context. The page covers budget planning/waterline/efficient frontier, resource planning, review-propose-approve cycles, measures, prioritization matrices, summary scorecards, portfolio scorecards, dashboards and Investor Map. ENT-06A consumes an existing read model and does not recreate these planning engines.
- **Create a Portfolio:** Portfolios page → Add Portfolio → add projects/programs/sub-portfolios → Configure Portfolio Details. Configuration can be done from the Portfolios page or the portfolio's Summary & Settings.
- **Add a Project to a Portfolio:** Object selector → Portfolio → View Portfolios List → select portfolio → Project List detail window → Edit Filter → Set Filter Criteria → Assign → Save. A project must be in the same workspace or a child workspace and may belong to multiple portfolios; Refresh Portfolio can be manual or automatic. This remains portfolio-membership ownership, not dashboard ownership.
- **Monitor a Portfolio Scorecard:** Object selector → Portfolio → View Portfolios List → select portfolio → Main Menu → Portfolio Analysis → Scorecard → Settings. Detail windows expose Projects, Programs and Measures tabs and All/Review/Budget Approved/Resource Approved selections. Recalculate Portfolio Measures and Refresh are explicit operations; neither is implemented as a dashboard calculation.
- **Measures Overview:** Measures are configured in the Workspace Measures Dictionary; portfolio/strategy measures must be associated with the portfolio/strategy. Actual/target values can be manual or formula-based and use typed aggregation sources. Measure computation has a scheduled UTC window. No measure dictionary, formula runtime or aggregation engine is added here.
- **Set a Threshold for a Portfolio or Strategy Measure:** Object selector → Workspace → View Summary & Settings → Dictionaries → Measures → select measure → Thresholds detail window → Add. Operator, Value, High Value, Indicator Color/Icon, Goal and Threshold Computation Method configure the threshold. This entire measure/threshold capability is Not Applicable to this dashboard slice.
- **Manage Dashboards:** Dashboards App → Manage Dashboards. Related screen topics include Dashboard Editor, Configure Dashboard Sharing, Assign a Dashboard, Duplicate a Dashboard, Organize Dashboards and Update the Owning Workspace. The editor adds/arranges tiles; sharing controls parent/child workspace inheritance and assignment ownership. Only the isolated duplicate and explicit user/role-share backend concepts are represented here; workspace inheritance and assignment are deferred.
- **Add a Dashboard:** Object selector → Workspace/Project/Portfolio/Program → Main Menu → Dashboards → Manage Dashboards → context tab → Add → Edit page. Fields include Name, Title, Description and Display in Viewer; Available Tiles are searchable/filterable. Selected tile settings include title visibility, column width (one-eighth to full screen), row height (one-eighth to full screen), tile type and type-specific settings. ENT-06A stores a bounded grid definition but does not claim this editor.
- **Add a Tile to a Dashboard:** Same object and Manage Dashboards path → select dashboard → Context menu → Edit → Available Tiles search/filter → drag/drop tile → configure selected tile properties → Save or Save and View. Editing requires the relevant security privilege. Cloud External URL tiles require http/https and preview; arbitrary external URLs are deliberately not admitted by the CUBI registry.
- **View a Dashboard:** Object selector → object → Main Menu → Dashboards → Dashboard List → select dashboard tab. Supported tiles can drill down/back, maximize/minimize, refresh and navigate through More or data fields to object pages; a currency selector affects supported cost tiles. These are UI interactions and remain deferred.
- **Working with Portfolio Dashboard Tile Types:** The page lists Overview, Chart, Gantt, Map Viewer, Photo, Text, List, Count, Measure and External Content. The v1 registry does not implement these Cloud-only tile types; only the two approved P6 EPPM/Enterprise portfolio read contracts are registered.
- **Analyze Portfolio Performance Using the Investor Map:** Object selector → Portfolio → View Portfolios List → select portfolio → Main Menu → Portfolio Analysis → Investor Map. The page configures Projects/Portfolios, X/Y axes, bubble size/color, legend/labels/grid, reference lines and All/Budget Approved/Resource Approved views, then Save View/Save View As. No map or investor-map calculation is introduced.

Additional Cloud Manage Dashboards topics inspected from the official HTML links:

| Related topic | Disposition | Navigation / screen / access note |
|---|---|---|
| [Dashboard Editor](https://primavera.oraclecloud.com/help/en/user/142302.htm) | Deferred | Editor surface for adding/arranging tiles and configuring tile settings; no UI/editor is part of ENT-06A. |
| [Configure Dashboard Sharing](https://primavera.oraclecloud.com/help/en/user/178503.htm) | Not Applicable to v1 | Workspace owner sets Manual/Automatic parent-child sharing and New Project/New Program/New Portfolio defaults from Manage Dashboards tabs; this hierarchy inheritance is not the explicit user/role share model. |
| [Assign a Dashboard](https://primavera.oraclecloud.com/help/en/user/142305.htm) | Deferred | Manage Dashboards → object tab → Assign; assigned dashboard is edited only at owner level. Object-to-object assignment is not in the bounded backend slice. |
| [Duplicate a Dashboard](https://primavera.oraclecloud.com/help/en/user/95937.htm) | Partial | Manage Dashboards → select row → Context menu → Duplicate → enter new Name → Duplicate → Save. Backend duplicate creates a new private dashboard owned by the current actor; UI and workspace-level inheritance are deferred. |
| [Organize Dashboards](https://primavera.oraclecloud.com/help/en/user/96011.htm) | Deferred | Manage Dashboards → select row → Context menu → Move Up/Move Down → Save; Display checkbox hides a dashboard from the current Dashboard List. Tab ordering and display preferences are not in v1. |

### 3.3 P6 Professional Version 26 — overlap and non-interference only

The complete official Professional V26 Help TOC was searched for Dashboard; no dashboard topic is present. The following official topics describe the Professional portfolio-selection/management surface, not the EPPM dashboard/portlet UI:

- [P6 Professional V26 Help TOC](https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm) — no Dashboard match in the TOC.
- [Using Portfolios](https://docs.oracle.com/cd/G48902_01/client_help/en_US/usingportfolios.htm) — lists portfolio selection, creation, user access and project membership topics.
- [Portfolios](https://docs.oracle.com/cd/G48902_01/client_help/en_US/portfolios.htm) — describes manual and filtered portfolios and how portfolios limit the projects loaded in Open Project and Projects.
- [Create a portfolio](https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_a_portfolio.htm) — uses Enterprise → Project Portfolios, General/User Access and Projects tabs.

**Disposition: Not Applicable to dashboard authoring; overlap/non-interference audit completed.** This slice adds no Professional dashboard shell, route, report, duplicate portfolio store or competing portfolio owner. Existing Engineering/Professional portfolio selection and project-loading behavior is untouched.

#### Navigation, screen elements and access notes — P6 Professional V26

The Professional navigation is Enterprise → Project Portfolios → Add → General → (for Shared Users) User Access → Projects → Close. The Project Portfolios dialog has General, User Access and Projects tabs plus Display Options/Details. The Using Portfolios section lists create, add/remove projects, add users, rename, change current portfolio, delete and view details. The Portfolios topic explains that a selected portfolio limits which projects load in Open Project and the Projects window. Manual portfolios are maintained in Professional; filtered portfolios must be created in P6 and cannot be created, modified or deleted in Professional. This is a non-interference boundary only; ENT-06A does not modify this selector or portfolio store.

### 3.4 P6 Team Member Version 26 — applicability

- [P6 Team Member Web Help TOC](https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/toc.htm) — complete TOC searched for Dashboard; no dashboard or portfolio-dashboard authoring topic is present.
- [P6 Team Member Web Overview](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-tm/p6-tmw_overview-51690a.html) — describes assigned activities, status updates, steps, codes/UDFs, related activities, discussions, documents and timesheets.

**Disposition: Not Applicable** to dashboard authoring and portlet registry. If a future portlet exposes Team Member activity/status/timesheet facts, it must use the authoritative Engineering/Team Member source boundary and re-authorize the current actor against each underlying project/activity. Dashboard sharing alone never grants that access.

#### Navigation, screen elements and access notes — P6 Team Member V26

The overview describes the activity-list and timesheet surfaces, not a dashboard authoring page. Users see assigned activities, can filter/sort by project/status, update allowed status fields, use steps/codes/UDFs, inspect related activities, discussions and documents, and submit/review timesheets. The project manager configures the status fields and privileges. The complete Help TOC has no Dashboard topic. These activity and timesheet records remain Engineering/Team Member-owned; a future dashboard tile must re-authorize the underlying project/activity and must not inherit access from a dashboard share.


## 4. Implemented-slice disposition

The statuses below describe the backend v1 work package, not complete P6 EPPM UI parity.

| Feature | Disposition | Evidence |
|---|---|---|
| Closed tenant-scoped dashboard definition and domain validation | Implemented | Versioned contract, strict field validation, context, visibility, revision, bounded portlet layout and typed filter validation. |
| Governed registry for the two approved portfolio source contracts | Implemented | Closed registry with source owner, required permission, context, contract version, typed config and drill-through shape. |
| PostgreSQL persistence, tenant isolation and revision history | Implemented | Dedicated tables, composite tenant/dashboard key, row locking and expected-revision checks. |
| Create/list/read/update/duplicate/share/revoke/archive use cases | Implemented | Authenticated application service with server-derived actor/tenant and owner/admin/share rules. |
| Immutable audit and idempotent create/update retries | Implemented | Same-transaction audit, append-only trigger, idempotency fingerprint and exact update retry recognition. |
| Per-project source authorization on every portlet read | Implemented | Existing source API plus project lifecycle PROJECT_READ authorization for every referenced project. |
| Source freshness and revision reporting | Partial | Snapshot freshness is fresh/stale/missing; Portfolio Decision currently has no generated timestamp and is explicitly unknown. |
| Applying saved dashboard filters to source queries | Deferred | Filter metadata is validated and returned; no shared source filter AST exists yet, so no source filtering or KPI recomputation is claimed. |
| EPPM dashboard UI, route mounting, drill-through navigation and browser acceptance | Deferred | Protected shared composition and UI paths are intentionally not changed in this backend slice. |
| P6 Professional dashboard authoring and Team Member dashboard authoring | Not Applicable | Their official V26 Help surfaces do not define the EPPM dashboard/portlet authoring capability; overlap/applicability checks are recorded above. |

## 4. Acceptance mapping

| Acceptance area | Implementation evidence | Current gate |
|---|---|---|
| Closed versioned contract | enterprise-dashboard.v1.schema.json and EnterpriseDashboard validation | Run contract/unit CI |
| Unknown fields, portlet types, filters and invalid layout rejected | Domain validators and negative unit cases | Run exact-head CI |
| Tenant/actor server-derived | Application service reads authenticated session; caller authority fields rejected | Run authorization tests |
| Private/user/role sharing | Explicit share fields and application checks | Run unit and PostgreSQL tests |
| Owner/admin mutation boundaries | Application boundary and role tests | Run unit and PostgreSQL tests |
| Revocation | Share removal is revision-guarded and audited | Run unit and PostgreSQL tests |
| Optimistic revision conflicts | Row lock + expected revision + guarded update | Run PostgreSQL integration |
| Idempotent create/duplicate | Tenant/owner/key uniqueness, advisory lock and stable fingerprint | Run PostgreSQL integration |
| Audit atomicity and immutability | Same transaction; append-only trigger; RESTRICT foreign key | Run PostgreSQL integration |
| Source authorization | Portfolio source boundary plus per-project lifecycle authorization | Run unit and PostgreSQL CI |
| Stale/missing source states | Explicit fresh/stale/missing/unknown response states | Run unit tests |
| Exact Oracle traceability | Tables in Section 3 | Review source coverage |
| Production route/UI/browser parity | Explicitly not included | Later handoff required |

## 5. Explicit deferrals and non-claims

- No production route or shared composition changes are made in this slice.
- No web, desktop, mobile or workspace-shell files are changed.
- No UI dashboard designer, browser acceptance, visual parity screenshot or drill-through navigation is claimed.
- No caching is implemented.
- Filter metadata is saved and returned, but is not applied to source queries until the source contracts accept a governed filter AST.
- The Portfolio Decision read contract does not currently expose a generated timestamp; its freshness state is therefore unknown, not falsely reported as fresh.
- The two registered portlets are read-only. No portfolio or project record can be changed through a dashboard.
- Cloud-only map, external-content, photo, text, Gantt, measure, budget-planning and investor-map features remain unimplemented.
- A green schema test, unit test or API class alone is not a full P6 parity claim.

## 6. Verification record

Exact-head verification must be attached to the pull request for the final commit:

- Python focused tests: tests/test_enterprise_dashboard.py and tests/test_enterprise_dashboard_repository.py.
- PostgreSQL live test: tests/integration/test_enterprise_dashboard_postgres_live.py, using CONSTRUCTION_PM_POSTGRES_DSN or P6_TEST_POSTGRES_DSN.
- Required repository CI matrix and PostgreSQL integration workflow on the exact final SHA.
- Record workflow URLs, job outcomes and the exact SHA. No local test result or deployment is asserted by this document.
