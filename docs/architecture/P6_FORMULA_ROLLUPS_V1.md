# P6 Formula Rollups v1

## Purpose

Provide a Shared Core rollup primitive for calculated columns that participate in Summary, WBS and Project views.

## Semantics

The rollup engine accepts the child scope selected by the domain/application layer and performs only typed aggregation:

- SUM ignores null children and returns null when no value is present.
- MIN ignores null children and returns null when no value is present.
- MAX ignores null children and returns null when no value is present.
- numeric units are normalized through FormulaValue and must remain compatible.
- child rows are traversed in stable identifier order for deterministic evaluation.
- nonnumeric present values are rejected; null values are not type errors.

A compiled numeric formula can be evaluated independently for each child row and then aggregated.

## Boundary

This module does not know about Activity, WBS or Project hierarchy traversal. The caller is responsible for selecting the child scope. It does not parse formulas, implement formula operators, persist results, or define UI behavior.

## Conformance

The primitive is intentionally aligned with the existing Shared Formula Core SUM/MIN/MAX null and unit semantics. It is not a claim of complete P6 rollup parity; that remains a conformance task for subject-area-specific summary behavior.
