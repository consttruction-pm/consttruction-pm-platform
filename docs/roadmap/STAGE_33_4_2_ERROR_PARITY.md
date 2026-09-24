# Stage 33.4.2 — Shared Client Error Parity

Status: **backend-owned support complete**

## Contract

Web, Desktop and Mobile consume the same machine-readable application error envelope:

- top-level `error` object
- `category`: validation, context, conflict, authorization, not_found, persistence
- `code`: stable machine-readable identifier
- `message`: human-readable diagnostic
- `retryable`: explicit retry signal

Schema: `docs/contracts/application_error_v1.schema.json`.

## Covered backend cases

Resource API regression coverage verifies the same envelope shape for:

- validation failure: `INVALID_INPUT`
- stale optimistic-lock revision: `STALE_REVISION`
- idempotency-key reuse conflict: `IDEMPOTENCY_KEY_REUSE`
- missing resource referenced by assignment: `RESOURCE_NOT_FOUND`

The contract remains client-agnostic. Web/Desktop/Mobile may present platform-specific UX, but they consume the same category/code/retryability semantics.

No Scheduling/P6, Progress/EVM, Resource/Cost calculation, calendar arithmetic, or Shared Calculation Core semantics were changed.
