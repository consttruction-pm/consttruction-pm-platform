## Change classification
- [ ] Product behavior / calculation semantics changed
- [ ] Test-only change; no semantic behavior change
- [ ] Documentation / tooling only

## Documentation-first conformance (required for calculation changes)
- Official source (publisher, exact version, section, URL):
- Source publication/version date:
- Source-derived rule(s):
- Edge cases and precedence:
- Calculation-conformance matrix entry:
- Authoritative Shared Core function/module:
- Regression test(s) mapped to each rule:
- Independent semantic reviewer and confirmation link:
- Any unresolved semantics (must be marked UNVERIFIED/BLOCKED):

## Verification evidence
- Focused command and result:
- Regression/full CI run URL and exact tested SHA:
- PostgreSQL/runtime evidence where affected:
- Explicit constraints and final resource-capacity checks preserved:
- Scope/revision/hash and persistence/fresh-read evidence where affected:

## Review gates
- [ ] No client/API adapter introduces duplicate calculation authority
- [ ] No validation/test was removed or weakened to make the change pass
- [ ] Independent semantic review completed when behavior changes
- [ ] Exact-head required CI is green
- [ ] Known gaps and non-verified behavior are stated honestly
