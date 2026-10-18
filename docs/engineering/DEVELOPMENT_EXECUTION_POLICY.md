# Development Execution Policy

## Canonical development and test environment

The primary environment for project development, code execution, and automated testing is **GitHub/Codex**.

ChatGPT is used for project coordination, analysis, specification, review, troubleshooting guidance, and other support tasks. It is **not** the canonical runtime/test environment for the project.

GitHub/Codex must remain the authoritative working environment because the project requires SQL/PostgreSQL, GitHub Actions, and the complete runtime/tooling stack for reliable integration and runtime verification.

## Working rule

1. Developers perform implementation, execution, debugging, and testing in GitHub/Codex.
2. ChatGPT may inspect, analyze, explain, review, and coordinate changes, but missing local/runtime dependencies must not cause the project workstream to move to a ChatGPT-only execution model.
3. GitHub remains the source-controlled project workspace and the location for committed implementation artifacts and test results.
4. This policy applies to all project developers and agents, including Jalal, Hassan, and Javad.
5. Any earlier project rule that made ChatGPT the exclusive coding/testing environment is superseded by this policy.

## Rationale

A previous ChatGPT-only execution attempt was stopped because the required SQL runtime was not available. The project therefore returns to the established GitHub/Codex workflow so database-backed and full-stack tests can execute in the intended environment.


## Mandatory PMBOK-aligned Form Builder calculation contract

Before creating, changing, reviewing, or debugging any website form template, field type, formula editor, validation/conditional rule, form submission/approval flow, calculated form field, form-derived KPI/report, or AI-assisted form generation, read:

- `docs/engineering/PMBOK_FORM_BUILDER_AND_FORM_CALCULATIONS.md`

This document identifies the current PMBOK edition and related PMI sources, distinguishes documented guidance from optional CUBI/project-configured formulas, defines typed form/field/calculation behavior, and maps current form/formula-core components with known gaps. It is mandatory engineering authority for this area.

For formulas that read schedule dates, durations, calendars, resource capacity/units/cost, progress, EVM or WBS values, the form layer must use the canonical shared CUBI domain/calculation services. It must not create a duplicate CPM, calendar, resource-leveling or EVM implementation. The standalone scheduling calculation contract remains the authority for reference-compatible scheduling/Project Controls formulas once merged.

Every form-calculation change must document contract section IDs, formula authority class, source/input/output units, null/zero/rounding behavior, field dependencies, tests and exact final SHA. AI-generated fields/formulas are draft-only until type-checked, tested and approved by an authorized human.

**Status: ACTIVE for engineering changes in the form-builder area on this branch; merge this policy/document before treating the requirement as active on main.**
