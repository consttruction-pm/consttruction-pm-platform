# Cross-Client Resource/Cost Parity

Web, Desktop, and Mobile Resource/Cost workflows use the same client-sync mutation envelope and typed presentation DTOs.

## Required parity

- Project context is identical across clients.
- Mutable operations preserve authoritative `expected_revision` and a stable `idempotency_key`.
- Resource and assignment decimal-like values remain canonical decimal strings.
- Authoritative revisions are accepted only from successful server outcomes.
- Conflict/rejected outcomes use the shared stable error and conflict-resolution boundaries.
- Resource/Cost calculations are never reimplemented in a client.

## Platform-specific presentation

A client may localize labels, format dates/numbers, and adapt interaction patterns for web, desktop, or field/mobile use. These presentation differences must not change mutation semantics, revision handling, or authoritative calculation results.

## Acceptance

The same fixture payloads and outcomes must normalize to equivalent semantic DTOs on every client adapter.
