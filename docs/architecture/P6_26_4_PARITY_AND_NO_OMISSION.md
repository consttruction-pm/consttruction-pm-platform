# P6 26.4 Parity & No-Omission Baseline

Effective date: 2026-09-28

## Purpose

This document is the authoritative compatibility and completeness baseline for the product areas that overlap Oracle Primavera P6. It converts the P6 requirement from "similar functionality" into a testable **no-silent-omission rule**.

The baseline is release-versioned. At this revision the reference set is:

1. Oracle Primavera P6 Professional User Guide — Version 26.
2. Oracle Primavera P6 EPPM 26.4 What's New.
3. Oracle Primavera P6 EPPM REST/API documentation — Release 26 and Integration API 26.4.
4. Oracle Primavera P6 EPPM XER Import/Export Data Map Guide — Project Version 26.
5. Oracle Primavera P6 EPPM XER Import/Export Data Map Guide — Resource Only Version 26.
6. Oracle Primavera P6 EPPM XLSX Import/Export Data Map Guide — Version 26.

This is a product engineering baseline, not Oracle certification.

## Non-negotiable rule

For every P6 capability that belongs to our defined product scope, the product must:

- implement equivalent behavior; or
- implement a deliberate superset without changing the established P6 meaning; or
- explicitly classify the capability as Outside Scope with a recorded architectural/product decision.

A capability must not disappear merely because it is inconvenient for a simplified UI, database model, spreadsheet format, or web implementation.

"Implemented" means behavior, data type, persistence, calculation semantics, interoperability and regression evidence exist. A screen placeholder or a same-named field is not parity.

## Parity dimensions

### 1. Field completeness

Maintain a versioned P6 field registry by subject area. The registry must distinguish:

- field identifier and display title;
- subject area / business object;
- data type;
- unit of measure;
- writable vs read-only;
- filterable and orderable behavior;
- computed/derived vs stored;
- default/nullability rules;
- applicable client/context;
- P6 version introduced/changed/deprecated;
- mapping to internal canonical fields;
- mapping to import/export formats;
- regression status.

The field registry is the source for UI column catalogs, API contracts, import/export mappings and conformance tests.

### 2. Column and view completeness

A field and a column are separate concepts.

The platform must support a reusable column/view engine with:

- standard P6 field columns;
- custom fields / UDF columns;
- add/remove;
- hide/show;
- reorder;
- rename/display-title override;
- width and alignment;
- pin/freeze where the client supports it;
- sort and group metadata;
- user/project/global layouts as applicable;
- layout persistence and versioning;
- field-level permissions;
- stable column identifiers so layouts survive software versions.

One field may appear in many layouts. A layout must not create a second copy of the underlying business field.

### 3. Custom fields and formulas

The platform must support typed custom fields for all applicable P6 subject areas.

Formula-capable fields/columns must use a safe calculation pipeline:

Formula text -> tokenizer -> parser -> AST -> type checker -> dependency analyzer -> cycle detector -> deterministic evaluator -> typed result.

The formula engine must not use Python/JavaScript eval-style execution or allow arbitrary code.

Required behaviors:

- explicit result type;
- operand compatibility checks;
- null semantics;
- unit compatibility;
- date/duration/calendar-aware functions where applicable;
- dependency graph;
- transitive invalidation/recalculation;
- circular dependency rejection;
- deterministic results;
- formula versioning and audit;
- clear validation errors;
- summary/group/WBS/project rollups;
- formula dependencies included in export/import context.

### 4. Calendar completeness

The Shared Calendar Domain must cover, at minimum:

- global calendars;
- project calendars;
- resource calendars;
- shared and personal resource-calendar concepts where applicable;
- calendar assignment to projects, activities and resources;
- base/global calendar inheritance;
- standard workweek;
- date-specific exceptions;
- holidays and nonworkdays;
- workdays overriding a normal exception;
- detailed intraday work intervals;
- total work hours per day;
- hours-per-time-period conversion factors;
- calendar-specific duration/unit conversion;
- calendar versioning;
- effective references carried by project calculations;
- deterministic replay after export/import.

Calendar semantics belong only to the Shared Domain/Calculation Core.

### 5. Scheduling/calculation option completeness

The project scheduler settings model must not be reduced to one forward/backward-pass switch.

The parity registry must include every applicable P6 setting that can affect calculation results or project interpretation, including:

- schedule mode;
- data date;
- project/activity/relationship-lag calendars;
- duration and lag units;
- relationship types and lag signs;
- constraints;
- out-of-sequence scheduling treatment (Retained Logic / Progress Override / Actual Dates);
- treatment of expected finish;
- open-ended activity criticality;
- critical activity definition and float threshold;
- longest path;
- multiple float paths and their method/endpoint/count;
- automatic rescheduling;
- resource leveling behavior and priorities;
- cross-project assignment consideration;
- preservation of scheduled early/late dates;
- resource/role cost recalculation behavior;
- actuals/progress calculation options;
- financial-period and stored-period behavior where applicable;
- baseline selection and summary behavior;
- project/WBS summary calculations.

Each option needs an explicit enum/boolean/typed contract, persistence, UI exposure where applicable, serialization, and regression tests.

### 6. Import/export completeness

The interchange layer is a first-class domain boundary, not a spreadsheet helper.

The release baseline must cover all approved P6 exchange surfaces applicable to the product, including:

- XER project;
- XER resource-only;
- XER role-only where applicable;
- Primavera XML;
- XLS/XLSX activity and related imports/exports;
- Microsoft Project XML;
- MPX where still applicable;
- UN/CEFACT, IPMDAR, CPP and other approved formats when product scope requires them.

Import/export must have:

- field mapping registry;
- explicit supported/unsupported status per field and format;
- typed conversion;
- locale-independent canonical storage;
- date and timezone policy;
- duration/unit preservation;
- decimal precision preservation;
- enum mapping;
- code/UDF mapping;
- relationship mapping;
- calendar mapping;
- baseline/scenario mapping;
- resource/rate mapping;
- financial-period mapping when supported;
- validation and actionable error reporting;
- round-trip tests.

An unsupported field must never be silently dropped. It must either be preserved as a supported extension/unknown-field container or produce an explicit compatibility warning/error according to the import policy.

### 7. Typed data rule

The canonical domain must not mix display formatting with data storage.

Examples:

- dates remain dates;
- durations remain typed quantities;
- numeric values remain numeric/Decimal;
- currencies carry currency semantics;
- percentages remain numeric percentages;
- Boolean fields remain Boolean;
- IDs/codes remain strings;
- enums remain stable symbolic values.

A Persian/Jalali display must not change the canonical stored date or its export type.

### 8. API and client parity

Web, Desktop and Mobile may present different screens, but they consume the same field registry, column definitions, layouts, formula engine and Shared Calculation Core.

No client may:

- invent a P6 field;
- change a P6 calculation;
- perform a different date/duration conversion;
- implement a private formula engine;
- silently hide an applicable field because it is not present in a particular client.

Client-specific presentation is allowed; client-specific business semantics are not.

## Required core architecture

The canonical dependency direction is:

P6 Parity Registry
-> Canonical Field Definitions
-> Column/View Definitions
-> Formula Definitions + Dependency Graph
-> Shared Calendar/Unit Semantics
-> Shared Scheduling/Calculation Core
-> Application Use Cases
-> API / Import / Export Adapters
-> Web / Desktop / Mobile presentations

Import/export adapters and UI grids consume the same registry. They do not own copies of field metadata.

## Subject-area coverage

At minimum, the parity inventory must explicitly cover:

| Subject area | Required baseline |
|---|---|
| Projects / EPS | standard fields, settings, codes, UDFs, summary values, baselines/scenarios, permissions and export mappings |
| WBS | hierarchy, responsible manager/OBS, dates, EV settings, summaries, UDFs, codes and export mappings |
| Activities | complete field catalog, dates, durations, types, percent-complete, costs/units, EV, baselines, floats, codes/UDFs, status/progress and relationships |
| Activity Steps | step fields, sequence, descriptions, weights, dates, UDFs |
| Relationships | FS/SS/FF/SF, positive/negative lag, lag units/calendar, cross-project references and import/export |
| Activity Resource Assignments | units, costs, rates, calendars, actual/remaining, spread/future-period data, codes/UDFs |
| Resources | hierarchy, labor/nonlabor, calendars, rates, shifts, roles, codes/UDFs, availability and export |
| Roles | hierarchy, rates over time, limits, codes/UDFs and export where applicable |
| Expenses | category, planned/actual/remaining costs, dates, WBS/activity linkage, UDFs and import/export |
| Activity/Project/Resource Codes | code definitions, values, hierarchy, security/availability rules, assignments and interchange |
| Cost Accounts | definitions, hierarchy, assignments and interchange |
| Calendars | all calendar pools, assignments, inheritance, exceptions, detailed hours and conversion factors |
| Baselines | primary/secondary/tertiary/user-selected baseline semantics and date/unit/cost comparisons |
| Financial Periods | period definitions and stored actual/period performance where applicable |
| Work Products & Documents | assignment metadata, status/categories, linkage and export/import behavior where applicable |
| Issues / Risks / Notices where in scope | fields, codes, status, ownership, dates, assignments, UDFs and reporting mappings |
| User Defined Fields | all applicable subject areas, supported data types, permissions, persistence, columns and import/export |
| Reporting / Layouts | selectable fields, filters, grouping, sorting, layout persistence and typed output |

This table is the minimum subject-area checklist, not permission to omit fields within an area.

## Current project gap assessment

As of 2026-09-28, the repository already contains important foundations for:

- shared calendar resolution and versioned calendar references;
- time-aware working-time arithmetic;
- project portability context;
- typed API contracts;
- resource/cost and scheduling foundations;
- shared architecture and web-readiness rules.

The repository does **not yet provide verified evidence of full P6 field-registry, generic column-layout, formula-column, and complete P6 interchange parity**. These are therefore mandatory implementation gaps, not optional enhancements.

The existing project-portability contract is a calculation-context portability contract. It is not yet a complete P6 project-file interchange implementation.

## Conformance gates

No Gate A release may declare P6 parity complete unless:

1. the applicable P6 version baseline is frozen;
2. every baseline field has a disposition;
3. every applicable calculation option has a disposition;
4. all calendar semantics are covered;
5. all approved import/export formats have typed mappings;
6. no field is silently dropped during import/export;
7. formula dependencies and cycles are tested;
8. client outputs are traceable to the Shared Core;
9. representative round-trip fixtures reproduce equivalent data and calculations;
10. regression tests cover both writable and computed fields.

## Version refresh rule

When Oracle publishes a new P6 release, the parity process starts with a diff against this baseline:

P6 release N
-> field/option/calendar/import-export inventory diff
-> impact classification
-> architecture gap list
-> implementation/test work
-> certification evidence.

The new version cannot be treated as "covered by inheritance" without an explicit inventory diff.

## Official Oracle references

- P6 Professional User Guide Version 26:
  https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/toc.htm
- P6 26.4 What's New:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-wn26/index.html
- P6 EPPM REST API Release 26:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/
- P6 Integration API Release 26.4:
  https://docs.oracle.com/cd/G48897_01/English/Integration_Documentation/p6_eppm_api_reference/
- XER Project Data Map Version 26:
  https://docs.oracle.com/cd/G48897_01/English/Mapping_and_Schema/xer_import_export_data_map_project/xer_import_export_data_map_project.pdf
- XER Resource-Only Data Map Version 26:
  https://docs.oracle.com/cd/G48897_01/English/Mapping_and_Schema/xer_import_export_data_map_resource_only/
- XLSX Data Map Version 26:
  https://docs.oracle.com/cd/G48897_01/English/Mapping_and_Schema/xlsx_import_export_data_map/xlsx_import_export_data_map.pdf
