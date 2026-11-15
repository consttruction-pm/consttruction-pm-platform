# CUBI Enterprise — OBS Project Access and Security Profiles V1

**Status:** Access-control foundation, WBS Responsible OBS, and first data-domain enforcement slice implemented; EPS responsibility, remaining data domains, and full V26 privilege parity remain open.  
**Oracle baseline:** Primavera P6 EPPM Help Version 26, English HTML (May 2026).  
**CUBI boundary:** Team membership is not project access. Project access is an independent, explicit user-to-OBS-to-project-profile assignment.

## Official Oracle V26 HTML Help traceability

- [Users Page](https://docs.oracle.com/cd/G48897_01/p6help/en/6187.htm): user accounts, module access, global security profile, project access, resource access and UI views.
- [Assigning OBS Elements to Users](https://docs.oracle.com/cd/G48897_01/p6help/en/35460.htm): assign one or more OBS elements to a user together with a Project Security Profile; root OBS assignment grants access across all projects beneath the root.
- [Creating OBS](https://docs.oracle.com/cd/G48897_01/p6help/en/7795.htm): hierarchical responsibility structure and user assignments.
- [Creating Project Security Profiles](https://docs.oracle.com/cd/G48897_01/p6help/en/35278.htm): create named profiles and select individual privileges.
- [Working with Security Profiles — P6 Version 26](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/workingwithsecurityprofiles-36451a.html): global and project profiles, Project Superuser, and privilege inheritance.
- [ProjectProfile REST endpoints — Release 26](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/api-projectprofile.html): project-profile semantics and responsible OBS scope.
- [WBS fields — Release 26](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-ws-ref/wbsfields-42404a.html): WBS OBSObjectId / responsible manager field.
- [About User Access — Application Administration Guide V26](https://docs.oracle.com/cd/G48897_01/English/Admin/p6_eppm_application_admin/6597.htm): Users, OBS, Global Security Profiles and Project Security Profiles.
- [Authorization: What Users Can Access — Application Administration Guide V26](https://docs.oracle.com/cd/G48897_01/English/Admin/p6_eppm_application_admin/99163.htm): module access, project security profiles and global security profiles.

These are Oracle HTML Help topics for P6 EPPM V26. CUBI implements analogous access concepts; it does not claim byte-for-byte feature parity or reproduce Oracle's UI.

## Implemented in this slice

1. Tenant-scoped project security profiles with a restricted permission vocabulary: project.read, project.write, project.schedule, project.admin.
2. Tenant-scoped user↔OBS↔project-profile assignments. Assignment requires an active user in the same tenant, an existing OBS node and an active profile.
3. OBS inheritance for project access: a grant on an ancestor OBS covers projects assigned to descendant OBS nodes. Recursive traversal has cycle protection in the database access function.
4. Authorization composition: global/module role permissions AND project-specific OBS/profile permission are required. Legacy project membership rows are not an authorization grant and cannot bypass OBS profile checks.
5. Project list/read resolution includes explicit OBS profile assignments. Project lifecycle metadata, checkout and status writes use project-admin profile checks; a legacy membership-only user is denied.
6. WBS records now persist an optional `responsible_obs_id` (Oracle's WBS Responsible Manager / OBSObjectId concept), expose it in the WBS API, and preserve it on subtree copy. Existing PostgreSQL and SQLite databases gain the nullable column through idempotent additive migrations.
7. PostgreSQL WBS-master authorization resolves the effective WBS responsible OBS (explicit WBS assignment, falling back to the project OBS only for legacy rows), inherits user grants through OBS ancestors, and requires the user's OBS assignment/profile to include that responsible OBS for access. There is no project-only read fallback for a WBS assigned to a different OBS. New WBS records require an explicit responsible OBS. The WBS API applies this check to create, read/list, update, delete, copy and milestone replacement.
8. Project issue records persist an independent `responsible_obs_id`; issue read/list/history/comment/create/update/delete operations enforce that OBS scope, with WBS scope retained as the fallback for legacy issues.
9. Threshold definitions persist an independent `responsible_obs_id`; threshold read/list/history/runs/monitor/create/update/delete operations enforce that OBS scope. Threshold-triggered issues inherit the threshold OBS.
10. Risk records carry a WBS reference and the risk register filters reads and enforces writes through that WBS responsible OBS. New Activity and Expense writes require WBS association; new Risk writes require WBS association; new Issue and Threshold writes require their own Responsible OBS.
11. Append-only project-access audit for profile creation, OBS assignment and revocation.
12. Production schema bootstrap and WSGI routes:
   - GET /api/enterprise/project-security-profiles
   - POST /api/enterprise/project-security-profiles
   - GET /api/enterprise/obs
   - POST /api/enterprise/user-obs-access
   - GET /api/enterprise/user-obs-access/{user_id}
   - DELETE /api/enterprise/user-obs-access/{user_id}/{obs_id} with profile_id and expected_revision JSON body
13. Every administration route requires the authenticated cp_session and an enterprise_admin session role; production Origin/CSRF/session protections remain owned by the outer production web boundary.


## Deliberate boundaries and gaps

- Team roles and team membership do not create or imply OBS assignments. Project membership rows are retained for lifecycle bookkeeping and are not a project-data authorization grant.
- Project security profile permissions are still limited to the coarse project.read / project.write / project.schedule / project.admin vocabulary. The V26 profile editor supports grouped, individual privileges (Activities, EPS and Projects, Project Data, Resource Assignments, Tools, Views and Reports, and related categories). The complete V26 privilege catalogue, per-privilege endpoint enforcement, and documented privilege inheritance (add/delete ⇒ edit/assign/view; edit ⇒ assign/view; assign ⇒ view) are not yet implemented. Module access remains controlled by the existing global role policy.
- Existing WBS records without an explicit responsible OBS resolve to the project OBS as a migration fallback; new WBS records require an explicit OBS. A WBS OBS text field is present in the editor, but a governed OBS-tree picker and authoritative OBS lookup/validation in the browser remain pending. EPS nodes also require their own responsible OBS in V26 and are not yet modeled here.
- WBS OBS enforcement is now connected to WBS master, activities, expenses and risks. Issues and thresholds also support their own Responsible OBS fields and authorization. Baseline, document/security-policy, resource, and all other project-data surfaces still need a complete endpoint-by-endpoint authorization matrix and tests.
- User/resource access, resource-node restrictions, module access administration, global security profiles (including the predefined Admin Superuser and No Global Privileges semantics), UI View assignment/editing restrictions and copy-user-settings are not part of this slice.
- The Organization & Access browser UI and received invitation inbox remain tracked separately; notification delivery remains a separate task.
- No Admin Superuser bypass is implemented. Global profile definition/assignment, the mandatory one-profile-per-user rule, Admin Superuser and No Global Privileges semantics, secure-code privileges, and Admin Superuser administration restrictions remain open. `enterprise_admin` is not equivalent to Admin Superuser.


## V26 acceptance details still required

The V26 Help distinguishes project membership from project security. A user generally needs an OBS assignment and a Project Security Profile to access the project; the responsible OBS assigned to the project/EPS/WBS determines the data scope. Root-OBS assignments inherit down the hierarchy. Project owner and Contributor exceptions, and the Admin Superuser global-profile exception, must be modeled explicitly rather than inferred from team membership.

The V26 privilege editor is not a four-checkbox CRUD model. It groups granular rights across Activities, EPS and Projects, Project Data, Resource Assignments, Tools, Views and Reports, and related domains. Profile definitions support group-level select/clear and individual privileges. The documented privilege inheritance must be normalized at profile save and enforced by each API route. The current four broad CUBI permissions are a compatibility foundation only.

Additional normative V26 topics reviewed:
- [Assigning Users to an OBS](https://docs.oracle.com/cd/G48897_01/p6help/en/7778.htm)
- [Creating Project Security Profiles](https://docs.oracle.com/cd/G48897_01/p6help/en/35278.htm)
- [Privileges Detail Window of the Project Security Profiles Page](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/102786.html)
- [Project Privilege Definitions](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-ws-ref/projectprivilegedefinitions-47746a.html)
- [WBS General Detail Window of the Activities Page](https://docs.oracle.com/cd/G48897_01/p6help/en/92498.htm)
- [Assigning Global Security Profiles](https://docs.oracle.com/cd/G48897_01/p6help/en/8117.htm)

## Verification

- Unit: pytest -q tests/test_enterprise_project_access.py
- PostgreSQL live: CONSTRUCTION_PM_POSTGRES_DSN=... pytest -q tests/integration/test_enterprise_project_access_postgres_live.py
- Added SQLite repository migration/round-trip tests, WBS HTTP DTO coverage, and WBS OBS authorization tests.
- Exact-head GitHub Actions, live PostgreSQL authorization scenarios, and a browser journey remain required before promotion.


## Privilege catalogue implementation slice (2026-11-15)

A versioned internal catalogue has now been added at `src/construction_pm/p6_project_privileges.py`, with category metadata and a fail-closed expansion helper for the documented Add/Delete → Edit/Assign/View hierarchy. The accompanying tests assert unique keys, group coverage, inheritance and rejection of unknown keys.

This is deliberately a catalogue foundation, **not** a claim of complete V26 catalogue parity or endpoint enforcement. The production `ProjectSecurityProfile` validator still accepts only the four compatibility permissions listed above; no granular catalogue key is accepted by production profile persistence until the endpoint-to-privilege matrix and API enforcement are implemented. The catalogue currently covers a bounded first set of V26 concepts and must be reconciled line-by-line against the complete Oracle Project Privilege Definitions help before being called exhaustive.


## Granular P6 privilege-profile slice (2026-11-15)

The initial privilege catalogue is now consumed by the authenticated `GET /api/enterprise/project-security-privileges` endpoint and the bilingual Enterprise Project Access form. The form renders grouped privileges with group-level Select all / Clear controls. Profile creation accepts legacy compatibility grants and granular catalogue keys; granular grants are normalized and stored using the V26 Add/Delete → Edit/Assign/View inheritance rules. Unknown privilege keys and missing inheritance targets fail closed. Tests cover profile normalization, invalid keys, inheritance targets and the authenticated catalogue endpoint.

**Important enforcement boundary:** this increment makes granular grants configurable and persisted; it does not yet claim every P6 API is mapped to its granular privilege. Existing API handlers still using `project.read` / `project.write` remain compatibility-authorized until their operation-level privilege mappings and tests are migrated. Do not assign granular-only profiles to production users for operational access until the endpoint matrix is enforced. Remaining work includes full V26 privilege-by-privilege reconciliation, profile edit/duplicate/default and audit administration, Global Security Profiles, resource/module access, and all API/UI enforcement.


## Operation-level enforcement increment (2026-11-15)

The granular catalogue is now enforced at the application API boundary for a bounded set of operations:

- **Activities:** create → `activity.add_edit`; update → `activity.edit`; get/list → `activity.view`. Activity listing was corrected to use the same view privilege as item retrieval instead of the legacy project-read key.
- **Activity relationships:** create/update/delete → `activity.relationship.add_edit_delete`; get/list → `activity.view`.
- **Issues:** create → `issue.add_edit`; update and add discussion comment → `issue.edit`; delete → `issue.delete`; get/list/history → `issue.view`.
- **Expenses:** create → `expense.add_edit`; get/list → `expense.view`. The current Expense API has no separate update/delete operation, so those catalogue rights are not represented as implemented routes.

The role policy accepts the granular capability as an application-level gate, while the Enterprise Project Authorization Policy additionally requires the corresponding project-profile grant. Explicit legacy `project.read`/`project.write` profile grants remain a compatibility fallback; they are not expanded into granular-only profiles. OBS/WBS checks remain a separate scope gate and continue to run on the data operations.

Tests added for activity view vs write separation and issue/expense operation-specific grants. The exact-head Python, web, typecheck and live PostgreSQL checks are the promotion gate; browser-level security acceptance remains outstanding.

**Still not full V26 parity:** Activity deletion is not exposed by the current Activity Master repository/API; Expense update/delete routes are absent; Risk and Threshold routes are not yet migrated; Baseline and the remaining Project Data, Resource Assignment, Tools, Views/Reports and related-application privileges still need endpoint-by-endpoint mapping. Global Security Profiles, module/resource access, Owner/Contributor exceptions, and the exhaustive Oracle privilege traceability matrix also remain open. Do not describe this increment as full P6 V26 security parity.


### Additional Project Data enforcement (risk and threshold registers)

- **Risks:** list/read/history use `risk.view`; create uses `risk.add_edit`; update uses `risk.edit`; delete uses `risk.delete`. Responsible WBS authorization remains independently checked.
- **Thresholds:** list/read/history/runs use `threshold.view`; create uses `threshold.add_edit`; update uses `threshold.edit`; delete uses `threshold.delete`. OBS responsibility checks remain independent. The monitor operation now has its own `threshold.monitor` Tools privilege, mapped to Oracle's documented **Monitor Project Thresholds** option; it is not treated as threshold editing.

These are route/service-boundary mappings, not a claim that all Project Data privileges are complete. In particular, threshold monitoring must be mapped to the exact V26 tool privilege before granular-only profiles can run it. The project privilege catalogue, resource assignment operations, baseline/document permissions, global/module/resource security and full acceptance matrix remain outstanding.


### Baseline operation enforcement

- Baseline create uses `baseline.create_update`.
- Baseline get/list use `baseline.view`.

The current baseline application surface has no delete/restore/assign operations; those rights are not claimed as implemented. Project-level profile grants and application-role grants are both checked. Legacy project read/write profile permissions remain compatibility fallbacks.


### WBS and Responsible OBS privilege alignment (2026-11-15)

- WBS create/copy use `wbs.add_edit`; update/milestone replacement use `wbs.edit`; delete uses `wbs.delete`; get/list use `wbs.view`. Copy checks source view and destination add/edit scope. These are separately checked from the OBS responsibility scope.
- Activity OBS checks now evaluate the corresponding activity privilege (`activity.view`, `activity.add_edit`, or `activity.edit`) rather than requiring the unrelated broad `project.read` / `project.write` profile keys.
- Expense, Issue, Risk, and Threshold Responsible OBS checks likewise use the operation's own granular privilege. This closes the granular-only profile failure where the route accepted an activity/issue/etc. privilege but the second OBS gate incorrectly demanded `project.read` or `project.write`.
- The WBS operation keys are CUBI route-level keys. They still require reconciliation against Oracle's full privilege-detail matrix, including the V26 combined WBS hierarchy privilege and WBS financial/cost restrictions; do not treat this increment as complete WBS privilege parity.
- **Threshold monitoring** now uses the separate `threshold.monitor` key in the Tools group, matching the V26 Help option "Monitor Project Thresholds". A profile with only `threshold.add_edit` or `threshold.edit` cannot run the monitor.

Tests added for granular WBS view/manage/delete boundaries and dedicated threshold monitor authorization. Exact-head Python and PostgreSQL CI remain the required verification gates.


### Oracle P6 EPPM Help V26 privilege-catalogue reconciliation (2026-11-15)

The project privilege registry has been expanded to include the checkbox-level concepts in the official V26 **Privileges Detail Window**. The catalogue now uses Oracle's eight detail-window categories: Activities, Codes, EPS and Projects, Project Data, Related Applications, Resource Assignments, Tools, and Views and Reports. Timesheet approval is placed in Project Data, not exposed as an invented top-level Oracle category.

New definitions include the separate EPS/WBS costs and financials gates, project costs masking, delete-published-data and delete-with-timesheet-actuals controls, project calendars, issue/threshold combined control, document-template prerequisites, related-application exchanges, resource/role planning assignment controls, future-period and period-performance controls, exclusive checkout, publication priority, global search/replace, project layouts/reports/website, and Visualizer layouts.

Privilege inheritance is now an explicit Help-reviewed mapping rather than suffix-based inference. This matters for compound Oracle options such as `Add/Edit/Delete WBS Except Costs/Financials`, `Add/Edit/Delete Issues and Issue Thresholds`, and `Add/Edit/Delete Template Documents`. The WBS financial privilege is deliberately not inferred from WBS structural edit, and template-document management does not automatically grant work-product/document management: V26 requires the latter separately before the template-document option can be selected.

Regression tests assert the V26 option-label inventory, unique stable keys, known inheritance targets, combined privilege expansion, and non-inheritance of WBS costs and template-document prerequisites. The registry is still a catalogue, not proof that every option is persisted in a user-editable profile or enforced by every endpoint. Full route/UI/profile persistence parity remains open.

Primary source: https://docs.oracle.com/cd/G48897_01/p6help/en/102786.htm

- The catalogue also exposes pure group-header semantics: selecting a V26 detail-window group selects all options in that group; clearing it clears that group while preserving other groups and re-expanding only explicitly inherited grants. Unknown group names and privilege keys fail closed. This is domain support for the editor; the administrative UI wiring remains open.


### V26 profile checkbox → route privilege enforcement (2026-11-15)

A second authorization mismatch was found during the catalogue review: storing the Oracle checkbox keys alone was not enough because several API gates use CUBI operation keys. The PostgreSQL authorization resolver now maps those operation keys explicitly to the V26 checkbox options (for example, wbs.add_edit to wbs.add_edit_delete_except_costs_financials, and issue/threshold operations to issue_threshold.add_edit_delete). The WBS Responsible OBS path uses the same resolver rather than comparing raw permission strings.

The mapping is intentionally narrow: WBS structural privileges do not grant wbs.edit_costs_financials; threshold monitoring does not grant threshold CRUD; activity structural editing does not grant relationship management. The resolver is installed by both the project-access and WBS repository initializers so the WBS gate does not depend on initialization order.

The live PostgreSQL acceptance test now uses an Oracle project.view profile to authorize the CUBI project-read operation, and an OBS-scoped profile containing only wbs.add_edit_delete_except_costs_financials to prove WBS view/add-edit/delete access, deny financial edits, and revoke the WBS grant immediately. Exact-head CI is still required before this increment is accepted.

Baseline operations now distinguish `baseline.view`, `baseline.assign`, and `baseline.update`. The assign route requires both Oracle V26 options **Assign Project Baselines** and **Edit Project Details Except Costs/Financials**; selective baseline update uses the separate Tools privilege **Run Baseline Update**. Baseline activity-window reads use `baseline.view`.


### Baseline and financial-read privileges (2026-11-15)

- Baseline summary/history and baseline activity-window reads now require baseline.view.
- Assigning a baseline uses the distinct baseline.assign route grant and is checked against both V26 options: project_baseline.assign (Assign Project Baselines) and project.edit_details_except_costs_financials (Edit Project Details Except Costs/Financials). Either one alone is insufficient.
- Selective baseline update preview requires baseline.view; applying the update requires the separate Tools privilege baseline.update (Run Baseline Update).
- Activity read-model and Earned Value read routes now require activity/baseline view as applicable plus the separate project.view_costs_financials grant before returning monetary actuals, costs or EVM values. Project view alone is not treated as financial visibility.
- Added unit tests for the two-part baseline assignment prerequisite and denial of financial read-model data without the explicit costs/financials grant.

The live PostgreSQL test fixture for combined WBS privileges now normalizes the inherited grants before persisting the profile, matching the repository's canonical profile validation contract. The earlier PostgreSQL failure was caused by a non-normalized test fixture; the corrected fixture is being re-run on the current head.
