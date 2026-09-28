# Field Operations API v1

## Scope

This boundary exposes the existing FieldOperation application service through a versioned, provider-neutral API contract for Daily Logs, Issues, Observations, Inspections, Quality records, Safety observations, Punch items, and Photos.

The API does not introduce new field-operation domain semantics.

## Contract

The transport identity is `field-operation.v1`.

Create requests require tenant/project scope, operation identity and revision, operation type, timezone-aware occurrence timestamp, authenticated actor identity, payload, expected revision, and idempotency key.

Reads use the same contract version and require `project.read`. Creates require `project.write`.

The authenticated tenant/project must equal the request scope, and the operation actor must equal the authenticated user. Scope and authorization failures fail closed.

## Boundary

FieldOperationAPI is a thin adapter over FieldOperationService and FieldOperationRepository. It does not implement field-operation calculations, define scheduling/calendar/duration semantics, bypass idempotency or revision checks, persist a second copy of operation truth, or add client-specific behavior.

## Verification

`tests/test_field_operations_api.py` covers versioned response envelope, timezone validation, tenant/project scope enforcement, authenticated actor binding, viewer read access, write authorization, and read scope checks.
