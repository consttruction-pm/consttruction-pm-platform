# V1 Full Project Audit Matrix — 2026-09-28

## Purpose
Single control matrix for completing the Web-first V1 Beta without repeating previously completed design work. Oracle Primavera P6 EPPM REST API Release 26 is the primary P6 reference for shared fields, business objects, options and interchange evidence. This matrix records project implementation maturity; it does not claim that every current feature is P6-certified.

## Evidence rules
- **Verified** means fresh executable/runtime evidence exists for the stated boundary.
- **Implemented** means source implementation exists but the required runtime gate may still be pending.
- **Foundation** means contract/architecture exists and integration is incomplete.
- **Gap** means material V1 work remains.
- **P6 evidence pending** means Oracle semantics/type/mutability/computed behavior still needs authoritative reconciliation.
- A field name match is not semantic equivalence.

| Domain | V1 target | Current evidence/state | Owner | Next gate | Priority |
|---|---|---|---|---|---|
| Architecture/Web-readiness | Shared Core + API/Application/Repository + infrastructure separation | Architecture baseline documented | Jalal | Cross-module audit for duplicate logic | P0 |
| Scheduling/CPM | P6-aligned scheduling, FS/SS/FF/SF, lag, constraints, passes, float, critical path | Strong prior foundation; later integration still requires end-to-end evidence | Jalal | Core-to-Web result parity fixtures | P0 |
| Calendar/Working Time | Project/activity/lag calendars, Jalali/Gregorian, exceptions, work time | Calendar inheritance/resolution contract exists | Jalal | Rich calendar configuration + runtime conformance | P0 |
| Activity fields | Complete P6 Release 26 Activity coverage | 275-field authoritative inventory; only 39 seeded registry entries | Jalal | Full field reconciliation and certification | P0 |
| WBS | Complete editing, hierarchy, codes, responsible manager, dates | WBS foundations exist | Javad + Hasan | Functional Web workflow + persistence/API check | P0 |
| Relationships | Complete relationship editing and calculation integration | Dependency graph foundation exists | Jalal + Hasan + Javad | End-to-end CRUD + scheduling verification | P0 |
| Columns/Layout | Field chooser, typed columns, formulas, layout persistence | P6-3 client contract PR exists | Javad + Hasan | Connect authoritative registry/API and runtime UI | P0 |
| Formula engine | Shared parser/AST/type/dependency/cycle/evaluation | Formula boundary exists; evaluator remains Core responsibility | Jalal | Authoritative evaluator + independent fixtures | P0 |
| Gantt | Real schedule-driven Gantt | UI scaffold exists | Javad | Bind authoritative schedule result model | P0 |
| Progress | Actuals, % complete, remaining, progress update | Progress/EVM foundations exist | Jalal + Hasan + Javad | Web update flow + persistence + result parity | P0 |
| EVM/SPI/CPI | Deterministic EVM/Earned Schedule calculations | Calculation foundation exists | Jalal | Cross-field/formula reconciliation | P0 |
| Resources | Resource categories, calendars, rates, roles, assignments | Resource foundation exists | Hasan + Javad | Functional V1 CRUD and schedule integration | P0 |
| Cost | Planned/actual/remaining/forecast/variance | Cost foundation exists | Hasan + Jalal | Connect resource/progress/schedule authoritative results | P0 |
| Documents | Documents, revisions, evidence, claims linkage | Persistence + recent rendering correction PR exists | Hasan + Javad | Functional Web document workflow | P0 |
| Reports | Typed datasets, schedule/progress/cost/control reports | Typed reporting foundation exists | Javad + Hasan | Web report screens and exports | P0 |
| Import/Export | P6 XER/XML and typed XLSX; no silent data loss | Provider-neutral adapter boundary exists; grammar not complete in PR #458 | Hasan + Jalal | Implement V1 formats and round-trip fixtures | P0 |
| Authentication/Authorization | Project/tenant/user permissions | Backend boundary exists | Hasan | Web permission-aware menus/actions | P0 |
| Localization | Persian/English + RTL/LTR | Multilingual foundations exist | Javad | Full V1 surface coverage | P0 |
| Jalali/Gregorian | Dual presentation without duplicate calculation logic | Calendar mode foundation exists | Jalal + Javad | End-to-end date/duration fixtures | P0 |
| Control room | Integrated project-control view | Web control/document foundations exist | Jalal + Javad + Hasan | End-to-end data projection | P1 |
| Portfolio | Cross-project control | Foundation exists | Hasan + Jalal | V1 scope verification before expansion | P1 |
| Field operations | Attendance/equipment/status flows | Core foundation exists | Hasan + Javad | Decide V1 depth; avoid expanding before Beta | P1 |
| Quality/Safety/Punch | Construction field-control suites | Competitive matrix marks product depth as missing/next maturity | Hasan + Javad | Scope only necessary V1 preview surfaces | P1 |
| Procurement/Commercial | Quotes, comparison, PO, commitment, delivery | Core foundation exists | Hasan + Javad | V1 workflow integration; retain deeper expansion after Beta | P1 |
| AI assistant | Safe assistant boundary | Architectural boundaries exist | Jalal + Hasan + Javad | Keep advanced AI features V2 unless required for V1 navigation | P1/V2 |
| Desktop/Mobile | Shared-client parity | Existing foundations | Javad | V2; preserve Core/API contracts | V2 |
| Web Beta packaging | Openable product with navigable real screens | Main Workspace scaffold exists | Javad + Hasan | Functional shell + seeded/demo data | P0 |
| CI/runtime verification | Fresh evidence for V1 gate | Several recent connector workflow queries returned no runs; some PRs explicitly say validation pending | Hasan + Jalal | Execute real GitHub/Codex checks | P0 |

## V1 hard stops
1. No authoritative calculation may be duplicated in a client.
2. No P6 equivalence may be certified from name similarity alone.
3. No important numeric/date/duration field may be transported as text where calculation semantics are required.
4. No menu/screen may appear complete when its functionality is only a placeholder; use Implemented/Partial/Preview.
5. No silent data loss during import/export.
6. No merge or release claim is made without fresh verification evidence.

## Fast-Beta strategy
V1 prioritizes a complete navigable Web surface and the shared calculation backbone. Desktop/Mobile and advanced AI are V2 unless a V1 boundary requires their contracts. Deeper P6 field certification continues in parallel behind the same registry; it must not block the visible Beta shell when the underlying contract is safely represented as Pending/Preview.
