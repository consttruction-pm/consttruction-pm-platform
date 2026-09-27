# Stage 34.3 — Shared Dependency Graph Contract

## Progress
**Contract-definition slice: 100%.** Runtime CI verification remains the gate for this slice.

## Authoritative Shared Core contract
The existing dependency-graph.v1 schema and control_intelligence.graph model are the authoritative cross-domain reference contract.

The graph is a typed, auditable reference model. It links authoritative domain records; it does not reimplement Scheduling/P6, Calendar/Duration, Progress/EVM, Resource/Cost, or financial calculations.

### Required semantics
- Explicit tenant/project/project revision scope.
- Typed domain identity for every node.
- Independent source and target revisions on every edge.
- Known relation/domain enums only; unknown values are rejected.
- Structural graph validation only; no hidden recalculation.
- Persistence/API owns storage, authorization, optimistic locking and transactions.
- Web/Desktop/Mobile consume the same contract and do not create client-specific calculation formulas.

## Regression evidence
- shared/contracts/dependency-graph.v1.schema.json
- src/construction_pm/control_intelligence/graph.py
- src/construction_pm/dependency_graph_conformance.py
- tests/integration/test_dependency_graph_contract.py

## Compatibility review
P6/Scheduling, Progress/EVM, Resource/Cost and financial semantics are unchanged. The contract only establishes cross-domain references and revision provenance.
