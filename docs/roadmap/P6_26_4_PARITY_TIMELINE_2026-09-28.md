# P6 26.4 Parity Implementation Timeline & Progress

Effective date: 2026-09-28

## Baseline

- P6 Version 26 / P6 EPPM 26.4 compatibility baseline: **100% reference**
- Construction PM overall product maturity: **78%**
- Construction PM current P6-parity coverage: **44%**
- Remaining P6-overlap gap: **56%**

These percentages are engineering coverage measures, not runtime performance benchmarks and not Oracle certification.

## Progress model

Two independent percentages are tracked:

1. **Stage completion %** — completion of the active P6 parity stage.
2. **P6 parity %** — weighted implementation/conformance coverage of the entire P6-overlap baseline.

The P6 parity percentage may stay flat while a stage is being prepared, then rise when implementation and regression evidence are accepted. A feature is not counted as complete merely because documentation or UI exists.

## Ordered timeline

| Gate | Workstream | Owner | Stage target | Expected P6 parity after accepted gate |
|---|---|---|---:|---:|
| P6-0 | Baseline + no-omission architecture | Jalal / all | 100% | **44% current** |
| P6-1 | Complete P6 Field Registry + field dispositions | Jalal | 100% | **52%** |
| P6-2 | Persistent typed field/UDF model + API | Hasan | 100% | **58%** |
| P6-3 | Column / View / Layout Engine | Javad | 100% | **66%** |
| P6-4 | Formula / Calculated Column engine | Jalal + Hasan + Javad | 100% | **72%** |
| P6-5 | Full Schedule Options parity | Jalal | 100% | **80%** |
| P6-6 | Full Calendar/Time/Conversion parity | Jalal + Hasan | 100% | **86%** |
| P6-7 | XER/XML/XLSX/MS Project interchange | Hasan | 100% | **93%** |
| P6-8 | Codes/Baselines/Financial Periods/Steps/Spreads | Hasan + Jalal | 100% | **97%** |
| P6-9 | Conformance fixtures + round-trip + client parity | All | 100% | **100%** |

The gate percentages are planning checkpoints, not guarantees. They indicate the intended cumulative coverage after each gate is actually accepted.

## Detailed acceptance checkpoints

### P6-1 — Field Registry
Target: 30% -> 52%

Completion requires:
- complete applicable field inventory from P6 Version 26/26.4;
- subject-area identifiers;
- type/unit/writable/read-only/computed metadata;
- UDF applicability;
- internal canonical mapping;
- Import/Export mapping references;
- explicit disposition for every item.

### P6-2 — Typed persistence/API
Target: 52% -> 58%

Completion requires:
- database persistence;
- tenant/project/revision scope;
- typed API DTOs;
- stable field identifiers;
- custom/UDF persistence;
- compatibility/version migration;
- database regression evidence.

### P6-3 — Column/View/Layout
Target: 58% -> 66%

Completion requires:
- add/remove/hide/show/reorder;
- rename/width/alignment;
- pin/freeze where client supports;
- sort/group/filter;
- saved user/project/global layouts;
- layout migration;
- standard + custom/UDF fields available through one Field Registry.

### P6-4 — Formula Engine
Target: 66% -> 72%

Completion requires:
- parser/AST;
- type checking;
- dependency graph;
- cycle detection;
- null/unit rules;
- deterministic evaluation;
- invalidation/recalculation;
- summary/WBS/project rollups;
- formula audit/versioning;
- formula import/export preservation.

### P6-5 — Schedule Options
Target: 72% -> 80%

Completion requires semantic parity for applicable current P6 options affecting schedule interpretation/results, including out-of-sequence behavior, criticality/float rules, longest path, multiple float paths, external relationships, expected finish, automatic rescheduling and resource-leveling-related settings.

### P6-6 — Calendar/Time
Target: 80% -> 86%

Completion requires:
- global/project/resource calendars;
- inheritance;
- assignments;
- day-specific work/nonwork overrides;
- detailed intervals;
- hours per day/week/month/year;
- unit conversion governed by assigned calendars;
- versioned deterministic replay.

### P6-7 — Interchange
Target: 86% -> 93%

Completion requires:
- XER project;
- XER resource-only and role where applicable;
- Primavera XML;
- XLS/XLSX;
- Microsoft Project XML/MPX where applicable;
- typed mapping registry;
- explicit unsupported-field policy;
- round-trip fixtures.

### P6-8 — Remaining P6 working surfaces
Target: 93% -> 97%

Completion requires:
- codes and scopes;
- baselines and comparison fields;
- financial periods;
- activity steps;
- activity period actuals;
- resource spreads/future-period data;
- reports/profile field mappings.

### P6-9 — Certification
Target: 97% -> 100%

Completion requires:
- all baseline items dispositioned;
- all Implemented/Equivalent-Superset items regression-tested;
- no silent data loss;
- representative import/export round trips;
- Web/Desktop/Mobile consuming identical Shared Core semantics;
- P6 regression pack green;
- fresh release-version parity diff recorded.

## Whole-product maturity tracking

The existing **78% overall product maturity** remains the independent product-level metric.

P6 parity reaching 100% does not mean the whole product is 100% complete. After P6 parity, Construction PM continues to close construction-specific capabilities and Release Gate B.

## Team responsibility map

| Person | Primary P6 responsibility | Supporting responsibility |
|---|---|---|
| Jalal | P6 semantics, Field Registry, Calendar, Schedule Options, Formula Engine, conformance | final integration/acceptance |
| Hasan | persistence, API, import/export, typed storage, migrations, DB verification | financial periods/codes/baselines data surfaces |
| Javad | Field Chooser, Column/Grid, Layouts, UDF editors, Formula Editor, print/report field UX | Web/Desktop/Mobile parity |

## Current active work

- #389 — P6 26.4 parity implementation backlog
- #391 — Jalal P6 parity track
- #392 — Javad P6 parity track
- #393 — Hasan P6 parity track

## Non-regression rule

No P6 parity stage may change the authoritative meaning of existing:
- Scheduling;
- Calendar arithmetic;
- Duration/Lag;
- Progress/EVM;
- Resource/Cost;
- Financial semantics.

New capabilities must integrate through Shared Core contracts.

