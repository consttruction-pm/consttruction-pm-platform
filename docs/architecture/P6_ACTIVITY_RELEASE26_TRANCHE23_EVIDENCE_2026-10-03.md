## Release 26 Activity tranche 23 — current-main carry-forward

This change carries the 20-field Activity registry tranche onto current `main`.

Guardrails:
- Shared Scheduling/EVM Core remains the sole calculation authority.
- No Activity dataclass expansion.
- No second CPM/EVM engine.
- No client-side scheduling semantics.

The registry tests verify exact field presence, deterministic types/units, and non-writability of computed outputs.
