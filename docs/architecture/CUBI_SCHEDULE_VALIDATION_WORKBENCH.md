# CUBI Schedule Validation Workbench

## Purpose

The validation workbench is a V1 engineering test path for schedule-engine conformance. A planner supplies an XER exported from a reference scheduler, CUBI normalizes the same schedule inputs, the authoritative Shared Scheduling Core calculates a new result, and a deterministic comparator reports activity-level deltas against the calculated values stored in the source file.

The first implementation slice is src/construction_pm/schedule_validation.py. It is deliberately only the comparison boundary: it reads standard stored-result fields from XER TASK rows and compares them with an already-calculated, normalized CUBI result. It does not yet import every XER input table into the scheduling core, invoke the scheduler, accept browser uploads, or expose a remote MCP server. Those capabilities must be added and verified before claiming end-to-end validation works from the site or ChatGPT.

## Source fields and normalized result

Oracle's Version 26 XER Project Data Map identifies these TASK columns:

| Source TASK column | Meaning in the comparison report | Normalized CUBI result key |
|---|---|---|
| task_code | Activity ID used to match records | activity_id |
| early_start_date | Early Start | early_start |
| early_end_date | Early Finish | early_finish |
| late_start_date | Late Start | late_start |
| late_end_date | Late Finish | late_finish |
| total_float_hr_cnt | Total Float in hours | total_float_hours |
| free_float_hr_cnt | Free Float in hours | free_float_hours |

Reference: https://docs.oracle.com/cd/G48897_01/English/Mapping_and_Schema/xer_import_export_data_map_project/97906.htm

The comparator requires the CUBI caller to provide float values already normalized to hours under an explicit and approved conversion policy. It never assumes a workday length and never performs CPM, calendar, resource leveling, or float calculations.

Planned/target dates (target_start_date, target_end_date) and actual dates (act_start_date, act_end_date) are not substitutes for stored calculated early/late dates. They must be kept separate in the import mapping.

## Comparison statuses

- MATCH: comparable values agree exactly for dates or within the declared float-hour tolerance.
- MISMATCH: both values exist with compatible precision, but they differ beyond tolerance.
- NOT_COMPARABLE: a field/value is absent, or date/time precision or timezone context cannot be aligned without assumptions.
- ONLY_SOURCE: an activity exists in the source XER but not in CUBI's calculated result.
- ONLY_CUBI: an activity exists in the CUBI result but not in the source TASK table.

The report contains the source file's SHA-256 hash, counts, and field-level entries with source value, CUBI value, delta, status and reason. This makes it possible to distinguish engine differences from incomplete input coverage and identity problems.

## Intended V1 workflow

1. The web workbench at /app/tools/schedule-validation accepts a bounded .xer upload into private, short-lived staging storage.
2. The existing P6XerCodec parses source tables. A versioned normalizer maps TASK, TASKPRED, PROJECT, CALENDAR and resource-assignment data into the existing canonical schedule input, with an explicit supported/unsupported field matrix.
3. Before calculation, the UI displays the source project, activity count, schedule options, calendars, dependencies, missing mappings and any required user choices.
4. A validation run executes in an isolated run scope through the single authoritative Shared Scheduling Core and never mutates the user's production project.
5. The comparator reconciles the original TASK calculation-result columns against CUBI output. Missing source semantics are NOT_COMPARABLE, not silently defaulted.
6. Users inspect the report and export JSON/CSV; a PDF rendering may be added as a presentation of the same report object.
7. A remote MCP service provides narrowly scoped tools to inspect an upload, start a validation run, and fetch reports by opaque run ID. It cannot write production project data.

## HTTP / ChatGPT integration target

Suggested authenticated endpoints, subject to implementation and contract tests:

- POST /api/v1/schedule-validation/uploads — multipart XER upload; validate size and structure; return an opaque, short-lived upload ID, source hash and preview summary.
- POST /api/v1/schedule-validation/runs — run authoritative calculation from a staged upload in an isolated scope, with an explicit schedule options/calendars/mapping context; return an opaque run ID.
- GET /api/v1/schedule-validation/runs/{run_id} — return run state, coverage and summary.
- GET /api/v1/schedule-validation/runs/{run_id}/report?format=json|csv — return the immutable report.

The current Pages/Codespaces web preview is a static client, not a hosted private scheduling runtime. A production authenticated HTTP host and remotely reachable MCP endpoint must exist before ChatGPT can call CUBI. After deployment, the project owner must register and authorize the remote MCP app in ChatGPT. Creating source files does not automatically establish this connection.

## Security and reproducibility

- Derive tenant, user and authorization scope from the authenticated session. Do not trust tenant/project IDs from raw browser headers.
- Enforce request size limits and strict XER parsing; do not extract arbitrary paths or execute file content.
- Stage files privately with short expiry and deletion controls. Do not issue public object URLs.
- Treat names and other XER text as untrusted content; do not follow URLs or instructions embedded in the file.
- Record source hash, mapping version, core version, selected schedule options, calendar versions, unit/tolerance policy and report hash.
- Require explicit user confirmation before any future corrective change; the V1 validator is read-only and must not mutate production data.

## Acceptance boundary

The comparison module and its unit tests do not prove full scheduling parity. End-to-end acceptance requires an actual supported P6 XER fixture, a complete normalized input context, one Shared Core calculation, deterministic field-level comparison, exact-head CI, an authenticated deployed runtime smoke test, and a successful ChatGPT MCP round trip after owner configuration.
