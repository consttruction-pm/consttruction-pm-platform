# P6 Document Storage Contract

Status: implemented on `agent3/document-storage-hardening-2026-11` (Issue #1799 Workstream 4). This document describes the HTTP/application contract, the byte-storage port, the malware-scanning boundary and the production configuration rules. It is not a deployment record.

## Content versions

Every successful upload creates one append-only `DocumentContentVersion`. The row records the document revision it belonged to, digest, type, size, original filename, uploader, timestamp, idempotency key and the scan verdict:

```json
{
  "document_id": "DOC-1",
  "version": 1,
  "document_revision": 2,
  "content_hash": "sha256:...",
  "content_type": "application/pdf",
  "byte_size": 1234,
  "original_filename": "drawing.pdf",
  "uploaded_at": "2026-11-12T12:30:00+00:00",
  "uploaded_by": "u1",
  "scan": {
    "status": "clean",
    "engine": "reference",
    "engine_version": "1",
    "detail": ""
  }
}
```

`scan.status` is one of `clean`, `infected`, `failed`, `unscanned`. Rows written before scan metadata existed deserialize as `unscanned` with empty engine fields, so no migration or table rebuild is required. An `infected` version is never persisted because the scanner runs before `put`; the status value exists for contract completeness and future retained evidence.

Uploads remain idempotent per `(tenant, project, document, idempotency_key)`. Replaying the same bytes returns the original version and verdict without writing a second object; reusing the key for different bytes is `409 DOCUMENT_CONTENT_IDEMPOTENCY_KEY_REUSE`.

## Byte storage port

`DocumentBinaryStorage` has three operations:

- `put(tenant_id, project_id, content_hash, extension, data) -> storage_ref`
- `read(storage_ref, tenant_id, project_id, expected_content_hash) -> bytes`
- `delete(storage_ref, tenant_id, project_id) -> None`

The application validates the payload before calling the port: allow-listed declared MIME type, magic-byte agreement, non-empty size, configured maximum and a server-derived SHA-256. Adapters must re-check the digest and enforce the same size limit.

Object keys are derived only from server values:

```
{scope(tenant)}/{scope(project)}/{digest[0:2]}/{digest}{extension}
scope(value) = first 16 hex chars of SHA-256(value)
```

Local references are `local:v1/{key}`. S3-compatible references are `s3:v1/{key}`. Both resolvers reject malformed references and any reference whose tenant/project scope hash does not match the caller before touching bytes. The digest embedded in a reference is checked against `expected_content_hash`.

## Malware scanning and quarantine

`DocumentScanner.scan(data, content_type=...) -> ScanVerdict` is the only scanning boundary. `ScanVerdict.validate()` requires a known status, a non-empty engine name and version, and string detail. The deterministic `ReferenceDocumentScanner` is a test/development adapter: it recognises only the public EICAR marker and reports engine `reference` version `1`. It is not an antivirus and must not be presented as one.

`DocumentApplicationService` accepts `scanner` and `require_scanned_content`. The behavior matrix is:

| Condition | `require_scanned_content=True` | `require_scanned_content=False` |
| --- | --- | --- |
| verdict `clean` | store and serve | store and serve |
| verdict `infected` | reject `DOCUMENT_CONTENT_INFECTED`; no object write | same |
| verdict `failed` | reject `503 DOCUMENT_SCAN_FAILED`; no object write | store as `failed`; not served as clean |
| verdict `unscanned` | reject `503 DOCUMENT_SCAN_UNAVAILABLE`; no object write | store as `unscanned` |
| scanner raises | reject `503 DOCUMENT_SCAN_UNAVAILABLE`; no object write | store as `failed` with engine `unavailable` |
| no scanner configured | reject `503 DOCUMENT_SCAN_UNAVAILABLE` | store as `unscanned` |

With `require_scanned_content=True`, downloads are quarantine-first:

- only a selected version whose `scan_status == "clean"` may be read;
- any other version returns `409 DOCUMENT_CONTENT_QUARANTINED` and no bytes;
- legacy metadata-only `storage_ref` download paths are refused, because they carry no verdict.

The preview runtime composes `ReferenceDocumentScanner` with `require_scanned_content=True`. Production composition must inject the real engine adapter and keep strict mode enabled. A real engine adapter, its credentials/licence and any quarantine review workflow are external dependencies and are not claimed here.

### HTTP outcomes

| Case | Status | Code |
| --- | --- | --- |
| infected upload | 409 | `DOCUMENT_CONTENT_INFECTED` |
| scan failed / scanner unavailable in strict mode | 503 | `DOCUMENT_SCAN_FAILED` / `DOCUMENT_SCAN_UNAVAILABLE` |
| download of a non-clean version | 409 | `DOCUMENT_CONTENT_QUARANTINED` |
| type/size/hash validation | 415 / 413 / 409 | existing document content codes |

## Local adapter

`LocalDocumentStorage(root)` writes atomically to the content-addressed path, refuses to overwrite different bytes, verifies the digest and scope on read, maps missing files to `DOCUMENT_CONTENT_NOT_FOUND` and modified files to `DOCUMENT_CONTENT_INTEGRITY_FAILED`. It is the development/test adapter and is forbidden in production configuration.

## S3-compatible adapter

`S3CompatibleDocumentStorage` signs requests with SigV4 over stdlib `urllib`; no vendor SDK is required. Supported settings:

| Environment variable | Meaning |
| --- | --- |
| `CONSTRUCTION_PM_DOCUMENT_STORAGE` | `local` or `s3` |
| `CONSTRUCTION_PM_S3_ENDPOINT_URL` | `http(s)` endpoint, no query/fragment |
| `CONSTRUCTION_PM_S3_BUCKET` | DNS-safe bucket name |
| `CONSTRUCTION_PM_S3_REGION` | SigV4 region |
| `CONSTRUCTION_PM_S3_ACCESS_KEY` / `..._SECRET_KEY` | credentials |
| `CONSTRUCTION_PM_S3_PREFIX` | object prefix, default `documents`; empty or `..` segments rejected |
| `CONSTRUCTION_PM_S3_PATH_STYLE` | `true` (default) or `false` |
| `CONSTRUCTION_PM_S3_SSE` | optional `AES256` or `aws:kms` |
| `CONSTRUCTION_PM_S3_SESSION_TOKEN` | optional temporary-credential token |

Behavior: path-style or virtual-host URLs, `x-amz-content-sha256` on every request, optional SSE on `PUT`, TLS via the endpoint scheme. `404` maps to `DOCUMENT_CONTENT_NOT_FOUND`; any other HTTP status or transport error maps to `DOCUMENT_STORAGE_OBJECT_UNAVAILABLE` (`503` at the HTTP boundary). `DELETE` of a missing object is idempotent.

`build_document_storage_from_environment(...)` is the only configuration entry point:

- outside production, an unset kind defaults to local;
- production with no kind fails `DOCUMENT_STORAGE_CONFIGURATION_REQUIRED`;
- production with `local` fails `DOCUMENT_STORAGE_LOCAL_FORBIDDEN_IN_PRODUCTION`;
- production with `s3` requires the full S3 settings; missing variable errors list variable names only and never values.

Production detection uses `CONSTRUCTION_PM_ENVIRONMENT=production|prod` unless the caller passes `production=` explicitly.

## Out of scope

- OCR and text extraction queues/status; no OCR engine is embedded.
- Retention/deletion lifecycle (legal hold, purge jobs, object garbage collection).
- Real antivirus engine integration, engine credentials/licence, quarantine review UI.
- A production scanner service being deployed, bucket provisioning or lifecycle policy.
- Web/Visual Workspace document UI changes (Agent 1 ownership).
