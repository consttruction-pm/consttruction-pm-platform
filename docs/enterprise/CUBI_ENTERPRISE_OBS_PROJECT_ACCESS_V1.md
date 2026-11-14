# CUBI Enterprise — OBS Project Access and Security Profiles V1

**Status:** Implemented access-control foundation; browser administration UI and WBS-level exceptions remain open.  
**Oracle baseline:** Primavera P6 EPPM Help Version 26, English HTML (May 2026).  
**CUBI boundary:** Team membership is not project access. Project access is an independent, explicit user-to-OBS-to-project-profile assignment.

## Official Oracle V26 HTML Help traceability

- [Users Page](https://docs.oracle.com/cd/G48897_01/p6help/en/6187.htm): user accounts, module access, global security profile, project access, resource access and UI views.
- [Assigning OBS Elements to Users](https://docs.oracle.com/cd/G48897_01/p6help/en/35460.htm): assign one or more OBS elements to a user together with a Project Security Profile; root OBS assignment grants access across all projects beneath the root.
- [Creating OBS](https://docs.oracle.com/cd/G48897_01/p6help/en/7795.htm): hierarchical responsibility structure and user assignments.
- [Creating Project Security Profiles](https://docs.oracle.com/cd/G48897_01/p6help/en/35278.htm): create named profiles and select individual privileges.
- [About User Access — Application Administration Guide V26](https://docs.oracle.com/cd/G48897_01/English/Admin/p6_eppm_application_admin/6597.htm): Users, OBS, Global Security Profiles and Project Security Profiles.
- [Authorization: What Users Can Access — Application Administration Guide V26](https://docs.oracle.com/cd/G48897_01/English/Admin/p6_eppm_application_admin/99163.htm): module access, project security profiles and global security profiles.

These are Oracle HTML Help topics for P6 EPPM V26. CUBI implements analogous access concepts; it does not claim byte-for-byte feature parity or reproduce Oracle's UI.

## Implemented in this slice

1. Tenant-scoped project security profiles with a restricted permission vocabulary: project.read, project.write, project.schedule, project.admin.
2. Tenant-scoped user↔OBS↔project-profile assignments. Assignment requires an active user in the same tenant, an existing OBS node and an active profile.
3. OBS inheritance for project access: a grant on an ancestor OBS covers projects assigned to descendant OBS nodes. Recursive traversal has cycle protection in the database access function.
4. Authorization composition: global/module role permissions AND project-specific profile permission are required. Existing direct project lifecycle memberships remain valid and are not silently removed.
5. Project list/read resolution includes explicit OBS profile assignments. Project lifecycle metadata, checkout and status writes use project-admin profile checks.
6. Append-only project-access audit for profile creation, OBS assignment and revocation.
7. Production schema bootstrap and WSGI routes:
   - POST /api/enterprise/project-security-profiles
   - POST /api/enterprise/user-obs-access
   - GET /api/enterprise/user-obs-access/{user_id}
   - DELETE /api/enterprise/user-obs-access/{user_id}/{obs_id} with profile_id and expected_revision JSON body
8. Every administration route requires the authenticated cp_session and an enterprise_admin session role; production Origin/CSRF/session protections remain owned by the outer production web boundary.

## Deliberate boundaries and gaps

- Team roles and team membership do not create or imply OBS assignments.
- Project security profile permissions are limited to project-level read/write/schedule/admin actions in this slice. Module access remains controlled by the existing global role policy.
- The current project record has one OBS reference. P6 allows OBS responsibility at EPS and WBS levels; WBS-level override/read-only behavior is not implemented here and must be a separate acceptance gate.
- User/resource access, module access administration, global security profiles, UI view assignment and copy-user-settings are not part of this slice.
- The Organization & Access browser UI, received invitation inbox, notification delivery, ownership transfer and last-owner controls remain separate tasks.
- No Admin Superuser bypass is implemented. Enterprise administration remains an explicit tenant-scoped role; do not imply it is equivalent to Oracle's special global Admin Superuser profile.

## Verification

- Unit: pytest -q tests/test_enterprise_project_access.py
- PostgreSQL live: CONSTRUCTION_PM_POSTGRES_DSN=... pytest -q tests/integration/test_enterprise_project_access_postgres_live.py
- Exact-head GitHub Actions and a browser journey remain required before promotion.
