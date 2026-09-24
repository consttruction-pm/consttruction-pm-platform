# Stage 33.2.4 — Typed Integration Contract

## Objective
Guarantee that authoritative Domain/Application values retain semantic types across API boundaries and are consumed identically by Web and Desktop.

## Rules
1. Decimal values are serialized as canonical decimal strings.
2. Dates use explicit ISO-8601 contracts.
3. Boolean and text remain distinct.
4. Nullable fields are explicitly nullable.
5. Calculated values must be obtained by invoking the authoritative Domain method.
6. API DTOs must not introduce alternative calculation formulas.
7. Web and Desktop consume the same versioned contract.
8. Contract changes require schema versioning and regression tests.

## Current implementation
Versioned Resource and ResourceAssignment JSON Schemas plus integration regression tests.

## Next
Apply the same contract pattern to Activity, Calendar, Progress/EVM, Cost, Document and project portability datasets.
