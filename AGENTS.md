# Repository-wide AI/Codex Instructions

## Mandatory calculation authority
Before creating, modifying, reviewing or debugging any scheduling, date, calendar, relationship, resource, cost, baseline, earned-value, float, resource-leveling, report/formula-column or AI calculation behavior, read:

- `docs/engineering/PRIMAVERA_CALCULATION_LOGIC_AND_FORMULAS.md`

Treat it as mandatory, version-controlled engineering authority. This requirement applies to all contributors and all product surfaces, including web, desktop, later mobile, API, persistence, import/export, chart/Gantt/grid, offline functionality and AI assistant/tools.

## Required workflow for calculation changes

1. Locate the relevant contract section and current official reference documentation. Do not rely on intuition, general CPM/EVM conventions, previous implementation or an existing test alone.
2. Put the section ID(s), applicable official source URL/title/edition, and exact rule in the PR description before implementation is considered ready for review.
3. When official material leaves behavior ambiguous, label the item OPEN/PARITY TEST REQUIRED, create or update a tracked issue, and create a reproducible reference fixture. Do not invent an answer or claim parity without evidence.
4. Implement calculation behavior only in the shared domain/calculation core. UI, API adapters, reports, exports and AI prompts must not contain shadow formulas.
5. Add focused formula, boundary, multi-calendar, option-interaction and regression tests as applicable. Keep final relationship/constraint/resource-capacity validators enabled.
6. Run focused tests and full required CI on the exact final commit SHA. Attach results and ask for independent review. Re-run after any subsequent edit.
7. Do not mark work complete or increase weighted project progress based only on a commit, comment, proposal, audit or red CI.

## Safety and architecture rules

- Never weaken/delete a validator, skip an exception, convert failure into a successful schedule, drop a relationship or guess a missing calendar/rate/capacity/baseline to make CI pass.
- Bind calculation inputs to immutable project/revision, calendar IDs/versions, selected options, baseline and calculation identity. Preserve scope and precision across storage/DTO/API/adapter paths.
- Keep user-facing product UI, help, docs, branding and AI responses free of internal reference-provider names, URLs, icons and source indications. Internal engineering documents/tests may cite official sources to demonstrate conformance.
- For CUBI-specific payment, claims, contract, ISO/PMBOK, cash-flow and AI additions, use a separate approved calculation contract; never silently alter base CPM/resource/EVM semantics.
- Presentation-only changes (icon, color, language, RTL/LTR or Jalali/Gregorian display) must not alter results.

## Pull request requirements

Calculation-affecting PRs must complete the checklist in `.github/pull_request_template.md`. Missing source evidence, missing tests, failing CI or unresolved high-risk ambiguity blocks merge. Review the calculation contract's OPEN backlog before claiming complete coverage.
