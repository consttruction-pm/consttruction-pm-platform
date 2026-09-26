# Stage 34.1 — Shared Control Intelligence

Status: **contract/domain foundation implemented and runtime-verified in main CI**.

## Implemented packages
- Cross-domain dependency graph with revision-scoped nodes and typed relationships.
- Auditable control-intelligence result with mandatory source references.
- Revision-scoped scenario request/proposal boundary; proposals cannot mutate authoritative state.
- Cross-domain impact contract linking Schedule/Progress/EVM/Resource/Cost and other construction domains.
- Natural-language schedule query contract with revision scope and traceable answers.
- Predictive schedule-risk boundary with model version, confidence and source evidence; no risk formula is defined here.
- Change/Claim impact links to schedule/cost evidence with application approval boundary.
- Portfolio control/decision/action boundaries were subsequently hardened in Stage 34.2 and remain separate from authoritative project calculations.

## Mandatory boundary
These contracts do not redefine or duplicate Primavera P6 scheduling, calendar, duration, Progress/EVM, Resource/Cost or financial formulas.
Client applications must consume these versioned contracts and must not become an authoritative calculation engine.

## Verification
- Focused control-intelligence domain regression tests are present.
- Full repository pytest CI runs successfully on the current main branch.
- Stage 34.2 integration work adds the persistence, client-sync, approval, audit and PostgreSQL runtime gates required around these shared contracts.
- Remaining work is product-level expansion/integration, not recovery of a missing Stage 34.1 contract foundation.
