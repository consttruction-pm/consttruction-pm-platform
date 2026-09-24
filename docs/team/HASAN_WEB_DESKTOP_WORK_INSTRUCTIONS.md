# Hasan — Web + Desktop Parallel Development Instructions

## Role
Hasan (GitHub: `hasanforoughi`) remains Developer 1 for Backend / Database / Application / API. The goal is to make one authoritative backend contract serve both the Website/Web Application and Desktop Application.

## Do not create two backends
There must be one authoritative Domain/Calculation/Application contract. Web and Desktop are clients of that contract.

## Hasan responsibilities
1. Backend/Application services.
2. Repository and database adapters.
3. API DTOs and typed serialization.
4. ProjectContext: tenant/company/project isolation.
5. Transaction boundaries at Application use-case level.
6. Optimistic locking and revision handling.
7. Resource and Cost backend.
8. Document storage/application integration.
9. Import/export contracts and schema versions.
10. Integration tests.
11. API compatibility and migration safety.
12. Audit/revision/history support.
13. Backend interfaces needed by AI Assistant/Smart Guide.

## Required client contract
For every backend feature Hasan must document:
- request DTO
- response DTO
- field types
- nullable/required fields
- validation rules
- permissions
- ProjectContext requirements
- revision/concurrency behavior
- transaction boundary
- error contract
- schema/version compatibility
- example payloads where useful

## Calculation rule
Never calculate scheduling, progress, EVM, resource or cost semantics again in API serialization or UI-specific code. Call the authoritative Domain/Calculation Core.

## Web and Desktop impact
For every backend feature, explicitly state:
- Web endpoint/contract required.
- Desktop endpoint/contract required.
- Whether both clients consume the same DTO.
- Any platform-specific presentation differences.
- Required parity test.

## Required notification
Every new or changed shared rule must:
1. Be added to the Master Reference when applicable.
2. Be added to the relevant specialized architecture document.
3. State date/stage/reason.
4. Check P6 compatibility, PMBOK/PMI alignment, Shared Calculation Core, Web-readiness, portability and tests.
5. Be explicitly announced to the user/product owner.
6. Include files/modules/actions/tests required from Hasan.

## Current immediate work
Continue Stage 33.2.3/33.2 integration hardening. PR #10 is the current transaction-contract implementation and is not yet merged. After its review/merge, continue with Stage 33.2.4 Typed Integration Contract.

## Acceptance
Hasan's backend work is accepted only when both Web and Desktop can consume the contract without creating separate business logic.
