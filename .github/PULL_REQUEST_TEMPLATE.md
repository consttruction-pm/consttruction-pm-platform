## Summary
<!-- What changed and why? -->

## Scope and ownership
- **Current main base SHA:**
- **Owner / reviewer:**
- **Related issue(s):**
- **Files/modules expected to change:**
- **Explicit non-goals:**

## Documentation-first conformance (mandatory for production changes overlapping P6 behavior)
- **Production behavior changed?** Yes / No
- **Product/profile and exact version:** (for example, P6 Professional v26 or P6 EPPM REST v26)
- **Official source and exact section/field:**
- **Direct official source URL(s):**
- **Versioned calculation-conformance matrix entry:**
- **Source-derived rule and edge cases:**
- **Affected canonical Shared Core field/function:**
- **Regression tests linked to the rule:**
- **Independent semantic reviewer (not the author):**
- **Reviewer disposition and evidence link, recorded before production implementation:**
- **Unspecified or unsupported semantics:** None / list and mark UNVERIFIED or BLOCKED
- **If this is test-only, explicitly confirm:** “No production semantic change; this test verifies an already documented contract.”

Do not guess when the versioned source does not specify a required behavior. Mark it UNVERIFIED/BLOCKED and leave production behavior unchanged until authoritative vendor evidence or a controlled versioned runtime fixture resolves it.

## Verification evidence
- **Focused tests and exact result:**
- **Regression tests and exact result:**
- **Exact PR head SHA:**
- **ConstructionPM CI:** link + result
- **Client Typecheck:** link + result / Not applicable with reason
- **PostgreSQL Integration / Sync State checks:** link + result / Not applicable with reason
- **Runtime or end-to-end verification:** evidence / Not applicable with reason

## Data, migration, and compatibility
- **Contracts/API/interchange affected:**
- **Persistence/migration/round-trip impact:**
- **Backward compatibility and failure behavior:**

## Remaining blockers and acceptance
- [ ] Required independent review is recorded before production-code changes.
- [ ] Source → rule → code → regression-test trace is complete for every affected P6-overlap behavior.
- [ ] All applicable exact-head checks are green.
- [ ] No unresolved source semantics are represented as verified.
- [ ] Remaining blockers are listed and the PR remains Draft if any applicable gate is unresolved.
- [ ] Final acceptance explicitly distinguishes green CI from full semantic parity.
