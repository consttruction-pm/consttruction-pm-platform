# CUBI Enterprise — OBS Project Access and Security Profiles V1

**Status:** Access-control foundation plus WBS Responsible Manager persistence and WBS-master OBS enforcement implemented; data-domain filtering and full V26 privilege parity remain open.  
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
4. Authorization composition: global/module role permissions AND project-specific profile permission are required. Existing direct project lifecycle memberships remain valid and are not silently removed.
5. Project list/read resolution includes explicit OBS profile assignments. Project lifecycle metadata, checkout and status writes use project-admin profile checks.
6. WBS records now persist an optional `responsible_obs_id` (Oracle's WBS Responsible Manager / OBSObjectId concept), expose it in the WBS API, and preserve it on subtree copy. Existing PostgreSQL and SQLite databases gain the nullable column through idempotent additive migrations.
7. PostgreSQL WBS-master authorization resolves the effective WBS responsible OBS (explicit WBS assignment, falling back to the project OBS for legacy rows), inherits user grants through OBS ancestors, allows project-scope read-only access to a WBS owned by a different OBS, and requires the WBS OBS's project profile for writes to that WBS. New WBS records require an explicit responsible OBS. The WBS API applies this check to create, read/list, update, delete, copy and milestone replacement.
8. Project issue records persist an independent `responsible_obs_id`; issue read/list/history/comment/create/update/delete operations enforce that OBS scope, with WBS scope retained as the fallback for legacy issues.
9. Threshold definitions persist an independent `responsible_obs_id`; threshold read/list/history/runs/monitor/create/update/delete operations enforce that OBS scope. Threshold-triggered issues inherit the threshold OBS.
10. Risk records carry a WBS reference and the risk register filters reads and enforces writes through that WBS responsible OBS.
6. Append-only project-access audit for profile creation, OBS assignment and revocation.
7. Production schema bootstrap and WSGI routes:
   - GET /api/enterprise/project-security-profiles
   - POST /api/enterprise/project-security-profiles
   - GET /api/enterprise/obs
   - POST /api/enterprise/user-obs-access
   - GET /api/enterprise/user-obs-access/{user_id}
   - DELETE /api/enterprise/user-obs-access/{user_id}/{obs_id} with profile_id and expected_revision JSON body
8. Every administration route requires the authenticated cp_session and an enterprise_admin session role; production Origin/CSRF/session protections remain owned by the outer production web boundary.

## Deliberate boundaries and gaps

- Team roles and team membership do not create or imply OBS assignments.
- Project security profile permissions are still limited to the coarse project.read / project.write / project.schedule / project.admin vocabulary. The complete V26 privilege catalogue, per-privilege endpoint enforcement, and documented privilege inheritance (add/delete ⇒ edit/assign/view; edit ⇒ assign/view; assign ⇒ view) are not yet implemented. Module access remains controlled by the existing global role policy.
- Existing WBS records without an explicit responsible OBS remain readable through a legacy project-OBS fallback; new WBS records require an explicit OBS. A WBS OBS text field is present in the editor, but a governed OBS-tree picker and authoritative OBS lookup/validation in the browser remain pending.
- WBS OBS enforcement is now connected to WBS master, activities, expenses and risks. Issues and thresholds also support their own Responsible OBS fields and authorization. Baseline, document/security-policy, resource, and all other project-data surfaces still need a complete endpoint-by-endpoint authorization matrix and tests.
- User/resource access, resource-node restrictions, module access administration, global security profiles (including the predefined Admin Superuser and No Global Privileges semantics), UI View assignment/editing restrictions and copy-user-settings are not part of this slice.
- The Organization & Access browser UI and received invitation inbox are tracked in PR #1971; notification delivery remains a separate task.
- No Admin Superuser bypass is implemented. Enterprise administration remains an explicit tenant-scoped role; do not imply it is equivalent to Oracle's special global Admin Superuser profile.

## Verification

- Unit: pytest -q tests/test_enterprise_project_access.py
- PostgreSQL live: CONSTRUCTION_PM_POSTGRES_DSN=... pytest -q tests/integration/test_enterprise_project_access_postgres_live.py
- Added SQLite repository migration/round-trip tests, WBS HTTP DTO coverage, and WBS OBS authorization tests.
- Exact-head GitHub Actions, live PostgreSQL authorization scenarios, and a browser journey remain required before promotion.
