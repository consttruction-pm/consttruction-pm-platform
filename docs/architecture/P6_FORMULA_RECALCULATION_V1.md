# P6 Formula Recalculation v1

## Purpose

Connect the deterministic formula dependency DAG to the Shared Formula Core evaluator so affected formula columns can be recalculated in dependency-safe order.

## Contract

Input:

- compiled formula set exposed through FormulaDependencyGraph;
- current field/formula values;
- a set of changed formula identifiers.

Processing:

1. Build the affected closure from the dependency DAG.
2. Produce deterministic topological recalculation order.
3. Evaluate each affected compiled formula using the current working values.
4. Feed each newly calculated result back into the working values for downstream formulas.
5. Return only the affected formula results and the executed plan.

## Boundaries

This layer does not:

- parse formula text;
- type-check formulas;
- implement operators or functions;
- own dependency discovery;
- own cycle semantics;
- persist formulas;
- own transactions or API state.

Those responsibilities remain in the Shared Formula Core, dependency graph and later persistence/application layers.

## Determinism

For the same compiled formulas, input values and changed set, the recalculation plan and results are deterministic. Formula evaluation stops on the first calculation error; no partial result object is returned.

## External field changes

The recalculation graph now indexes every referenced dependency identifier. A change to an external/base field can therefore invalidate the directly dependent formulas and their full transitive dependent closure without treating the external field as a formula node.

The contract now exposes `recalculate_changes(...)` for this use case. Changes to unrelated fields produce an empty deterministic plan.
