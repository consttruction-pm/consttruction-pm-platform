# CUBI Enterprise — page-by-page Help, feature and icon crosswalk (V26)

**Authority:** Product-owner acceptance specification  
**Reference baseline:** Oracle P6 EPPM Version 26 HTML Help, baseline G48897-01 (May 2026).  
**Repository audit revision:** `main` at `3be46c10b13586c6848fed291923eeb8c0b5417c` before this document.  
**Scope:** Every page registered in `apps/web/src/enterprise/router.ts` and rendered by `apps/web/src/enterprise/app.ts`, including shared entry pages needed to reach Enterprise.  
**Official Preview:** The one canonical URL in `docs/standards/CUBI_PAGE_BY_PAGE_DESIGN_AND_ACCEPTANCE.md`.  
**Important:** This is a complete reference/acceptance map, not a claim that the current UI has achieved the visual match. Current code evidence is distinguished from required target behavior.

---

## 1. Verified application inventory and inheritance

The actual Enterprise application is a separate document under `/cubi/*`. The router declares 26 PageIds; `app.ts` registers 24 renderers plus the login and not-found flows. It mounts a shared Enterprise shell with sidebar, top bar, breadcrumb, language selector, notifications, contextual Help link, session identity and page body. All Enterprise pages inherit that shell unless explicitly marked public/entry.

**Canonical inheritance chain**

`/cubi/{page}/` → `apps/web/src/enterprise/router.ts` → `apps/web/src/enterprise/app.ts` → shared shell (`styles.ts`, `ui.ts`, `session.ts`, `api.ts`) → one page renderer under `apps/web/src/enterprise/pages/` → its page-specific service/API and server authorization → tenant/project-scoped persistent source.

The Engineering workspace is a separate application and calculation authority. Enterprise must not mount an Engineering shell or duplicate Engineering scheduling calculations. Project schedule, resource, EVM, risk and document source records remain owned by their authoritative services and are read by Enterprise through permission-checked, revision-aware read models.

### 1.1 Current router inventory (read from source, not inferred from the older 16-row registry)

| PageId | Current canonical route | Renderer / owner | Page class | Help mapping |
|---|---|---|---|---|
| home | `/cubi/` | `pages/home.ts` | Public entry | CUBI-owned |
| login | `/cubi/login/` | `pages/login.ts` | Authentication | CUBI-owned |
| roles | `/cubi/roles/` | `pages/roles.ts` | Authenticated access information | About Users / security profiles |
| workbench | `/cubi/workbench/` (navigation resolves to shared `/workbench/`) | `pages/workbench.ts` | Shared Personal Workbench | Dashboard / portlets concepts; CUBI post-login flow is CUBI-owned |
| environments | `/cubi/environments/` (navigation resolves to shared `/workbench/`) | `pages/environments.ts` | Shared environment selection | CUBI-owned |
| dashboard | `/cubi/enterprise/dashboard/` | `pages/dashboard.ts` | Enterprise | Dashboards / portlets |
| portfolio | `/cubi/enterprise/portfolio/` | `pages/portfolio.ts` | Enterprise | Portfolios / Portfolio Views |
| projects | `/cubi/enterprise/projects/` | `pages/projects.ts` | Enterprise | Projects / EPS |
| access | `/cubi/enterprise/access/` | `pages/access.ts` | Enterprise organization-scoped | Users / security profiles / OBS concepts |
| tasks | `/cubi/enterprise/tasks/` | `pages/tasks.ts` | Enterprise | Team Member status updates; CUBI generic tasks are a separate contract |
| workflows | `/cubi/enterprise/workflows/` | `pages/workflows.ts` | Enterprise | Team Member review configuration; CUBI workflow graph is CUBI-owned |
| approvals | `/cubi/enterprise/approvals/` | `pages/approvals.ts` | Enterprise | Reviewing / accepting / rejecting Team Member status updates |
| resources | `/cubi/enterprise/resources/` | `pages/resources.ts` | Enterprise read model | Capacity Planning / Resource Analysis |
| reports | `/cubi/enterprise/reports/` | `pages/reports.ts` | Enterprise | Report settings / reports |
| knowledge | `/cubi/enterprise/knowledge/` | `pages/knowledge.ts` | CUBI-owned | No exact EPPM equivalent; CUBI knowledge and assistant source policy |
| risks | `/cubi/enterprise/risks/` | `pages/registers.ts` | Enterprise read model | About Risks / Working with Project Risks |
| documents | `/cubi/enterprise/documents/` | `pages/registers.ts` | Enterprise read model | About Documents / Document Reviews |
| eps | `/cubi/enterprise/eps/` | `pages/registers.ts` | Enterprise project hierarchy | EPS / Configuring EPS Views |
| memberActivities | `/cubi/enterprise/member-activities/` | `pages/member-activities.ts` | Enterprise read-only bridge | Team Member Activities / status updates; Engineering remains owner |
| timesheets | `/cubi/enterprise/timesheets/` | `pages/registers.ts` | Enterprise | [About Timesheets](https://docs.oracle.com/cd/G48897_01/p6help/en/6610.htm) / [Working with Timesheets](https://docs.oracle.com/cd/G48897_01/p6help/en/6670.htm) / [Approving or Rejecting Timesheets](https://docs.oracle.com/cd/G48897_01/p6help/en/7847.htm) |
| notifications | `/cubi/enterprise/notifications/` | `pages/registers.ts` | Enterprise | Email Notifications / Notifications settings |
| settings | `/cubi/enterprise/settings/` | `pages/registers.ts` | Enterprise | My Preferences / Application Settings |
| forms | `/cubi/enterprise/forms/` | `pages/registers.ts` | CUBI-owned | No exact equivalent; shared CUBI Form Builder |
| audit | `/cubi/enterprise/audit/` | `pages/audit.ts` | Enterprise read-only | Table Auditing / Viewing Audit Data |
| directory | `/cubi/enterprise/directory/` | `pages/registers.ts` | Enterprise organization-scoped | Users / OBS / Security Profiles |
| not-found | resolved fallback | `app.ts` | System state | CUBI-owned |

### 1.2 Legacy traceability mismatch — must be resolved, not hidden

The previous `docs/traceability/enterprise-v26.json` lists 16 routes such as `/enterprise/`, `/enterprise/organization/`, `/enterprise/admin/`, `/enterprise/portal/`, and `/enterprise/operations/`. Those are NOT the canonical routes declared by the current Enterprise router. The current router has 26 PageIds under `/cubi/*`, and the older matrix omits several pages (knowledge, EPS, timesheets, notifications, settings, forms, audit, directory, member activities, access).

Required migration of traceability references:

| Old registry entry/route | Current route(s) | Action |
|---|---|---|
| ENT-HOME `/environments/` | shared `/workbench/`; environment route currently redirects through `appHref` | CUBI-owned shared flow; do not treat as Enterprise module page |
| ENT-DASHBOARDS `/enterprise/` | `/cubi/enterprise/dashboard/` | Update canonical route |
| ENT-PORTFOLIO `/enterprise/portfolio/` | `/cubi/enterprise/portfolio/` | Update canonical route |
| ENT-PROJECTS `/enterprise/projects/` | `/cubi/enterprise/projects/` | Update canonical route |
| ENT-TEAM-TASKS `/enterprise/tasks/` | `/cubi/enterprise/tasks/` | Update canonical route |
| ENT-FEEDBACK-APPROVAL `/enterprise/approvals/` | `/cubi/enterprise/approvals/` | Update canonical route |
| ENT-OPERATIONS `/enterprise/operations/` | No dedicated current PageId | Do not invent a route; scheduled services remain a documented future gap |
| ENT-WORKFLOW `/enterprise/workflows/` | `/cubi/enterprise/workflows/` | Update canonical route |
| ENT-ORG-ACCESS `/enterprise/organization/` | `/cubi/enterprise/access/` and `/cubi/enterprise/directory/` | Split access governance from directory |
| ENT-PORTAL `/enterprise/portal/` | `/cubi/enterprise/projects/` (project portal tabs) | Map to project detail only; no separate route unless approved |
| ENT-INTEGRATION `/enterprise/integrations/` | No current Enterprise PageId | Record as missing route / future capability; do not fake it |
| ENT-RESOURCES `/enterprise/resources/` | `/cubi/enterprise/resources/` | Update canonical route |
| ENT-REPORTS `/enterprise/reports/` | `/cubi/enterprise/reports/` | Update canonical route |
| ENT-ADMIN `/enterprise/admin/` | `/cubi/enterprise/access/`, `settings/`, `audit/` | Split by actual ownership |
| ENT-DOCUMENTS `/enterprise/documents/` | `/cubi/enterprise/documents/` | Update canonical route |
| ENT-RISKS-ISSUES `/enterprise/risks/` | `/cubi/enterprise/risks/` | Update canonical route |

No old route should be silently redirected or deleted as part of a documentation-only task. Runtime route migration requires a separate scoped change and tests.

---

## 2. Help source register — exact V26 topics

The following official EPPM Help topics are the source of behavior. The main table-of-contents link is included so reviewers can navigate related subtopics and screen illustrations.

- [P6 EPPM V26 Help — Table of Contents](https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm)
- [Working with the P6 User Interface](https://docs.oracle.com/cd/G48897_01/p6help/en/9038.htm) — navigation, shortcuts, pages, tabs, dialogs, detail windows, portlets, fields, lists, buttons, links, tables, charts, calendars; screen-highlight callouts and context menu.
- [About Dashboards](https://docs.oracle.com/cd/G48897_01/p6help/en/6608.htm), [Working with Dashboards](https://docs.oracle.com/cd/G48897_01/p6help/en/6665.htm), [Customizing Dashboards](https://docs.oracle.com/cd/G48897_01/p6help/en/7827.htm), [Configuring Dashboard Content](https://docs.oracle.com/cd/G48897_01/p6help/en/7831.htm).
- [About Portfolios](https://docs.oracle.com/cd/G48897_01/p6help/en/6611.htm), [About Portfolio Views](https://docs.oracle.com/cd/G48897_01/p6help/en/14087.htm), [Creating Portfolio View Portlets](https://docs.oracle.com/cd/G48897_01/p6help/nl/44295.htm), [Customizing Portfolio View Portlets](https://docs.oracle.com/cd/G48897_01/p6help/nl/44303.htm), [Portfolio View Portlet](https://docs.oracle.com/cd/G48897_01/p6help/en/5959.htm).
- [About Projects](https://docs.oracle.com/cd/G48897_01/p6help/en/6636.htm), [About EPS](https://docs.oracle.com/cd/G48897_01/p6help/en/6621.htm), [Configuring EPS Views](https://docs.oracle.com/cd/G48897_01/p6help/en/44026.htm).
- [About Users](https://docs.oracle.com/cd/G48897_01/p6help/en/43794.htm), [About Administration](https://docs.oracle.com/cd/G48897_01/p6help/en/6590.htm), [About User Access](https://docs.oracle.com/cd/G48897_01/English/Admin/p6_eppm_application_admin/6597.htm), [Security Profiles topics in the official V26 Help TOC](https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm).
- [About P6 Team Member Status Updates](https://docs.oracle.com/cd/G48897_01/p6help/en/50904.htm), [Reviewing Team Member Status Updates](https://docs.oracle.com/cd/G48897_01/p6help/en/51331.htm), [Configuring P6 Team Member Status Update Reviews](https://docs.oracle.com/cd/G48897_01/p6help/en/50915.htm).
- [About Capacity Planning](https://docs.oracle.com/cd/G48897_01/p6help/en/36490.htm), [Analyzing Role Allocation (Capacity Planning)](https://docs.oracle.com/cd/G48897_01/p6help/en/7855.htm).
- [Configuring Report Settings](https://docs.oracle.com/cd/G48897_01/p6help/en/78291.htm).
- [About Risks](https://docs.oracle.com/cd/G48897_01/p6help/en/6628.htm), [About Documents](https://docs.oracle.com/cd/G48897_01/p6help/en/6620.htm), [About Importing and Exporting Data](https://docs.oracle.com/cd/G48897_01/p6help/en/6604.htm), [About Project Scheduled Services](https://docs.oracle.com/cd/G48897_01/p6help/en/46217.htm).
- [About Find, Search, and Filter Features](https://docs.oracle.com/cd/G48897_01/p6help/en/6607.htm), [About Filters](https://docs.oracle.com/cd/G48897_01/p6help/en/9027.htm).
- For the current page's complete child topics, use the linked topic's Related Topics and the official TOC. A parent overview topic alone does not satisfy reading the procedures needed by a control.

**Source limitation:** EPPM V26 is HTML Help, not a page-numbered PDF baseline. Do not invent PDF page numbers. The official Help pages expose figure callouts and descriptions, but do not define numeric CSS dimensions for every control. Numeric pixel targets must therefore be measured from the actual Help illustration at a recorded viewport, not fabricated from prose.

---

## 3. Shared shell — icon-by-icon register inherited by every Enterprise page

These are semantic CUBI icon IDs, not claims that Oracle uses the same glyph artwork. The reference column identifies the exact Help concept/screen evidence. The final glyph geometry, stroke, color, size and placement must be sampled from the official reference screenshot where a corresponding icon exists; where Help only describes a text control, use the approved CUBI icon system and record the design decision.

| Icon ID | Location/control | Required behavior | Help reference | Current source observation |
|---|---|---|---|---|
| `brand-cubi` | CUBI mark | Navigate to CUBI entry; no vendor logo | CUBI-owned brand rule | Text mark "CB" is rendered |
| `nav-dashboard` | Dashboard navigation | Open Enterprise dashboard | 9038, 6608, 6665 | Sidebar currently renders text links without icon glyph |
| `nav-portfolio` | Portfolio navigation | Open portfolio analysis | 9038, 6611, 14087 | Text-only |
| `nav-projects` | Projects navigation | Open project register | 9038, 6636 | Text-only |
| `nav-eps` | EPS navigation | Open hierarchy view | 6621, 44026 | Text-only |
| `nav-access` | Access navigation | Open organization/access control | 43794, 6597, 36451 | Text-only |
| `nav-directory` | Directory navigation | Browse authorized people/teams | 43794 | Text-only |
| `nav-tasks` | Tasks navigation | Open task center | 50904 | Text-only |
| `nav-member-activities` | Member activities | Open read-only Engineering activity projection | 50904; CUBI boundary | Text-only |
| `nav-timesheets` | Timesheets | Open time reporting/approval register | About Timesheets; 65 link in TOC | Text-only |
| `nav-workflows` | Workflow studio | Open workflow definition and versions | 50915 | Text-only |
| `nav-approvals` | Approvals | Open review/decision queue | 51331 | Text-only |
| `nav-resources` | Resources | Open resource/capacity read model | 36490, 7855 | Text-only |
| `nav-reports` | Reports | Open report catalogue and runs | 78291 | Text-only |
| `nav-knowledge` | Knowledge | Open CUBI guidance and coverage | CUBI-owned | Text-only |
| `nav-risks` | Risks | Open authorized risk register | 6628 | Text-only |
| `nav-documents` | Documents | Open document register/reviews | 6620 | Text-only |
| `nav-notifications` | Notifications | Open notification center | Email Notifications / notifications settings | Text-only |
| `nav-forms` | Forms | Open shared CUBI form library | CUBI-owned | Text-only |
| `nav-settings` | Settings | Open personal/Enterprise settings | 6590 / My Preferences | Text-only |
| `nav-audit` | Audit | Open immutable audit history | Table Auditing / Viewing Audit Data | Text-only |
| `nav-signout` | Sidebar footer | Sign out current session safely | CUBI identity/session policy | Text-only button |
| `top-search` | Global search | Type-ahead, keyboard navigation, scoped results | 6607, 9038 | Search input is present |
| `top-notifications` | Bell | Open notifications; unread count badge | Notifications / email notifications | Bell CSS glyph is present |
| `top-workbench` | Personal Workbench link | Return to one shared Personal Workbench | 9038 concept; CUBI-owned routing | Text link |
| `top-engineering-switch` | Engineering switch | Switch authorized environment without logout | CUBI-owned | Text link |
| `top-language` | Locale selector | Change locale, direction and formatting | CUBI localization standard | Select control |
| `top-help` | Help (?) | Open official contextual Help topic for current page | Each page's exact Help links below | Current link opens only TOC; must become contextual |
| `top-user` | User/avatar menu | Show authenticated identity and allowed account actions | 43794; CUBI identity model | Avatar initials |
| `action-refresh` | Refresh | Re-read authoritative server source | Common UI / data refresh | Some pages have text refresh buttons |
| `action-search` | Search | Filter current register without changing source data | 6607 | Present on selected registers |
| `action-filter` | Filter | Open explicit filter criteria and apply/clear | 9027 | Present on selected registers |
| `action-sort` | Sort | Toggle deterministic sort with visible direction | Grouping/sorting Help | Select controls on selected pages |
| `action-columns` | Columns | Show/hide/reorder columns; persist view | About Columns / UI | Not verified on all registers |
| `action-group` | Group | Group/ungroup rows by selected field | Grouping/sorting Help | Not verified |
| `action-view` | View/layout | Choose saved view/layout | 44026, 7827 | Page-dependent |
| `action-add` | Add/Create | Open validated create form; permission-gated | Page-specific create topic | Page-dependent |
| `action-open` | Open/details | Open selected record/detail page | 9038, page topic | Page-dependent |
| `action-edit` | Edit | Enter edit state only when authorized | Page-specific topic | Page-dependent |
| `action-save` | Save | Validate, submit with expected revision, show outcome | Creating/modifying data; page topic | Page-dependent |
| `action-cancel` | Cancel/close | Close without unintended persistence | Common dialog behavior | Page-dependent |
| `action-delete` | Delete | Confirm destructive action; server permission; audit | Deleting Entries | Only where policy allows |
| `action-approve` | Approve | Approve exact submitted revision; audit actor/time | 51331 | Approval page |
| `action-reject` | Reject | Require reason where configured; preserve history | 51331 | Approval page |
| `action-export` | Export/download | Export authorized rows only; preserve filters and provenance | 6604 | Page-dependent |
| `action-import` | Import/upload | Validate schema, preview errors, idempotency and audit | 6604 | No Enterprise integration route currently |
| `action-help` | Contextual help | Open the exact page topic, not generic TOC | 9038 / page-specific | Current generic TOC link is insufficient |

**Current icon parity finding:** `app.ts` builds sidebar links with text only. `styles.ts` defines a generic 16×16 square `.cubi-icon` pseudo-element, but the current sidebar renderer does not attach a per-page icon ID to links. This is not icon-by-icon parity. The CSS bell is a hand-drawn glyph, not a verified Help-matched icon. Every page remains visually unaccepted until the icon inventory above is implemented and screenshot-compared. Do not mark this document itself as proof that icons were implemented.

---

## 4. Page-by-page specification and icon inventory

For every icon below, the semantic key is mandatory. If the matching Help page has an illustration/screen callout, capture that exact illustration and compare the CUBI icon against it. If the Help does not show a dedicated glyph, record "no explicit Help glyph" and use the CUBI icon family consistently; never pretend a generic glyph is an Oracle-defined icon.

### ENT-00 — Public home / entry
- **Route / source:** `/cubi/`; `pages/home.ts`; public renderer.
- **Inheritance:** Public CUBI entry shell; not an authenticated Enterprise dashboard.
- **Help:** CUBI-owned. Link to EPPM Help only as product reference, not as a substitute for CUBI marketing or sign-in guidance.
- **Features:** Product overview; Engineering and Enterprise descriptions; sign-in; access request; Help; language selection.
- **Icon register:** `brand-cubi`, `home-engineering`, `home-enterprise`, `home-revision`, `home-security`, `home-audit`, `home-locales`, `action-open`, `top-language`, `top-help`.
- **Acceptance:** No role selection; no fabricated user/project data; CUBI brand only; each CTA routes to the canonical flow.

### ENT-01 — Login
- **Route / source:** `/cubi/login/`; `pages/login.ts`.
- **Inheritance:** Authentication boundary; no Enterprise sidebar before authenticated session.
- **Help:** CUBI-owned identity/session contract. Do not borrow EPPM's role/profile model as the login process.
- **Features:** Username + password, validation, pending/error state, safe next path, session establishment.
- **Icon register:** `auth-user`, `auth-password`, `auth-password-visible`, `auth-submit`, `auth-error`, `auth-help`.
- **Acceptance:** No persona/role chooser. Identity is username; entitlements are server-side. Never reveal password; never alter credentials in a UI polish task.

### ENT-02 — Roles / granted access information
- **Route / source:** `/cubi/roles/`; `pages/roles.ts`.
- **Inheritance:** Authenticated shared entry; server session authority.
- **Help:** [About Users](https://docs.oracle.com/cd/G48897_01/p6help/en/43794.htm), [Security Profiles topics in the official V26 Help TOC](https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm).
- **Features:** Display only server-granted access; explain allowed environment and access request path.
- **Icon register:** `access-user`, `access-shield`, `access-scope`, `access-status`, `action-open`, `top-help`.
- **Acceptance:** This is informational, not a login-time selection page. No hard-coded demo persona or client-side role switching. The administrator defines entitlements.

### ENT-03 — Personal Workbench
- **Route / source:** Shared canonical destination `/workbench/`; Enterprise route alias `/cubi/workbench/`; `pages/workbench.ts` plus shared Personal Workbench.
- **Inheritance:** Shared Personal Workbench is the post-login landing workspace; it must not be duplicated inside Enterprise.
- **Help:** Dashboard and portlet concepts: 6608, 6665, 7827. Post-login and environment switching are CUBI-owned.
- **Features:** User's authorized projects, tasks, knowledge shortcuts, alerts and environment entry points.
- **Icon register:** `workbench-home`, `workbench-projects`, `workbench-tasks`, `workbench-knowledge`, `workbench-alerts`, `workbench-engineering`, `workbench-enterprise`, `top-user`.
- **Acceptance:** One canonical Personal Workbench only; dashboard content derives from live user entitlements and real data.

### ENT-04 — Environment selection
- **Route / source:** Router lists `/cubi/environments/`; `pages/environments.ts`; current `appHref` maps navigation to shared `/workbench/`.
- **Inheritance:** Shared Personal Workbench / environment selector, not a separate Enterprise workspace.
- **Help:** CUBI-owned.
- **Features:** Show authorized environments, current environment, access status, continue/open links.
- **Icon register:** `environment-engineering`, `environment-enterprise`, `environment-current`, `environment-restricted`, `action-open`.
- **Acceptance:** Switch without forced logout where authorized. Do not create duplicate selectors or role choice. Reconcile the declared route with the shared `/workbench/` canonical destination.

### ENT-05 — Enterprise dashboard
- **Route / source:** `/cubi/enterprise/dashboard/`; `pages/dashboard.ts`.
- **Inheritance:** Enterprise shell → dashboard renderer → dashboard API and source-specific read models.
- **Help:** 6608, 6665, 7827, 7831; portlets 5959, 6667; dashboard filter/layout/access child topics.
- **Features:** Delivery, executive and governance dashboards; project scope; portlet filter; refresh; designer; add/remove/reorder/resize; reset; layout persistence; data-source and revision status.
- **Icon register:** `nav-dashboard`, `dashboard-select`, `dashboard-project-filter`, `action-search` (filter portlets), `action-refresh`, `dashboard-designer`, `portlet-add`, `portlet-remove`, `portlet-move-up`, `portlet-move-down`, `portlet-resize`, `dashboard-reset`, `action-open`, `top-help`.
- **Portlets requiring independent icon IDs:** schedule health, portfolio status, cost/EVM, resource capacity, task throughput, approval queue, risk register, document control, reports, access governance.
- **Acceptance:** KPI values must be sourced from named services with revision/time provenance; Enterprise must not calculate Engineering schedule/EVM values. Layout saved to server before claiming shared persistence; local cache clearly labeled. Compare portlet headings, chart legend, axis, filters, drag/drop affordance and controls to Help figures. Dashboard customization access must be permission-enforced.

### ENT-06 — Portfolio and executive center
- **Route / source:** `/cubi/enterprise/portfolio/`; `pages/portfolio.ts`.
- **Inheritance:** Enterprise shell → portfolio page → project/portfolio KPI and decision services.
- **Help:** 6611, 14087, 44295, 44303, 5959; What-if Analysis topic from TOC.
- **Features:** Search projects; status filter; sort by name/revision/start/finish; project count; scorecard; KPI/trend source states; decision register; record decision with outcome and revision.
- **Icon register:** `nav-portfolio`, `portfolio-search`, `portfolio-filter-status`, `portfolio-sort`, `portfolio-scorecard`, `portfolio-chart`, `portfolio-histogram`, `portfolio-trend`, `portfolio-decision`, `action-open`, `action-save`, `action-help`.
- **Acceptance:** Distinguish portfolio from project register. Chart types, legends, thresholds, labels and scorecard fields must match Help topic behavior. No interpolated trend, fabricated KPI or client-side approval. Decision writes must be revision-bound and auditable.

### ENT-07 — Projects register and project portal
- **Route / source:** `/cubi/enterprise/projects/`; `pages/projects.ts`.
- **Inheritance:** Enterprise shell → project register → selected-project detail tabs.
- **Help:** 6636, 6621, 44026, project details and preferences child topics.
- **Features:** Search, status filter, sort by name/revision/start/finish; select project; tabs Overview, Engineering, Resources, Documents, Risk, Reports; project detail; links to Engineering and portfolio.
- **Icon register:** `nav-projects`, `projects-search`, `projects-filter-status`, `projects-sort`, `project-open`, `project-overview`, `project-engineering`, `project-resources`, `project-documents`, `project-risks`, `project-reports`, `action-refresh`, `top-help`.
- **Acceptance:** Project list and every tab must respect project-level read authorization. Engineering tab is a link/read-model boundary, not a second schedule engine. Every displayed value includes source/revision. Project creation is not implied unless separately specified and permission-tested.

### ENT-08 — Organization and access governance
- **Route / source:** `/cubi/enterprise/access/`; `pages/access.ts`.
- **Inheritance:** Enterprise shell → tenant-scoped access service; server session is the authority.
- **Help:** 43794, 6597, 36451; OBS and user access topics from TOC.
- **Features:** Current session/tenant scope; organization, people, teams, memberships, invitations, roles, grants, access audit; policy matrix; access administration; tenant-isolation and IDOR evidence.
- **Icon register:** `nav-access`, `access-organization`, `access-users`, `access-teams`, `access-memberships`, `access-invitations`, `access-roles`, `access-grants`, `access-audit`, `access-shield`, `action-add`, `action-edit`, `action-delete`, `action-refresh`, `action-open`.
- **Acceptance:** Global administrator and organization administrator are different scopes. Organization admin cannot grant beyond own organization. Global Admin keeps system-wide entitlements. The UI never allows self-grant or changes role authority client-side. All writes are server-authorized, revision-checked and audited; append-only audit cannot be deleted.

### ENT-09 — Team and task center
- **Route / source:** `/cubi/enterprise/tasks/`; `pages/tasks.ts`.
- **Inheritance:** Enterprise shell → Enterprise Task API v1; distinct from Engineering activities and timesheets.
- **Help:** 50904 and Team Member status update workflow topics; use only for collaboration/status-review interaction patterns, not to claim generic CUBI tasks are P6 activities.
- **Features:** Project/status/priority filters; title search; new task; task register; assigned user/team; due date; status update; expected revision; idempotency; API status and errors.
- **Icon register:** `nav-tasks`, `tasks-filter-project`, `tasks-filter-status`, `tasks-filter-priority`, `tasks-search`, `task-create`, `task-refresh`, `task-status`, `task-priority`, `task-assignee`, `task-team`, `task-due-date`, `task-save`, `task-open`.
- **Acceptance:** Task CRUD only through live Enterprise Task API. Do not display demo tasks as production data. Status update uses expected revision; stale writes show conflict and require refresh. Never update schedule/actuals from this page.

### ENT-10 — Workflow studio
- **Route / source:** `/cubi/enterprise/workflows/`; `pages/workflows.ts`.
- **Inheritance:** Enterprise shell → versioned workflow draft editor → workflow service for publish.
- **Help:** 50915; 51331 for review stages. The visual graph editor is a CUBI-owned workflow feature; P6 Team Member review configuration is related behavior only.
- **Features:** Workflow name; steps; terminal states; transitions; graph visualization; validation; local draft; revision; publish service availability; save/restore.
- **Icon register:** `nav-workflows`, `workflow-step-add`, `workflow-step-remove`, `workflow-step-terminal`, `workflow-transition-add`, `workflow-transition-remove`, `workflow-graph`, `workflow-validation-pass`, `workflow-validation-error`, `workflow-save-draft`, `workflow-publish`, `workflow-version`, `workflow-history`.
- **Acceptance:** Distinguish device-local draft from server-published workflow. Publish disabled unless the real workflow endpoint is available and permission-authorized. Graph node/edge states, arrowheads, terminal marker and error states need their own screenshot specification; no fake publish success.

### ENT-11 — Feedback and approval center
- **Route / source:** `/cubi/enterprise/approvals/`; `pages/approvals.ts`.
- **Inheritance:** Enterprise shell → approval API and revision-bound decision record.
- **Help:** 51331 plus accept/reject/override/hold/history subtopics under Team Member Status Updates in official TOC.
- **Features:** Pending/submitted/approved/rejected/held items; reviewer; item detail; review; approve; reject; override/hold only if policy supports; decision history; revision conflict.
- **Icon register:** `nav-approvals`, `approval-inbox`, `approval-review`, `approval-approve`, `approval-reject`, `approval-hold`, `approval-override`, `approval-history`, `approval-comment`, `action-refresh`.
- **Acceptance:** Approve/reject the exact submitted revision; capture actor, timestamp, decision and reason. No silent update to Engineering actuals. All action availability comes from server entitlements.

### ENT-12 — Resource capacity
- **Route / source:** `/cubi/enterprise/resources/`; `pages/resources.ts`.
- **Inheritance:** Enterprise shell → Engineering resource/capacity read models; Engineering remains source of truth.
- **Help:** 36490, 7855; Resources, Resource Planning, Resource Analysis and Resource Assignments chapters.
- **Features:** Project selector; resource register; capacity segments; allocation/overload; source stamps; capability probe; links to project portal and Engineering.
- **Icon register:** `nav-resources`, `resource-project-select`, `resource-person`, `resource-role`, `resource-team`, `resource-capacity`, `resource-allocation`, `resource-overallocated`, `resource-availability`, `resource-open-engineering`, `action-refresh`.
- **Acceptance:** No client-side capacity calculation or duplicated resource master. Show units/time buckets, availability, demand and over-allocation only when the source supplies them. No write controls unless explicitly routed to the authoritative Engineering service.

### ENT-13 — Enterprise reports
- **Route / source:** `/cubi/enterprise/reports/`; `pages/reports.ts`.
- **Inheritance:** Enterprise shell → shared reporting runtime and report definition/run/schedule services.
- **Help:** 78291 plus reports, report settings, parameters and scheduling related TOC topics.
- **Features:** Project scope; report catalogue; definitions; selected report; run; run history; schedules; job detail; retry only for supported jobs; source state.
- **Icon register:** `nav-reports`, `reports-project-select`, `reports-catalogue`, `reports-definition`, `reports-run`, `reports-history`, `reports-schedule`, `reports-job`, `reports-download`, `reports-retry`, `action-refresh`.
- **Acceptance:** Report execution uses the existing shared runtime; no second report queue. Output, parameters, filters, schedule and status must be traceable. Download only when output exists and authorization permits.

### ENT-14 — Knowledge and guidance
- **Route / source:** `/cubi/enterprise/knowledge/`; `pages/knowledge.ts`.
- **Inheritance:** Enterprise shell → shared CUBI knowledge API and shared Form Builder summary.
- **Help:** No exact P6 EPPM equivalent. CUBI-owned; the assistant must cite internal card ID, version, locale and authoritative source.
- **Features:** Search guidance; localized results; published cards; coverage; ingestable sources; translation/publication state; shared Form Builder link.
- **Icon register:** `nav-knowledge`, `knowledge-search`, `knowledge-card`, `knowledge-source`, `knowledge-coverage`, `knowledge-language`, `knowledge-published`, `knowledge-draft`, `knowledge-rejected`, `knowledge-forms`, `action-refresh`.
- **Acceptance:** Never display draft/rejected content as published guidance. Search result cites exact card and official source. Do not duplicate the Form Builder implementation.

### ENT-15 — Risks
- **Route / source:** `/cubi/enterprise/risks/`; `pages/registers.ts`.
- **Inheritance:** Enterprise shell → project risk read model; Engineering owns project risk source.
- **Help:** 6628, Working with Project Risks, risk categories, scoring matrices, thresholds, response plans and activity links in TOC.
- **Features:** Authorized risk register; status/severity/owner; impact/probability; project context; source revision; detail and related project/activity references.
- **Icon register:** `nav-risks`, `risk-register`, `risk-severity`, `risk-probability`, `risk-response`, `risk-owner`, `risk-project-link`, `risk-activity-link`, `action-filter`, `action-search`, `action-open`.
- **Acceptance:** Risk scoring/analysis must not be invented in Enterprise. Show only source-owned fields and supported scoring. Any edit opens the authoritative service; read-only bridge stays read-only.

### ENT-16 — Documents and reviews
- **Route / source:** `/cubi/enterprise/documents/`; `pages/registers.ts`.
- **Inheritance:** Enterprise shell → project document register/content repository boundary.
- **Help:** 6620 plus document repository, folders, check-in/out, document review, search, viewing and download topics in TOC.
- **Features:** Project/private distinction where supported; folder; document metadata; status/category; related items; upload/download/check-in/out/review only if the repository capability exists.
- **Icon register:** `nav-documents`, `document-file`, `document-folder`, `document-upload`, `document-download`, `document-checkout`, `document-checkin`, `document-review`, `document-version`, `document-related-items`, `action-search`, `action-filter`.
- **Acceptance:** Do not expose check-in/out or review controls when the content repository is not connected. Virus scanning, file size, allowed type and access policy must be enforced server-side. No fabricated document rows.

### ENT-17 — EPS / organization project hierarchy
- **Route / source:** `/cubi/enterprise/eps/`; `pages/registers.ts`.
- **Inheritance:** Enterprise shell → project hierarchy service; authorization inherited from server-scoped organization/project data.
- **Help:** 6621, 44026, EPS columns/grouping/filter/bars/Gantt/access subtopics.
- **Features:** Hierarchical nodes; projects at leaf level; responsible organizational manager; expand/collapse; grouping; filters; columns; view; project open.
- **Icon register:** `nav-eps`, `eps-root`, `eps-node`, `eps-project`, `eps-expand`, `eps-collapse`, `eps-responsible-manager`, `eps-view`, `eps-columns`, `eps-filter`, `eps-group`, `eps-sort`, `eps-gantt`, `action-open`.
- **Acceptance:** Preserve parent/child hierarchy and roll-up semantics. Every node has its correct responsible manager and access scope. Do not conflate EPS with OBS; show the relationship explicitly.

### ENT-18 — Member activities (read-only Engineering bridge)
- **Route / source:** `/cubi/enterprise/member-activities/`; `pages/member-activities.ts`.
- **Inheritance:** Enterprise shell → authenticated project selector → Engineering activity read API.
- **Help:** Team Member status update topics 50904 / 51331; CUBI boundary: Engineering calculation authority.
- **Features:** Project selector; search activity ID/name; activity table; read-only status and schedule fields; source state.
- **Icon register:** `nav-member-activities`, `member-project-select`, `member-activity-search`, `member-activity-open`, `member-activity-status`, `member-activity-due`, `member-activity-source`, `action-refresh`.
- **Acceptance:** No create/edit/delete/progress write controls. Do not calculate or modify schedule, actuals or resource assignments. The search control must be enabled only when rows are available; no fake results.

### ENT-19 — Timesheets
- **Route / source:** `/cubi/enterprise/timesheets/`; `pages/registers.ts`.
- **Inheritance:** Enterprise shell → timesheet service; resource identity and project scope are server-authoritative.
- **Help:** [About Timesheets](https://docs.oracle.com/cd/G48897_01/p6help/en/6610.htm), [Working with Timesheets](https://docs.oracle.com/cd/G48897_01/p6help/en/6670.htm), [Approving or Rejecting Timesheets](https://docs.oracle.com/cd/G48897_01/p6help/en/7847.htm), resource delegate topics under TOC.
- **Features:** Period, resource, project, status; timesheet entries; submit; approve/reject; delegation; history.
- **Icon register:** `nav-timesheets`, `timesheet-period`, `timesheet-resource`, `timesheet-project`, `timesheet-entry`, `timesheet-submit`, `timesheet-approve`, `timesheet-reject`, `timesheet-delegate`, `timesheet-history`, `action-filter`, `action-refresh`.
- **Acceptance:** Do not treat timesheet hours as activity actuals until the approved authoritative workflow posts them. Validate period, resource, project, status, duplicate submission and approval permissions.

### ENT-20 — Notifications
- **Route / source:** `/cubi/enterprise/notifications/`; `pages/registers.ts`.
- **Inheritance:** Enterprise shell → notification service and user preference boundary.
- **Help:** About email Notifications / Working with Email Notifications; Notifications settings topic in Administration.
- **Features:** Unread/read; category; date; source; open target; mark read; preference navigation.
- **Icon register:** `nav-notifications`, `notification-unread`, `notification-read`, `notification-filter`, `notification-open-target`, `notification-mark-read`, `notification-settings`, `action-refresh`.
- **Acceptance:** Unread count reconciles with the service. Notification deep links respect session and project authorization. Mark-read actions persist and do not alter source records.

### ENT-21 — Enterprise settings / preferences
- **Route / source:** `/cubi/enterprise/settings/`; `pages/registers.ts`.
- **Inheritance:** Enterprise shell → personal preference and organization settings services; distinct scopes.
- **Help:** 6590, My Preferences, global currency/date/notification/resource preferences, Application Settings, audit and data limits.
- **Features:** Personal preferences; locale/date/number/time formats; notifications; view preferences; organization settings only for authorized administrators.
- **Icon register:** `nav-settings`, `settings-profile`, `settings-locale`, `settings-date-format`, `settings-number-format`, `settings-currency`, `settings-notifications`, `settings-view`, `settings-organization`, `action-save`, `action-cancel`.
- **Acceptance:** Personal preferences cannot mutate organization-wide settings. Admin settings require server authorization. Preserve current credentials and sessions unless user explicitly initiates a supported password/session action.

### ENT-22 — Forms
- **Route / source:** `/cubi/enterprise/forms/`; `pages/registers.ts`.
- **Inheritance:** Enterprise shell → shared CUBI Form Builder service; the Knowledge page links to the same editor.
- **Help:** CUBI-owned; no direct EPPM feature match. Record related P6 topics only as adjacent form/data-entry concepts, never as equivalent feature proof.
- **Features:** Shared form catalogue; template; field schema; validation; versions; submission and review state; links to shared editor.
- **Icon register:** `nav-forms`, `form-template`, `form-field`, `form-validation`, `form-version`, `form-submission`, `form-review`, `form-open-builder`, `action-add`, `action-open`.
- **Acceptance:** Exactly one shared Form Builder implementation. Enterprise and Engineering entry points open the same records/service. No duplicated schemas or separate formula engines.

### ENT-23 — Audit history
- **Route / source:** `/cubi/enterprise/audit/`; `pages/audit.ts`.
- **Inheritance:** Enterprise shell → append-only audit API.
- **Help:** [About Table Auditing](https://docs.oracle.com/cd/G48897_01/p6help/en/102813.htm), Configuring Audit Settings, Viewing Audit Data.
- **Features:** Actor; action; target; decision; timestamp; source; refresh; filters if supported.
- **Icon register:** `nav-audit`, `audit-history`, `audit-actor`, `audit-action`, `audit-target`, `audit-decision`, `audit-timestamp`, `audit-source`, `action-filter`, `action-refresh`.
- **Acceptance:** Read-only. No edit/delete affordance. The API must reject mutation. Preserve immutable event ordering, actor identity and provenance.

### ENT-24 — Organization directory
- **Route / source:** `/cubi/enterprise/directory/`; `pages/registers.ts`.
- **Inheritance:** Enterprise shell → tenant-scoped organization directory.
- **Help:** 43794, OBS and User Access topics.
- **Features:** Authorized people, teams, organizational units, associated resource and contact data where permitted; search/filter; profile details.
- **Icon register:** `nav-directory`, `directory-person`, `directory-team`, `directory-organization`, `directory-manager`, `directory-contact`, `directory-search`, `directory-filter`, `directory-open-profile`.
- **Acceptance:** Directory is not an independent identity database. Never invent email/phone values. Hide sensitive contact fields unless authorized. Organization scoping is server-enforced.

### ENT-25 — Not found / unavailable states
- **Route / source:** router fallback and app error renderers.
- **Inheritance:** Shared Enterprise shell only when session exists; otherwise authentication boundary.
- **Help:** CUBI-owned.
- **Icon register:** `state-not-found`, `state-forbidden`, `state-unavailable`, `state-error`, `state-loading`, `action-retry`, `action-back`, `action-help`.
- **Acceptance:** Distinguish 401, 403, 404, 409, 5xx, empty result and unconnected capability. No false empty state for a failed API. Retry only idempotent reads/actions.

---

## 5. Page visual measurement record — mandatory fields per screenshot

The following fields must be populated for every page and every distinct dialog, menu, drawer, table, chart, portlet and icon family before the page is accepted:

1. Help topic title, exact URL, relevant heading and related subtopics read.
2. Screenshot source/asset URL or Help image callout; date accessed; source revision/version.
3. Comparison viewport width/height, browser zoom, device pixel ratio and locale/direction.
4. Outer shell: sidebar width, topbar height, content max width, padding, page title placement, column split, sticky behavior.
5. Each icon ID: reference glyph image/callout, semantic meaning, bounding box, width/height, stroke/fill, line weight, baseline, internal padding, hit target, hover/focus/active/disabled state.
6. Each button: width/height, horizontal/vertical padding, border, radius, text metrics, icon gap, fill/text colors, focus ring, hover/pressed/disabled/destructive states.
7. Each filter/search: dimensions, label, placeholder, search/filter icon, clear affordance, dropdown arrow, focus and selected states.
8. Each table: header height, row height, column width, grid/border, sort glyph, selected/hover states, empty/loading/error row, scroll behavior.
9. Each chart/portlet: card dimensions, chart plot area, title, legend, axis labels, units, tooltip, threshold/status color and resize behavior.
10. Every dialog/menu: width/height, title row, action placement, overlay, close affordance, keyboard/focus behavior.
11. Color tokens with measured HEX/RGB and reference sample coordinates; do not guess.
12. Typography family, weight, size, line height and fallback; note localized wrapping.
13. LTR and RTL comparison captures, including Arabic/Persian and long translated labels.
14. Screenshot file path, before/after comparison and reviewer sign-off.

**No numeric value is to be filled by guess.** If Help contains no screenshot for a control, mark `NO_OFFICIAL_GLYPH` or `NO_OFFICIAL_PIXEL_SPEC`, cite the closest behavior topic, and obtain an approved CUBI design decision. The acceptance standard requires a screenshot-based visual measurement, not a fabricated official value.

---

## 6. Current code-vs-target gaps observed in the source

These are source inspection findings, not claims from a live browser test:

1. Sidebar navigation in `app.ts` appends plain text anchors and does not attach per-route icons. The generic `.cubi-icon` CSS is not a per-page icon registry.
2. The top bar's Help link opens the generic EPPM TOC, not the current page's exact contextual Help topic. This must be connected to a page-keyed Help registry.
3. The older 16-row Enterprise traceability registry does not match the 26 PageIds and canonical `/cubi/*` routes in the current router.
4. Several current page renderers are combined in `pages/registers.ts`; each route still requires an independent page record and acceptance test even though render functions share a source file.
5. Some current pages intentionally report an unconnected service and disable writes. That is a transparent gap, not a completed feature.
6. The workflow designer has device-local drafts; it must not claim published workflow state without the server workflow endpoint.
7. Member Activities is read-only and must stay separate from Engineering activity editing and scheduling.
8. Access administration contains a policy reference table and live API probes; the UI cannot become the authority for user roles or entitlements.
9. The current shell has generic CSS dimensions and a generic bell glyph. They are CUBI implementation values, not evidence of parity with EPPM. Each must be compared against the Help illustrations before acceptance.
10. No live browser visual inspection of the official Preview is asserted by this document.

---

## 7. Mandatory build and acceptance sequence for each Enterprise page

For each ENT page separately:

1. Read `AGENTS.md`, the global design standard and this crosswalk.
2. Read the current router, app shell, page renderer, styles, API/service contracts and tests.
3. Open the exact official Help topic and all related child topics listed for the page. Inspect every available screenshot, figure, table of screen highlights and icon callout.
4. Create the page's pre-build control inventory. Assign a stable icon ID to every navigation entry, toolbar action, filter, tab, table action, chart/portlet action, dialog action and state.
5. Capture Help screenshots and fill the measurement record. Record explicitly when the official Help does not specify a glyph or numeric dimension.
6. Compare current CUBI behavior against the Help workflow and list each missing or divergent feature.
7. Write acceptance tests before implementation.
8. Implement only that page's scoped changes, reusing the shared Enterprise shell and shared icon system. Do not fork the shell or duplicate service logic.
9. Verify every icon and control at the same viewport and locale as the reference. Test mouse, keyboard, focus, tooltip, disabled and permission states.
10. Verify API provenance, persistence, revision, tenant/project scope and empty/loading/error/forbidden states.
11. Test the page on the single official CUBI Preview. Do not use a new Vercel project or random Preview URL as the acceptance environment.
12. Attach before/after screenshots, test evidence, exact commit/PR and reviewer decision to the page record.

### Rejection rules

Reject the page if any of the following is true:
- It has a generic placeholder icon instead of its registered semantic icon.
- The icon has no Help source or explicitly approved CUBI-owned rationale.
- A visible control is decorative, dead, or has no tested action.
- A button/filter/table/chart/dialog differs materially from the measured reference without an approved reason.
- The page uses the wrong environment's Help baseline.
- A KPI, report, task, risk, resource or document row is fabricated or sourced from the wrong system.
- Access is enforced only in the browser.
- A page is accepted based on a build, code review or agent assertion without visual evidence.
- A second Preview URL or duplicate workspace shell is introduced.

**Definition of done:** every route above has its own complete page record, all icon IDs are implemented and visually verified, every visible control passes functional tests, all relevant Help topics are linked and read, and the reviewer signs off on the page. This crosswalk records the target and the known source gaps; it does not falsely mark unfinished pages as accepted.
