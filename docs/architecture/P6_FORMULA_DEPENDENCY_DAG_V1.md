# P6 Formula Dependency DAG v1

## Purpose

The formula engine already extracts deterministic field dependencies and rejects direct formula cycles. This layer adds a small, persistence-independent dependency graph for formula-to-formula recalculation.

## Rules

- A dependency is a formula edge only when its identifier exists in the supplied formula set.
- Other dependency identifiers remain external field dependencies.
- Graph construction is deterministic and rejects cycles with a dependency trace.
- Dependents are discovered transitively.
- Recalculation uses deterministic topological order; ties are resolved lexicographically.
- Only the affected closure is scheduled for recalculation.
- The graph does not own persistence, transactions, scheduling, calendars, API state, or UI state.
- No dynamic code execution is introduced.

## Flow

changed formulas -> transitive dependents -> affected closure -> deterministic topological order

For A -> B -> C, changing A produces the recalculation plan A, B, C. For a branch A -> {B, C} -> D, the stable plan is A, B, C, D.

## Boundary

This is the dependency-planning layer only. Runtime formula values remain owned by the formula evaluator/application layer. Persistence, audit records, API contracts, and client recalculation behavior are separate concerns.
