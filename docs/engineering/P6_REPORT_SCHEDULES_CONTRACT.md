# Durable report schedule contract (`p6-report-api.v1`)

Schedules persist a cadence plus the snapshot identity of a stored report
definition. Execution materializes a normal immutable `ReportRun` and records
the SHA-256 of the rendered export. The module owns **no timer and no background
thread**: a trusted deployment trigger (existing cron/worker tick) calls the
runner. This avoids a second scheduler in the process.

## Definition fields

| Field | Rule |
|---|---|
| `schedule_id` | non-empty, unique within tenant/project |
| `cadence` | `daily`, `weekly`, `monthly` |
| `run_time` | local wall clock `HH:MM` |
| `timezone` | IANA zone name |
| `weekday` | required only for `weekly`, `0` = Monday … `6` = Sunday |
| `day_of_month` | required only for `monthly`, `1`–`28` |
| `project_revision` | non-negative; snapshot revision used by the run |
| `export_format` | `csv`, `xlsx`, `pdf` |
| `locale` | `en`, `fa` (PDF only) |
| `parameters` | explicitly supplied, canonicalized parameter values |
| `enabled` | boolean |
| `revision` | optimistic concurrency counter |

`project_revision` is captured when the schedule is created or updated (the
HTTP layer defaults it to the request's project revision). The scheduled run is
therefore reproducible against that revision rather than silently following a
later project state. Updating the schedule is how an operator deliberately
moves it forward.

`parameters` stores **only explicit values**. Defaults are re-resolved when the
occurrence executes, and the resulting run records the real
`explicit`/`default` provenance. Supplying an unknown or unbound key, a missing
required value, or an invalid type/enum fails the request with the normal
`REPORT_PARAMETER_*` codes.

## Next occurrence

`compute_next_run` converts the local wall clock through the zone database and
returns UTC:

- strict `>` comparison: an occurrence equal to `after` is skipped;
- a nonexistent local time (DST gap) maps forward with the post-gap offset;
- a repeated local time (DST fall-back) uses `fold=0`;
- the result is deterministic for a fixed `after` and zone database.

## Endpoints

```
GET    .../reports/{report_id}/schedules
POST   .../reports/{report_id}/schedules
GET    .../reports/{report_id}/schedules/{schedule_id}
PUT    .../reports/{report_id}/schedules/{schedule_id}
PATCH  .../reports/{report_id}/schedules/{schedule_id}
DELETE .../reports/{report_id}/schedules/{schedule_id}?expected_revision=N
GET    .../reports/{report_id}/schedules/{schedule_id}/history
```

- Reads require project-read; create/update/delete require project-write in the
  same tenant/project scope. A cross-scope or unprivileged request is `403`.
- `PUT`/`PATCH` replace the schedule representation and require
  `expected_revision`. A stale revision is `409
  REPORT_SCHEDULE_REVISION_CONFLICT`.
- A duplicate id is `409 REPORT_SCHEDULE_ALREADY_EXISTS`; an unknown schedule
  is `404 REPORT_SCHEDULE_NOT_FOUND`.
- Invalid cadence/time/zone/format/locale/parameters are `400` with the
  specific `INVALID_REPORT_SCHEDULE_*` code.
- Delete is a hard delete of the row; the append-only audit trail keeps
  `created`/`updated`/`deleted` events even if the same id is re-created.
- The catalogue advertises `schedule_cadences`.

## Durable execution

`SQLiteReportScheduleStore` and `ReportScheduleRunner` implement a claim/lease
cycle:

1. `claim_due(now, worker_id, lease_seconds, limit)` selects enabled schedules
   whose `next_run_at <= now` and whose claim is absent or expired, then sets a
   random `claim_token` and `claimed_until` with a conditional update. A lost
   race yields no claim for that row.
2. The runner materializes the run with the deterministic id
   `RUN-SCH-{schedule_id}-{scheduled_for:%Y%m%dT%H%M%SZ}` and
   `generated_at = scheduled_for`, so a crash after `save_run` but before
   completion reuses the stored run instead of duplicating it.
3. Success records `last_run_at`, `last_status=succeeded`, resets `attempts`,
   clears the claim and advances `next_run_at`.
4. Any failure records `last_status=failed`, the bounded error text, increments
   `attempts` and schedules a retry with exponential backoff (base 5 minutes,
   cap 60 minutes by default). A later success resets the counter.
5. A worker whose lease expired loses the claim; `complete`/`fail` then raise
   `REPORT_SCHEDULE_CLAIM_LOST` rather than overwriting another worker.

Each success also returns the export `content_sha256` for the configured
format/locale. Delivery (email/S3/webhook), delivery retries and delivery
checksum persistence are **not implemented**; the transport credentials are an
external gate. The runner records the checksum so a transport can attach it
later without re-rendering.

## Schema and migration

`project_report_schedule` stores the fields above plus `last_run_at`,
`last_status`, `last_error`, `attempts`, `claim_token`, `claimed_until`,
`created_at` and `updated_at`. `initialize()` creates the table and the
`(enabled, next_run_at)` due index, and adds `project_revision` with a `0`
default to databases created by an earlier build. Schedule audit events use
`entity_type = 'report_schedule'` in the existing `project_report_audit` table;
report-definition history filters `entity_type = 'report'` so the two streams
cannot mix.

## Out of scope in this slice

- In-process timers or a second scheduler; the deployment tick is external.
- Transport delivery, retries, credentials and destination configuration.
- Browser/Web UI for schedule management (Agent 1 owns the workspace surface).
- A PostgreSQL schedule store; like the report register it remains SQLite-only.
