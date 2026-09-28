# P6 Formula Definition Persistence/API Boundary v1

## Purpose

This document defines the Hasan-owned persistence and application/API boundary for Shared Core formula definitions.

Shared Core remains authoritative for parsing, AST/type checking, units, dependency discovery/DAG, cycle detection and deterministic evaluation. The persistence/API layer stores and returns the metadata supplied by Shared Core; it never parses or evaluates an expression.

## Persisted identity

A formula definition is immutable at:

- tenant + project + formula_id + formula version

The project revision is part of the persisted scope and is checked on reads/writes. Historical formula versions remain readable at their original revision.

## Stored contract

The boundary preserves:

- source expression;
- declared result type;
- result-unit metadata;
- Shared Core semantic version/reference;
- deterministic dependency metadata supplied by Shared Core;
- arbitrary metadata as opaque JSON, including fields unknown to the backend.

The dependency list is stored as received. The backend does not infer dependencies from the expression.

## API

Contract version: `p6-formula-definition-api.v1`.

The API exposes create, read and list-version operations with project-scope authorization. DTOs preserve tenant/project/revision context and all formula metadata.

No scheduling, calendar/duration, Progress/EVM, Resource/Cost, financial, parsing or evaluation semantics are introduced here.


## Audit trail v1

Formula versioning is immutable at `tenant + project + formula_id + version`. Each newly created version can also emit one immutable `create` audit event in the same application transaction.

The audit event records:

- tenant/project/revision scope;
- formula id and version;
- authenticated actor id;
- UTC timestamp;
- Shared Core semantic version;
- SHA-256 digest of the source expression.

Re-submitting an identical immutable version is idempotent and does not create duplicate audit events. A new formula version creates a new audit event. The audit repository is provider-neutral and has SQLite/PostgreSQL implementations; the application/API layer remains responsible for authorization.
