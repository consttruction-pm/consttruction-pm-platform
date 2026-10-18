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

## Priority Rule 02 — Mandatory calculation-contract and source conformance

This rule is project-wide and mandatory for Jalal, Hasan, Farmj/Javad and every current/future contributor, including AI coding agents.

### 1. Required source of truth

Before implementing, changing, debugging, reviewing or signing off any scheduling, relationship, calendar, date, float, resource leveling, assignment, rate/cost, baseline, earned-value, WBS rollup, calculated report/grid/chart/Gantt field, calculation API or AI calculation tool, read:

- \`docs/engineering/PRIMAVERA_CALCULATION_LOGIC_AND_FORMULAS.md\`
- Root \`AGENTS.md\`
- The applicable current official reference documentation linked by the calculation contract.

The calculation contract governs reference-compatible calculation behavior. A test or existing code path is not sufficient evidence if it conflicts with documented behavior.

### 2. Pre-implementation gate

Before editing calculation code, the contributor must identify the contract section IDs and official source title/URL/edition, explain the rule being implemented, define test inputs and expected outputs, and state any unresolved ambiguity. If official sources do not define an edge case, mark it OPEN/PARITY TEST REQUIRED and obtain reproducible reference evidence or a documented decision. Guessing or claiming parity without evidence is prohibited.

### 3. Formula and implementation location

Calculation formulas must reside in the shared domain/calculation core. UI, API adapters, persistence mapping, reports, chart/Gantt rendering, exports, and AI prompts/tools must not introduce independent shadow calculations. A command, button, icon, field, report or AI tool that can change or display calculations must map to the calculation contract and the UI action/icon registry requirement in its Section 18.

### 4. Mandatory evidence before completion

A calculation PR must identify contract sections, cite official references and the exact rule, include formula and interaction regression tests, assert final dates and final resource demand where applicable, preserve all fail-closed validators, pass focused tests and full required CI on the exact final SHA, and receive independent review. Re-run tests after any later code change.

A proposed resource shift is not a calculated schedule. No result is acceptable if relationships, constraints or selected capacity rules are violated, even when an intermediate proposal passes. Do not weaken validators or hide failures to turn CI green.

### 5. Product-surface invariance

The same engine/output must be used across web, desktop, reports, exports, offline mode and the CUBI assistant. Language selection, RTL/LTR, Jalali/Gregorian date presentation, numerals, icons, colors and theme cannot change calculation results. User-facing content must not expose internal source-provider branding or links; internal engineering evidence may cite official sources.

### 6. Merge and progress gate

Missing source evidence, missing tests, failing CI, or unresolved high-risk ambiguity blocks merge/completion. Do not increase Jalal 4 weighted progress for an audit, comment, undocumented assumption or red-CI commit. Update the OPEN backlog rather than deleting a gap to make coverage appear complete.

**Status: ACTIVE — PROJECT-WIDE — MANDATORY.**
