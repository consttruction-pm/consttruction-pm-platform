# CUBI Enterprise — CUBI-ID Team Invitations V1

**Status:** Backend domain, PostgreSQL persistence and authenticated HTTP API including recipient-scoped inbox; browser UI and notification delivery remain open; team ownership transfer is now included in the backend/API slice.
**Baseline:** Oracle P6 EPPM Help Version 26, with CUBI-native identity and invitation behavior.

## Version 26 functional traceability

The CUBI Organization & Access capability is aligned to the V26 User Administration concepts, not a pixel copy:

| V26 documented behavior | CUBI behavior and boundary | Acceptance evidence |
|---|---|---|
| Users page creates accounts and configures security profiles/access privileges | Existing CUBI identity remains authoritative; CUBI-ID directory is a separate immutable public identifier mapped to an existing user | Unique ID, same-tenant lookup, no email/phone disclosure |
| Project Access assigns responsible-manager/OBS scope and project security profile | Team invitation grants only a team role. It does not create project access or imply access to any project, resource, form, document or report | Negative project-access tests; explicit project grants remain a separate next slice |
| User status controls whether an account can log in | Invitation acceptance requires the target active authenticated account; inactive or cross-tenant users cannot be invited | Active-account and tenant-boundary repository tests |
| Security profiles determine available actions | CUBI role is checked at the server boundary; only team owner/admin can invite, and only owner can grant team-admin role | Manager, owner and role-escalation negative tests |
| User access can be removed or changed | Invitation lifecycle is pending → accepted/declined, or revoked/expired; accepted membership is persisted once | Replay, wrong-account, token-hash and audit tests |

### Official Version 26 HTML references

- https://docs.oracle.com/cd/G48897_01/p6help/en/6187.htm — Users Page, P6 EPPM Help V26.
- https://docs.oracle.com/cd/G48897_01/p6help/en/35460.htm — Assigning OBS Elements to Users, P6 EPPM Help V26.
- https://docs.oracle.com/cd/G48897_01/English/Admin/p6_eppm_application_admin/35460_1.htm — Assigning OBS Elements to Users, Application Administration Guide V26.
- https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm — P6 EPPM Help V26 contents.

These references describe user administration, module/project access, security profiles and OBS-based project access. CUBI-ID invitation is a CUBI product extension, not a claim that P6 has this same invitation workflow. Oracle/P6 names and assets must never appear in CUBI user-facing UI.

## Implemented in this slice

- Immutable, random public CUBI IDs are stored separately from mutable identity profile data; the repository lazily backfills IDs for active users in the current tenant.
- Exact CUBI-ID lookup returns only the public ID and display name, never email, phone, credentials or unrelated membership data.
- Team invitations are bound to tenant, team, target user, inviter, role, expiry and a high-entropy one-time token.
- Only a SHA-256 token digest is persisted.
- Acceptance is bound to the authenticated target account and writes the membership plus access audit in the same database transaction.
- Decline, revoke and expiry are explicit states; duplicate pending invitations are constrained by a partial unique index.
- The recipient inbox endpoint returns only pending invitations for the authenticated user in the current tenant; it never returns invitation tokens. Inbox accept/decline actions bind to the authenticated target user and unguessable invitation ID; external token-based accept/decline remains supported. Expiry is surfaced via expires_at and enforced atomically on accept.
- Authenticated API routes are mounted behind the production session, Origin and CSRF boundary, including GET /api/enterprise/invitations/inbox. Team membership does not grant project access. Project/OBS grants, notification delivery and the Organization & Access UI remain subsequent acceptance gates. Team ownership transfer is now exposed through the team administration API.

## Verification required before promotion

- Unit tests: tests/test_enterprise_invitation.py.
- Live PostgreSQL integration must cover unique public IDs, tenant isolation, duplicate invitation prevention, concurrent accept/replay, token secrecy, expiry, revocation, atomic membership creation and append-only audit.
- Production API composition and recipient-scoped inbox are wired; exact-head CI and live PostgreSQL verification are required before promotion. The browser UI and push/email notification delivery are not included in this slice. Team creation/listing, member add/remove and ownership transfer are exposed through the production Organization & Access API.

## Team administration and ownership transfer API

The production team API is versioned as cubi-enterprise-organization-access.v1:

- GET /api/enterprise/teams — list teams for the authenticated user.
- POST /api/enterprise/teams — create a team (active Pro entitlement and enterprise_admin role required).
- GET /api/enterprise/teams/{team_id}/members — list membership and roles (owner/admin only).
- POST /api/enterprise/teams/{team_id}/members — add a same-tenant active user with a team role.
- DELETE /api/enterprise/teams/{team_id}/members/{user_id} — remove a member using expected_revision.
- POST /api/enterprise/teams/{team_id}/transfer-ownership — transfer ownership using expected_team_revision.

Ownership transfer is restricted to the current active owner. The successor must already be an active team member and an active account in the same tenant. The old owner is retained as an admin; the new owner becomes the sole active owner. Team revision and both membership revisions advance in one request transaction, and the transfer is recorded in the append-only access audit. A partial unique index enforces one active owner per team. Removing the final owner is prohibited.

Oracle Help V26 reference: [Users Page](https://docs.oracle.com/cd/G48897_01/p6help/en/6187.htm) and [Assigning OBS Elements to Users](https://docs.oracle.com/cd/G48897_01/p6help/en/35460.htm). Team membership and ownership are CUBI-native extensions, not P6 project-security-profile behavior.


## Invitation inbox API

- GET /api/enterprise/invitations/inbox — list pending invitations only for the authenticated recipient in the current tenant; token hashes and raw tokens are never returned.
- POST /api/enterprise/invitations/{invitation_id}/accept-from-inbox — accept after server-side verification of the authenticated target account.
- POST /api/enterprise/invitations/{invitation_id}/decline-from-inbox — decline after the same target-account verification.

The inbox actions do not require a token in the browser because the invitation ID is high-entropy and the server also checks tenant, pending state, expiry and exact authenticated target user. External token-based accept/decline routes remain available for secure invitation links. Expired invitations are transitioned and audited when the recipient attempts acceptance; the inbox exposes expires_at so the UI can label them before action.


## Organization & Access browser surface

The authenticated browser surface is mounted at /enterprise/organization and linked from the Enterprise Task Center. It includes:
- Current user's CUBI ID and copy action.
- Team creation for enterprise administrators with the active Pro entitlement.
- Team selection and manager-scoped member listing.
- CUBI ID lookup and role-scoped team invitation.
- Received invitation inbox with authenticated accept/decline actions.
- Owner-only transfer control to an active team member and manager removal control.
- English/Persian copy, RTL direction, responsive layout and CSRF-protected mutation requests.

The UI intentionally does not display raw invitation tokens or email addresses. It uses the authenticated CUBI identity and the invitation inbox rather than asking the recipient to copy a token manually.
