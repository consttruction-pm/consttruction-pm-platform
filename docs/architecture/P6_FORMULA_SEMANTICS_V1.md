# P6 Formula Semantics v1

Status: implemented on branch `codex/jalal/p6-formula-semantics-v1`; runtime-verified by ConstructionPM CI run **1700** and Client Typecheck run **1403**.

## Scope

This slice establishes the first safe Shared/Core formula semantics boundary for the P6 parity track. It is provider-neutral and does not move scheduling, calendar, progress/EVM, resource/cost, or financial calculations into formula infrastructure.

## Pipeline

`Formula text -> tokenizer -> parser -> AST -> type checker -> dependency analyzer -> cycle detector -> deterministic evaluator`

The evaluator never executes Python or JavaScript source and never calls `eval`/`exec`.

## Supported v1 semantics

- field references using `[field_id]`;
- Decimal numeric literals and deterministic Decimal arithmetic;
- unary `+` and `-`;
- arithmetic `+`, `-`, `*`, `/`, `^`;
- comparisons `=`, `==`, `!=`, `<>`, `<`, `<=`, `>`, `>=`;
- boolean `AND`, `OR`, `NOT`;
- functions `IF`, `SUM`, `MIN`, `MAX`, `ABS`, `ROUND`, `COALESCE`;
- explicit result-type validation;
- null propagation / null-aware aggregate behavior;
- numeric unit compatibility checks;
- deterministic field dependency extraction;
- circular formula dependency rejection;
- versioned formula definitions.

## Explicit boundaries

Date/datetime and calendar-aware formula functions are intentionally not implemented in this first slice. Those semantics must consume the authoritative Shared Calendar/Duration Core rather than introducing a second date engine.

Formula persistence, API transport, columns/views/layouts, import/export mappings, WBS/project rollups, and audit storage remain separate subsequent boundaries.

## Regression evidence

The focused test module covers:

- precedence and Decimal arithmetic;
- dependency extraction;
- logical/conditional formulas;
- null behavior;
- incompatible units;
- missing fields;
- branch type mismatch;
- Decimal rounding;
- division-by-zero;
- syntax failures;
- aggregate/coalesce null handling;
- circular dependency detection;
- result-type mismatch;
- unsupported function rejection.

The implementation was corrected after the first CI run exposed two nullable-result/aggregate typing defects. The corrected commit passed the full repository test suite on all three supported Python versions.