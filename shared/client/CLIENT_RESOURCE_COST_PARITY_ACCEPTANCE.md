# Resource/Cost Client Parity Acceptance

This acceptance checklist is the cross-client gate for Resource/Cost integration.

## Web / Desktop / Mobile

Each client adapter must:

1. Preserve tenant, company, and project context.
2. Preserve the authoritative expected revision on mutations.
3. Generate and preserve a stable idempotency key for retryable mutations.
4. Normalize Resource/Assignment DTOs with identical field semantics.
5. Preserve decimal-like values as canonical strings.
6. Advance revision only from applied/replayed authoritative outcomes.
7. Surface conflict/rejected outcomes through the shared error/conflict contracts.
8. Never calculate Resource/Cost totals, rates, utilization, variance, or EVM locally.

## Platform-specific behavior

Localization, number/date formatting, navigation, and interaction patterns may differ by platform. Mutation identity, revision semantics, decimal representation, calculation ownership, and conflict actions may not differ.

## Release gate

A client Resource/Cost implementation is conformant only when its adapter tests pass against the shared fixture pack and produce semantically equivalent normalized payloads.
