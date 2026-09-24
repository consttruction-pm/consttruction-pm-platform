# Work Split — Two Developer Model

## Developer 1 — Backend / Database
Owner: نفر اول تیم توسعه
Contact email: Farmj22001@gmail.com

Primary scope:
- Database and migrations
- Backend domain/application/repository layers
- API contracts
- Resource & Cost backend
- Validation and persistence
- Backend tests
- Integration support with Scheduling, Progress/EVM and Reporting

## Developer 2 — Product/Core/Integration
Owner: نفر دوم / project lead
Primary scope:
- Shared scheduling/calculation core
- P6-compatible scheduling semantics
- Progress and EVM integration
- Reporting/print
- AI assistant and smart guide
- Product workflows and UI
- Cross-module architecture and acceptance

## Shared rules
- Both developers pull/rebase from main before starting a new task.
- Do not overwrite another developer's active work.
- Use feature branches for non-trivial changes.
- Every change requires tests where applicable.
- Database changes must be documented and migration-safe.
- Shared contracts must be backward-compatible unless explicitly versioned.
- The repository documentation is the source of truth for project state.
