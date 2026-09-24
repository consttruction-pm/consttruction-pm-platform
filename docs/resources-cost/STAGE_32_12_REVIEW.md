# Stage 32.12 — Resource/Cost Backend Integration Review

## Review status

- Source branch reviewed: `feature/resource-backend-foundation`
- Review branch: `review/stage-32-12-resource-backend`
- Hasan's branch head: `c9b63d23f4a9da7fdb50c4cc2f72caed361472fc`
- Main at review start: `58fd04c7b68f058ba747c853a3c1b1c817896f88`
- Branch relation: 18 commits ahead, 1 commit behind main; divergent.
- Merge decision: **do not merge yet**.

## Confirmed alignment

1. Domain, application, repository, persistence and API boundaries are separated.
2. Decimal values remain exact through the persistence boundary.
3. SQLite foreign-key integrity and explicit transaction boundaries are present.
4. Resource optimistic locking and schema version tracking are present.
5. Persistence tests cover rollback, exact Decimal text, rate round-trip and stale revisions.

## Defects found during review

### API DTO defect — fixed on review branch

`assignment_to_dto()` passed the bound method `assignment.normalized_remaining_units` instead of calling it. This would produce an incorrect DTO value and contradict the existing API test expectation.

Fix:
`decimal(assignment.normalized_remaining_units())`

### Remaining production-readiness items

- Add tenant/company/project ownership context to persistence contracts.
- Decide and implement revision/concurrency semantics for assignments.
- Define application-level transaction orchestration for multi-step use cases.
- Keep resource-rate history auditable rather than relying on delete/reinsert semantics for all updates.
- Keep infrastructure adapters database-specific while preserving a portable repository contract.
- Add integration tests against the authoritative Stage 32.8 resource/EVM/XLSX contracts.
- Reconcile the branch with the latest main before PR approval.
- Execute the full test suite in CI/local development; current review has not executed the repository test runner.

## Acceptance gate

The branch should not be merged into `main` until the remaining production-readiness items are addressed and the complete test suite passes.
