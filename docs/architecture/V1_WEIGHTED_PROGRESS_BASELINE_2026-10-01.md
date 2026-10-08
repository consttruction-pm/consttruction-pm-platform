> **Historical baseline notice:** This 2026-10-01 document is retained as the original weighted-baseline record. Live weighted progress is governed by the current Jalal 3 snapshot and the current-main audit pointer; do not interpret the historical SHA below as today's main HEAD.

# V1 Weighted Progress Baseline — 2026-10-01

## Purpose
This is the single governance baseline for progress reporting. It prevents PR count, commit count, code volume, stale branches, and duplicate issues from being treated as product completion.

## Baseline
- Repository: consttruction-pm/consttruction-pm-platform
- Current main governance baseline before audit sync: `9445ec2`; audit sync commit: `e01e9e9`
- Master audit: `docs/V1_MASTER_AUDIT_MATRIX.md`
- Governing principles: `docs/architecture/PRODUCT_PRINCIPLES.md`
- V1 master track: #459
- Governance issue: #680

## Scoring rule
A capability contributes only against its assigned weight:
- Verified = 100% of its capability weight.
- In progress = 50% of its capability weight, unless explicit evidence justifies another completion fraction.
- Audit required = 25% of its capability weight.
- Gap = 0%.
- Open/unmerged PR = 0% incremental completion until merged and validated.
- Superseded/duplicate work = 0% additional weight.
- A status cannot be upgraded without current-main code/test, merged-PR, or runtime/CI evidence.

## V1 weighted domains

| Domain | Weight | Current evidence status | Working completion |
|---|---:|---|---:|
| Shared Core / P6 scheduling / calendars / duration / progress-control semantics | 25 | Audit required | 25% |
| Backend / DB / API / persistence / authorization / interoperability | 20 | In progress | 50% |
| Web V1 workspace / WBS / Activity / Gantt / reports / navigation | 25 | Verified foundation, broader beta incomplete | 60% |
| Desktop V1 foundation / offline-capable shared-core client | 10 | Gap / foundation only | 15% |
| Mobile / field client | 5 | Gap / V2-priority | 10% |
| Localization / all-language packs / RTL-LTR / typography | 5 | Gap | 25% |
| Help Center / product documentation | 5 | Audit required | 35% |
| Integration / regression / release evidence | 5 | In progress | 50% |

> The percentages in the last column are intentionally conservative working values derived from the master-audit statuses and current evidence; they are not claims of P6 certification.

## Calculated V1 implementation indicator
Weighted calculation:
- Core: 25 × 0.25 = 6.25
- Backend: 20 × 0.50 = 10.00
- Web: 25 × 0.60 = 15.00
- Desktop: 10 × 0.15 = 1.50
- Mobile: 5 × 0.10 = 0.50
- Localization: 5 × 0.25 = 1.25
- Help: 5 × 0.35 = 1.75
- Integration/QA: 5 × 0.50 = 2.50

**Working weighted indicator = 38.75 / 100**

This number must not be called "release readiness". It is a governance indicator for implementation progress only.

## V1 Web Beta indicator
Web Beta is measured separately because Web is the current delivery priority.

| Web capability | Weight |
|---|---:|
| Entry/workspace/navigation | 15 |
| WBS/activity editing surface | 15 |
| Gantt/scheduling presentation | 15 |
| P6 fields/layout/formula presentation | 15 |
| Backend/API persistence integration | 15 |
| Progress/report/print workflow | 10 |
| Localization/RTL/LTR | 5 |
| E2E/regression/accessibility | 10 |

Current verified foundation is present, but E2E completion, backend runtime evidence and all-language coverage remain incomplete. Therefore the Web Beta percentage must not be inferred from the 60% domain value until this sub-matrix is refreshed with direct evidence.

## P6/Core certification indicator
P6/Core is **not certified complete**. Material open scope includes:
- #403 ScheduleOptions remaining semantics.
- #595 Out-of-Sequence public scheduling behavior.
- #597/#646 Resource Leveling authority.
- #672 RemainingEarly/RemainingLate scheduler-backed mapping.
- Complete P6 field/formula catalog and interoperability evidence.
- Progress/EVM/Earned Schedule parity reconciliation.

## Active remaining-work register
- #403 — Shared Core ScheduleOptions.
- #595 — Out-of-Sequence semantics.
- #597 / #646 — Resource Leveling.
- #672 — RemainingEarly/RemainingLate.
- #678 — Hasan backend runtime/regression gate.
- #607 — Farmj22002 Help Center.
- #459 — master Web V1 audit and functional beta.
- #393 — P6 persistence/API/import-export parity, to be advanced only where a concrete non-duplicate gap remains.
- #88 and related localization work — all-language requirement.
- Stage 34 #78/#79/#80 — broader construction completeness beyond the minimal Web Beta gate.

## Anti-duplication decisions
- #631 is closed and must not be revived.
- Old Farmj branches/PRs such as #528/#593 are not baseline without reconciliation.
- Merged #674/#677 are counted through current-main evidence only.
- #636 is not a new implementation task; its completed/superseded evidence must not be double-counted.
- Hasan's current bounded task is #678.
- Farmj22002's current relevant lanes are #392 and #607; Javad Foroughi remains observer/read-only.

## Required next refresh
1. Re-read current main after the next merge.
2. Replace working percentages with capability-level evidence.
3. Recalculate the four official indicators: Overall V1, Web Beta, Source/Implementation, P6/Core.
4. Never reuse a previous percentage without recomputation.
