# CUBI Enterprise — Primavera P6 EPPM Help V26 HTML parity baseline

**Requirement owner:** Product decision from the EPPM MENU project, recorded 2026-11-15.  
**Normative reference:** Oracle Primavera P6 EPPM Help **Version 26**, English HTML, May 2026.  
**Documentation release family:** P6 EPPM Version 26. The English Help is the latest language edition in Oracle's Version 26 library.  
**Status:** Mandatory product-requirements baseline for CUBI Enterprise design, implementation, QA and release acceptance. This is not a claim that CUBI already has full P6 EPPM feature parity.

## 1. Canonical source set

Use the versioned HTML topics below as the primary reference. Do not substitute a PDF, a P6 Professional Help set, Primavera Cloud Help, Unifier Help, or an older P6 EPPM release without explicitly recording the reason.

- P6 EPPM Help V26 — HTML table of contents: https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm
- P6 EPPM V26 — Users Page: https://docs.oracle.com/cd/G48897_01/p6help/en/6187.htm
- P6 EPPM V26 — Creating Project Security Profiles: https://docs.oracle.com/cd/G48897_01/p6help/en/35278.htm
- P6 EPPM V26 — Project Security Profile Privileges: https://docs.oracle.com/cd/G48897_01/p6help/en/102786.htm
- P6 EPPM V26 — Global Security Profile Privileges: https://docs.oracle.com/cd/G48897_01/p6help/en/102785.htm
- P6 EPPM V26 — About User Access (Application Administration Guide): https://docs.oracle.com/cd/G48897_01/English/Admin/p6_eppm_application_admin/6597.htm
- P6 EPPM Version 26 — User Guides library: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/user.html
- P6 EPPM Version 26 — All Guides: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/books.html
- P6 Team Member Help V26 — HTML table of contents: https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/toc.htm
- P6 EPPM V26 — What's New / 2026 releases: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-wn26/index.html

The HTML Help title page identifies this source as "Oracle Primavera P6 EPPM Help Version 26", May 2026. The Team Member Web guide is a separate Version 26 help set and must be reviewed separately for contributor-facing workflows.

## 2. Product interpretation rules

1. **Help-first:** Before designing or changing an Enterprise capability, inspect the relevant V26 HTML topic, its related topics, screen elements, prerequisites, security notes, and "Getting Here" navigation path. Record the topic URL and the observed behavior in the feature's acceptance evidence.
2. **EPPM-first:** Deliver the closest CUBI-equivalent to the P6 EPPM capability before adding CUBI-only extensions. Do not silently omit an EPPM concept because it is inconvenient.
3. **CUBI-native expression:** Translate the workflow and information architecture into CUBI's own vocabulary and visual language. The parity requirement is behavioral and conceptual, not a direction to copy Oracle artwork, wording, branding, proprietary assets, or pixel-level layout.
4. **No false parity:** Mark each capability as Implemented, Partial, Planned, Not Applicable, or Deferred with evidence. A route, mock, schema, or documentation entry alone is not implementation.
5. **Version control:** V26 is the current baseline as of this record. If Oracle publishes a newer major Help version, add a reviewed delta and explicit product decision before changing the baseline. If a deployment runs an older supported version, document the compatibility subset and feature flags.
6. **Product boundaries:** P6 EPPM and Primavera Unifier are separate products. Unifier-only commercial/contract workflows are not P6 EPPM parity. Primavera Cloud and P6 Professional help are not substitutes for the P6 EPPM Help baseline.
7. **Engineering ownership:** CUBI Engineering remains authoritative for schedule, CPM, activities, WBS, resources, cost, progress, EVM and critical path. Enterprise must not create parallel schedule or engineering calculations. Cross-environment references require a versioned, revision-pinned, permission-checked adapter.

## 3. V26 functional navigation and parity map

The V26 HTML topic “Working with P6” explicitly lists seven main sections: Dashboards, Portfolios, Projects, Resources, Approvals, Reports and Administration. Access to sections and features is constrained by security profiles, access settings, user-interface views, preferences and assignments. The following is the CUBI Enterprise parity backlog. It supplements the existing EPPM-first roadmap and does not replace the Engineering roadmap.

| P6 EPPM V26 capability family | CUBI Enterprise destination / work package | Current evidence / state |
|---|---|---|
| Dashboards and configurable portlets | Portfolio & Executive Center; role-based dashboards and portlet catalog | Planned; existing reporting/read-model infrastructure must be verified before reuse |
| Portfolios, portfolio analysis, scorecards and project grouping | Portfolio & Executive Center | Planned; portfolio control read model and decision boundary exist as foundations, not full UI parity |
| Projects, EPS, project lifecycle, WBS and project overview | Project Portal and Engineering-linked project context | Partial across CUBI platform; authoritative schedule structures remain Engineering-owned |
| Resources, resource administration, analysis and capacity | Organization & Access / Resource and Capacity views | Partial foundations; verify resource and team membership semantics separately |
| Approvals for timesheets and configured activity status updates | Feedback & Approval Center with Engineering Activity Status review integration | Planned; approval authority must stay with the owning Engineering/team workflow and role grants |
| Team Member Web, My Activities, status updates and timesheets | Team & Task Center plus future Engineering Activity Status surface | Separate concepts: current Enterprise Task is an organizational task, not a P6 schedule Activity or a timesheet |
| Risks and issues | Project Portal / Risk & Issue Management | Partial in Engineering; Enterprise must consume authorized, revision-pinned records rather than duplicate authoritative risk/schedule data |
| Reports and performance status | Portfolio & Executive Center / Reporting | Existing reporting capabilities require end-to-end parity verification |
| Enterprise administration, user security, access and privileges | Organization & Access Center | Partial; tenant teams/memberships, account lifecycle, protected V26 built-ins and operator bootstrap, persisted Global/Project profiles, EPS hierarchy/project placement, WBS responsible-OBS overrides, audited WBS assignment, WBS/activity object scoping, and selected Global/Project privilege mappings are implemented on PR #1974. EPS administration UI/API/audit, remaining WBS-linked APIs, full resource/module/UI-view access, invitations/password lifecycle, Copy User Settings, effective-access preview/reporting, and Team Member/timesheet/review workflows remain open. |
| Project documents and information | Project Portal / Document & Information Management | Partial; use existing document service and access rules where verified |
| Workflow, notifications and approvals | Workflow Studio / Feedback & Approval Center | Planned; status updates/approval semantics from Team Member V26 are a specific acceptance input |

## 4. Administration V26 — user and access administration requirements

The V26 Users Page is the authoritative reference for account administration. It includes account creation, status, associated resource, Team Member/Timesheet module access, global security profile, project access, resource access, and User Interface View assignment. Copy User Settings covers copying selected combinations of module access, resource access, UI views, global security profile, project access and user preferences. CUBI must model these as separate, auditable access dimensions; a team role must never be treated as a substitute for any of them. The Global Security Profile privilege catalog includes administration privileges such as Add/Edit/Delete OBS, Security Profiles, Users and User Interface Views; the Project Security Profile privilege catalog is grouped into Activities, Codes, Project Data, Related Applications, Resource Assignments, Tools, and Views/Reports. Project profile access is assigned in the context of OBS responsibility and project structure. These are separate permission dimensions, not a single role string.

Current Organization & Access includes tenant teams/memberships, account status administration, current-owner-only team transfer, and a persisted P6 V26 Global/Project Security Profile engine. The schema stores separate Global and Project privilege catalogs; profile and assignment changes are revision-guarded and append-only audited. Every user must have a Global profile. The three Oracle built-ins are reserved and protected: **Admin Superuser**, **No Global Privileges**, and **Project Superuser**. The operator-only bootstrap provisions all three built-ins and the first Admin Superuser; assignment of Admin Superuser and Project Superuser requires an existing Admin Superuser, and the last active Admin Superuser cannot be deactivated or replaced through normal administration. Admin Superuser bypasses CUBI role checks for mapped P6 global/project operations; Project Superuser bypasses mapped project privileges only within its assigned OBS scope. No Global Privileges remains compatible with project access through an OBS-assigned Project Profile.

EPS responsibility is persisted in a tenant-scoped EPS hierarchy with project-to-EPS placement. Project creation requires an eligible EPS branch and the V26 `add_projects` privilege; when the caller omits `eps_id`, the service selects the first branch on which that caller has the privilege. Project access resolves the direct project OBS and responsible OBS values along the assigned EPS ancestor chain. OBS membership itself is exact: assignment to a parent OBS does not implicitly assign the user to a child OBS.

WBS-level responsible OBS overrides are stored in `p6_wbs_obs_responsibility`, revision-guarded and append-only audited. The authenticated WBS responsibility GET/PUT/PATCH API is wired into production. WBS list/read/write/delete/copy/milestone operations use WBS-scoped authorization. Activity Master create/read/list/update is also scoped to the activity's WBS. A project/EPS OBS assignee can retain read-only visibility when a WBS overrides responsibility to another OBS; write access requires the matching WBS OBS assignment. Project membership remains a separate prerequisite.

Mapped P6 permissions are now profile-authoritative rather than being vetoed by the generic CUBI role map. Implemented mappings include UDF definitions, OBS administration, cost accounts, financial-period calendars, roles, resource add/edit, activities, activity relationships, expenses, issues/issue thresholds, baselines, project calendars, WBS administration, project creation and selected project operations. The remaining P6 surfaces are not yet fully mapped or wired. In particular, EPS administration UI/API/audit, risk and issue WBS-level filtering, all other WBS-linked resource/expense/document/threshold APIs, resource access and role/resource assignment security, module access, UI Views, Copy User Settings, invitation/password lifecycle, profile copy/delete/default, effective-access preview/reporting, and Team Member/timesheet/status-review workflows remain open. Therefore this is meaningful implementation progress, not a claim of complete Oracle P6 EPPM V26 parity. See `CUBI_ENTERPRISE_ORGANIZATION_ACCESS_API_V1.md` for API contracts and test boundaries.

## 5. Team Member V26 — workflow-specific acceptance requirements

The Team Member Help V26 is a distinct reference set. Its My Activities workflow must be assessed independently from the Enterprise task list.

At minimum, the reference review must cover:

- assigned activities and work distribution; project, WBS and resource filters;
- Active, Due, Overdue, Starred and Completed views; text filtering, sorting and grouping;
- activity progress/status fields, actual/remaining units and dates where configured;
- starting, updating, completing and returning completed activities to in-progress;
- activity steps and step progress;
- predecessor/successor context and related activities;
- discussions, notebooks, documents and attachments;
- timesheet periods, actual time entry, notes, submit/withdraw and approval behavior;
- project-level Team Member preferences, permitted update fields, review requirements, reviewer roles and out-of-sequence warnings;
- keyboard accessibility and responsive/browser behavior.

**Important distinction:** the current CUBI Enterprise Task API supports generic personal/project tasks with lifecycle status, priority and due date. It does not yet implement P6 activity assignment, schedule status fields, step progress, timesheets, Team Member approval, or CPM/schedule update semantics. Do not present the Task Center as a replacement for P6 Team Member or as complete V26 Team Member parity.

## 6. Task Center V1 — parity-informed acceptance

The initial Task Center is a narrow, truthful slice of the Enterprise Team & Task Center, not a complete Team Member module.

| Requirement | V1 behavior | Evidence |
|---|---|---|
| Authenticated personal work list | Read personal tasks for the signed-in user | Existing /api/enterprise/tasks session-bound GET |
| Project context | Select an authorized project and list its tasks | Server-side project read authorization |
| Status views | All, Active, Due today, Overdue, Blocked and Completed filters | filterEnterpriseTasks unit tests |
| Task search | Case-insensitive title and description search | enterprise-task-center.test.ts |
| Create | Title, description, priority, due date and personal/project scope | Authenticated POST with CSRF and idempotency key |
| Update lifecycle | Start, complete and reopen via revision-checked PATCH | Authenticated PATCH; server owns completion actor/time |
| Scope and security | Same-origin credentials, CSRF, explicit server-side Enterprise environment roles, no client-supplied tenant/actor authority, and separate project permissions | Production WSGI integration coverage; exact-head CI pending |
| Responsive and RTL | Narrow-screen layout and Persian RTL direction | Browser QA required before acceptance |

Not included in V1: team assignment (disabled server-side until the Task API consumes the active-membership authorization adapter), Engineering references (disabled until the authorized resolver), starred tasks (no persisted star field yet), schedule activity status, time entry/timesheets, approvals, notifications, dependency editing, offline work, and mobile-native features. Each must be separately scoped against the V26 Help topics.

## 6. Mandatory design and QA workflow

For every Enterprise work package:

1. Create a trace row: V26 Help topic URL → documented user goal → CUBI user journey → owning module/service → API/data contract → permissions/audit → acceptance test.
2. Review prerequisites and role/privilege gates in Help; implement server-side authorization, not merely hidden controls.
3. Preserve P6's useful workflow concepts (context selection, list filtering, detail panels, explicit save/submit, validation, status feedback, related records and role-based views) while retaining CUBI design decisions.
4. Test English LTR and Persian RTL, keyboard operation, responsive breakpoints, empty/loading/error/conflict states, stale revisions, unauthorized access and multi-tenant isolation.
5. Run relevant unit, API, PostgreSQL integration, client typecheck/build and browser E2E checks. Record exact commit SHA and evidence.
6. Do not claim parity or release readiness while any required V26 workflow remains unverified.

## 7. Sources reviewed for this baseline

- P6 EPPM Help V26 title and HTML contents: /p6help/en/toc.htm.
- P6 Team Member Help V26 contents: /team_member/web/help/en/toc.htm.
- V26 Team Member activity completion and timesheet topics were checked to distinguish generic tasks from schedule activities and time reporting.
- The Oracle V26 User Guides and All Guides indexes establish the V26 release family and the available HTML Help set.

**Owner decision recorded:** all future CUBI Enterprise design and implementation must be checked against the Oracle P6 EPPM Help V26 HTML reference set above. This rule is part of the project delivery baseline and must be preserved in future plans, issues, PR descriptions and acceptance reviews.
