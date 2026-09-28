# P6 Mapping Registry API v1

## Purpose

`p6-mapping-registry-api.v1` exposes the persisted P6 interchange mapping metadata through a typed, authorized application/API boundary.

The API delegates persistence and transaction ownership to the existing `P6MappingRegistryApplicationService`.

## Contract

The response preserves:

- tenant/project/project-revision scope;
- immutable mapping identity;
- `p6-field-registry.v1` registry identity;
- interchange format identity;
- source and canonical field identity;
- explicit `SUPPORTED`, `UNSUPPORTED_PRESERVE`, or `UNSUPPORTED_REJECT` status;
- optional source/canonical type, unit and notes metadata.

Reads support deterministic listing with format, subject-area and status filtering.

## Authorization and isolation

- Create requires `project.write`.
- Read/list requires `project.read`.
- Authenticated tenant/project must exactly match the requested scope.
- Revision conflict and immutable-definition behavior remain owned by the repository/application boundary.

## Boundary

This API does not parse XER/XML/XLS/XLSX/MS Project files and does not evaluate P6 scheduling, calendar, formula, Progress/EVM, Resource/Cost or financial semantics.

Shared Core remains authoritative for canonical P6 meaning. File parsing/import/export adapters must consume this mapping boundary rather than redefine field semantics.

## Verification

Focused regression tests cover versioned DTO identity, typed format/status preservation, status filtering, cross-scope rejection and permission enforcement.
