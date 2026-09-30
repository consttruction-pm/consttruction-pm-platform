# P6 Backend Parity Gap Audit — 2026-09-30

## Baseline

- Repository: `consttruction-pm/consttruction-pm-platform`
- Current `main`: `29b496fe7a7dcf6d369dd00eea499270ea9fcc2b`
- Owner: Hasan — Backend / Database / Application / API / Import-Export
- Authority: Jalal — Shared Core / P6 scheduling, calendar, formula and calculation semantics
- Client owner: Javad/Farmj22002 — Web/Desktop/Mobile UX and integration
- Audit issue: #559
- Rule: merged current-main evidence counts; stale branches/PRs do not.

## P6-2 typed persistence/API

| Surface | Current-main evidence | Result |
|---|---|---|
| Field Registry metadata | `p6_field_registry_repository.py`, `p6_field_registry_api.py`, PostgreSQL live tests | Implemented |
| Custom/UDF definitions | `p6_user_defined_fields_repository.py`, SQLite/PostgreSQL tests | Implemented |
| Typed UDF values | `p6_user_defined_field_values_repository.py`, typed value tests + PostgreSQL coverage | Implemented |
| Formula definitions | `p6_formula_definition_repository.py`, `p6_formula_definition_api.py`, PostgreSQL tests | Implemented; Shared Core semantics remain external |
| Report/profile field mappings | `p6_report_profile_repository.py`, PostgreSQL/concurrency tests | Implemented |
| Tenant/project/revision scope | Present across the above repositories/APIs | Implemented |
| Versioning/immutability | Formula/versioned definitions and immutable mapping/field contracts | Implemented |
| PostgreSQL race safety | Field, mapping, formula, report-profile, resource-assignment/spread and other P6 upserts have live concurrency coverage | Implemented on audited surfaces |
| Compatibility/version migration | No authoritative target registry-version transition found | Deferred; do not invent migration semantics |

## P6-7 interchange

| Surface | Current-main evidence | Result |
|---|---|---|
| Mapping Registry | `p6_mapping_registry.py` + versioned API/schema | Implemented |
| Provider-neutral mapping | `p6_interchange_mapping.py` | Implemented |
| Adapter boundary | `p6_interchange_adapter.py` | Implemented |
| XER project/resource-only/role-only | `p6_xer_codec.py` + conformance round-trip fixtures | Implemented |
| Primavera XML | `p6_primavera_xml_codec.py` + round-trip fixture | Implemented |
| XLS/XLSX | `p6_xls_codec.py`, `p6_xlsx_codec.py` + round-trip fixtures | Implemented |
| Microsoft Project XML/MPX | `p6_msproject_xml_codec.py`, `p6_mpx_codec.py` + round-trip fixtures | Implemented |
| Unsupported/unknown field policy | Mapper preserves unknown/unsupported values as extensions or rejects explicitly; collision/metadata regressions exist | Implemented |
| No silent XLSX loss | Oversized sheet names, malformed/duplicate extension metadata and collisions are explicitly rejected | Implemented |
| Round-trip conformance | `tests/test_p6_interchange_conformance_fixtures.py` covers XER, Primavera XML, XLS/XLSX, MS Project XML and MPX | Implemented |

## P6-8 working data

| Surface | Current-main evidence | Result |
|---|---|---|
| Activity period actuals | repository + PostgreSQL live coverage | Implemented |
| Activity steps | repository + PostgreSQL live coverage | Implemented |
| Activity step templates | repository + PostgreSQL live coverage | Implemented |
| Codes / assignments | code definition + assignment repositories and PostgreSQL coverage | Implemented |
| Cost accounts | repository + PostgreSQL coverage | Implemented |
| Expenses | repository + PostgreSQL coverage | Implemented |
| Financial periods | repository + PostgreSQL coverage | Implemented |
| Resource assignments | repository + PostgreSQL/concurrency coverage | Implemented |
| Resource spreads / future-period data | repository + PostgreSQL/concurrency coverage; PR #586 is on current main | Implemented |
| Baseline metadata | repository + PostgreSQL coverage | Implemented; comparison/calculation semantics remain Shared Core-owned |
| Report/profile mappings | repository + PostgreSQL/concurrency coverage | Implemented |

## Cross-cutting gates

- Tenant/project isolation: present in audited repository/API contracts.
- Revision/optimistic-lock checks: present in audited persistence boundaries.
- Transaction ownership: application services own transactions where applicable.
- Idempotency/replay: covered by existing persistence/application tests on audited surfaces.
- PostgreSQL verification: live integration workflow covers the audited P6 persistence set.
- API contract identity: Mapping Registry v1 drift was fixed in PR #535; do not repeat it.
- Interchange scope validation: backend scope checks and codec validation are present.
- No duplicate Shared Core calculations: audit found no Hasan-owned implementation of scheduling/calendar/formula calculation semantics.

## Proven remaining gaps / dependencies

1. **P6-3 Column/View/Layout** is Javad-owned. No Hasan implementation should duplicate the client/layout engine.
2. **P6-5 Schedule Options / OOS / Expected Finish** remains Shared Core/Jalal-owned; open PRs #582/#583/#585/#587 are not Hasan work.
3. **Baseline comparison/variance semantics** require Shared Core authority before any backend persistence/API extension.
4. **Field behavior where writable + scheduler-derived** is still dependent on the Shared Core contract being finalized; backend schema evolution should follow that contract rather than anticipate it.
5. No independent, proven Hasan-owned persistence/API defect was found on the audited P6-2/P6-7/P6-8 surfaces on current `main`.

## Audit conclusion

The current evidence does **not** justify another speculative backend feature. The correct continuation after PR #586 is to keep the current-main evidence boundary, advance only when a new authoritative contract or reproducible backend defect appears, and avoid duplicating merged persistence/codecs or Shared Core semantics.
