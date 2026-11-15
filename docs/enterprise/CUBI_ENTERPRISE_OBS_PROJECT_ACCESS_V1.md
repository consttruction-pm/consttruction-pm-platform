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
