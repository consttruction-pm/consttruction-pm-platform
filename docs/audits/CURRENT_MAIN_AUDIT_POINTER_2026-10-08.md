# Current-main Audit Pointer — 2026-10-08

This document is the live governance pointer for the current repository integration state.

## Authoritative main

- Repository: `consttruction-pm/consttruction-pm-platform`
- Current `main` HEAD: `d4a24216e28bb8be750e4e64e6f138344d12163c`
- Last merged Jalal capability slices:
  - PR #1311 — production composition seam for authoritative Schedule Query.
  - PR #1312 — P6 Activity Baseline1 semantic certification.
- PR #1310 — homepage/Web work, merged and separately verified.

Historical audit documents retain older SHAs as historical checkpoints. Those SHAs are not the live integration baseline.

## Weighted progress authority

- Governing baseline: **Jalal 3**
- Latest library snapshot: **59.41% weighted complete / 40.59% remaining**
- Date of latest recorded snapshot: **2026-10-08**
- Progress rule: merged + independently verified evidence is required before capability status can contribute.
- A merged capability with no distinct approved sub-weight in Jalal 3 is recorded as verified work but does **not** receive an invented incremental percentage.

This prevents PR count, commit count, additions/deletions, or duplicate/superseded work from changing the completion percentage without an approved weight.

## Active Jalal lanes

- Issue #1251 — calculation identity vs provenance policy.
- Issue #1226 — cross-platform P6 field/column/formula contract parity.
- Issue #1226 — cross-platform P6 field/column/formula contract parity.

Issue #1249 is closed after #1314 and #1316 were merged and independently verified on current `main`. PR #1313 was superseded by #1316.

## Acceptance rule

Current `main` is the only integration baseline. Required CI evidence must correspond to the latest PR head SHA; earlier successful checks do not satisfy the latest-head requirement.
