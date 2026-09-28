# P6 Formula Unit Semantics v1

Status: implementation slice on `codex/jalal/p6-formula-unit-semantics-v1`.

## Scope

This slice makes numeric formula units compositional while keeping unit semantics inside the Shared/Core formula engine. It does not introduce currency conversion, calendar arithmetic, duration arithmetic, or product-specific cost engines.

## Rules

- `+` and `-` require compatible canonical units.
- `*` combines unit dimensions by adding factor exponents.
- `/` subtracts factor exponents and can create inverse units.
- `^` requires a unitless integer exponent and raises each unit exponent accordingly.
- Unit expressions are normalized deterministically, with factors sorted by name and zero exponents removed.
- Unit strings are symbolic dimensions only. No automatic currency conversion or physical-unit conversion is performed.
- Invalid unit expressions fail closed.
- Null arithmetic still returns null without inventing a unit-bearing value.

## Examples

- `m3 * USD/m3 -> USD`
- `USD / m3 -> USD/m3`
- `1 / m3 -> 1/m3`
- `m3 ^ 2 -> m3^2`
- `USD + m3 -> rejected`

## Boundary

Duration, date arithmetic, calendar-aware functions, and real unit conversion must consume the authoritative Shared Duration/Calendar Core through an adapter. This slice intentionally does not duplicate that logic.

## Verification

Focused regression coverage includes multiplication, division, inverse units, deterministic normalization, integer power semantics, incompatible units, and invalid unit syntax.
