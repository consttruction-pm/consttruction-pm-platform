# Stage 33.4.68 — Canonical Resource Identity in Shared Leveling

Status: **implementation slice added; exact-head CI and independent semantic review pending**

## Objective

Preserve resource identity and tenant/project scope throughout the Shared Core demand/capacity ledger so equal display IDs in separate projects do not accidentally aggregate, while explicitly shared tenant resources still aggregate against one capacity stream.

## Implemented in this slice

- Added optional canonical ResourceIdentity, tenant_id and project_id to ResourceDemand and ResourceCapacity without removing the legacy positional constructor fields.
- Canonical keys use tenant_id + resource_identity_id; project-local identity ownership is validated against the usage project.
- Scoped legacy records use tenant_id + project_id + legacy resource_id. Unscoped legacy records retain legacy single-project compatibility.
- Over-allocation calculations and forward/backward leveling now group, select, and shift demand by identity-aware keys.
- Over-allocation diagnostics preserve canonical identity and tenant/project scope.
- ExternalResourceAssignment can carry canonical identity and scope; authoritative batch orchestration fills the batch tenant for legacy assignments and rejects cross-tenant assignment records.
- Multi-project leveling rejects unscoped legacy demand/capacity with MULTI_PROJECT_RESOURCE_IDENTITY_REQUIRED rather than silently treating a raw resource ID as globally shared.
- P6 read adapter supports an explicit mapping from (tenant_id, project_id, legacy resource_id) to ResourceIdentity and carries the resolved identity to demand/capacity.
- Regression cases cover distinct project-local identities with equal raw IDs, explicit shared identity aggregation, ambiguous display-code selection, conflicting canonical definitions, shift preservation, adapter mapping, and rejection of unscoped multi-project input.

## Explicit limitations / remaining gates

This slice is **not** the end-to-end completion of Issue #1347 or of resource-calendar parity.

- Resource master identity and legacy-ID binding persistence still need an authoritative storage/API contract and migration policy.
- Canonical resource identity is not yet a first-class member of AuthoritativeScheduleInput resource-calendar assignments or snapshot materialization/replay.
- Version-pinned ResourceCalendarAssignment must still be propagated through authoritative snapshots, resolver registry lookup, demand/capacity slices and the multi-project leveling entry point as one lossless pipeline.
- Tenant-shared resource capacity must be deduplicated once per canonical identity/period when assembled from multiple project reads; different calendars for the same canonical shared identity must fail closed.
- Existing resource_id selection options are display-code compatibility inputs; ambiguous IDs now fail instead of selecting multiple canonical identities.
- The separate resources.calendar.ResourceCalendar runtime path remains a migration boundary until it can resolve the exact version-pinned CalendarReference through the authoritative Shared Core registry. It must not become a second calendar arithmetic authority.
- No local test execution was available in this GitHub-only editing session. The exact branch head must pass ConstructionPM CI, Client Typecheck and applicable PostgreSQL Integration before any completion claim.
- Keep PR #1353 and #1371 unmerged until their branches are reconciled with current main, end-to-end identity/capacity acceptance tests pass, and fresh independent semantic review approves the exact final heads.

## Non-negotiable compatibility rules

- Same raw ID or display code never implies shared identity.
- Tenant-shared identity is explicit and cannot cross tenant boundaries.
- Project-local identity cannot be used by another project.
- WBS/WorkPackage hierarchy, activity identity, resource master identity, and resource assignment identity remain distinct concepts.
- Resource calendar metadata does not automatically replace an activity's assigned calendar; any activity-type-dependent calendar semantics must be defined in the authoritative Shared Core.
- CPM forward/backward formulas, calendar arithmetic and P6 constraint semantics are unchanged by this slice.
