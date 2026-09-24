# Stage 33.4.60 — Live PostgreSQL CI Integration

A dedicated GitHub Actions workflow now provisions PostgreSQL 16 as a CI service and runs an opt-in live connectivity integration test.

## Scope

The workflow verifies that CI can provision PostgreSQL and establish a real client connection.

## Verification rule

Creating the workflow is not the same as a successful CI execution. Stage completion for runtime verification requires an actual successful GitHub Actions run.

## Security

The CI database is ephemeral and uses test-only credentials. No production credentials are stored in the repository.

## Next gate

After the live connectivity run is verified, execute real sync-state persistence and concurrent idempotency tests against the same service.
