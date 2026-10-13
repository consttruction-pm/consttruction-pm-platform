# Jalal 4 — Weighted Rebaseline Proposal
Date: 2026-10-13
Status: **Proposed baseline; requires current-main reconciliation before it becomes the official progress report**

## Why Jalal 4 replaces Jalal 3

Jalal 3 assigned only 3% to “Web AI Assistant / Smart Guide” and counted 20% completion. That measures a narrow UI work item, not the mandatory, cross-layer V1 AI Project Controls Assistant. The assistant's integrated end-to-end acceptance is therefore set to **0%** until evidence proves the required flow. Existing Smart Guide/query/approval primitives are foundations, not end-to-end completion.

This schedule restores the delivery order: **Website/Web first, desktop second, mobile postponed to V2**. Mobile-only V1 rows from Jalal 3 are removed from the V1 denominator; their weight is reassigned to web, AI, integration and release evidence. No open/unmerged PR receives progress credit.

## Measurement rules

- Total planned weight = 100 points.
- Earned points = activity weight × evidence-backed completion fraction.
- The mapped percentages below are carried forward from the last reconciled Jalal 3 record dated 2026-10-12, only where the activity is sufficiently comparable. They are **provisional**, not a claim that a fresh audit of every current-main code path has been completed.
- The AI assistant and system-wide release QA are deliberately set to 0% integrated acceptance until end-to-end evidence exists.
- A documentation-only PR, issue, branch, commit count, UI placeholder or passing component CI does not count as implementation completion.
- Refresh the baseline SHA and activity percentages after current-main code/test review; avoid double credit where one implementation supports multiple work packages.
- A feature is not “P6-compatible” based on field-name similarity. Its documented semantics, Shared Core path, persistence/interchange behavior and regression evidence must be traced.

## Jalal 4 weighted work packages

| # | Work package | Owner | Weight | Provisional completion | Earned points | Evidence / boundary |
|---:|---|---|---:|---:|---:|---|
| 1 | Shared Domain/Calculation Core + P6 semantic parity inventory | Jalal | 14 | 65% | 9.10 | Carry-forward from Jalal 3; refresh against the versioned 26.4 baseline and calculation-by-calculation fixtures |
| 2 | CPM/scheduling engine and schedule options | Jalal | 8 | 98% | 7.84 | Carry-forward; 98% is not a certification claim |
| 3 | Calendar, Jalali/Gregorian dates, duration, lag and constraints | Jalal | 6 | 93% | 5.58 | Carry-forward; re-test versioned calendars and API boundaries |
| 4 | Progress, float, out-of-sequence logic, EVM / earned schedule reconciliation | Jalal | 7 | 85% | 5.95 | Carry-forward; confirm reconciliation tests and calculation identities |
| 5 | Formula dependency DAG / deterministic formula engine | Jalal | 3 | 76% | 2.28 | Carry-forward; confirm type, null, cycle and roll-up cases |
| 6 | Core regression fixtures and calculation verification | Jalal | 5 | 70% | 3.50 | Carry-forward only; expand reference-to-code-to-fixture traceability |
| 7 | API/DTO/versioned application contracts | Hasan | 5 | 35% | 1.75 | Carry-forward; verify against current-main contracts |
| 8 | Database/persistence, tenant isolation, revision, transactions and fresh-read verification | Hasan | 6 | 85% | 5.10 | Carry-forward for existing persistence scope; AI production authorization/audit is not credited here unless separately evidenced |
| 9 | Typed import/export and round-trip interchange | Hasan | 5 | 85% | 4.25 | Carry-forward; verify unsupported-field reporting and round-trip fixtures |
| 10 | Web project workspace, field registry, columns and layouts | Farmj22002 | 5 | 100% | 5.00 | Carry-forward; do not infer every field/option is certified by workspace completion |
| 11 | Web Gantt, schedule pages and authoritative result presentation | Farmj22002 | 7 | 55% | 3.85 | Carry-forward; validate actual API/core result linkage |
| 12 | Web dashboard, responsive UX, RTL/LTR and localization | Farmj22002 | 4 | 40% | 1.60 | Carry-forward; verify real workflows, not only visual presence |
| 13 | **Production V1 AI Project Controls Assistant — integrated vertical slice** | Hasan (runtime/API) + Farmj22002 (UX) + Jalal (calculation acceptance) | **12** | **0%** | **0.00** | Must prove intake/import → preview → authorized write → authoritative calculation → fresh read → report; approval/rejection, permissions and durable audit included |
| 14 | Multilingual Help and documentation aligned to released behavior | Jalal + team inputs | 2 | 10% | 0.20 | Carry-forward; help must not promise unreleased behavior |
| 15 | Desktop integration with Shared Core/API | Jalal + Hasan + Farmj22002 by boundary | 5 | 10% | 0.50 | Carry-forward; after Web workflow stabilizes |
| 16 | System-wide integration, regression, security and release QA | All three owners | 6 | 0% | 0.00 | No credit until integrated current-main evidence, negative tests and release gate results exist |
|  | **Total** |  | **100** |  | **56.50 / 100** | Provisional weighted implementation indicator only |

## Provisional owner allocation

Owner-level totals are not additive beyond the 100-point schedule. Shared work is allocated by primary delivery boundary and has one acceptance owner.

| Owner / lane | Primary responsibility | Assigned weight (approx.) |
|---|---|---:|
| Jalal — Shared Core, P6 semantics, calculations, regression, final integration | Packages 1–6; calculation acceptance for 13; Help and desktop participation | 47 |
| Hasan — API, application, persistence, import/export, AI runtime/security | Packages 7–9; runtime/API half of 13; desktop participation | 25 |
| Farmj22002 — Web/client UX, Gantt, dashboard, AI interaction | Packages 10–12; UX half of 13; desktop participation | 22 |
| Team-wide release acceptance | Package 16 | 6 |
| **Total** |  | **100** |

The approximate owner split is for capacity planning, not an additional progress denominator. Where a shared package is owned by multiple people, the package's weight is earned once only.

## Critical dependencies and sequence

1. **Governance prerequisite:** merge/reconcile the new principles PR before treating Principle 1B / 6A as current-main policy. PR #1424 is open and unmerged at the time this schedule was drafted.
2. **P6 calculation evidence:** for each applicable calculation/option, record reference version and section, canonical model/option, Shared Core implementation path, fixture/input, expected output, test result and disposition. Unknown/ambiguous semantics remain unresolved rather than guessed.
3. **Assistant vertical slice:** Hasan wires typed tools to real application services and persistence; Farmj22002 implements functional preview/approval/rejection and operation states; Jalal validates calculation authority and schedule result parity.
4. **Web-first integration:** prioritize one complete vertical user journey through UI → API/application → persistence → Shared Core → fresh read → result UI.
5. **Desktop second:** consume the same canonical contracts/core after the Web workflow is stable. Mobile is V2 and is excluded from this V1 weighted denominator.
6. **Release gate:** system-wide QA remains 0% until a current-main build passes end-to-end, authorization-negative, stale-revision, rejection-no-mutation, import validation, retry/idempotency and report-data consistency tests.

## Mandatory acceptance checklist

- [ ] PR #1424 is merged or its requirements are reconciled in authoritative main documents.
- [ ] No authoritative control document still defers the mandatory V1 assistant to P3.
- [ ] AI work is tracked as a cross-layer capability, not only a Smart Guide UI task.
- [ ] Each applicable P6 field/option/calculation has an explicit disposition and evidence link.
- [ ] No calculation is independently reimplemented in UI, API adapters or AI.
- [ ] A real persisted project can be created/populated, calculated, changed under authorization, re-read and reported.
- [ ] Rejected/unauthorized/stale proposals produce no authoritative mutation.
- [ ] The same calculation identity/result is represented consistently across API, Web and Desktop.
- [ ] CI/runtime evidence is tied to the exact tested commit.
- [ ] Weighted percentages are refreshed from current-main evidence, with no credit for open PRs or duplicate work.

## Progress statement

**56.50% is a provisional reweighted planning indicator, not a fresh certified project-progress result.** It intentionally differs from Jalal 3's 59.50% because the V1 scope denominator has changed: mobile-only V1 work was deferred, the integrated assistant was raised from a 3% UI item to a 12% release capability and receives 0% until end-to-end proof, and system-wide QA remains 0%. Publish a final Jalal 4 percentage only after reconciling the latest main SHA, open/merged PRs, and direct implementation/test evidence.
