# ENT-06A — Dashboard & Portlet Registry Backend v1

**Issue:** #2028  
**Implementation branch:** feat/ent06-dashboard-portlet-backend-v1  
**Scope:** isolated CUBI Enterprise backend foundation  
**Status:** backend implementation and Help traceability complete; exact-head CI and Client Typecheck status are tracked on PR #2030.

This document describes the bounded backend slice only. It is not a claim that the complete P6 EPPM dashboard experience, dashboard designer UI, production HTTP routes, browser workflows, or full Oracle parity are complete.

## 0. Preflight and non-interference record

- Base main SHA: 20778a0394dfad0686e2854a4dd043f3b1189172.
- All eight issue-allowed target paths were absent from the base recursive Git tree.
- Current changed-file lists for all 122 open pull requests (including this PR) were checked. None of the other 121 open PRs touches any of the eight target paths. The seven other PRs updated since the original 11:14 preflight were refreshed again; none overlaps the target paths.
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
- Private, explicitly assigned user, explicitly assigned Enterprise role, combined sharing, and P6-style all-tenant global visibility (admin-only).
- An owner-controlled `restrict_filter_override` policy matching the P6 shared-dashboard filter lock.
- Active/archived lifecycle state and optimistic revision.
- Ordered portlet instances with stable instance IDs, exact registered type/version, typed configuration and a two-column Narrow/Wide-compatible layout.
- Typed, allow-listed filters for portfolio/project selection, source status and freshness.
- P6 General-section `max_rows_per_portlet` setting (default 100, bounded 1–500) applied to read projections without changing source totals.
- Creation and update timestamps.

The default portlet ceiling is twelve, matching the EPPM Content tab default. The General-section maximum displayed rows setting is persisted as `max_rows_per_portlet` (CUBI default 100; allowed range 1–500) and applied to the returned project rows while source totals remain intact. Layout coordinates model the EPPM two-column Narrow/Wide choices (six columns for Narrow, twelve for Wide), left/right placement and vertical ordering. Overlapping portlet rectangles and unsupported widths are rejected. This remains presentation-only; the drag/drop and arrow controls are UI work.

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
- enterprise_dashboard_display_preferences (actor-scoped display order/visibility and saved filter overrides)

The repository provides create, get, tenant list, optimistic update, revision history, idempotency and append-only audit. It does not commit or roll back; the caller owns the transaction. Dashboard and audit writes occur in the same transaction. The audit table has a database trigger rejecting UPDATE and DELETE, and its foreign key prevents deletion of a dashboard with audit history.

The application service provides:

- Create and list.
- P6-style displayed/available dashboard catalog, actor-scoped show/hide, deterministic tab reordering, and search.
- Actor-scoped saved Filter by overrides, reset independently from the shared dashboard definition.
- P6 General-section maximum rows per portlet; snapshot output is capped while summary totals and source authorization remain based on the full filtered source set.
- Read dashboard definition.
- Update title, description, portlets and filters.
- Duplicate into a new private dashboard owned by the current actor.
- Assign and revoke explicit user or Enterprise-role shares; user targets are resolved against the canonical identity_users directory and must be active members of the same tenant.
- Assign/revoke all-tenant global visibility; only an Enterprise administrator can create, edit, or revoke a global dashboard.
- Enforce the owner-controlled filter-override restriction.
- Archive.
- Actor-specific dashboard tabs: displayed/available catalog, show/hide, search and order.
- Actor-specific saved Filter by overrides, reset independently from the shared definition.
- Read portlet data through existing source boundaries.

The authenticated session is the sole authority for actor and tenant. Caller-supplied owner or tenant fields are rejected. Enterprise viewers can read but cannot mutate. Owners and Enterprise administrators can manage private/user/role-shared dashboards; global dashboards require Enterprise-administrator mutation, matching the P6 All Users privilege boundary.

### 2.4 Source authorization and freshness

A dashboard share grants access to the dashboard definition only. For each portlet read:

1. The existing Portfolio Control Snapshot or Portfolio Decision boundary is called with an AuthorizationContext derived from the current authenticated session.
2. Portfolio snapshot filters are applied to source-backed project rows. Before returning the filtered projection and its preserved source_refs, every project referenced by the original snapshot is re-authorized through the existing project lifecycle authorize_project(..., PROJECT_READ) boundary. Portfolio Decision affected-project references are all re-authorized before decision data is returned.
3. Tenant, portfolio and source contract identity are checked before returning data.
4. The response preserves source snapshot identity and source revision. Snapshot source revision is represented by the ordered source-reference revision set; a decision uses its persisted decision revision.
5. Snapshot age is explicitly classified as fresh or stale. Missing source records return missing; source contracts without a generated timestamp return unknown.
6. A dashboard share never grants project, activity, document, claim or other source-record access.

No cache is introduced. Drill-through references are emitted as typed IDs and revisions, but no UI navigation or route is mounted in this slice.

### 2.5 Filter contract and P6 override semantics

Filters are stored and validated against a closed key/operator/value catalogue:

- `portfolio_id` (selects the portfolio used by configured portlets; in portfolio context it must equal the context portfolio);
- `project_id` (eq/in selection);
- `project_status` and `membership_status` (applied to Portfolio Control Snapshot project rows);
- `decision_status` (applied to Portfolio Decision);
- `generated_after` / `generated_before` (source timestamp bounds);
- `include_stale` (when false, stale and unknown source data are suppressed while freshness remains explicit).

The filter list is bounded to 20 entries and multi-value selectors to 200 values. The owner may set `restrict_filter_override=true`. When false, a reader may supply a request-scoped override or save an actor-only override in the user's dashboard preferences; when true, only the owner or Enterprise administrator may save or apply an override. A saved user override never mutates the shared dashboard definition and can be reset independently. The read response distinguishes the dashboard's saved filters from the effective/applied filters. Project-code filtering is explicitly deferred because the existing Portfolio Control Snapshot contract does not carry a canonical project-code field; no guessed lookup or parallel project-code source is introduced.

Filters are applied as a read-only projection over existing source records. Snapshot project rows are filtered for presentation, but every project in the underlying source snapshot is re-authorized before any snapshot or source-reference metadata is returned. Filtering never bypasses source-record authorization. A row-count summary is recomputed from filtered source rows; no schedule, cost, progress, EVM, risk or KPI calculation is added. Unsupported filter/source combinations fail closed by returning a filtered-out portlet rather than silently showing unfiltered data. Source snapshot identity/revision is preserved.

## 3. Oracle Help crosswalk

Official HTML Help is the normative source. Each disposition below is limited to this backend slice.

### 3.1 P6 EPPM Version 26 — primary normative parity

| Source topic | Backend disposition | Evidence / gap |
|---|---|---|
| [EPPM V26 Help TOC](https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm) | Partial | The Dashboards and Portlets sections identify dashboard management, content, access, filters, layout and the portfolio-view portlet family. The backend implements the bounded definition and read-model foundation, not the full UI inventory. |
| [Working with Dashboards](https://docs.oracle.com/cd/G48897_01/p6help/en/6665.htm) | Partial | Private, explicit-user, explicit-role and global-to-all-enterprise-users visibility are represented. Global mutation is administrator-only. Actor-scoped displayed/available tabs, show/hide and ordering are implemented; P6 user-interface-view assignment remains deferred. The Help notes that module access, privileges and project role continue to govern displayed data; source reauthorization is retained. |
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
| [Configuring Dashboard Access](https://docs.oracle.com/cd/G48897_01/p6help/en/32010.htm) | Partial | Current User maps to private; List of Users maps to explicit user shares; All Users maps to global visibility, restricted to Enterprise administrators. Explicit Enterprise-role sharing is a CUBI extension. The Access tab and user-picker UI remain deferred. |
| [Configuring Dashboard Filters](https://docs.oracle.com/cd/G48897_01/p6help/en/32012.htm) | Partial | Owner-controlled filter restriction and request-scoped per-user overrides are implemented. Portfolio/project selection and source-backed status/date filters are applied without KPI recalculation. Project-code filtering is deferred because the canonical snapshot contract has no project-code field. |
| [Configuring Dashboard Layout](https://docs.oracle.com/cd/G48897_01/p6help/en/32008.htm) | Partial | Narrow/Wide width and left/right/up/down-compatible coordinates are validated; overlap is rejected and read ordering follows saved coordinates. Drag/drop and arrow controls remain UI work. |
| [Working with Portlets](https://docs.oracle.com/cd/G48897_01/p6help/en/47039.htm) | Partial | Portlet identity, layout and typed read response exist. Expand/collapse, help, refresh, maximize/restore, close, print, toolbars and tooltips are UI behavior and are not claimed. |
| [List of Portlets](https://docs.oracle.com/cd/G48897_01/p6help/en/6667.htm) | Partial | The v1 registry deliberately includes only the two stable portfolio source contracts. Personal, project-performance, resource and custom P6 portlets are not silently represented as implemented. |
| [Customizing Portfolio View Portlets](https://docs.oracle.com/cd/G48897_01/p6help/en/44303.htm) | Partial | Source configuration is typed and closed. Chart/scorecard/histogram-specific customization remains deferred. |
| [Creating Portfolio View Portlets](https://docs.oracle.com/cd/G48897_01/p6help/en/44295.htm) | Partial | A registered source-backed portlet can be added to a dashboard definition. Portfolio-view creation, chart type selection and scorecard configuration are not implemented. |

#### Navigation, screen elements and access notes — EPPM V26

The source-family TOC and each required topic were inspected for the path, page controls and security notes below.

- **Working with Dashboards:** Navigation Menu → Dashboard → Dashboards. The page has dashboard tabs and the Manage Dashboards entry. The screen highlights Customize, Content, Custom Portlets/Add, Layout and Access. Content selects portlets; Layout uses arrows or drag/drop and the Narrow option/Wide option; Access selects common user-account controls. Global dashboard edits require the security privilege; multi-user access is controlled by the Access tab; displayed project facts remain subject to module access, privileges and the actor's project role.
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

The related EPPM screen topics were checked against their HTML screen definitions. The complete topic-by-topic inventory, every dashboard portlet listed in the V26 Help catalogue, and related action/workflow topics are mapped in the following inventory. The backend implements only the bounded read-only portfolio source slice; it does not claim the rest of the P6 portlet catalogue.

#### Complete EPPM V26 dashboard and portlet HTML inventory

The V26 Dashboard, Project Performance Metrics, Portlets and adjacent Portfolio Views TOC branches and linked screen/topic pages were inspected as official HTML. The traceability test requires all 109 exact official HTML URLs to appear in this crosswalk. These rows cover the Manage Dashboards page, the Customize page and its three tabs, display preferences, the portlet framework, every portlet in the Help catalogue, and adjacent action/workflow topics.

| Official HTML topic | Disposition | Navigation, screen/access note and CUBI mapping |
|---|---|---|
| [About Dashboards](https://docs.oracle.com/cd/G48897_01/p6help/en/6608.htm) | Partial | Defines User, Multi-user and Global dashboards. CUBI maps User to private, Multi-user to explicit user/role shares, and Global to tenant-wide Enterprise visibility with administrator-only mutation. P6 user-interface-view assignment remains deferred. |
| [Manage Dashboards Page](https://docs.oracle.com/cd/G48897_01/p6help/en/5937.htm) | Partial | Context selector → Dashboard → Manage Dashboards. The page lists dashboards available in the assigned UI view and currently displayed dashboards; columns include Title, Filter, Available To, Created By and Date Created, plus Create Dashboard, search, Move Up/Down and Delete. CUBI has tenant-scoped list/read and access metadata; UI view assignment, search, display state, tab order and destructive delete are deferred. Archive is the v1 lifecycle operation. |
| [Showing and Hiding Dashboards](https://docs.oracle.com/cd/G48897_01/p6help/en/44266.htm) | Implemented (backend) | Manage Dashboards → Displayed Dashboards / Available Dashboards → show/hide; tab order is actor-scoped and persisted separately from the shared dashboard definition. The visual list and arrow controls remain UI work. |
| [Customize Dashboard Page](https://docs.oracle.com/cd/G48897_01/p6help/en/34915.htm) | Partial | From Manage Dashboards or Dashboard → select a dashboard → Customize. It exposes Content, Layout and Access tabs. Backend fields are persisted, but the page and its save/restore-default interactions are deferred. |
| [Content Tab of the Customize Dashboard Page](https://docs.oracle.com/cd/G48897_01/p6help/en/8107.htm) | Partial | Dashboard Details → Content. General, Portfolio Views, Project Performance, Resources, Personal Information and Custom Portlets sections expose selectable portlets; General options depend on Access settings. CUBI validates the two registered source types only; the P6 catalogue and section-specific editors are not implemented. The default 12-portlet limit is enforced. |
| [Layout Tab of the Customize Dashboard Page](https://docs.oracle.com/cd/G48897_01/p6help/en/8108.htm) | Partial | Dashboard Details → Layout. The work area represents selected portlet size/position; Narrow/Wide and left/up/right/down controls are exposed. CUBI enforces Narrow=6/12 and Wide=12/12 widths, coordinates, ordering and non-overlap. The visual work area, drag/drop and arrow controls are UI work. |
| [Access Tab of the Customize Dashboard Page](https://docs.oracle.com/cd/G48897_01/p6help/en/8106.htm) | Partial | Dashboard Details → Access. Current User, All Users and List of Users are the three P6 options. CUBI implements private, explicit users, explicit Enterprise roles and global-to-all-tenant-Enterprise-users; global mutation is Enterprise-admin-only. The common user picker and P6 security-privilege UI are deferred. |
| [About Portlets](https://docs.oracle.com/cd/G48897_01/p6help/en/36613.htm) | Partial | Portlets are expandable subject-matter windows with data based on association, ownership or filters; P6 portlets may also modify/personalize project/resource/portfolio data. CUBI v1 is intentionally read-only and only uses the two governed source contracts. |
| [Customizing Portlets](https://docs.oracle.com/cd/G48897_01/p6help/en/44952.htm) | Deferred | Per-portlet Customize dialogs are specific to the portlet type. CUBI's typed configuration is implemented for the two registered sources; P6-specific per-field and per-chart dialogs are not. |
| [Customizing the My Risks Portlet](https://docs.oracle.com/cd/G48897_01/p6help/en/44292.htm) | Deferred | Dashboard → My Risks → Customize → Columns / Filter → Save. The risk source and per-user risk filter configuration remain with Engineering; no parallel risk query is created. |
| [Creating Custom Portlets](https://docs.oracle.com/cd/G48897_01/p6help/en/41580.htm) | Not Applicable | P6 allows a user to enter a title and arbitrary URL in Customize → Content → Custom Portlets → Add. This is deliberately not reproduced: the ENT-06A registry prohibits arbitrary external URLs, executable content and user-controlled code. |
| [Custom Portlet of the Dashboards Page](https://docs.oracle.com/cd/G48897_01/p6help/en/37744.htm) | Not Applicable | The P6 custom portlet embeds URL content and supports dynamic {USER}, {USER_ID}, {PASS}, {PROJ} and {PROJ_ID} substitutions. In particular, credential-bearing URL substitution is incompatible with the CUBI security boundary; no URL portlet is registered. |
| [Document Review Portlets](https://docs.oracle.com/cd/G48897_01/p6help/en/44954.htm) | Not Applicable | Document-review workflow is not a read-only portfolio projection. |
| [Document Reviews Portlet of the Dashboards Page](https://docs.oracle.com/cd/G48897_01/p6help/en/6036.htm) | Not Applicable | Dashboard → Document Reviews; Action Required and My Reviews tabs expose review workflows. Content repository availability is an additional dependency, not a portlet read-model contract. |
| [Action Required Tab of the Document Reviews Portlet](https://docs.oracle.com/cd/G48897_01/p6help/en/7753.htm) | Not Applicable | Lists assigned document reviews with initiator/date/due-date and approve/reject actions; document workflow remains out of scope. |
| [My Reviews Tab of the Document Reviews Portlet](https://docs.oracle.com/cd/G48897_01/p6help/en/7771.htm) | Not Applicable | Lists reviews initiated by the current actor with status and due dates; terminate/review operations remain out of scope. |
| [Participating in Document Reviews](https://docs.oracle.com/cd/G48897_01/p6help/en/7904.htm) | Not Applicable | Dashboard → Document Reviews → Action Required → View/Details → Approve or Reject. This mutates document-review workflow and requires a separate document permission boundary; not part of ENT-06A. |
| [Terminating Document Reviews](https://docs.oracle.com/cd/G48897_01/p6help/en/7901.htm) | Not Applicable | Dashboard → Document Reviews → My Reviews → Terminate. This is an action workflow and is not exposed by the read-only portlet registry. |
| [Sending Email to Resource Teams](https://docs.oracle.com/cd/G48897_01/p6help/en/44309_1.htm) | Not Applicable | Communication/resource-team portlet → Filter by → email resource team → edit recipients/message → Send Email. This is an outbound communication action, not a read-only portlet contract. |
| [Assigning Resources to Unstaffed Activities Using Open Requests for Resources Portlet](https://docs.oracle.com/cd/G48897_01/p6help/en/61157.htm) | Not Applicable | Open Requests for Resources → select role/project → Resource Staffing → Assign Resource. This mutates Engineering resource assignments and remains outside Enterprise dashboard scope. |
| [Sending Email Notifications about Resource Assignments](https://docs.oracle.com/cd/G48897_01/p6help/en/8009.htm) | Not Applicable | My Preferences → Global → General → send email on assignment changes. This is a resource notification preference and is not a dashboard read contract. |

#### Full P6 EPPM List of Portlets — per-portlet disposition

P6 navigation for each row is Navigation Menu → Dashboard → Dashboards → select dashboard → expand the named portlet. Every portlet remains subject to the P6 module/role/project access notes; CUBI does not infer source access from dashboard sharing.

| P6 V26 portlet HTML | Source behavior / Help screen elements | ENT-06A disposition |
|---|---|---|
| [Communication Center](https://docs.oracle.com/cd/G48897_01/p6help/en/5947.htm) | Project/team member association, contact details and Send an email action. | Not Applicable — messaging and recipient access are not read-only portfolio facts. |
| [My Activities](https://docs.oracle.com/cd/G48897_01/p6help/en/5954.htm) | Activities assigned as a resource or activity owner; dates, remaining units and primary-resource state; access is limited by assignment/project access. | Deferred — requires the Engineering activity/assignment read contract and actor-specific assignment authorization. |
| [My Issues](https://docs.oracle.com/cd/G48897_01/p6help/en/5956.htm) | Associated project issues with Add, Delete, Search, Customize View, Print and Email Issue Details controls. | Not Applicable — issue creation/deletion and project-issue ownership require a separate workflow/source capability. |
| [My Projects](https://docs.oracle.com/cd/G48897_01/p6help/en/6034.htm) | Projects where the actor is owner, has OBS access, or is assigned as resource/activity owner; start/finish, percent complete, last summarized and owner fields. | Deferred — source access semantics are noted; the current Portfolio Control Snapshot has a narrower project summary and is not asserted to be a My Projects replacement. |
| [My Calendar](https://docs.oracle.com/cd/G48897_01/p6help/en/5946.htm) | Weekly activity/milestone calendar with previous/next week and project/activity navigation. | Deferred — requires a calendar/activity read contract and user assignment authorization. |
| [My Risks](https://docs.oracle.com/cd/G48897_01/p6help/en/5958.htm) | Associated risk records, threat/opportunity, status, owner, notes and user-defined fields; per-portlet column/type customization. | Deferred — use the Engineering risk source and authorization boundary; no parallel risk store or calculation is added. |
| [Portfolio View](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/5959.html) | Chart/scorecard, Customize, Save/Cancel, Add/Delete What-If projects, Expand/Collapse, Export Spreadsheet and Open Project. Summary data is as of the last summarizer run; up to 50 Portfolio View portlets may be allowed in applicable contexts. | Partial — the CUBI snapshot/decision read portlets provide source-backed read-only portfolio data and revision/freshness. P6 chart/scorecard editing, What-If mutation, export and 50-view semantics are not implemented; the v1 dashboard ceiling remains 12. |
| [Earned Value Performance](https://docs.oracle.com/cd/G48897_01/p6help/en/5950.htm) | Current/forecast SV, CV and labor-unit variance with threshold indicators and user preference for costs or labor units. | Not Applicable — Engineering remains authoritative for EVM calculations; no Enterprise calculation or threshold engine is added. |
| [Schedule Performance](https://docs.oracle.com/cd/G48897_01/p6help/en/5968.htm) | Current/forecast schedule, cost and labor-unit variances, baseline comparisons and performance thresholds. | Not Applicable — schedule/CPM and cost calculations remain Engineering-owned. |
| [Index Performance](https://docs.oracle.com/cd/G48897_01/p6help/en/5951.htm) | SPI, CPI and TCPI with performance threshold indicators. | Not Applicable — no duplicated index or earned-value calculations. |
| [Project Statistics](https://docs.oracle.com/cd/G48897_01/p6help/en/6041.htm) | Configurable row/column project and WBS data, Expand/Collapse, Customize View, Print and Search. | Deferred — requires an approved Engineering project/WBS projection and per-project authorization. |
| [Project Health](https://docs.oracle.com/cd/G48897_01/p6help/en/5962.htm) | Project/portfolio status indicators (Exceptional, Acceptable, Warning, Critical) based on thresholds in My Preferences. | Deferred — threshold configuration and status derivation must remain with the authoritative Engineering read model. |
| [Project Notebooks](https://docs.oracle.com/cd/G48897_01/p6help/en/5964.htm) | Notebook topics and descriptions; topic links can open an editor and HTML content. | Not Applicable — project notebook/document ownership and edit permissions are outside the two registered read contracts. |
| [Project Gantt Chart](https://docs.oracle.com/cd/G48897_01/p6help/en/6037.htm) | Project bars, progress, remaining effort, start/finish milestones, baseline milestones, activity-code filters and project navigation. | Not Applicable — no Gantt, schedule or critical-path renderer/calculation is added to Enterprise. |
| [Open Requests for Resources](https://docs.oracle.com/cd/G48897_01/p6help/en/5935.htm) | Role-team staffing requests, unstaffed/staffed units and links into Resource Staffing. | Not Applicable — staffing and resource assignment remain Engineering-owned actions. |


#### Dashboard Content-tab sections — detailed HTML screen mapping

| Official HTML topic | Disposition | Navigation, screen elements, access and CUBI mapping |
|---|---|---|
| [General Section of the Content Tab](https://docs.oracle.com/cd/G48897_01/p6help/en/31954.htm) | Implemented / Partial | Navigation Menu → Dashboard → Dashboards → Customize → Content → General. P6 exposes Dashboard Title, Dashboard Filter, Restrict users from changing dashboard filter, User Filter and Maximum number of rows displayed. CUBI persists the owner filter lock, actor-scoped saved overrides and `max_rows_per_portlet` (default 100, range 1–500); title/filter editor UI and P6 project-code filtering remain deferred. |
| [Portfolio Views Section of the Content Tab](https://docs.oracle.com/cd/G48897_01/p6help/en/31978.htm) | Partial | Customize → Content → Portfolio Views. P6 exposes Add/Remove, view checkbox, Title, Type, X/Y axes, Group By, Color Theme, 3-D, gridlines, all-axis-values, Bubble Size and Pie data/group labels/percentage. CUBI has typed configuration for two approved portfolio read contracts only; chart/scorecard/histogram designers and field-level portfolio-view customization are not implemented. |
| [Project Performance Section of the Content Tab](https://docs.oracle.com/cd/G48897_01/p6help/en/31955.htm) | Not Applicable / Deferred | Customize → Content → Project Performance exposes Schedule Performance, Earned Value Performance, Index Performance (SPI/CPI/TCPI), Project Statistics, Project Health, Project Notebooks and Project Gantt Chart. These calculations and source records remain Engineering-owned; no duplicate KPI, threshold, schedule or Gantt engine is added. |
| [Resources Section of the Content Tab](https://docs.oracle.com/cd/G48897_01/p6help/en/31964.htm) | Not Applicable | Customize → Content → Resources exposes Open Requests for Resources, all-projects vs dashboard-filter display, Role by Project / Project by Role / Role by Project by Project Codes, Role Team and Project Code. The portlet leads to Resource Staffing and assignment mutations; it is not a read-only Enterprise portlet. |
| [Personal Information Section of the Content Tab](https://docs.oracle.com/cd/G48897_01/p6help/en/31974.htm) | Deferred / Not Applicable | Customize → Content → Personal Information exposes My Projects, My Activities, My Risks, My Issues, Communication Center, My Documents and My Calendar. Access depends on project rights, assignment/resource ownership and project-owner status; My Documents is also shown in this section although it is not listed in the List of Portlets catalogue. These require their own authoritative read contracts and source authorization, and are not implied by dashboard sharing. |
| [Custom Portlets Section of the Content Tab](https://docs.oracle.com/cd/G48897_01/p6help/en/31977.htm) | Not Applicable | Customize → Content → Custom Portlets → Add exposes a title and URL content. P6 supports dynamic `{USER}`, `{USER_ID}`, `{PASS}`, `{PROJ}` and `{PROJ_ID}` substitutions. CUBI explicitly rejects arbitrary URL/executable content and especially credential-bearing `{PASS}` substitution; no custom URL portlet is registered. |

#### Project Performance Metrics branch — source ownership and non-interference

| Official HTML topic | Disposition | Navigation / screen / source-owner evidence |
|---|---|---|
| [About Project Performance Metrics](https://docs.oracle.com/cd/G48897_01/p6help/en/44844.htm) | Not Applicable | Defines schedule, earned-value and index metrics and project health thresholds. These are Engineering source calculations, not Enterprise dashboard calculations. |
| [Assessing Project Performance](https://docs.oracle.com/cd/G48897_01/p6help/en/43935.htm) | Not Applicable | Navigation Menu → Dashboard → Dashboards → expand Earned Value Performance, Schedule Performance, Index Performance or Project Statistics. P6 drills from project to WBS performance; this requires authoritative Engineering read models and is not recreated here. |
| [Assessing Project Health](https://docs.oracle.com/cd/G48897_01/p6help/en/43938.htm) | Not Applicable | Navigation Menu → Dashboard → Dashboards → expand Project Health. Health is derived from schedule-performance thresholds and remains Engineering-owned. |
| [Customizing Project Statistics](https://docs.oracle.com/cd/G48897_01/p6help/en/43951.htm) | Deferred | Customize → Content → Project Performance → Project Statistics → Customize Project Statistics → Columns / Group. A future projection needs an approved project/WBS source contract; the dashboard registry does not invent it. |
| [Identifying Critical Activities Behind Schedule](https://docs.oracle.com/cd/G48897_01/p6help/en/43937.htm) | Not Applicable | Projects → Activities → Filters → Manage Filters (Critical = Yes), then Customize View → Columns / Filtering / Sorting. This is activity scheduling/float analysis, not a dashboard portlet contract. |
| [About Performance Thresholds](https://docs.oracle.com/cd/G48897_01/p6help/en/6634.htm) | Not Applicable | Describes Exceptional, Acceptable, Warning and Critical ranges for WBS/project/portfolio metrics. No threshold calculation or indicator engine is added. |
| [Working with Performance Thresholds](https://docs.oracle.com/cd/G48897_01/p6help/en/6691.htm) | Not Applicable | User menu → My Preferences → Global → Performance Threshold. Thresholds depend on schedule, earned-value and index calculations; they remain with Engineering. |
| [About Cost Performance Index (CPI)](https://docs.oracle.com/cd/G48897_01/p6help/en/43460.htm) | Not Applicable | CPI = Earned Value Cost / Actual Cost. The dashboard never recomputes CPI. |
| [About Schedule Performance Index (SPI)](https://docs.oracle.com/cd/G48897_01/p6help/en/43459.htm) | Not Applicable | SPI = Earned Value Cost / Planned Value Cost. The dashboard never recomputes SPI. |
| [About To-Complete Performance Index (TCPI)](https://docs.oracle.com/cd/G48897_01/p6help/en/43948.htm) | Not Applicable | TCPI is a projection from remaining work and funds (BAC/EAC). The dashboard never recomputes TCPI. |

#### Portfolio lifecycle and Portfolio View branches — adjacent EPPM HTML

| Official HTML topic | Disposition | Navigation / screen / ownership mapping |
|---|---|---|
| [About Portfolios](https://docs.oracle.com/cd/G48897_01/p6help/en/6611.htm) | Partial | Defines portfolios as project collections used to filter dashboards and view group summaries. CUBI consumes the existing Portfolio Control Snapshot; it does not own portfolio membership. |
| [Working with Portfolios](https://docs.oracle.com/cd/G48897_01/p6help/en/6671.htm) | Not Applicable | Portfolio context requires existing projects and a configured portfolio; filtered portfolios refresh on an administrative stale-period interval. Portfolio lifecycle and refresh remain with the source owner. |
| [Opening Portfolios](https://docs.oracle.com/cd/G48897_01/p6help/en/7866.htm) | Not Applicable | Context selector → Portfolios → Open Portfolio → Organize By (EPS / Portfolio / Project Code) → select group → Open. This is P6 portfolio selection state, not dashboard state. |
| [Creating Projects While Working with Portfolios](https://docs.oracle.com/cd/G48897_01/p6help/en/7859.htm) | Not Applicable | P6 permits project creation from dashboard scorecards and Portfolio Analysis. ENT-06A is read-only and cannot create projects. |
| [Creating Projects in a Portfolio View Scorecard Portlet](https://docs.oracle.com/cd/G48897_01/p6help/en/7870.htm) | Not Applicable | Dashboard → maximize Portfolio View scorecard → Add → set default EPS/Responsible Manager → edit new project row → Save. This is a project-creation workflow and is explicitly excluded. |
| [Creating Projects on the Portfolio Analysis Page](https://docs.oracle.com/cd/G48897_01/p6help/en/7869.htm) | Not Applicable | Portfolios → Portfolio Analysis → select scorecard row → Add Project → specify project ID/name/EPS/manager/start date → Create. No project creation is exposed by Enterprise dashboards. |
| [Defining Performance Thresholds](https://docs.oracle.com/cd/G48897_01/p6help/en/7857.htm) | Not Applicable | User menu → My Preferences → Global → Performance Threshold; logical threshold constraints govern schedule/EVM/index indicators. These remain Engineering-owned. |
| [About Portfolio Views](https://docs.oracle.com/cd/G48897_01/p6help/en/14087.htm) | Partial | Portfolio views are scorecards/charts shared on dashboards or used in Portfolio Analysis. CUBI's two approved read portlets are not asserted to be replacements for named P6 views. |
| [Working with Portfolio Views](https://docs.oracle.com/cd/G48897_01/p6help/en/14090.htm) | Not Applicable | Manage Portfolio Views supports scorecard, bubble, pie, basic/side-by-side/stacked histogram and editable fields/waterline. Charting and project mutation are not in the v1 registry. |
| [Creating Portfolio Views](https://docs.oracle.com/cd/G48897_01/p6help/en/7868.htm) | Deferred | Portfolios → Manage Portfolio Views → Create View → select New/Existing → configure Type-specific details → Save. CUBI portlet registry types are fixed by approved source contracts; no separate portfolio-view designer/store is introduced. |
| [Working with Portfolio View Scorecards](https://docs.oracle.com/cd/G48897_01/p6help/en/9116.htm) | Not Applicable | Scorecards expose up to 30 data columns, waterline analysis, editing, adding and deleting projects. CUBI's Portfolio Control Snapshot is read-only and cannot emulate those mutating scorecard semantics. |
| [Working with Portfolio View Bubble Charts](https://docs.oracle.com/cd/G48897_01/p6help/en/9113.htm) | Not Applicable | Portfolio Analysis bubble charts map X/Y fields, bubble size and Group By, with legends and source-data tooltips. No chart or metric aggregation engine is introduced. |
| [Working with Portfolio View Pie Charts](https://docs.oracle.com/cd/G48897_01/p6help/en/9115.htm) | Not Applicable | Portfolio Analysis pie charts group source fields into proportionate slices and legends. This requires chart aggregation and remains outside the read-model projection. |
| [Working with Portfolio View Histograms](https://docs.oracle.com/cd/G48897_01/p6help/en/9114.htm) | Not Applicable | Portfolio Analysis supports basic, side-by-side (Group By) and stacked (Stack By) histograms. No histogram renderer or calculation is added. |
| [About What-if Analysis](https://docs.oracle.com/cd/G48897_01/p6help/en/36491.htm) | Not Applicable | P6 What-if projects model scenario impact on costs/investments and business goals. Scenario creation/calculation is not part of this read-only dashboard backend. |

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
| [Update the Owning Workspace of a Dashboard](https://primavera.oraclecloud.com/help/en/user/100788.htm) | Not Applicable | Workspace hierarchy ownership transfer is not in the tenant-scoped CUBI dashboard definition contract. No cross-workspace transfer or inheritance is added. |

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
| Applying saved dashboard filters and P6-style per-user overrides | Implemented / Partial | Typed portfolio/project/status/date/freshness filters are applied to existing read-model projections; owner filter lock, request-scoped overrides and actor-only saved/resettable overrides are implemented. Project-code filter remains deferred because the source contract does not expose that field. No KPI calculation is added. |
| P6 General-section maximum displayed rows | Implemented | `max_rows_per_portlet` is persisted (default 100, range 1–500); response includes `row_limit` and `truncated`, while summary totals remain based on the full filtered source set. |
| P6 Manage Dashboards display catalog and tabs | Implemented (backend) | Actor-scoped displayed/available lists, show/hide, search and deterministic ordering are stored separately from dashboard definitions. UI view assignment and visual controls remain deferred. |
| EPPM dashboard UI, route mounting, drill-through navigation and browser acceptance | Deferred | Protected shared composition and UI paths are intentionally not changed in this backend slice. |
| P6 Professional dashboard authoring and Team Member dashboard authoring | Not Applicable | Their official V26 Help surfaces do not define the EPPM dashboard/portlet authoring capability; overlap/applicability checks are recorded above. |

## 4. Acceptance mapping

| Acceptance area | Implementation evidence | Current gate |
|---|---|---|
| Closed versioned contract | enterprise-dashboard.v1.schema.json and EnterpriseDashboard validation | Run contract/unit CI |
| Unknown fields, portlet types, filters and invalid layout rejected | Domain validators and negative unit cases | Run exact-head CI |
| Tenant/actor server-derived | Application service reads authenticated session; caller authority fields rejected | Run authorization tests |
| Private/user/role/global sharing | Explicit share fields, active same-tenant identity lookup for user shares, and admin-only global access | Run unit and PostgreSQL tests |
| Owner/admin mutation boundaries | Application boundary; global dashboards are admin-only | Run unit and PostgreSQL tests |
| Revocation | Share removal is revision-guarded and audited | Run unit and PostgreSQL tests |
| Optimistic revision conflicts | Row lock + expected revision + guarded update | Run PostgreSQL integration |
| Idempotent create/duplicate | Tenant/owner/key uniqueness, advisory lock and stable fingerprint | Run PostgreSQL integration |
| Audit atomicity and immutability | Same transaction; append-only trigger; RESTRICT foreign key | Run PostgreSQL integration |
| Source authorization | Portfolio source boundary plus per-project lifecycle authorization | Run unit and PostgreSQL CI |
| Stale/missing/filtered-out source states | Explicit fresh/stale/missing/unknown freshness, filtered_out flag and separate saved/applied filter lists | Run unit tests |
| Exact Oracle traceability | 109 official HTML URLs across the EPPM dashboard, content, portlet, performance and portfolio branches plus Cloud/Professional/Team Member comparisons | Review source coverage |
| P6 row limit and actor-specific dashboard display | Domain, repository, application service and unit/PostgreSQL tests | Exact-head CI |
| Production route/UI/browser parity | Explicitly not included | Later handoff required |

## 5. Explicit deferrals and non-claims

- No production route or shared composition changes are made in this slice.
- No web, desktop, mobile or workspace-shell files are changed.
- No UI dashboard designer, browser acceptance, visual parity screenshot, P6 user-interface-view assignment or drill-through navigation is claimed. Actor-specific dashboard display preferences and saved filters are backend-complete only.
- No caching is implemented.
- Typed filters are applied at the read-model projection boundary. Project-code filtering and source-specific filters that cannot be evaluated from the registered contracts fail closed / remain deferred; no ungoverned query AST or KPI engine is introduced.
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
