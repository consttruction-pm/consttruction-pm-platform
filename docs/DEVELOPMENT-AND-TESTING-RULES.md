# Development & Testing Rules

## Priority Rule 01 — ChatGPT-First Development and Testing

This is a mandatory project-wide rule for **Jalal, Hassan, Javad, and every future project contributor**.

### 1. Primary development and test environment

All project work must be performed first in the **ChatGPT working environment** by:

- importing/uploading the required project files into ChatGPT;
- reviewing the current source, architecture, requirements, and existing tests;
- implementing and modifying code in the ChatGPT working environment;
- executing the required tests in the ChatGPT working environment;
- fixing detected defects;
- rerunning the relevant tests and regression tests;
- completing the required verification before the work is considered finished.

### 2. GitHub is not the primary development/test environment

GitHub is **not** the project's primary coding, implementation, execution, or test environment.

GitHub is used as:

- a source from which project files can be obtained;
- the controlled repository for storing completed project files;
- a version/history repository for completed and approved changes;
- a return/storage path for finalized artifacts after implementation and testing are complete.

### 3. Mandatory workflow

The standard project workflow is:

**GitHub → obtain project files → ChatGPT → inspect → implement/code → execute → test → fix → retest/regression → verify → return finalized files to GitHub**

A change must not be considered complete merely because it has been committed or stored in GitHub.

### 4. Completion gate

Before returning a changed artifact to GitHub:

1. The implementation must be complete for its assigned scope.
2. Required unit, integration, regression, concurrency, validation, or other applicable tests must be executed in the ChatGPT working environment.
3. Detected failures must be resolved or explicitly documented as an approved blocker.
4. The final artifact must be consistent with the project's architecture and established engineering rules.
5. Only the completed/finalized artifact is returned to GitHub.

### 5. Team-wide applicability

This rule applies equally to **Jalal, Hassan, Javad, and all other contributors**. No contributor may bypass this rule by treating GitHub itself as the authoritative test environment for work that has not first been implemented and verified in the ChatGPT working environment.

### 6. Relationship to other project rules

This rule has project-wide priority and must be applied together with:

- Primavera P6 baseline behavior for shared scheduling/project-control logic;
- shared Domain/Calculation Core and web-readiness requirements;
- deterministic and reproducible calculations;
- typed data models and export requirements;
- versioning, auditability, idempotency, optimistic locking, and transaction rules;
- mandatory automated testing and regression verification.

When a process conflict is discovered, the work must preserve the completed, tested, and verified state rather than bypassing the development/test gate.

## Rule status

**Status: ACTIVE — PROJECT-WIDE — MANDATORY**

**Applies to:** Jalal, Hassan, Javad, and all current/future contributors.

**Effective from:** 2026-09-26
