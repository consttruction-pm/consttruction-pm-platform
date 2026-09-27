# Stage 33.2.6 — Cross-Module Regression Suite

This suite verifies the integration boundary after the 33.2.1–33.2.5 contracts.

## Covered boundaries

- Resource assignment -> authoritative Resource/Cost calculation -> EVM bridge.
- Resource assignment optimistic-lock revision rejection.
- Tenant/company/project isolation with no cross-project assignment leakage.
- Project export/import preserving calendar/version, calculation settings and Resource/Cost configuration deterministically.

The tests consume existing authoritative Resource/Cost and EVM implementations. They do not introduce scheduling, Progress/EVM, Resource/Cost or financial formulas into the integration layer.

## Regression rule

A future integration change must preserve the existing calculation outputs and pass these boundary tests. Cross-module references remain typed/opaque at the portability boundary; authoritative modules retain ownership of their calculations.

## Remaining verification

Reporting/read models must continue to consume authoritative calculated datasets rather than recomputing domain formulas in API/client layers.