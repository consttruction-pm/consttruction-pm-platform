# Stage 33.3.2 — Stable Error Contract

Date: 2026-09-24

## Contract

Application/API failures are represented by a stable machine-readable error object:

- category
- code
- message
- retryable

Supported categories:
- validation
- context
- conflict
- authorization
- not_found
- persistence

The Domain/Calculation Core is not coupled to this transport/application error model.

## Current implementation

Resource application validation and invalid ProjectContext now map to stable ApplicationError values. Unknown resources map to NOT_FOUND. Resource API serializes these errors through the same boundary.

## Rules

- Clients must branch on category/code, not message text.
- Messages are human-readable and may be localized at the client layer.
- Retry behavior is explicit through retryable; it must not be inferred from HTTP/database exception types.
- Future API envelopes may wrap this error object but must preserve category/code semantics.

## Tests

Regression coverage verifies validation, context and not-found error serialization.

## Next

Proceed to 33.3.3 mutation idempotency.