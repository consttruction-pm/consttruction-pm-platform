# P6 Document OCR Contract

Status: implemented on `agent3/document-ocr-2026-11` (Issue #1799 Workstream 4). This is the durable extraction queue, not a promise that an OCR engine is deployed. The reference engine only decodes already-textual payloads.

## Queue model

A successful upload of a **clean** content version enqueues one `project_document_ocr` row when `DocumentApplicationService.ocr_store` is configured. The queue is keyed by `(tenant_id, project_id, document_id, version)`, so re-requesting the same version is idempotent and never starts duplicate work.

Each row snapshots the immutable content facts (`storage_ref`, `content_hash`, `content_type`, `byte_size`, `original_filename`), so a worker never has to re-read mutable document metadata. Status values are `pending`, `running`, `succeeded`, `failed`, `skipped`.

| Field | Meaning |
| --- | --- |
| `status` | queue lifecycle |
| `attempts` / `max_attempts` | durable retry accounting |
| `next_attempt_at` | earliest next claim (UTC) |
| `claim_token` / `claimed_until` / `claimed_by` | lease owned by one worker |
| `text` / `char_count` | extracted text when `succeeded` |
| `engine` / `engine_version` | extraction identity |
| `detail` | unsupported reason or bounded failure code |

## Claim, lease and completion

`DocumentOcrRunner.run_due(now, worker_id, limit)` claims due rows with a random token and a 300-second lease. A second worker cannot claim a live lease. A crashed worker's lease can be reclaimed after expiry, and the stale token can no longer complete, skip or fail the job (`DOCUMENT_OCR_CLAIM_LOST`). There is no in-process timer: a deployment invokes `run_due` from its external scheduler, exactly like durable report schedules.

On success the row stores text, character count and engine identity. A failure increments `attempts` and schedules exponential backoff (5 minutes, doubling, capped at 60 minutes) until `max_attempts`; then the status becomes terminal `failed`. `retry` accepts only `failed` or `skipped`, resets attempts and moves the job back to `pending`; any other status returns `409 DOCUMENT_OCR_NOT_RETRYABLE`.

## Engine boundary

`DocumentOcrEngine.extract(data, content_type=...) -> OcrExtraction` is the only extraction port. `ReferenceDocumentOcrEngine`:

- decodes `text/plain`, `text/csv`, `application/xml` and `text/xml` as UTF-8 (invalid bytes replaced);
- raises `OcrUnsupported` for PDF, office and image payloads, which the runner records as `skipped`;
- performs no network call and is not an OCR engine.

A real engine adapter, its credentials/licence, language packs, page/layout metadata and confidence scores are external dependencies. No extracted text is claimed to be accurate for scanned documents until such an adapter exists.

The text limit (`DEFAULT_OCR_MAX_CHARS`, 200,000 by default) is enforced after extraction. Larger output fails the job rather than silently truncating evidence.

## Authorization and quarantine

Queueing needs project-write; reading status/history needs project-read; the actor must match the session. The service refuses to queue a version whose scan verdict is not `clean` (`409 DOCUMENT_CONTENT_QUARANTINED`), so quarantined bytes never reach an extraction engine. Uploading with `require_scanned_content=True` and a scanner that produces `clean` is the normal path.

The upload and the queue insert share one transaction. A deployment that does not configure `ocr_store` keeps the previous upload behavior; no OCR row is created.

## HTTP

| Method and path | Meaning |
| --- | --- |
| `POST /api/projects/{p}/documents/{id}/content/{version}/ocr` | enqueue (idempotent), `202` |
| `GET /api/projects/{p}/documents/{id}/content/{version}/ocr` | status/result, `200` |
| `GET /api/projects/{p}/documents/{id}/ocr` | all queued versions, `200` |
| `POST /api/projects/{p}/documents/{id}/content/{version}/ocr/retry` | requeue failed/skipped, `202` |

Missing job/version → `404 DOCUMENT_OCR_NOT_FOUND`; retry of a non-terminal job → `409 DOCUMENT_OCR_NOT_RETRYABLE`; missing service → `503 DOCUMENT_OCR_UNAVAILABLE`; auth failures → `403`.

## Storage and parity

`SQLiteDocumentOcrRepository` and `PostgresDocumentOcrRepository` share the same SQL and row serializer, differing only in the placeholder. `initialize()` is additive (`CREATE TABLE IF NOT EXISTS` plus an index), so no existing database is dropped or rebuilt.

## Out of scope

- A real OCR engine, provider credentials, language packs or confidence/layout output.
- Page images, bounding boxes or searchable-PDF generation.
- Embedding extracted text into full-text search (a later integration slice).
- An in-process worker/cron; deployment must trigger `run_due`.
- Web/Visual Workspace OCR progress UI (Agent 1).
