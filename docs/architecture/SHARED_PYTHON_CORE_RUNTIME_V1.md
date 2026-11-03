# Shared Python Core Runtime v1

**Status:** Versioned operation registry and the first persisted project-domain adapters are implemented on PR #1684 review branch; complete V1 domain coverage and native runtime acceptance remain open.
**Product split:** Web online-only; Windows Desktop and Flutter Mobile V1 (Android/iOS) fully offline for approved local project workflows.

## Purpose

Expose the existing Python Shared Domain/Calculation Core through a transport-independent runtime so server and installed native clients invoke the same application services and calculation implementation. The runtime must not depend on WSGI, HTTP, browser state, Flutter widgets or desktop UI.

## Current implementation

- Module: `src/construction_pm/shared_core_runtime.py`
- Contract: `cubi.shared-core-runtime.v1`
- First operation: `schedule.query`, delegating to the existing `ScheduleQueryAPI` and `AuthoritativeScheduleQueryProvider`.
- Web production composition uses the same `build_shared_core_runtime` factory.
- JSON dispatch is provided for future Windows/Flutter native bridges.
- The host supplies a validated `AuthorizationContext` out-of-band. JSON payloads cannot grant themselves a tenant, user, role or permission.
- Snapshot, calculation-context, calendar resolution, resource-leveling provenance and calculation identity remain owned by the existing backend/application/shared-core contracts.

## JSON request envelope

```json
{
  "contract_version": "cubi.shared-core-runtime.v1",
  "operation": "schedule.query",
  "payload": {
    "contract_version": "schedule-query.v1",
    "query_id": "caller-generated-id",
    "scope": {
      "tenant_id": "host-authorized-tenant",
      "project_id": "host-authorized-project",
      "project_revision": 12
    },
    "requested_by": "host-authenticated-user",
    "query_text": "Return authoritative schedule facts",
    "kind": "fact",
    "language": "en",
    "constraints": {
      "snapshot_id": "published-immutable-snapshot-id"
    }
  }
}
```

The native host must derive the authorization context from its trusted local session/entitlement store and must bind that identity to the request. The host must also pass the project's current revision from its trusted local project store as the out-of-band `expected_project_revision` argument. A caller-supplied identity or revision in JSON is not authentication or authoritative project context. The runtime validates requester equality, revision equality and delegates tenant/project/permission enforcement to the existing application service. A stale request returns `STALE_PROJECT_REVISION` without evaluating the snapshot.

## Versioned operation registry

The runtime exposes an allow-listed registry. A host can inspect `SharedCoreRuntime.supported_operations` before enabling a client feature. Every registered operation declares its exact API contract version, permission, required/allowed request fields and typed Application/API handler. A request carries the runtime contract version, operation name, and an operation-specific payload with its own `contract_version` and exact project scope.

Current registered operations on the implementation branch:

| Operation family | Operations | Domain contract |
|---|---|---|
| Schedule | `schedule.query`, `schedule.settings.get`, `schedule.publish` | `schedule-query.v1`, `p6-project-schedule-settings-api.v1`, `p6-schedule-snapshot-api.v1` |
| WBS | `wbs.list/get/create/update/delete` | `p6-wbs-master-api.v1` |
| Activities | `activity.list/get/create/update` | `p6-activity-master-api.v1` |
| Relationships | `relationship.list/get/create/update/delete` | `p6-relationship-api.v1` |
| Constraints | `constraint.list/get/create/update` | `p6-constraint-master-api.v1` |
| Calendar master | `calendar.list/get/create/update/delete` | `p6-calendar.v1` |
| Calendar detail | `calendar.copy/replace`, `calendar.exception.save/list`, `calendar.work_hours.list/save` | `p6-calendar.v1` |
| Calendar snapshots | `calendar.snapshot_get` | `p6-calendar-read-api.v1` |
| Baseline | `baseline.list/get/create` | `p6-baseline-api.v1` |
| Cost accounts | `cost_account.list/get/create` | `p6-cost-account-api.v1` |
| Expenses | `expense.list/get/create` | `p6-expense-api.v1` |
| Resource assignments | `resource_assignment.list/get/create`, `resource_assignment_period.list/get/create` | `p6-resource-read-api.v1`, `p6-resource-write-api.v1` |
| Resource spreads | `resource_spread.list/get/save` | `p6-resource-spread-api.v1` |
| Resource capacity | `resource_capacity.list/profile/on/save` | `p6-resource-capacity-read-api.v1`, `p6-resource-capacity-write-api.v1` |

These adapters call the existing authenticated typed APIs. They do not implement project validation, persistence, CPM, date arithmetic, resource leveling or cost rules. Project scope and project revision are reconstructed from the trusted host's `AuthorizationContext` and `expected_project_revision`; they are not accepted as authority from JSON. Operations that mutate a record use the existing API's record-revision/optimistic-lock contract. A local host must additionally route every write through `SQLiteLocalApplicationRuntime.apply_offline_mutation` so its domain change and durable outbox record share one transaction.

The JSON boundary rejects duplicate object keys, non-finite JSON constants, unknown envelope fields, unsupported contract versions, undeclared operation names and payload fields outside the operation schema. The request is capped at 1 MiB. Permission, tenant/project scope and expected project revision are checked before a handler is invoked. The runtime returns stable validation, conflict, authorization or internal error envelopes.

For a mutating operation on a local native runtime, the payload must also include the reserved mutation metadata object:

```json
{
  "mutation": {
    "mutation_id": "host-generated-unique-id",
    "idempotency_key": "host-generated-project-scoped-key"
  }
}
```

The runtime removes this reserved metadata before applying the operation-specific DTO. The local mutation executor creates the durable `OfflineMutation` using the host-authenticated tenant/project and current revision, calls the typed API, and appends the mutation to the same SQLite outbox transaction. The domain write and outbox append commit or roll back together. A missing mutation envelope returns `MUTATION_ENVELOPE_REQUIRED` before the typed handler is called. While an earlier mutation remains pending in the local outbox, a repeated mutation ID or project-scoped idempotency key is rejected before the typed handler is called (`DUPLICATE_MUTATION_ID` / `DUPLICATE_IDEMPOTENCY_KEY`). This pending-queue guard prevents duplicate local side effects; it does not claim response replay or a permanent local idempotency receipt after acknowledgement. The server synchronization endpoint remains responsible for durable, project-scoped idempotency across acknowledgement/restart boundaries. The Web online runtime does not create a local outbox; its server transaction and authorization remain authoritative.

Example registered request:

```json
{
  "contract_version": "cubi.shared-core-runtime.v1",
  "operation": "wbs.create",
  "payload": {
    "contract_version": "p6-wbs-master-api.v1",
    "scope": {
      "tenant_id": "host-authorized-tenant",
      "project_id": "host-authorized-project",
      "project_revision": 12
    },
    "wbs": {
      "wbs_id": "WBS-100",
      "parent_kind": "project",
      "parent_wbs_id": null,
      "code": "1",
      "name": "Project",
      "sequence_number": 0
    }
  }
}
```

The host must supply the authenticated context and current revision out-of-band. The scope in the payload is a consistency assertion only and must exactly match those host values.

## Remaining V1 ABI coverage

The registry above is an implemented first tranche, not the complete command/query contract requested in Issue #1690. The following operation families still require adapters and contract tests: full project lifecycle/session and settings mutations; calendar exception/work-hour writes and all calendar assignment workflows; resource master, roles, assignments, assignment periods, spreads, capacity and leveling configuration; baseline lifecycle and comparison; cost accounts, expenses, progress/actuals and EVM; reports, import/export and files/attachments; audit/history, backup/restore, undo/redo, entitlement and synchronization/conflict operations. Existing typed APIs/repositories must be reused; no new client-side calculation engine is permitted.

## Runtime response

A successful operation returns the existing `schedule-query-result.v1` under the runtime envelope's `result` member. Existing stable application errors are preserved under the same member. Unsupported runtime versions/operations and malformed envelopes return stable runtime validation errors.

JSON encoding is UTF-8, compact and key-sorted. Numeric/date semantics remain those of the Python Shared Core; clients must not parse and recalculate returned values.

## Platform boundaries

| Product | Runtime execution | Network requirement |
|---|---|---|
| Web | Python Shared Core on authenticated server | Online; no Web offline/PWA calculation runtime |
| Windows Desktop | Bundled local CPython + native host bridge | No Internet for approved local project operations/calculations |
| Flutter Android/iOS | Embedded CPython + narrow native bridge | No Internet for approved local project operations/calculations |

## Deliberately not certified by this first slice

- Windows embedded interpreter, packaging, signing and clean-machine installation.
- Flutter Android/iOS projects, CPython embedding, native bridge and real-device execution.
- Durable local project repositories, attachments, SQLite transactions, durable outbox, backup/restore and crash recovery.
- Complete V1 operation-family coverage; the current registry is the first tranche listed above.
- Golden-result parity across server, Windows, Android and iOS.
- Offline entitlement lifecycle and local inference/AI packaging.

These are mandatory follow-on gates under Issues #1678–#1681. Web remains online-only throughout.
