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

Application-level events for uploads, exchange runs, report runs, scheduled
jobs and storage reconciliation should use the same logger and correlation id;
the shared middleware supplies the id through
`environ["construction_pm.correlation_id"]`.

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

## Not claimed

- No production or staging deployment occurred.
- No real object-storage bucket, scanner service or OCR engine was provisioned
  or called.
- No credential was created or rotated.
- The reference scanner remains a test adapter; production readiness reports
  configuration, not a live scanner verdict.
- Alert routing, dashboard provisioning and on-call ownership remain
  deployment-owner responsibilities.

These are explicit external gates, not implementation gaps.
