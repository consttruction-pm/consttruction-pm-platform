# Client Mutation Result Boundary

## Purpose

Define one framework-neutral presentation boundary for online mutation responses.

## Accepted authoritative inputs

The boundary accepts exactly one of:

1. client-sync.v1 outcome: applied, replayed, conflict, or rejected.
2. application_error_v1 stable error envelope.

## Presentation rules

- Applied/replayed are successful and carry the authoritative revision.
- Conflict/rejected remain non-success states; their sync outcome fields remain authoritative.
- ApplicationError becomes a presentation error state using category/code/retryable.
- Error message text is retained for fallback display only and is never a discriminator.
- Clients must not calculate replacement schedule, cost, Progress, calendar, or revision values.
- Revision advances only from authoritative successful outcomes; this boundary does not advance session state itself.

## Cross-client parity

Web, Desktop, and Mobile should consume the same semantic result shape even if their controls and visual presentation differ.

For `conflict` results, the shared `ClientConflictPresentation` bridge projects the authoritative `error_code`, `retryable`, operation, idempotency key, and queued mutation revision into `client-conflict-presentation.v1`. The bridge does not alter the result or perform any local business calculation.

## Scope

This is a presentation/adapter boundary. It does not change server semantics, retry policy, conflict resolution, or business calculations.
