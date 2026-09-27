# Stage 35 — Read/API Boundary Hardening Final Gate

## Current-main validation

This validation branch starts from the current `main` baseline and reapplies Control Intelligence evidence revision isolation.

### Hardened boundary

- Top-level Control Intelligence source references must match the requested authoritative project revision.
- Finding source references must match the requested authoritative project revision.
- Proposed-action source references must match the requested authoritative project revision.
- Non-integer or stale evidence revisions are rejected deterministically with `STALE_CONTROL_INTELLIGENCE_SOURCE`.

### Acceptance constraints

1. Read/API boundaries remain authoritative.
2. Tenant/project/revision isolation is enforced.
3. Malformed and stale read payloads are rejected deterministically.
4. No client-side consequential Scheduling/P6, Progress/EVM, Resource/Cost, or financial calculation is introduced.
5. Regression coverage protects the hardened contracts.

CI must be evaluated against this branch's exact HEAD before merge.
