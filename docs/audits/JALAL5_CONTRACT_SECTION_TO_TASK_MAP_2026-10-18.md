# Jalal 5 — P6/PMBOK Contract Section → Work Package Map

**Date:** 2026-10-18  
**Status:** proposed section-to-task mapping for engineering review; not proof of implementation or certification.

## How to use this map

- Each listed contract section is assigned to concrete Jalal 5 task IDs, making the relationship from source rule to implementation and acceptance review discoverable without rediscovering the requirements.
- P6 Release 26/26.4 remains the compatibility and no-silent-omission baseline where semantics overlap. Use official source evidence and parity tests; do not guess unclear private-engine behavior.
- PMBOK 8th and current PMI guidance are a tailoring/governance/form profile. Each formula must keep its authority class, and no form/UI formula may duplicate the Shared Core schedule, calendar, resource, cost or EVM engine.
- This is section-level scheduling traceability, not a claim that mapped code, controls or tests already exist. Acceptance needs exact-main evidence for each mapped task.
- Use these mappings to fill the `P6 PMBOK Ledger` with concrete task IDs. Keep the 56 P6 sections and 33 PMBOK sections individually traceable.

## P6 calculation contract — 56 sections

| Section | Contract heading | Jalal 5 task IDs |
|---|---|---|
| P6-01 | Purpose and authority | A02; B01; B19; J12 |
| P6-02 | Calculation core and shared input contract | B01; B20; G03; G04; J03 |
| P6-03 | Activity types: every supported type has different semantics | B02; F02; J03 |
| P6-04 | Duration types and units/rate synchronization | B02; B12; F04; J03 |
| P6-05 | Activity percent complete and dates/status | B07; F07; J03 |
| P6-06 | Relationship network: FS, SS, FF, SF, lag/lead | B03; F03; G03; J03 |
| P6-07 | CPM forward pass, backward pass and float | B04; F05; J03 |
| P6-08 | Constraints | B06; F06; J03 |
| P6-09 | Scheduling options: every user selection changes the calculation contract | B14; F06; J03 |
| P6-10 | In-progress activities and out-of-sequence modes | B07; F07; J03 |
| P6-11 | Resource leveling | B08; B18; F08; J01; J03 |
| P6-12 | Resource assignments, rates, spread and expenses | B09; B10; F08; F09; J04 |
| P6-13 | Earned Value Management (EVM) and forecast techniques | B11; C08; F07; F09; J04 |
| P6-14 | Baselines, actuals, period performance and history | B13; F07; F09; J03; J04 |
| P6-15 | WBS, summary activity and rollup rules | B13; F02; J03 |
| P6-16 | Grids, Gantt, charts, KPIs, reports and exports | B17; F04; F05; F13; E15 |
| P6-17 | CUBI-specific extensions must stay separate | B20; C05; F12 |
| P6-18 | Mandatory UI action/icon registry | B15; F01; F16 |
| P6-19 | Required test design | B19; J03; J12 |
| P6-20 | OPEN/parity backlog and source maintenance | B19; J12 |
| P6-21 | Official source index | A02; B01; B19 |
| P6-22 | Definition of done | B19; J12 |
| P6-23 | Activity steps and step-weighted physical progress | B07; F07; C05 |
| P6-24 | Schedule percent complete and other date-derived indicators | B07; B13; F07 |
| P6-25 | Leveling priority list: complete documented field vocabulary and tie rules | B08; B18; F08; J01; J03 |
| P6-26 | Global Change and user-defined arithmetic | B12; F04; J04 |
| P6-27 | Command-to-calculation mapping: reference control inventory for the actual CUBI UI audit | B15; F01; F16 |
| P6-28 | Expanded official source index | A02; B01; B19 |
| P6-29 | Exhaustive source-coverage rule: calculation-related official guide scope | B19; J12 |
| P6-30 | Calendar arithmetic, hours/time-period conversion and display units | B05; B06; F06; G03; J03 |
| P6-31 | Full schedule command input/output contract | B14; G03; G04; J03 |
| P6-32 | Exact Project Details → Calculations tab behavior | B14; F06; J03 |
| P6-33 | Progress commands, Progress Spotlight and Apply Actuals | B07; F07; J03 |
| P6-34 | Resource/role rate source, price calculations and resource details | B09; B10; F08; F09; J04 |
| P6-35 | Complete Resource Leveling command options and edge cases | B08; B18; F08; J01; J03 |
| P6-36 | Resource curves, future-period buckets and Earned Value interaction | B09; B11; F09; J04 |
| P6-37 | Baseline selection, baseline values and historical period data | B11; B13; F07; F09; J04 |
| P6-38 | Activity/work-calendar defaults and project settings | B05; B14; F06; G03; J03 |
| P6-39 | Check Schedule Report as a calculated diagnostic contract | B17; F13; J03 |
| P6-40 | Complete calculation menu/control coverage matrix — additions after TOC audit | B15; F01; F16 |
| P6-41 | Activity field matrix: calculation dependencies and invalidation | B12; B20; F04; G03; J03 |
| P6-42 | Final source and coverage audit ledger | B19; J12 |
| P6-43 | Expanded source index for detailed option and formula pages | A02; B01; B19 |
| P6-44 | Budget log, spending plan, funding and variance formulas | B10; C08; F09; J04 |
| P6-45 | Separate percent-complete, scheduled-percent, and remaining-float fields | B04; B07; F05; F07; J03 |
| P6-46 | Role limits, resource availability and resource-analysis outputs | B08; B09; F08; J01; J03 |
| P6-47 | Cross-checks for the activity duration synchronization table | B02; B12; J03 |
| P6-48 | Cost spread, resource-hour reporting and material units | B09; B10; F08; F09; J04 |
| P6-49 | Summary service and stored time-phased data | B13; B17; F13; G08; J04 |
| P6-50 | Top-down estimation: formulas, inputs and required parity fixtures | B10; C03; C08; F09; J04 |
| P6-51 | Identity-changing activity operations and graph integrity | B03; F02; F03; G03; J03 |
| P6-52 | Project controls affecting calculation scope and diagnostics | B14; B17; F15; J03 |
| P6-53 | Time-phased outputs and Tracking-view options | B09; B11; B17; F13; J04 |
| P6-54 | Schedule/estimate/report scope does not imply automatic data mutation | B17; D11; D12; J05 |
| P6-55 | Financial-period dictionary, fiscal start and summary boundary tests | B10; F09; J04 |
| P6-56 | Base currency, view currency and conversion invariants | B10; C03; F09; J04 |

## PMBOK form and calculation contract — 33 sections

| Section | Contract heading | Jalal 5 task IDs |
|---|---|---|
| PMBOK-01 | Purpose and binding rule | C01; C09; J12 |
| PMBOK-02 | What the latest PMBOK baseline means for CUBI | C01; C05; C09 |
| PMBOK-03 | Authority, source attribution and formula labels | C01; C03; C09; J04 |
| PMBOK-04 | Main architecture and boundaries | C02; C04; C08; G04 |
| PMBOK-05 | Form/template and submission data model | C02; C07; F14; G04 |
| PMBOK-06 | Supported field types and exact meaning | C03; C07; F14 |
| PMBOK-07 | Form validation contract | C03; C04; C07; J04 |
| PMBOK-08 | Formula and conditional-rule language | C03; C04; F14; J04 |
| PMBOK-09 | Numeric precision, nulls, errors, and units | C03; C04; J04 |
| PMBOK-10 | Formula dependencies and recalculation lifecycle | C04; C08; B20; J04 |
| PMBOK-11 | Canonical calculation context and project integration | B10; B11; C08; G03; J04 |
| PMBOK-12 | Form/template lifecycle | C02; C07; F14; G04 |
| PMBOK-13 | Core form field examples and semantics | C05; C07; F14 |
| PMBOK-14 | Form catalog and domain coverage | C05; F10; F11; F12; F14 |
| PMBOK-15 | Canonical general formulas for form fields | C03; C04; C08; J04 |
| PMBOK-16 | Risk and opportunity form calculations | C05; C08; F09; J04 |
| PMBOK-17 | Estimation forms and uncertainty calculations | C05; C08; F09; J04 |
| PMBOK-18 | Procurement and option-evaluation scores | C05; F12; G07 |
| PMBOK-19 | Quantity progress and weighted physical progress forms | B07; B11; C05; F07; J04 |
| PMBOK-20 | Cost, change-impact and payment-form calculations | B10; B11; C05; C08; F09; F12; J04 |
| PMBOK-21 | Quality, inspection, NCR/CAPA and checklist calculations | C05; F11; G06 |
| PMBOK-22 | Stakeholder, communications, issue, decision and action forms | C05; F11; F12; G07 |
| PMBOK-23 | Change governance, approval and workflow formulas | C02; C05; C07; G09; J04 |
| PMBOK-24 | Multilingual, RTL/LTR, Jalali/Gregorian and accessibility contract | E16; H01; H02; H03; H04; H05; H06; H07; H08; J07 |
| PMBOK-25 | Security, evidence, privacy and audit | C07; D05; D11; G09; J09 |
| PMBOK-26 | AI-assisted form creation under the 2026 AI standard | C06; D08; D11; D12; J05 |
| PMBOK-27 | User-facing website menu, controls and icon registry | C07; F01; F14; F16 |
| PMBOK-28 | Calculation and validation examples to make testable | C03; C04; C08; J04 |
| PMBOK-29 | Existing CUBI implementation baseline and gap mapping | C09; C07; F14; G02 |
| PMBOK-30 | Required test matrix and merge gate | C03; C04; C09; J04; J12 |
| PMBOK-31 | Official source register | C01; C09; J12 |
| PMBOK-32 | OPEN items and adoption ledger | C09; J12 |
| PMBOK-33 | Definition of Done | C09; J12 |

## Mandatory acceptance loop

1. Implement one source-backed rule in its owning domain/service; no duplicate UI/API/AI formula.
2. Link its official source and exact section, typed contract, implementation path, golden/negative tests and current-main SHA.
3. Have Jalal review semantic/P6 authority, Hasan review real service/persistence/authorization, and Farmj22002 review screen/control, localization and link behavior as applicable.
4. Mark each section `Verified`, `Partial`, `OPEN / parity test required`, or `Outside Scope (approved)` only with evidence. A section linked to a workstream ID but missing actual implementation or tests remains open.
5. Recalculate Jalal 5 earned weight only after a mapped row passes its own Definition of Done. A coverage map alone does not change the weighted progress value.

## Sources

- [P6 Calculation Contract PR #1478](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1478)
- [PMBOK Form/Calculation Contract PR #1480](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1480)
- [Jalal 5 plan PR #1484](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1484)
- [Master V1 audit #459](https://github.com/consttruction-pm/consttruction-pm-platform/issues/459)
- [Progress governance #680](https://github.com/consttruction-pm/consttruction-pm-platform/issues/680)