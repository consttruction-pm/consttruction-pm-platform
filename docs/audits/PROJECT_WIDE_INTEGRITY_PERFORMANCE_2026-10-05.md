# Project-wide integrity, performance and architecture audit — 2026-10-05

## Audit scope

This audit is intentionally broader than Jalal 3. It covers the project history represented in the current repository, the registered project requirements, the prior performance/design audits, and the current `main` branch.

Reference point:
- Current `main`: `d020df11cd28be1b30c1ee44546e01a287a69cfa` (this audit's performance fix)
- Previous Jalal 3 baseline: `772d4c5f31a631e72d1fc6e4f26927df6113e3e6`
- `main` was 49 commits ahead of the Jalal 3 baseline before this audit fix.

## Binding architecture requirements checked

1. Shared Domain/Calculation Core remains authoritative and UI/OS/DB independent.
2. Web, Desktop and Mobile consume shared scheduling/calculation contracts; no client-side replacement CPM engine.
3. Primavera/P6 semantics are preserved rather than simplified for UI convenience.
4. Jalali/Gregorian and working-day/working-time calendar semantics remain centralized.
5. Calendar inheritance/exception persistence remains deterministic and does not silently alter CPM arithmetic.
6. P6 field/layout presentation is a presentation layer and does not redefine calculation semantics.
7. CUBI visual rules remain calm/data-first; brand colors do not become calculation/status semantics.
8. No unnecessary runtime dependency or visual effect should be introduced into dense project-control surfaces.
9. GitHub `main` is the canonical integration baseline.

## Findings and actions

### A. Web workspace rerender overhead — fixed

Before this audit, every workspace selection/menu/language/layout update replaced the entire application shell with `container.innerHTML`, recreated the status/language controls, and then rebuilt the workspace.

This was unnecessary DOM churn and could become visible as activity/field counts grow.

Action taken:
- The application shell is now created once and reused.
- The status/language control is updated in place.
- Workspace content is still deliberately rendered from the authoritative immutable state; this does not move any calculation into the UI.
- No scheduling, CPM, calendar, P6 formula, EVM or persistence semantics were changed.

Commit: `d020df11cd28be1b30c1ee44546e01a287a69cfa`.

### B. CUBI visual system — registered and retained

The prior color/frame audit is included in this project-wide baseline:
- Deep Navy / Navy Dark
- Engineering Blue
- Copper Orange
- Brushed Titanium family
- calm neutral workspace surfaces
- semantic Success/Warning/Error colors
- Inter + Vazirmatn
- restrained brushed-metal treatment limited to brand chrome
- no decorative metallic backgrounds in dense Gantt/table/control panels

The existing visual-system document and tests enforce the main brand anchors and logo color restrictions.

### C. Homepage performance risk — bounded, not converted into product UI debt

The homepage contains gradients, a dashboard illustration, a grid-glow and limited backdrop/transform effects. These are confined to the marketing surface rather than the dense scheduling workspace.

The audit rule is therefore:
- keep visual effects out of core Gantt/grid/control panels;
- do not add large image/video assets merely for decoration;
- keep the existing CSS-only visual treatment unless runtime evidence shows a real regression.

No P6 or project-control calculations are coupled to homepage presentation.

### D. Scheduling/P6 separation — confirmed in reviewed areas

The current calendar inheritance/exception work explicitly stores persistence-ready semantics while leaving scheduling arithmetic in Shared Core. Mobile project-shell code likewise presents relationship/lag data and delegates scheduling through the shared adapter.

No new client calculation engine was introduced by the reviewed changes.

### E. Calendar parity — correctly identified as incomplete rather than falsely marked complete

The repository now has first-class persisted calendar inheritance/exception structures and regression tests, but the repository itself explicitly classifies full P6 Calendar CRUD / Copy / Replace / REST API parity as outside the completed slice.

Open follow-up work remains in the calendar API parity issue. This is a genuine product gap, not a reason to rewrite completed Shared Core work.

### F. CI/runtime evidence — gap

The repository contains PostgreSQL-backed CI configuration and client typecheck/test workflows. However, the GitHub connector currently reports no workflow-run evidence for the exact current head and no combined status entries.

Therefore this audit does **not** claim fresh runtime-green verification for the current head. Code reading and repository configuration are evidence of intended gates, not proof that those gates executed successfully on this exact commit.

## Repository organization decision

The repository's current high-level separation is coherent:
- `src/construction_pm/` — authoritative Python/domain/calculation/persistence implementation
- `apps/web/` — Web presentation/integration
- `apps/desktop/` — Desktop presentation/integration
- `apps/mobile/` — Mobile presentation/integration
- `apps/client-sync/` — shared client synchronization boundary
- `docs/` — contracts, design, responsibilities and implementation evidence
- `tests/` — Python/domain/integration/regression tests
- `infra/` and `tools/` — infrastructure and utilities

No duplicate Shared Core folder or second calculation engine was added during this audit.

## Visual + performance rule for future work

A UI change is not accepted merely because it looks better. It must preserve:
- data readability;
- P6/CPM authority;
- deterministic calculations;
- shared client contracts;
- low DOM/runtime overhead;
- semantic status colors;
- multilingual RTL/LTR behavior.

Dense scheduling, Gantt, cost, EVM and control surfaces must remain calmer and lighter than the marketing homepage.

## Verdict

**Specification:** Partial — the architectural and visual requirements reviewed here are aligned, but full P6 Calendar API parity and some end-to-end product surfaces remain unfinished.

**Engineering quality:** Partial — the reviewed separation is sound and the identified Web shell rerender inefficiency has been fixed, but fresh exact-head CI/runtime evidence is currently unavailable through the connected GitHub status/run interface.

**Important:** This audit is a whole-project integrity baseline. Jalal 3 remains a progress/workload baseline, not the scope of the audit.
