# ENT-13 Trusted Claim Party Membership v1

Status: implemented as a backend foundation; **not yet a public API or completed ENT-13 workflow**.

## Purpose and ownership

A claim-party membership is the server-owned relationship between an authenticated CUBI identity user and a named contractual party on one exact tenant/project/contract/claim. It is separate from Enterprise team membership: team membership does not imply contractual party membership or access to claim evidence.

The existing `ChangeClaim` aggregate remains the Claims Register source. The membership repository verifies that the referenced resource exists in `project_change_claims`, has `resource_type=claim`, and its payload names the same `contract_id`. It also verifies that the target identity user is active and belongs to the same tenant.

## Security invariants

- Tenant, actor and session are derived from the authenticated server session; callers cannot supply them.
- Grant/revoke is currently restricted to the trusted `enterprise_admin` role. Do not widen this to a caller-supplied role or assume a project/team role grants contract authority.
- Grant scope is exact: tenant + project + contract + claim + party + user.
- Active party resolution is performed server-side and joins `identity_users` to require the account to remain active.
- Effective-from/effective-until timestamps are timezone-aware and evaluated at a server-supplied instant.
- Revocation is revision-guarded, immediately removes the party from subsequent resolution, and records actor/time.
- Membership audit is append-only at the PostgreSQL layer.
- Cross-tenant users, unknown claims, non-claim ChangeClaim resources, and contract mismatch fail closed.
- This slice exposes no HTTP route. A future route must derive authenticated identity from the existing production session runtime, use this resolver, and never accept `party_id` or membership as authority from request JSON.

## Existing ownership reused

- `src/construction_pm/identity_session.py`: authenticated identity and persisted session.
- `src/construction_pm/change_claims.py`: existing ChangeClaim resource envelope; no third claim aggregate.
- `src/construction_pm/enterprise_organization_access.py`: team membership remains a distinct organization concept.
- `src/construction_pm/claim_day_archive.py`: archive domain; its `claim_party_ids` must be populated from this trusted resolver at the HTTP/service boundary, never from client input.
- `src/construction_pm/deployment/schema.py`: idempotent production DDL bootstrap.

## Validation

- Unit: `tests/test_claim_party_membership.py`
- Live PostgreSQL: `tests/integration/test_claim_party_membership_postgres_live.py` (uses `CONSTRUCTION_PM_POSTGRES_DSN` or CI's `P6_TEST_POSTGRES_DSN`).
- The live test persists an existing ChangeClaim, grants a party membership, rejects a contract mismatch, revokes the grant, verifies resolution is empty, and verifies audit rows cannot be updated.

## Remaining hard gates before any claim archive endpoint

1. Compose the membership resolver with the authenticated production HTTP request context.
2. Add contract-scoped administrator grants/permission checks; tenant admin is intentionally the only grantor in this foundation slice.
3. Add read/list/download authorization using resolved membership plus evidence visibility, tenant/project/contract/claim scope.
4. Add disclosure and revocation audit, chain-of-custody access events, and retention/legal-hold enforcement.
5. Add API negative tests for guessed IDs, cross-tenant/project/contract/claim, private evidence, and revoked membership.
6. Keep Engineering as the sole owner of CPM/delay calculations and link immutable Engineering snapshots only.

## Product/help alignment

The V26 HTML Help crosswalk in `docs/enterprise/ENT13_CLAIM_DAY_ARCHIVE_IMPLEMENTATION_CROSSWALK_V1.md` remains normative for applicable workflow, record permission, document revision, audit and activity-document behavior. This membership slice adds a backend security foundation; it does not claim UI parity or replace the official Help mapping.