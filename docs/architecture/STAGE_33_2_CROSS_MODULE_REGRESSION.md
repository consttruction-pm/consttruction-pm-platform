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

## Covered integration contracts

- Versioned Scheduling CalendarContext resolves to the authoritative Shared Core calendar resolver.
- Resource calendar capacity is preserved alongside time-phased resource values; the integration layer does not recalculate those values.
- Portfolio/reporting read models pass through authoritative calculated metrics without recomputing formulas.

## Remaining verification

PostgreSQL runtime coverage should continue to exercise the same boundaries where a production gate is available.