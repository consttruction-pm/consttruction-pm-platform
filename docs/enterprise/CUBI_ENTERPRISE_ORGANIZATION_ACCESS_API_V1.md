# CUBI Enterprise Organization & Access — Team API V1

**Status:** Implemented on an isolated branch; exact-head CI and live PostgreSQL verification pending.  
**Reference:** Oracle P6 EPPM Help V26, Administration / user security and team-related workflows.  
**Ownership:** Enterprise; tenant and authenticated identity remain owned by the existing identity/session layer.

## Contract

All routes are same-origin and require the existing `cp_session` authenticated session. Production's existing origin/CSRF boundary remains in front of the API. Responses are JSON, non-cacheable and versioned.

| Method | Route | Behavior |
|---|---|---|
| GET | `/api/enterprise/teams` | List active teams for the authenticated user in the session tenant |
| POST | `/api/enterprise/teams` | Create a tenant team; atomically creates owner membership |
| POST | `/api/enterprise/teams/{team_id}/members` | Add an active same-tenant account with a team role and optional project-scope metadata |
| DELETE | `/api/enterprise/teams/{team_id}/members/{user_id}` | Revoke membership using body `expected_revision` |

Create and membership mutation bodies use `contract_version: cubi-enterprise-team.v1`. The API never accepts tenant or actor identity from the client. Tenant and actor are derived from the authenticated session by `EnterpriseOrganizationAccessService`.

## Security and data invariants

- Team creation requires both server-side `enterprise_admin` and `pro_monthly_active` claims. Until entitlement provisioning is authoritative, creation fails closed.
- Membership management requires an active owner/admin membership in the target team.
- Member accounts must exist, be active and belong to the same tenant.
- The owning account cannot be removed through the member-revocation endpoint; last-owner protection is enforced transactionally in PostgreSQL.
- Revocation increments membership revision and writes an append-only actor-bound audit event.
- Team membership and `scope_project_ids` are not project authorization grants. They do not grant access to projects, forms, documents, files, reports or Engineering records.
- Team assignment in Task API remains disabled until that API explicitly consumes the active-membership authorization adapter and adds its own cross-scope tests.

## V26 Help traceability

This is the first concrete Organization & Access service slice supporting the EPPM administration/security capability family. It does not claim full parity for users, security profiles, granular privileges, project access, invitations, effective-access previews or access reports. Each of those requires its own V26 topic-to-contract-to-test trace row and server-side authorization evidence.

Normative source: https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm

## Verification gate

Before promotion, run the new HTTP tests, existing organization-access domain tests, live PostgreSQL integration tests, all Python versions, Client Typecheck, and the production-runtime composition tests on the exact final branch SHA. A green run on an earlier SHA is not evidence for later changes.
