# Resource infrastructure boundary

Date: 2026-10-08

## Canonical production boundary

New cross-module infrastructure must use the `backend_p0` family:

- `backend_p0.models.BackendScope` for tenant/project/revision scope.
- `backend_p0.transactions.TransactionManager` for transaction ownership.
- `backend_p0.idempotency.IdempotencyStore` for durable idempotency and replay.

## Legacy Resource package

The `construction_pm.resources` package still contains a supported Resource-domain compatibility surface. Its `ProjectContext` and idempotency implementation remain in use by Resource application/repository code and existing regression tests, so they are not removed speculatively.

The legacy transaction module is already explicitly a compatibility/test adapter; production Resource application code uses the canonical `backend_p0.transactions.TransactionManager`.

The legacy scope/idempotency modules are marked deprecated and are migration-only boundaries. They must not spread into unrelated production packages.

## Enforcement

`scripts/check_legacy_resource_infrastructure.py` scans production Python under `src/construction_pm` and fails when the three legacy infrastructure module paths escape the `resources/` package.

This is intentionally a containment gate, not a claim that the Resource package migration is complete.

## Migration order

1. Keep Resource behavior stable while documenting the boundary.
2. Migrate Resource production consumers from legacy scope/idempotency to canonical adapters with dedicated regression coverage.
3. Re-run full repository search and CI.
4. Remove the legacy modules only after supported consumers reach zero.
