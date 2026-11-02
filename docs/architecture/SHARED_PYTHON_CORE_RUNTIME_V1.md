# Shared Python Core Runtime v1

**Status:** Initial runtime boundary implemented on a review branch; native packaging and full offline persistence remain open.
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
- Complete local composition for every project domain operation beyond the first scheduling query seam.
- Golden-result parity across server, Windows, Android and iOS.
- Offline entitlement lifecycle and local inference/AI packaging.

These are mandatory follow-on gates under Issues #1678–#1681. Web remains online-only throughout.
