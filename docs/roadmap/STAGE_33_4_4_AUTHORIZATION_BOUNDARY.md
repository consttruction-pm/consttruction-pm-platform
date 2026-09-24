# Stage 33.4.4 — Backend Authorization Boundary Support

Status: **backend-owned support complete**

The application boundary remains provider-independent and receives an authorization policy adapter. Resource mutations are authorized before persistence.

The shared client error contract exposes authorization failures as:
- category: `authorization`
- code: `FORBIDDEN`
- message: operation-specific diagnostic
- retryable: `false`

Regression coverage confirms Web/Desktop/Mobile can consume the same machine-readable denial result without exposing authentication-provider details to the Shared Domain/Calculation Core.

No authentication provider, client UI, or Scheduling/P6/Progress/EVM semantics were changed.
