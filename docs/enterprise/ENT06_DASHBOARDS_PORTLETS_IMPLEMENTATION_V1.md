# ENT-06A — Dashboard & Portlet Registry Backend v1

**Issue:** #2028  
**Implementation branch:** feat/ent06-dashboard-portlet-backend-v1  
**Scope:** isolated CUBI Enterprise backend foundation  
**Status:** implementation candidate; exact-head CI and PostgreSQL evidence pending

This document describes the bounded backend slice only. It is not a claim that the complete P6 EPPM dashboard experience, dashboard designer UI, production HTTP routes, browser workflows, or full Oracle parity are complete.

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

### 3.3 P6 Professional Version 26 — overlap and non-interference only

The complete official Professional V26 Help TOC was searched for Dashboard; no dashboard topic is present. The following official topics describe the Professional portfolio-selection/management surface, not the EPPM dashboard/portlet UI:

- [P6 Professional V26 Help TOC](https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm) — no Dashboard match in the TOC.
- [Using Portfolios](https://docs.oracle.com/cd/G48902_01/client_help/en_US/usingportfolios.htm) — lists portfolio selection, creation, user access and project membership topics.
- [Portfolios](https://docs.oracle.com/cd/G48902_01/client_help/en_US/portfolios.htm) — describes manual and filtered portfolios and how portfolios limit the projects loaded in Open Project and Projects.
- [Create a portfolio](https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_a_portfolio.htm) — uses Enterprise → Project Portfolios, General/User Access and Projects tabs.

**Disposition: Not Applicable to dashboard authoring; overlap/non-interference audit completed.** This slice adds no Professional dashboard shell, route, report, duplicate portfolio store or competing portfolio owner. Existing Engineering/Professional portfolio selection and project-loading behavior is untouched.

### 3.4 P6 Team Member Version 26 — applicability

- [P6 Team Member Web Help TOC](https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/toc.htm) — complete TOC searched for Dashboard; no dashboard or portfolio-dashboard authoring topic is present.
- [P6 Team Member Web Overview](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-tm/p6-tmw_overview-51690a.html) — describes assigned activities, status updates, steps, codes/UDFs, related activities, discussions, documents and timesheets.

**Disposition: Not Applicable** to dashboard authoring and portlet registry. If a future portlet exposes Team Member activity/status/timesheet facts, it must use the authoritative Engineering/Team Member source boundary and re-authorize the current actor against each underlying project/activity. Dashboard sharing alone never grants that access.

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
