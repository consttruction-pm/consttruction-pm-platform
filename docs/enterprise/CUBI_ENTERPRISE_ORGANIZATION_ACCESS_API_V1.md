# CUBI Enterprise Organization & Access — Team API V1

**Status:** Implemented on PR #1974 branch; live PostgreSQL integration and all client typechecks passed for the account-administration slice, including the end-to-end WSGI test. Python CI and ConstructionPM Web CI remain pending on the latest code/test head. Do not merge until exact-head checks and browser acceptance are green.  
**Reference:** Oracle P6 EPPM Help V26, Administration / user security and team-related workflows.  
**Ownership:** Enterprise; tenant and authenticated identity remain owned by the existing identity/session layer.

## Contract

All routes are same-origin and require the existing `cp_session` authenticated session. Production's existing origin/CSRF boundary remains in front of the API. Responses are JSON, non-cacheable and versioned.

| Method | Route | Behavior |
|---|---|---|
| GET | `/api/enterprise/teams` | List active teams for the authenticated user in the session tenant |
| GET | `/api/enterprise/teams/{team_id}/members` | List membership and revision state for an active team member; tenant-scoped |
| GET | `/api/enterprise/teams/{team_id}/eligible-users` | List active same-tenant accounts not yet active members; owner/admin only |
| POST | `/api/enterprise/teams` | Create a tenant team; atomically creates owner membership |
| POST | `/api/enterprise/teams/{team_id}/members` | Add an active same-tenant account with a team role and optional project-scope metadata |
| DELETE | `/api/enterprise/teams/{team_id}/members/{user_id}` | Revoke membership using body `expected_revision` |
| GET | `/api/enterprise/users` | List safe account identity/status fields for the authenticated tenant; Enterprise administrator only |
| PATCH | `/api/enterprise/users/{user_id}/status` | Activate/deactivate an account; deactivation revokes every persisted session for that tenant/user |

Create and membership mutation bodies use `contract_version: cubi-enterprise-team.v1`. Account status mutation uses `contract_version: cubi-enterprise-user-admin.v1` and a strict boolean `active` field. The API never accepts tenant or actor identity from the client. Tenant and actor are derived from the authenticated session by `EnterpriseOrganizationAccessService`.

## Security and data invariants

- Team creation requires both server-side `enterprise_admin` and `pro_monthly_active` claims. Until entitlement provisioning is authoritative, creation fails closed.
- Membership changes and eligible-user directory access require an active owner/admin membership in the target team. Roster visibility requires an active membership in that team.
- Member accounts must exist, be active and belong to the same tenant.
- The owning account cannot be removed through the member-revocation endpoint; last-owner protection is enforced transactionally in PostgreSQL.
- Revocation increments membership revision and writes an append-only actor-bound audit event.
- Account directory and status changes require a currently active `enterprise_admin` role re-read from the tenant-bound identity row; the browser/session role snapshot is not the sole authorization source.
- Account deactivation is tenant-scoped, prevents self-deactivation, prevents disabling the last active Enterprise administrator, and prevents deactivating an owner of an active team before ownership transfer.
- Deactivation atomically changes account state, revokes all existing sessions, and appends an immutable actor/target audit event. Session resolution independently rechecks account state as defense in depth.
- Team membership and `scope_project_ids` are not project authorization grants. They do not grant access to projects, forms, documents, files, reports or Engineering records.
- Team assignment in Task API remains disabled until that API explicitly consumes the active-membership authorization adapter and adds its own cross-scope tests.

## V26 Help traceability

This slice now includes a live Organization & Access page at `/enterprise/organization`, active team roster visibility, manager-only same-tenant eligible-user lookup, member addition and revision-guarded revocation. It also includes tenant-scoped account directory/status controls for active Enterprise administrators, audited activation/deactivation, last-admin/team-owner protections and immediate session revocation. It remains partial against V26: account invitation/creation and password lifecycle, global and project security profiles, granular privilege matrices, module access, OBS/project/resource access, User Interface Views, Copy User Settings, effective-access previews and access reports are not yet implemented.

| V26 Help topic / observable behavior | CUBI contract or surface | Evidence / state |
|---|---|---|
| [Users Page](https://docs.oracle.com/cd/G48897_01/p6help/en/6187.htm) — create accounts; configure security profiles and access privileges; active/inactive state; module access; project/resource access; Team Member and Timesheet access | Identity account administration + Organization & Access | Partial: authenticated same-tenant eligible-user directory and team membership lifecycle are live. Account creation/deactivation, password administration, module access and project/resource access controls are not implemented in this slice. |
| [Copy User Settings Dialog Box](https://docs.oracle.com/cd/G48897_01/p6help/en/98209.htm) — copy module, resource, UI view, global profile, project access and preferences | Access profile templates / controlled bulk assignment | Planned; do not infer copy semantics from team roles. |
| [Team Member Tab of Project Preferences](https://docs.oracle.com/cd/G48897_01/p6help/en/91692.htm) — allowed update fields, assignment/activity status, step permissions, out-of-sequence warnings and review settings | Engineering-owned Team Member project preferences and status update policy | Planned; Enterprise teams are not schedule resources or activity assignment grants. |
| [Configuring P6 Team Member Status Update Reviews](https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_user/50915.htm) — enable reviews, Anyone/Everyone review type, project/WBS reviewers and per-activity review requirement | Engineering Activity Status + Feedback & Approval Center | Planned; requires Engineering-owned status update records and approval transactions. |
| [Team Member Web V26 contents](https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/toc.htm) — My Activities, filters, status updates, steps, discussions, documents, notebooks and timesheets | Team Member workspace | Planned; generic Enterprise Tasks remain a separate concept. |

These sources are topic-level requirements, not claims that every underlying P6 feature is already implemented. Continue to record exact V26 HTML topic, Getting Here path, fields, permission rules and tests per delivered feature.

Normative source: https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm

## Verification gate

Verified on the account-administration code head: HTTP/domain tests, live PostgreSQL integration (including real WSGI login → tenant account directory → CSRF-protected deactivation → immediate session rejection), and Client Typecheck. The full Python matrix and ConstructionPM Web CI are still running on the newest test head. Before promotion, require all of those exact-head workflows plus browser acceptance and a usable preview deployment. A green run on an earlier SHA is not evidence for later changes.
