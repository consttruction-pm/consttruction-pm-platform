# Resource/Cost Client Integration Definition of Done

A Resource/Cost client integration is complete only when all of the following are true:

- ProjectContext is attached to every project-scoped mutation.
- Resource/Assignment DTOs preserve the `resource.v1` contract and authoritative revision.
- Decimal-like units and costs remain canonical decimal strings at the client boundary.
- Retryable mutations carry stable idempotency keys.
- Expected revision is preserved when supplied by the authoritative session.
- Applied/replayed outcomes are the only outcomes that advance the client session revision.
- Conflict/rejected outcomes remain explicit and enter the shared conflict/defer workflow.
- Refresh-and-retry obtains an authoritative revision and uses a fresh idempotency key.
- Web, Desktop, and Mobile adapters preserve the same mutation and outcome semantics.
- Clients do not calculate Resource/Cost totals, rates, utilization, variance, EVM, or other authoritative financial/resource results locally.
- Localization changes presentation only and does not alter contract semantics.
- Fixture and client-sync CI tests are green before the integration is considered releasable.

This definition of done is a client integration gate; it does not replace backend/resource-domain acceptance or formal end-to-end certification.
