# CUBI Enterprise — CUBI-ID Team Invitations V1

**Status:** Backend domain and PostgreSQL persistence slice; not yet exposed as a production HTTP/UI feature.
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
- Team membership does not grant project access. Project/OBS grants, ownership transfer, HTTP routes and UI remain subsequent acceptance gates.

## Verification required before promotion

- Unit tests: tests/test_enterprise_invitation.py.
- Live PostgreSQL integration must cover unique public IDs, tenant isolation, duplicate invitation prevention, concurrent accept/replay, token secrecy, expiry, revocation, atomic membership creation and append-only audit.
- Production API must be mounted behind the existing authenticated session, origin and CSRF boundary before this is called end-to-end.