# Daily Parallel Work Allocation

## Purpose
This document establishes the project's daily parallel-work model so that one developer's unfinished PR does not unnecessarily stop another developer's work.

## Core rule
Work must proceed in parallel whenever technically possible. A PR being unfinished is **not** by itself a blocker for another lane.

Only a real technical dependency may block a task. When a dependency exists, convert it into a stable contract/interface, mock, fixture, or test boundary where practical so independent work can continue.

## Mandatory daily start procedure
Before starting daily work, every team member must read and confirm understanding of:
- this document,
- current project status,
- active engineering rules,
- assigned daily task and expected output.

No development activity should start before reviewing these rules.

## Development and test environment rule
The project currently uses:
- ChatGPT: design, analysis, code review, implementation guidance, test planning, debugging support and preparation of changes.
- GitHub: source control, team synchronization, version history and controlled CI execution.

ChatGPT is not considered a permanent replacement for a real runtime environment. PostgreSQL, long-running tests, performance tests and full integration verification must be executed in a suitable GitHub/runtime environment when available.

## GitHub Free resource management rule
To avoid hitting GitHub Free limitations:
- Daily development changes should use focused tests.
- Fast CI tests should be preferred for frequent commits.
- Heavy regression, performance and database-load tests should be scheduled periodically, not on every commit.
- Test execution must be planned according to available CI resources.

## Lanes

### Jalal — Shared Core / Project Controls Intelligence / Integration QA
Daily focus:
- Shared Domain and Calculation Core
- Scheduling and project-controls logic
- P6/PMBOK conformance checks
- Cross-module architecture and contracts
- Independent tests and verification
- Integration readiness and regression analysis
- Work that does not require Hasan's or Javad's PR to be merged

Dependency rule:
- Do not wait for Backend or Client PR completion unless the work is technically impossible without it.
- Prefer contracts, fixtures, mocks, and independent verification.

### Hasan — Backend / Database / Application / API / Enterprise Integration
Daily focus:
- Backend and database implementation
- API/application/repository layers
- Persistence, transactions, locking, idempotency and integration boundaries
- Backend tests and CI/typecheck fixes
- Complete and verify his own bounded PRs

Dependency rule:
- Do not wait for Jalal's or Javad's branch to finish when the backend contract is already defined.
- Publish/update the contract when a client-facing dependency is needed.

### Javad — Web / Desktop / Mobile / UX / Field Experience
Daily focus:
- Client applications and UI/UX
- Web/Desktop/Mobile experience
- Client sync and offline/online behavior
- API-contract consumption using stable contracts/mocks when Backend is not yet merged
- Client tests and typecheck

Dependency rule:
- Do not wait for Backend merge when the API contract is sufficient to continue.
- Use fixtures/mocks for unfinished backend behavior.

## Integration policy
1. Each lane owns a bounded daily outcome.
2. Shared files are changed only when necessary and with coordination.
3. Integration happens after independent work reaches a verifiable boundary.
4. No lane is treated as a serial prerequisite for the others.
5. Merge/CI problems are investigated separately from product development so they do not unnecessarily consume another lane's working time.
6. Any actual blocker must be recorded with:
   - exact dependency,
   - affected lane,
   - why a contract/mock/fixture cannot unblock it,
   - next concrete action.

## Daily completion standard
Each lane should finish with:
- implemented or verified scope,
- tests/evidence where applicable,
- known blockers explicitly identified,
- a clear handoff point for integration.

Status: Active project working rule.
