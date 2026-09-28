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

## Current limitation

The v1 contract accepts changed formula IDs. Changes to external/base fields will require a later dependency-index extension so a field change can invalidate the formulas that reference it without pretending the field itself is a formula node.
