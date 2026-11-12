# P6 Exchange API contract (`p6-exchange-api.v1`)

Backend contract for the workspace Import / Export surface. The Web UI is Agent 1's
scope; this document defines what the backend accepts and returns.

## Endpoints

| Method | Path | Permission | Purpose |
| --- | --- | --- | --- |
| GET | `/api/projects/{project}/exchange/datasets` | `PROJECT_READ` | Catalogue: datasets, columns, importability, export formats. |
| GET | `/api/projects/{project}/exchange/export?dataset=...&format=csv\|xlsx` | `PROJECT_READ` | Download the dataset from authoritative stores. CSV is JSON-wrapped; XLSX streams bytes with `Content-Disposition` and `X-Content-SHA256`. |
| POST | `/api/projects/{project}/exchange/import/preview` | `PROJECT_READ` | Validate a file and return row diagnostics without writing. |
| POST | `/api/projects/{project}/exchange/import` | `PROJECT_WRITE` | Validate and atomically apply a file; requires `idempotency_key`. |
| GET | `/api/projects/{project}/exchange/imports` | `PROJECT_READ` | Newest-first run history. |

Payload: `{dataset, content, format?, idempotency_key?}`. `format` is `csv`
(default) or `xlsx`; XLSX `content` is base64 of the workbook bytes. Maximum
content length is 1,000,000 characters.

## Datasets and columns

| Dataset | Importable | Columns |
| --- | --- | --- |
| `activities` | yes | `activity_id, name, activity_type, status, actual_start, expected_finish, duration_value, duration_unit, percent_complete, wbs_id` |
| `resources` | yes | `resource_id, name, resource_type, parent_resource_id, calendar_id, default_units_per_time, unit_of_measure, email, is_active` |
| `wbs` | yes | `wbs_id, code, name, parent_wbs_id, sequence_number` |
| `assignments` | yes | `assignment_id, activity_id, resource_id, role_id, units, actual_units, remaining_units, planned_cost, actual_cost, remaining_cost, unit, currency, calendar_id` |
| `costs` | yes | `expense_id, name, category, activity_id, wbs_id, expense_date, planned_cost, actual_cost, remaining_cost, currency, note` |
| `risks` | no | `risk_id, title, category, status, probability, impact, score, exposure, owner, response_strategy, date_identified` |

Imports are create-only. Existing IDs are rejected (`*_ALREADY_EXISTS`), as are
duplicate IDs inside the file. Identifiers stay text in XLSX; numeric and date
columns use typed cells where the contract defines them.

## Validation

- Required/unknown columns, row arity, blank rows and duplicate headers fail with
  row/field/code diagnostics; preview never writes.
- Enum values: activity type, status, duration unit, resource type.
- WBS: parent must exist in the project or in the same file; cycles and
  `PROJECT`-kind roots that conflict with the existing root fail closed.
- Activities: WBS is required; dates and percentages are validated.
- Assignments: activity and resource must exist; decimals must be finite.
- Costs: activity/WBS references must exist; expense date is ISO.
- Cross-tenant/project references never resolve; every read and write is scoped.
- Spreadsheet formula injection is neutralised on export (leading `= + - @ TAB CR`
  becomes an apostrophe-prefixed literal); imports store text as data.

## Atomicity and idempotency

Apply validates the full dependency graph first, then writes inside one
application-owned transaction. A failing row, repository exception, constraint
violation or stale reference rolls back the entire batch. The run record and the
idempotency reservation are part of the same transaction, so a rolled-back batch
does not reserve its key. Same key + same normalized payload returns the stored
run with `replayed: true`; same key + different payload returns HTTP 409
`EXCHANGE_IDEMPOTENCY_KEY_REUSE`.

## Formats

- CSV: UTF-8, `csv.DictReader`/`DictWriter`, quoted fields, embedded delimiters
  and multiline cells supported.
- XLSX: one worksheet, header row, typed numeric/date cells, base64 transport.
- XML: not part of this contract. No versioned XML register schema exists in the
  repository, so the backend does not invent one.

## Compatibility

CSV remains the default. The contract only adds datasets, `format`, and
`atomic`/`created` fields; existing `resources` CSV clients keep working.
