## Summary
<!-- Describe the behavior and user-visible scope. -->

## Calculation contract (mandatory for any calculation-related or calculation-adjacent change)
- [ ] I reviewed `docs/engineering/PRIMAVERA_CALCULATION_LOGIC_AND_FORMULAS.md` and identified applicable section IDs (or stated why this PR does not affect calculations).
- [ ] Official reference source URL/title/edition and exact rule are stated below.
- [ ] Any unresolved behavior is marked OPEN/PARITY TEST REQUIRED and tracked; no undocumented assumption is presented as reference behavior.
- [ ] Calculation logic remains in the shared domain/calculation core; no duplicate formulas were added to UI, API, reports, exports or AI prompts.
- [ ] Formula/boundary/option-interaction/regression tests cover the change and preserve relationship, constraint and resource-capacity validators.
- [ ] Final demand, dates, float, cost/EVM and summaries (as applicable) are asserted from the authoritative final result, not just a proposal.
- [ ] Focused tests and full required CI are green on the exact final SHA.
- [ ] Independent review completed.

**Contract section IDs:**  
**Official reference sources and exact rule:**  
**Tests / expected inputs and outputs:**  
**Exact final SHA and CI links:**  
**OPEN risks / tracked issue:**  

## General verification
- [ ] Relevant typecheck/build/integration/database tests pass.
- [ ] Persistence/API/DTO/import/export round trips are covered where affected.
- [ ] Accessibility, multilingual, RTL/LTR and locale invariance are preserved where applicable.
- [ ] User-facing text does not expose internal engineering source-provider names or URLs.
