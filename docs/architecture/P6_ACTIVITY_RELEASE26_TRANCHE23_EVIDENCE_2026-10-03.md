## Release 26 Activity tranche 23

This commit carries exactly the 20 Release 26 Activity registry fields from the reviewed Tranche 23 work onto current `main`.

Guardrails:
- Shared Scheduling/EVM Core remains the sole calculation authority.
- No Activity dataclass expansion.
- No second CPM/EVM engine.
- No client-side scheduling semantics.
- Snapshot persistence, time-forward-pass syntax, and unrelated test-fixture repairs are deliberately excluded because they already belong to current-main history.

Validation:
- Exact 20-field membership and uniqueness.
- Deterministic P6 types and units.
- Computed outputs remain non-writable.
