## Change type
- [ ] Feature / production behavior
- [ ] Calculation-semantic or calculation-input mapping change
- [ ] Persistence / API / interoperability contract
- [ ] Test-only or documentation-only; **no calculation-semantic change**

## Documentation-first conformance (mandatory for scheduling, relationships, priorities/leveling, calendars, constraints, dates/durations, progress/EVM, or numerical AI outputs)
- [ ] Exact authoritative source cited with document/version and specific topic/section:
- [ ] Source-derived rule and edge cases added to docs/architecture/CALCULATION_CONFORMANCE_MATRIX.md (stable rule ID):
- [ ] Typed input/output contract, units, precedence, scope/revision and error behavior stated:
- [ ] Independent semantic reviewer (not the author) confirmed the interpretation **before production calculation code was changed**; reviewer/outcome:
- [ ] Positive, boundary, negative and interaction tests mapped to the matrix rule; test names:
- [ ] Production write → commit → fresh scoped read → immutable input → real provider/query path tested where applicable:
- [ ] Unsupported, stale, cross-scope or incomplete calculation input fails closed; no silent defaults/omission:
- [ ] Exact-head ConstructionPM CI, Client Typecheck and PostgreSQL Integration evidence recorded:
- [ ] No product-facing UI/help/branding output exposes internal source citations or source-vendor references.

If a source is ambiguous or an independent review is missing, mark the relevant rule BLOCKED/UNVERIFIED and do not merge a production calculation-semantic change. For test-only/docs-only changes, explicitly state why no calculation semantics change.
