# Shared Client Integration Contract v1

## Authority
Web and Desktop are clients of the same application/API contracts. Shared Domain/Calculation Core remains authoritative for business calculations.

## Required propagation
- ProjectContext for every project-scoped operation.
- API contract version.
- Optimistic-lock revision on mutable resources.
- Idempotency key for retryable mutations.
- Stable ApplicationError category/code/retryability.

## Typed boundary
- Decimal-like values cross the API boundary as canonical decimal strings.
- Dates use explicit ISO-8601 representations.
- Nullable values remain explicit.
- Clients display/format values but do not replace authoritative calculations.

## Parity
A feature is not complete for a client until the equivalent Web/Desktop contract and workflow behavior is either implemented or explicitly documented as platform-specific.
