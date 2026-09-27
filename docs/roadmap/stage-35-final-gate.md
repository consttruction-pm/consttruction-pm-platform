# Stage 35 — Read/API Boundary Hardening Final Gate

## Status
Stage 35 hardening is complete on the current validation branch and pending merge of PR #306.

## Verified scope
- Workspace read envelope rejects malformed context/workspace payloads.
- Required collections must be arrays.
- Optional collections reject explicit null/non-array values.
- Document projections are isolated to the requested tenant/project/revision.
- Control Intelligence evidence references are isolated to the requested authoritative project revision.
- Stale top-level, finding, and proposed-action evidence is rejected with `STALE_CONTROL_INTELLIGENCE_SOURCE`.
- Regression coverage exists for each hardened boundary.

## Current-main validation
PR #306 reapplies the Control Intelligence evidence revision isolation on current `main`, avoiding the obsolete/diverged PR #293 base.

Latest validation commit: `2d9a98245ee9ee9b788ba8f20095ebeaf36729cd`

## CI evidence
- Client Typecheck workflow run **36336791354**: success.
- ConstructionPM CI workflow run **36336791357**: success.
- Both workflows completed successfully for the latest validation commit.
- PR #306 remains open and unmerged.

## Acceptance constraints
1. Read/API boundaries remain authoritative.
2. Tenant/project/revision isolation is enforced.
3. Malformed and stale read payloads are rejected deterministically.
4. No client-side consequential Scheduling/P6, Progress/EVM, Resource/Cost, or financial calculation is introduced.
5. Regression coverage protects the hardened contracts.

## Merge policy
This gate does not merge PR #306 automatically. Merge remains a repository integration decision.
