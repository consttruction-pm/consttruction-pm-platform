# Development & Testing Rules

## Priority Rule 01 — GitHub/Codex-First Development and Testing

This is a mandatory project-wide rule for **Jalal, Hassan, Javad, and every future project contributor**.

### 1. Primary development and test environment

The project's **canonical and primary development, implementation, execution, and test environment is GitHub/Codex and the project repository**:

- Repository: `consttruction-pm/consttruction-pm-platform`
- Primary branch: `main`
- Feature/fix work is performed in repository branches and/or approved Codex working environments connected to the repository.
- Source code, tests, configuration, documentation, migrations, SQL/PostgreSQL work, and other project artifacts are developed against the repository's current state.
- Required unit, integration, regression, concurrency, validation, client, and database-backed tests are executed in the GitHub/Codex development/test workflow and its CI/runtime environments as applicable.
- The repository history, commits, pull requests, reviews, and CI results provide the authoritative trace of implementation and verification.

### 2. ChatGPT is the coordination, analysis, and review environment

ChatGPT is **not the project's primary coding, implementation, execution, or test environment**.

ChatGPT is used for:

- project direction and technical coordination;
- architecture and requirements analysis;
- implementation planning;
- code and change review;
- audit and gap analysis;
- test strategy and acceptance criteria;
- interpreting CI, PostgreSQL, client, and other runtime results;
- identifying defects and specifying corrective work;
- coordinating contributors and avoiding duplicate implementation.

ChatGPT may inspect repository content through the available GitHub/Codex tooling when necessary, but this does **not** make the ChatGPT conversation environment the authoritative development or test environment.

### 3. No transfer-to-ChatGPT development rule

Project files must **not** be transferred/imported into the ChatGPT environment as a prerequisite for development or testing.

The previous rule requiring:

- importing/uploading project files into ChatGPT;
- implementing code in the ChatGPT working environment;
- executing tests in the ChatGPT working environment; or
- returning finalized files from ChatGPT to GitHub

is **obsolete and explicitly revoked**.

The repository remains the source of truth throughout the workflow.

### 4. Mandatory workflow

The standard project workflow is:

**GitHub Repository → inspect current state → plan/implement in GitHub/Codex → commit → CI/runtime tests → review/audit → fix if required → retest → merge to main → post-merge verification**

For database-backed work:

**Repository → implementation → real PostgreSQL-capable runtime/CI → verification → merge**

A change must not be considered complete merely because it has been written locally or committed. It must satisfy the applicable repository/CI/runtime verification gates.

### 5. Team-wide applicability

This rule applies equally to **Jalal, Hassan, Javad, and all other contributors**.

No contributor should treat a ChatGPT conversation or ChatGPT-local working environment as the authoritative source of project code or test results.

The authoritative implementation is the repository state; the authoritative automated verification is the applicable GitHub/Codex/CI/runtime evidence.

### 6. Completion gate

Before a stage is marked complete:

1. The implementation exists in the canonical repository.
2. The relevant focused tests have been executed.
3. Applicable regression tests have been executed.
4. Database-backed behavior has real database-backed verification when required.
5. Client changes have applicable typecheck/runtime verification.
6. Failures have been fixed or explicitly documented as approved blockers.
7. The resulting change has been reviewed for architectural and boundary consistency.
8. The verified change is merged or otherwise recorded according to the project's approved Git workflow.

### 7. Relationship to other project rules

This rule must be applied together with:

- Primavera P6 baseline behavior for shared scheduling/project-control logic;
- Shared Domain/Calculation Core and web-readiness requirements;
- deterministic and reproducible calculations;
- typed data models and export requirements;
- versioning, auditability, idempotency, optimistic locking, and transaction rules;
- mandatory automated testing and regression verification;
- real PostgreSQL verification for database-backed behavior.

When a process conflict is discovered, preserve the canonical repository state and its verified history rather than creating a parallel ChatGPT-local implementation.

## Rule status

**Status: ACTIVE — PROJECT-WIDE — MANDATORY**

**Applies to:** Jalal, Hassan, Javad, and all current/future contributors.

**Effective from:** 2026-09-27

**Correction:** This document supersedes the obsolete ChatGPT-first development/testing wording that previously appeared in this file.