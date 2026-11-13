# P6 Production Readiness Contract

Status: implemented and tested on `agent3/production-readiness-2026-11` (Issue
#1799 Workstream 7). **No production deployment, cloud provisioning, scanner
activation, OCR activation or DNS/billing change was performed.** This document
records configuration validation, readiness semantics, observability behavior
and the deployment/backup gates that remain owner-controlled.

## Configuration validation

`construction_pm.production_readiness.validate_environment(environ, production=...)`
returns `EnvironmentValidation` with:

- `valid`, `environment`, `production`;
- `components`: whether each service is explicitly configured;
- `errors` / `warnings`: stable `code` plus the offending **variable name**;
- `component_problems`: per-component stable codes.

Values, DSNs, bucket names, endpoints, keys and exception messages are never
copied into the result. Validation is pure and performs no network call.

Production mode rejects the development adapters and requires an explicit
setting for every mandatory dependency:

| Component | Production rule | Development rule |
| --- | --- | --- |
| Database (`CONSTRUCTION_PM_DATABASE_URL` or legacy `CONSTRUCTION_PM_POSTGRES_DSN`) | PostgreSQL required; SQLite rejected | SQLite allowed |
| Object storage (`CONSTRUCTION_PM_DOCUMENT_STORAGE`) | `s3` with complete `CONSTRUCTION_PM_S3_*` settings; local rejected | local or s3 |
| Scanner (`CONSTRUCTION_PM_SCANNER`) | `external` with HTTPS `CONSTRUCTION_PM_SCANNER_ENDPOINT`; `reference` rejected | reference or external |
| Strict scanning (`CONSTRUCTION_PM_REQUIRE_SCANNED_CONTENT`) | Required and must be true | Optional |
| OCR (`CONSTRUCTION_PM_OCR`) | Optional; `disabled`, `reference` or `external` | Same |
| Job queue (`CONSTRUCTION_PM_JOB_QUEUE`) | `durable`; `in_process` rejected | in_process or durable |
| Retention (`CONSTRUCTION_PM_RETENTION`) | `enabled` | enabled or disabled |
| Logging (`CONSTRUCTION_PM_LOG_FORMAT`, `CONSTRUCTION_PM_LOG_LEVEL`) | JSON required; known level | JSON or text |
| Tracing (`CONSTRUCTION_PM_OTEL_ENDPOINT`) | Optional HTTPS URL | Optional |

An invalid value (unknown kind, malformed URL, conflicting database variables)
is an error in any environment. A production override can be supplied with
`production=True` for tests and startup checks.

## Readiness semantics

`build_readiness_service(environ, probes=..., production=...)` aggregates
`configuration`, `database`, `object_storage`, `malware_scanner`, `ocr`,
`job_queue`, `retention` and `observability` checks.

- A failed **required** component makes the report `not_ready`.
- A failed **optional** component makes the report `degraded`; traffic is
  still accepted.
- Every component is required in production except `ocr`, which is optional.
- A configured required component without a real probe reports
  `PROBE_NOT_CONFIGURED`; configuration alone is not treated as health.
- Probe exceptions are reduced to `PROBE_FAILED:<ExceptionClassName>`.
  Probe detail is restricted to `[A-Za-z0-9_.:-]{1,120}`; anything else becomes
  `PROBE_DETAIL_REDACTED`.

Deployment probes should check real connectivity: a database round trip, an
object-storage read/head in the deployment's own bucket, and scanner
availability. OCR is optional and may remain `disabled`.

## HTTP operational surface

`construction_pm.http.operational.OperationalMiddleware` exposes:

| Path | Methods | Behavior |
| --- | --- | --- |
| `/api/health/live` | GET, HEAD | `200 {"status":"alive"}` while the process serves |
| `/api/health/ready` | GET, HEAD | `200` for `ready`/`degraded`; `503` for `not_ready` |
| other methods on those paths | — | `405` with `Allow: GET, HEAD` |

Responses are `application/json`, `Cache-Control: no-store`, and include a
validated or generated `X-Request-ID`. They never include DSNs, endpoints,
buckets, credentials, exception text or stack traces. Requests with an invalid
or absent `X-Request-ID` receive a new opaque id.

`build_project_lifecycle_wsgi_app(..., readiness_service=..., readiness_probes=...,
request_logger=..., operational_endpoints=True)` wraps the composed app with this
middleware by default. Supplying `operational_endpoints=False` is available for
unusual embedding, but a production deployment should keep the probes enabled.

## Metrics export

`construction_pm.metrics_export` adds an optional, bounded exporter from the
in-process `OperationalMetrics` registry. It is disabled by default and is not
required by health or readiness.

| Variable | Default | Meaning |
| --- | --- | --- |
| `CONSTRUCTION_PM_METRICS_EXPORT_ENABLED` | unset (disabled) | `1/true/yes/on` enables the scrape route |
| `CONSTRUCTION_PM_METRICS_EXPORT_TOKEN` | none | Bearer token, 16–512 printable characters; required when enabled |
| `CONSTRUCTION_PM_METRICS_EXPORT_MAX_BYTES` | `262144` | Hard cap (1 B–4 MiB) on the exposition body |
| `CONSTRUCTION_PM_METRICS_EXPORT_MAX_SERIES` | `2000` | Registry cap applied when composing the exporter |

When enabled, `GET|HEAD /api/metrics` serves
`text/plain; version=0.0.4` with `Cache-Control: no-store`:

- `404` when export is disabled (the route does not exist).
- `401` with `WWW-Authenticate: Bearer realm="metrics"` when the token is
  missing, malformed or wrong. Comparison is constant-time; the response never
  indicates which part failed and never echoes the token.
- `503` when the export is enabled but misconfigured, has no registry, exceeds
  the byte cap, or the renderer fails. The error code is a static identifier or
  an exception class name, never an exception message.
- `405` with `Allow: GET, HEAD` for other methods.

Export is deterministic: series are ordered by metric name and label set, and
numbers are rendered without locale variation. Counters appear as `<name>`;
observations appear as `<name>_count`, `_sum`, `_min`, `_max` and `_mean`.
Non-finite observations are rejected by the registry. Labels remain bounded to
the registry's validated `[A-Za-z0-9_.:/-]` values, so tenant ids, user ids,
tokens, document names and raw request paths cannot become labels.

Scrapes and health probes are served outside request instrumentation: they do
not increment `http_requests_total` and do not depend on the exporter.
Rendering failures are contained to the scrape request; business requests and
health probes continue to work. The exporter covers the existing
`http_requests_total` / `http_request_duration_ms`, `document_uploads_total`,
`document_ocr_jobs_total`, `exchange_runs_total`, `report_runs_total`,
`report_schedule_runs_total`, storage reconciliation and backup-consistency
series.

This is metrics export only. There is no span exporter, collector, sampling,
trace context propagation or vendor agent, so the platform does **not** claim
distributed tracing.

## Structured events

`StructuredEventLogger` emits one JSON object per line:

```json
{
  "correlation_id": "req-123",
  "duration_ms": 12,
  "event": "http.request.completed",
  "method": "GET",
  "path": "/api/projects/P1/tracking/read",
  "service": "construction-pm",
  "severity": "info",
  "status": 200,
  "timestamp": "2026-11-12T12:00:00+00:00"
}
```

The middleware logs method, path (without query string), status and duration.
It does not log bodies, headers, cookies, tokens, file content or query strings.
`redact_fields` additionally replaces keys containing `authorization`, `cookie`,
`credential`, `password`, `secret`, `token`, `api_key`, `access_key`,
`private_key`, `content`, `payload`, `body` or `bytes`; string values are capped
at 512 characters and bearer/basic credentials are scrubbed. A failed request
logs `http.request.failed` with the exception class name only.

Application-level events use the same logger and inherit the request
correlation id from the context variable:

| Event | Emitted by | Fields (all bounded) |
| --- | --- | --- |
| `document.content.uploaded` | document upload | `document_id`, `version`, `content_type`, `byte_size`, `scan_status`, `replay` |
| `document.ocr.job` | OCR runner | `document_id`, `version`, `status`, `engine`, `char_count` |
| `exchange.run` | exchange preview/apply/export | `operation`, `dataset`, `status`, `format`, `valid`, `row_count`, `accepted`, `rejected`, `run_id`, optional export `content_sha256` |
| `report.run.completed` | report materialization | `report_id`, `run_id`, `source`, `report_revision`, `project_revision`, `row_count` |
| `report.schedule.run` | schedule runner | `schedule_id`, `state`, `run_id`, `content_sha256` |

Counter metrics `document_uploads_total`, `document_ocr_jobs_total`,
`exchange_runs_total`, `report_runs_total`, `report_schedule_runs_total`,
`document_storage_reconciliation_total`, `http_requests_total` and the
`http_request_duration_ms` / `document_storage_reconciliation_ms` observations
live in the bounded in-process `OperationalMetrics` registry.

## Staging smoke test

`construction_pm.staging_smoke.run_staging_smoke` / `scripts/staging_smoke.py`
performs only `GET` requests against liveness and readiness, validates the JSON
shape, and requires configured components to report healthy. It never posts,
writes, migrates or sends external messages. A passing run is staging evidence
only; it is not production verification.

## Deployment template

`infra/deploy/production.env.example` lists every expected variable with
placeholder values. `infra/deploy/deployment.template.yaml` is a generic
container manifest template with liveness/readiness probes wired to the paths
above. Neither was applied. The deployment owner must supply image digest,
namespace, secrets, ingress, TLS, backups and provider-specific settings.

## Backup and restore implications

Document bytes and document metadata live in separate systems. The existing
project/layout backup snapshot captures authoritative metadata but **does not**
contain document bytes. A complete restore therefore needs:

1. a PostgreSQL point-in-time backup of document metadata, retention policy and
   disposition rows, and content-version rows;
2. an object-storage backup or versioned replica of the same point in time;
3. a consistent cut-off so metadata never references bytes that were not
   captured, or vice versa.

`construction_pm.document_backup_consistency.verify_document_versions` /
`verify_document_scope` are read-only post-restore checks. They report `ok`,
`missing`, `integrity_failed` or `unavailable` per version and never delete or
repair objects. `StorageConsistencyReport.as_dict()` omits `storage_ref` and
includes only counts, document ids and version numbers. A restore is consistent
only when `consistent` is true; missing or tampered bytes must be restored from
the object backup, not silently regenerated.

Restore tests cover: copying a SQLite metadata database plus a local object
root, reading every restored version with hash verification, detecting a
deleted object as `missing`, and detecting same-length tampering as
`integrity_failed`.

## Storage reconciliation and orphan cleanup

`construction_pm.document_storage_reconciliation.DocumentStorageReconciler`
classifies drift between the metadata store and the byte store and can remove
bytes that are provably unreferenced. It deliberately separates detection from
destruction:

- `reconcile()` defaults to `dry_run=True` and writes nothing to either system;
  a dry run does not advance the observation counter either.
- The metadata snapshot (content versions, dispositions, retention policies) is
  read before the object store is listed. A metadata or inventory failure
  returns `status="aborted"` and deletes nothing, so an unavailable database
  cannot be mistaken for "everything is an orphan".
- Classes are `match`, `metadata_only`, `orphan_object`, `checksum_mismatch`,
  `size_mismatch`, `incomplete_upload`, `pending_deletion`, `unknown_object`,
  `retention_protected` and `unavailable`. Only `orphan_object`,
  `incomplete_upload` and `pending_deletion` are destructive candidates.
- `ReconciliationPolicy.min_observations` is validated to be at least two and
  the default grace period is 24 hours; the conditional claim re-checks both in
  SQL, so a single pass can never delete and a competing reconciler skips.
- Tenant/project ownership is proven by mapping the object scope hash back to
  exactly one metadata scope. Unmapped or ambiguous scopes are
  `unknown_object` and are never deleted.
- `pending_deletion` requires every version that references the same
  content-addressed object to be disposed; a live version or a legal hold keeps
  the bytes. This is the reference-count protection for deduplicated content.
- The lease is committed before the external delete, and `deleted` / `failed`
  outcomes commit immediately with an append-only cleanup row (actor, reason,
  object handle, checksum, size, status, attempt, timestamp). Failed deletes
  are retryable on the next pass.
- The machine-readable report contains document ids, versions and opaque
  object handles only; storage references, filesystem paths, bucket names and
  credentials are never emitted.
- `LocalDocumentObjectInventory` walks the content-addressed layout and detects
  `.upload-*` staging files; `S3DocumentObjectInventory` uses signed
  `ListObjectsV2` pagination over the configured bucket and prefix. Local
  deletion revalidates the path, rejects symlinks and re-checks the scope hash.

A default deployment should run a dry run, compare its counts, and then run
repeated apply passes. The reconciler does not schedule itself and does not
replace the retention `dispose` action: deliberate disposition still deletes
bytes through the retention service, and reconciliation only cleans residual
objects.

## Not claimed

- No production or staging deployment occurred.
- No real object-storage bucket, scanner service or OCR engine was provisioned
  or called.
- No credential was created or rotated.
- The reference scanner remains a test adapter; production readiness reports
  configuration, not a live scanner verdict.
- Alert routing, dashboard provisioning and on-call ownership remain
  deployment-owner responsibilities.
- Storage reconciliation is not scheduled, no production bucket or object root
  was reconciled, and no operator actor identity was provisioned. Local and
  live PostgreSQL tests only.
- Metrics are exported only from the in-process registry. No Prometheus server,
  collector, remote-write endpoint or scrape target was configured in any
  environment, and distributed tracing is not implemented or claimed.

These are explicit external gates, not implementation gaps.
