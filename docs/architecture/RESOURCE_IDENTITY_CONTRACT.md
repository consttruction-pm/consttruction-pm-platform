# Resource Identity Contract for Multi-Project Scheduling

Status: proposed design decision for Issue #1347. This document defines the identity boundary; it does not authorize merging the current resource-calendar PRs or claim implementation/test completion.

## 1. Problem statement

A raw `resource_id` is currently used in several scheduling paths, but its meaning is not consistently defined. It may be a project-local identifier, a catalog identifier, or an intentionally shared resource identifier. A display code is not sufficient identity. Calendar resolution keyed by `(project_id, resource_id)` can preserve local scope in one layer while downstream demand/capacity aggregation keyed by the raw ID erases it.

The core must not infer shared identity merely because two projects use the same string.

## 2. Canonical model

### Resource master identity

Every schedulable resource must resolve to one immutable canonical `resource_identity_id` within the tenant/resource catalog.

Minimum identity metadata:

- `resource_identity_id`: immutable opaque internal key used by scheduling calculations.
- `identity_scope`: exactly `TENANT_SHARED` or `PROJECT_LOCAL`.
- `tenant_id`: required for tenant-owned identities.
- `project_id`: required for `PROJECT_LOCAL`; absent for tenant-shared identities.
- `resource_code`: mutable/display-oriented code; never a calculation identity.
- `source_system` and `source_resource_key`: optional integration mapping, unique only within the declared source namespace.
- `external_guid`: optional external resource GUID, distinct from assignment GUID; uniqueness is scoped to the source system unless a provider contract guarantees global uniqueness.
- `revision` / lifecycle state: managed by persistence, not used to silently change identity.

Constraints:
1. A project-local identity belongs to exactly one tenant/project.
2. A tenant-shared identity is explicitly created/authorized and can be referenced from multiple projects in that tenant.
3. Same code or same legacy ID does not automatically mean same resource.
4. Different external resource objects cannot collapse into one canonical identity without an explicit mapping decision.
5. Assignment identity is separate: `assignment_id` identifies an assignment, which references `resource_identity_id`, `activity_id`, `role_id`, and tenant/project/revision scope.

### Calendar assignment

A resource calendar assignment references `resource_identity_id` and a version-pinned `CalendarReference`. Its scope/authorization is validated at the authoritative input boundary. Calendar resolution and exception inheritance continue to use the existing Shared Scheduling Core registry; this proposal does not introduce another calendar engine.

## 3. Identity through the scheduling pipeline

The canonical `resource_identity_id` must survive, without lossy conversion, through:

1. resource catalog and persistence adapters;
2. external assignment import/materialization;
3. authoritative schedule input and snapshot serialization/hash/replay;
4. resource calendar assignment and calendar resolution;
5. `ResourceDemand` and `ResourceCapacity` (or a compatibility wrapper carrying the canonical identity);
6. batch leveling, overload grouping, capacity consumption, diagnostics, and output mapping.

No multi-project aggregation may key on display code or an ambiguous legacy `resource_id`. Project scope must not be discarded before the identity has been canonicalized.

## 4. Backward compatibility and migration

- Existing single-project records with only `resource_id` may be mapped to a project-local identity by the owning adapter when ownership is authoritative and unambiguous.
- Existing catalog records with a proven catalog-wide primary key may map to a canonical identity through that catalog adapter; this must not imply that unrelated project-scoped stores share the same namespace.
- Cross-project equal IDs/codes must not be auto-merged into a shared resource.
- Promote multiple legacy records to one shared identity only through an explicit verified mapping, with audit trail and uniqueness validation.
- Missing, ambiguous, cross-tenant, stale, or conflicting mappings fail closed with a stable diagnostic code; do not silently fall back to bare-ID aggregation.
- Preserve old snapshot readability. Materialization must deterministically resolve legacy identities or fail with a migration diagnostic; never rewrite historical snapshots silently.

## 5. Required acceptance tests

1. Same display code in two projects, distinct local identities: no demand/capacity aggregation.
2. Explicit tenant-shared identity referenced by two projects: demand is aggregated against one capacity stream exactly once.
3. Same raw legacy ID but no verified sharing mapping: fail closed or map to distinct project-local identities according to adapter policy; never infer sharing.
4. Shared identity with different version-pinned calendar references: reject the inconsistent authoritative input.
5. Same local identity referenced outside its owning project/tenant: reject authorization/scope mismatch.
6. External assignment and snapshot assignment referencing the same canonical identity: deduplicate/validate by canonical identity and assignment semantics, not raw string coincidence.
7. Snapshot hash is order-independent for equivalent identity assignments; restore/replay preserves canonical IDs.
8. Legacy snapshot without canonical identity follows documented migration behavior and remains deterministic.
9. Existing shared-resource batch regression continues to pass through an explicit shared identity.
10. Jalali/Gregorian calendars, calendar exceptions, and working/nonworking resource capacity remain covered by the existing registry-backed tests.

## 6. Merge and release gates

- Do not merge the resource-calendar implementation solely because an earlier SHA passed CI.
- Reconcile stacked branches with current `main`, then run the full Python matrix, client typecheck, and PostgreSQL integration on each final exact head.
- Obtain fresh independent semantic review of the exact head.
- Keep PR #1353 / #1371 unmerged until the identity model is implemented end-to-end and all acceptance tests pass.
- Do not claim full resource-calendar/resource-leveling parity before those gates are evidenced.

## 7. Ownership boundary

- Shared Scheduling Core owns the canonical identity contract, validation, deterministic snapshot behavior, and demand/capacity semantics.
- Persistence/API adapters own storage mapping, tenant/project authorization, legacy migration, and external-ID translation.
- Presentation-only layers must not invent identity rules or calculate alternate resource capacity.
