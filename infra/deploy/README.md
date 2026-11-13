# Deployment template — NOT applied by Agent 3.

This directory contains configuration and a manifest **template**. Nothing in
this directory has been applied to a cluster, cloud account, DNS, billing system
or production environment. Replace every `REPLACE_*` value and inject secrets
from the deployment secret manager; never commit real credentials.

## Required environment

Copy variable names from [`production.env.example`](production.env.example).
`construction_pm.production_readiness.validate_environment` fails startup
validation when a mandatory production dependency is missing:

| Component | Required production setting |
| --- | --- |
| Database | `CONSTRUCTION_PM_DATABASE_URL` with a PostgreSQL URL |
| Object storage | `CONSTRUCTION_PM_DOCUMENT_STORAGE=s3` plus complete S3 settings |
| Malware scanner | `CONSTRUCTION_PM_SCANNER=external` and an HTTPS endpoint; strict scanned content |
| Job queue | `CONSTRUCTION_PM_JOB_QUEUE=durable` |
| Retention | `CONSTRUCTION_PM_RETENTION=enabled` |
| Observability | `CONSTRUCTION_PM_LOG_FORMAT=json` |
| OCR | Optional; `CONSTRUCTION_PM_OCR=disabled` is valid |

The reference scanner and local document storage are development/test adapters
and are rejected in production configuration. The production composition must
also supply real readiness probes for database, scanner and object storage; a
required component without a probe reports `PROBE_NOT_CONFIGURED`.

## Probes

- Liveness: `GET /api/health/live` — process is serving.
- Readiness: `GET /api/health/ready` — `200` for `ready` or `degraded`, `503`
  for `not_ready`. `degraded` means only optional components are unavailable.

The readiness response contains component names, requirements, healthy/
unhealthy states and stable detail codes. It does not contain endpoints,
buckets, credentials, DSNs or exception text.

## Staging smoke test

Run from the candidate environment after starting staging:

```bash
PYTHONPATH=src python scripts/staging_smoke.py \
  --base-url https://REPLACE_STAGING_HOST \
  --require-component configuration \
  --require-component database
```

The smoke test issues only `GET` requests to the two health paths. Exit code
`0` means both probes passed, `1` means a probe failed, `2` means the target URL
was invalid. Do not run it against production unless the owner explicitly
authorizes it.

## Manifest

[`deployment.template.yaml`](deployment.template.yaml) is a generic container
manifest template with the health probes wired. It has no image, secret,
namespace, ingress or cloud-provider values and must be adapted by the
deployment owner. It is not a deployment record.
