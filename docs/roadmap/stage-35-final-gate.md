# Stage 35 — Read/API Boundary Hardening Final Gate

## Status
Stage 35 hardening is complete pending merge of the current-main validation PR.

## Verified scope
- Workspace read envelope rejects malformed context/workspace payloads.
- Required collections must be arrays.
- Optional collections reject explicit null/non-array values.
- Document projections are isolated to the requested tenant/project/revision.
- Control Intelligence evidence references are isolated to the requested authoritative project revision.
- Stale control-intelligence evidence is rejected with `STALE_CONTROL_INTELLIGENCE_SOURCE`.
- Regression coverage exists for each hardened boundary.

## Current-main validation
PR #306 reapplies the Control Intelligence evidence revision isolation on current `main`, avoiding the obsolete/diverged PR #293 base.

Commit: `dff6e8ff81983c063e2697d1aa280a0ef16b62a0`

## CI evidence
- ConstructionPM CI: success
  - Python 3.11: success
  - Python 3.12: success
  - Python 3.13: success
- Client Typecheck: success
  - Client Sync typecheck + runtime tests: success
  - Web typecheck + runtime tests: success
  - Desktop typecheck: success
  - Mobile typecheck: success

## Acceptance constraints
1. Read/API boundaries remain authoritative.
2. Tenant/project/revision isolation is enforced.
3. Malformed and stale read payloads are rejected deterministically.
4. No client-side consequential Scheduling/P6, Progress/EVM, Resource/Cost, or financial calculation is introduced.
5. Regression coverage protects the hardened contracts.

## Merge policy
This gate does not merge PR #306 automatically. Merge remains a repository integration decision.
