# P6 Expense Persistence Boundary v1

## Scope

This boundary persists P6 expense records needed by the P6 working-data inventory. It is persistence/application infrastructure only.

Stored metadata includes:

- tenant/project/project revision scope;
- immutable expense identity;
- name and category;
- optional activity and WBS linkage;
- optional expense date;
- typed Decimal planned, actual and remaining cost values;
- optional currency metadata;
- optional note.

## Invariants

- Definitions are immutable by tenant, project and expense identity.
- An identical write is idempotent.
- A different definition for the same identity is rejected.
- Reads and writes reject stale project revisions.
- Decimal values are persisted as exact decimal text; no float coercion occurs.
- Reads are deterministic by expense_id.
- Application transactions are owned by the caller/application service.

## Explicit boundary

This module does not calculate planned/actual/remaining cost, rates, currency conversion, earned value, financial-period allocation, resource cost, or schedule behavior. Those semantics remain owned by the authoritative Shared/Core domains.

It also does not implement XER/XML/XLSX parsing. Interchange adapters consume this typed persistence contract and the authoritative P6 mapping registry.

## Verification

SQLite regression coverage proves round-trip, deterministic ordering, activity filtering, tenant/project isolation, stale-revision rejection, identical replay idempotency, immutable-definition rejection, Decimal preservation and fail-closed validation.
