# Stage 33.4 — Production Web/Desktop Client Foundation and Shared Client Integration

Date: 2026-09-24

## Purpose
Establish the production client foundation for the Web and Desktop applications while preserving one shared business and calculation semantics.

## Mandatory rules
- Web and Desktop consume the same versioned API/Application contracts.
- Shared Domain/Calculation Core remains the single source of calculation truth.
- Clients must not reimplement Scheduling/P6, Progress/EVM, Resource/Cost, duration, calendar, or financial calculations.
- ProjectContext must be propagated for project-scoped operations.
- Typed API contracts remain authoritative; Decimal-like values cross boundaries as canonical decimal strings.
- API/application errors remain stable and machine-readable.
- Optimistic locking and idempotency behavior must be represented consistently in both clients.
- Authentication providers stay outside the Shared Domain/Calculation Core.
- Jalali/Gregorian presentation and localization are client concerns; calendar arithmetic remains in the shared core.
- Web/Desktop capability parity is a completion requirement.

## Workstreams
### 33.4.1 Client application shells
- Web application shell and routing/navigation foundation.
- Desktop application shell and routing/navigation foundation.
- Shared workspace/navigation concepts.

### 33.4.2 Shared client integration
- Versioned API contract consumption.
- ProjectContext/session propagation.
- Typed DTO parsing/validation.
- Stable error handling.
- Revision/conflict handling.
- Idempotency-key handling for retryable mutations.

### 33.4.3 Localization and calendar presentation
- Persian/English foundation.
- Jalali/Gregorian presentation.
- No client-side duplicate scheduling/calendar arithmetic.

### 33.4.4 Security boundary
- Authentication/session integration points.
- Authorization result handling.
- Core remains provider-independent.

### 33.4.5 Cross-client parity
- Same business capabilities exposed where applicable.
- Shared contract tests.
- Web/Desktop workflow parity tests.
- Regression tests for contract/version changes.

## Ownership
- User: Web and Desktop UI/UX, client integration, presentation, localization, product acceptance.
- Hasan: backend/API integration support, shared contracts, persistence/integration support, regression coverage for shared changes.

## Completion gate
Stage 33.4 is complete only when Web and Desktop can consume the same authoritative contracts, handle context/revision/idempotency/errors consistently, and pass cross-client parity/regression checks.

No Scheduling/P6 or Progress/EVM semantics are redefined in this stage.
