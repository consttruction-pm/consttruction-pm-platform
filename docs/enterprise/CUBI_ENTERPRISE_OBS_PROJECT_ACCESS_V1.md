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
   - GET /api/enterprise/project-security-profiles
   - POST /api/enterprise/project-security-profiles
   - GET /api/enterprise/obs
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


## Browser administration surface — follow-on implementation

The authenticated route `/enterprise/project-access` is mounted from the Enterprise Task Center. It consumes the production project-access API rather than maintaining a browser-side permission store.

- Lists active Project Security Profiles and their project-level permission set.
- Creates named profiles with the supported `project.read`, `project.write`, `project.schedule`, and `project.admin` permissions.
- Renders the tenant OBS hierarchy as an indented tree using the authoritative OBS API.
- Assigns a user to an OBS element with a selected Project Security Profile.
- Lists the target user's active OBS assignments and revokes a selected assignment with its expected revision.
- Warns explicitly when the root OBS is selected because Oracle documents that root assignment grants access to all projects beneath it.
- Uses the authenticated session, enterprise_admin gate, same-origin credentials, CSRF header, server-side authorization, and bilingual Persian/English responsive UI.

The UI accepts the internal CUBI user ID for an assignment because the current V1 access API is keyed by user_id. It does not silently treat a team member or a CUBI-ID string as a project grant. A dedicated user picker / CUBI-ID-to-internal-user resolution endpoint remains a UX/API follow-up.

## V26 responsibility and WBS security acceptance

Oracle V26 Help establishes more than a user-to-OBS assignment:
- Users can receive multiple OBS + Project Security Profile pairs (Users Page / Project Access detail window).
- OBS is hierarchical; assigning the root OBS grants access throughout the root EPS tree.
- Projects/EPS nodes have a Responsible Manager (OBS) which controls the branch's responsible scope.
- WBS elements can have their own Responsible Manager / OBS. A WBS-level OBS different from the project-level OBS makes that WBS data read-only to users who are not assigned to that WBS OBS; assigning the matching OBS plus an appropriate Project Security Profile grants the additional rights.
- Project Security Profiles are privilege sets, not the same thing as team roles or global/module access. Oracle's generated Project Superuser profile and Admin Superuser global profile have special semantics and must not be emulated by silently granting broad access.

Official V26 references:
- [Project Access Detail Window of the Users Page](https://docs.oracle.com/cd/G48897_01/p6help/en/6186.htm)
- [Assigning OBS Elements to Users](https://docs.oracle.com/cd/G48897_01/p6help/en/35460.htm)
- [Assigning OBS Elements to the EPS](https://docs.oracle.com/cd/G48897_01/p6help/en/11735.htm)
- [About Security Profiles](https://docs.oracle.com/cd/G48897_01/p6help/en/6595.htm)
- [Creating Project Security Profiles](https://docs.oracle.com/cd/G48897_01/p6help/en/35278.htm)
- [Creating an OBS](https://docs.oracle.com/cd/G48897_01/p6help/en/7795.htm)

**Parity status remains PARTIAL, not complete.** V1 currently enforces project-level OBS inheritance and project-level permissions. It does not yet persist Responsible Manager on EPS nodes or WBS nodes, does not implement WBS-specific OBS overrides/read-only fallback, does not filter WBS activities/risks/issues by their responsible OBS, and does not implement Oracle's full project-profile privilege catalog, global/module profiles, Resource Access, or UI Views. These are explicit release gates; the current UI must not be described as full P6 V26 access-administration parity.
