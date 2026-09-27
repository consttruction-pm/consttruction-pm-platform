# Development Memory — Permanent Team Rule

## Repository and synchronization rule
- The canonical project repository is `consttruction-pm/consttruction-pm-platform`.
- All developers must work against this repository and coordinate through its current `main` branch / approved team workflow.
- Before starting work, check the latest repository state and recent commits so work is based on the current team version.
- After modifying source, tests, configuration, documentation, or other project files: run the relevant tests/validation, then commit the verified changes to this repository.
- Do not maintain an untracked parallel implementation as the authoritative version.
- Preserve existing team changes; reconcile conflicts instead of overwriting colleagues' work.
- Commit messages should clearly describe the change and its stage/area.
- This file is the persistent team reminder; treat these rules as project development memory.

## Current project convention
The repository name intentionally contains the double-`t` spelling: `consttruction-pm` / `consttruction-pm-platform`. Do not silently correct it to `construction-pm`.

## Permanent P6 parity construction rule
- P6 Version 26 / P6 EPPM 26.4 is the current compatibility baseline for all overlapping scheduling/project-controls behavior.
- The product follows a no-silent-omission rule: every applicable P6 field, input option, calculation option, calendar rule, column/layout capability and approved import/export mapping must be implemented, intentionally superseded with equivalent/superset semantics, or explicitly dispositioned as Outside Scope.
- P6 parity must be implemented through the Shared Domain/Calculation Core and shared contracts; client/backend copies of P6 business semantics are prohibited.
- The current P6 parity baseline and timeline are maintained in:
  - docs/architecture/P6_26_4_PARITY_AND_NO_OMISSION.md
  - docs/architecture/P6_26_4_PARITY_SCORECARD_2026-09-28.md
  - docs/roadmap/P6_26_4_PARITY_TIMELINE_2026-09-28.md
- Parent implementation backlog: Issue #389.
- Team tracks: Jalal #391, Javad #392, Hasan #393.
- Current evidence-based P6 parity is 44%; overall product maturity remains 78%. These are planning/coverage measures, not runtime performance benchmarks or Oracle certification.
