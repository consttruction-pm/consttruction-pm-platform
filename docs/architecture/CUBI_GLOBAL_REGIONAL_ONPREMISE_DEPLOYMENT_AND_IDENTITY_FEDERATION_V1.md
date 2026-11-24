# CUBI Global, Regional and On-Premise Deployment & Identity Federation

**Status:** Architecture direction recorded; implementation not yet verified  
**Reviewed main SHA:** `17de9bd3004c7bc9420af063d327a4bc7b5f080f` (2026-11-24)  
**Tracking:** [Issue #2134](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2134)  
**Related foundation:** [Issue #1605](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1605)

## 1. Decision summary

CUBI is one product with one canonical application architecture, domain model, calculation core, versioned API contracts and database migration lineage. It can be deployed in three locations:

1. **Global Cloud** — the central CUBI service. Normal Individual, Pro, Team and Enterprise Cloud accounts are hosted here.
2. **Regional** — a CUBI deployment with its own active database and file storage in a selected country/region infrastructure. Users and organizations assigned to that deployment use that regional service.
3. **On-Premise** — a CUBI deployment with its own active database and file storage on the customer's company infrastructure.

Regional and On-Premise are deployment locations, not separate products or separate database/domain designs. Each deployment is an independently operable installation of the same product and schema contract.

### Database cardinality

- One active PostgreSQL database per deployment installation/cluster, not one database per user.
- Global customers share the Global deployment's database under strict tenant, owner, workspace and project authorization boundaries.
- Organizations/users hosted on a Regional deployment use that Regional deployment's database; tenant isolation remains logical inside that deployment.
- An On-Premise customer operates the database installed with its CUBI deployment. It is not a database connection that an ordinary user selects.
- Object storage, encryption keys/secrets, backups, migration ledger and operational controls are deployment-local.
- No deployment may query another deployment's database directly for normal application operations.

## 2. Ownership and workspace model

The product distinguishes human identity, personal ownership, organization ownership, deployment location and project access. These are not interchangeable concepts.

- **Global personal space:** the Global user's own account, personal projects, documents, settings and subscription entitlements.
- **Organization space:** projects and records owned by the organization in the deployment where that organization is hosted.
- **Membership/grants:** local, revocable authorization for a person to use specific organization/project scopes. Membership does not transfer ownership.
- **Deployment context:** selects which deployment's workspace and local resources the user is currently accessing.

A project creator may be its initial project administrator, but this does not make the project personally owned if its declared owner is an organization. Removing a member must not delete organization-owned projects or the member's separate personal Global data.

## 3. Required Global Pro guest scenario

A Global Pro subscriber keeps their personal Global account and its approved 2 GB personal Global storage allocation. If invited by an organization hosted on Regional or On-Premise:

1. The user authenticates with their existing Global identity.
2. The target deployment validates the invitation and establishes a trusted identity handoff.
3. The target deployment creates/uses a local external-principal mapping and accepts the invitation only once.
4. The target organization assigns local membership and explicit project/WBS/feature grants.
5. The user can switch between their Global personal workspace and the target organization's workspace.
6. Global personal projects/files remain in Global. Organization projects/files remain in the target deployment.
7. The Global 2 GB personal quota remains Global-owned; it is not copied, pooled into or consumed by the organization's storage quota.
8. Ending the organization membership revokes target-deployment access while preserving the Global account and personal data.

The target deployment stores only the minimum external identity reference, local membership/grants, local session state and audit evidence required for authorization. It does not replicate the user's password, personal projects, personal files or Global database rows.

## 4. Federation and authorization trust boundary

### Identity proof

Use standards-based federation, preferably OpenID Connect Authorization Code Flow with PKCE. Map an external principal using the immutable pair **(issuer, subject)**. Email, username, display name and CUBI public ID may help locate an invitation but are not the federation primary key.

The target deployment must validate signature, issuer, audience, expiry, nonce/state and authorized client. It must fail closed on any mismatch. The Global identity provider proves who the person is; it does not grant access to target-deployment data.

### Local authorization authority

The target deployment is authoritative for:
- organization membership and its lifecycle;
- local roles and permission profiles;
- project, WBS and feature-level grants;
- data classification and export/download permissions;
- local session, CSRF, audit and revocation.

Never trust Global token claims for target tenant_id, organization_id, project IDs, local roles or permission grants. Those values must be resolved from the target deployment's invitation, membership and grant records. Every request rechecks local authorization.

### Invitation lifecycle

Invitations are target-deployment records, bound to a specific organization and intended grant scope. They must support pending, accepted, declined, revoked and expired states; one-time acceptance; expiration; replay protection; duplicate-membership protection; and audit history. Acceptance binds the invitation to the verified issuer+subject. An email match alone must not silently link an existing account.

### Sessions and connectivity

- The target deployment issues and owns its own local session and CSRF state. Raw Global session cookies/tokens and database credentials are never shared with the target deployment.
- Global-to-target SSO is a handoff, not a shared database session.
- Regional and On-Premise local users must continue normal authorized local work when Global is unreachable.
- External guest sessions use bounded lifetimes and a documented revocation policy. Instant remote revocation cannot be promised while the target deployment is disconnected.
- A fully isolated On-Premise installation can disable federation and use its own local identity authority. Federation is optional, never a runtime dependency for local users.

## 5. Project portability across deployments

A project is authoritative in one deployment at a time. Cross-deployment movement is an explicit, permission-checked CUBI project package export/import/transfer workflow with validation, ownership decision, conflict report, audit and fresh read-back.

Do not implement cross-deployment live project access as database joins, shared database credentials or implicit replication. A guest can collaborate on a target organization's project because that project is stored and authorized locally in the target deployment—not because the project is remotely mounted from Global.

## 6. Compatibility requirements

Every deployment must use:
- the same canonical domain and calculation core;
- the same versioned API and identity/authorization contracts;
- the same schema migration lineage and compatibility rules;
- the same project semantics, audit/revision/idempotency invariants and permission model;
- deployment-specific configuration for database, object storage, secrets, mail, backups, encryption and network policy.

A deployment must report its product build, schema migration level and contract versions. Federation must reject unsupported trust/contract combinations rather than silently weakening security. Upgrade, rollback, backup and restore must be tested per deployment profile.

## 7. Feasibility review against current main

Reviewed at main commit `17de9bd3004c7bc9420af063d327a4bc7b5f080f`.

### Compatible foundations found

- Production runtime already has a PostgreSQL request/transaction boundary, versioned additive migrations and a deployment-owned database connection.
- Authenticated sessions carry local user, tenant and role context; project reads/writes are tenant- and membership-scoped.
- Existing project lifecycle and Enterprise authorization patterns can be extended without changing the canonical calculation core.
- The product architecture already requires a shared identity/team/entitlement contract and prohibits a parallel identity implementation.

### Material gaps found

1. **Identity is currently deployment-local.** The current identity schema stores user and session rows with tenant_id. Registration creates a local user and local tenant. This is a valid local-auth foundation but does not itself identify the same Global human in another independent database.
2. **Federation is not implemented.** `src/construction_pm/enterprise_identity.py` defines a claims shape and a reference mapping adapter. The adapter does not verify OIDC/SAML tokens, establish trust metadata or bind invitations; it is not a production federation boundary.
3. **Invitation acceptance is not implemented.** Current Enterprise access documentation/UI explicitly marks acceptance and replay protection as pending.
4. **Deployment packaging is not evidenced.** Current production database documentation names one reference Supabase PostgreSQL project in Frankfurt. It does not establish repeatable Regional or On-Premise provisioning, independent object storage, secrets, backup/restore or disconnected operation.
5. **Personal quota and cross-deployment ownership need end-to-end proof.** The product requirements define account/team storage controls, but the reviewed production database matrix does not show a complete personal 2 GB quota service across deployments.
6. **Project exchange/backup is not yet in production composition.** The database architecture audit lists exchange/backup as separate modules not mounted in production. That is a separate required capability for explicit project portability and recovery.

### Verdict

**Architecture feasibility: PASS, with additive platform work required.** No fundamental conflict was found with the canonical project model or calculation core. The design can be added through deployment-local external-principal mappings, invitation/membership/grant services and repeatable deployment profiles.

**Current implementation readiness: PARTIAL / NOT IMPLEMENTED for cross-deployment operation.** Do not claim Regional, On-Premise, OIDC federation, cross-deployment guest invitations, Global 2 GB quota continuity or disconnected federation as delivered until their runtime and security acceptance tests pass.

## 8. Implementation sequence

Tracked in [Issue #2134](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2134), linked to the existing identity foundation [Issue #1605](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1605):

1. Audit and reconcile current identity, organization membership, invitation, entitlement, quota and authorization implementations. Reuse existing services/contracts; do not create parallel identity or billing.
2. Define versioned deployment identity federation contract and local trust registry; add external-principal mapping keyed by issuer+subject.
3. Complete local invitation acceptance and lifecycle with organization-bound grants, replay protection and audit.
4. Implement verified OIDC handoff; Global proves identity only, target deployment resolves all local permissions.
5. Prove Global personal ownership/projects/2 GB quota remain independent from Regional/On-Premise organization storage.
6. Add repeatable Regional and On-Premise deployment manifests, PostgreSQL migrations, object storage, secrets, backup/restore and upgrade/rollback.
7. Add isolated local-auth mode and disconnected-operation policy for On-Premise.
8. Run security and recovery tests for wrong issuer/audience, token replay, email collision, invitation expiry/revocation, role escalation, cross-tenant/project IDOR, personal-data isolation, quota isolation, connectivity loss, version mismatch and restore.

No broad production refactor or calculation-core change is authorized by this architecture record. Implement bounded vertical slices under the linked issue and verify each against the exact target deployment.
