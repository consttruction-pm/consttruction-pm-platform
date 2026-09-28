# P6 Interchange Mapping Boundary v1

## Purpose

`P6InterchangeMapper` provides a provider-neutral application boundary for lossless row-level P6 interchange mapping.

It consumes the authoritative persisted `P6MappingDefinition` records. It does not parse XER/XML/XLS/XLSX/MPX files and does not redefine P6 field semantics.

## Behavior

For the selected interchange format:

- `SUPPORTED` mappings translate source fields to canonical fields on import and canonical fields to source fields on export.
- `UNSUPPORTED_PRESERVE` values are retained in an explicit extension namespace and produce a compatibility warning.
- `UNSUPPORTED_REJECT` fails closed with an actionable compatibility error.
- fields without a mapping are retained in the extension namespace rather than silently dropped.
- mappings from a different interchange format are not applied.
- mappings with ambiguous source or canonical identities for the same format are rejected.
- mapping scope must be consistent for the mapper instance.

The result separates mapped values, preserved extensions and deterministic warnings so callers can decide how a concrete file parser/writer represents them.

## Boundary

Concrete file parsers/writers remain provider-specific adapters. They should parse or serialize the external representation and delegate field translation to this boundary.

Shared Core remains authoritative for P6 meaning and all Scheduling, Calendar/Duration, Formula, Progress/EVM, Resource/Cost and financial calculation semantics.

## Verification

Regression coverage proves supported import/export, unsupported preservation, unknown-field preservation, explicit rejection, scope isolation and fail-closed ambiguity handling.
