# P6 Backend Security Hardening Audit

Status: focused audit implemented on `agent3/security-hardening-2026-11` (Issue #1799 Workstream 6). This records code review, negative tests and residual risk. It is **not** an independent security review: no separate human or agent reviewer completed one for this slice, and the Codex review quota was previously exhausted.

## Reviewed scope

Document upload/download and storage adapters, exchange CSV/XLSX/XML import and export, report export, Tracking read, durable job execution and shared HTTP routes. UI code and the knowledge/assistant pipeline are out of scope (owned by other agents).

## Controls and evidence

| Boundary | Control | Evidence |
| --- | --- | --- |
| Tenant/project isolation | repositories key every query by `tenant_id` and `project_id`; routes derive both from the authorized session, never the payload | document/retention/OCR live and unit tests; cross-scope assertions |
| Actor identity | `actor_id` must equal the session user; payload-supplied actors rejected | document application/retention tests |
| Optimistic locking | document revision and retention revision guarded in `UPDATE ... WHERE`; stale writes return 409 | document and retention tests, live parity tests |
| Idempotent replay | document/exchange/sync keys are unique; same key + same payload returns stored result, different payload returns 409 | document, exchange and sync live tests |
| Path traversal/symlink | storage refs derived from server-side scope and SHA-256; local adapter uses normalized resolved paths and `O_NOFOLLOW` | `test_document_binary_storage.py` |
| MIME spoofing | allow-listed content types plus magic-byte sniffing; extension allow-list for object keys | `test_document_scan_and_object_storage.py` |
| Upload size | 25 MB document limit and per-route WSGI body limits | document HTTP tests, `http/wsgi.py` |
| Malware | quarantine-first scan contract; strict mode serves only `clean`; infected payloads never reach storage | scan and OCR tests |
| Filename/header injection | basename-only printable sanitization; RFC 6266 quoted fallback; no CR/LF reaches `Content-Disposition` | `test_security_hardening.py` |
| CSV injection | exported cells beginning `= + - @ TAB CR` are prefixed | report and exchange export tests |
| XML external entities | codecs reject any payload containing `<!DOCTYPE` or `<!ENTITY` before parsing; payload size bounded | `test_security_hardening.py` |
| XLSX archive bombs | macros (`vbaProject.bin`) rejected; total uncompressed size bounded; row iteration capped; links not kept | `test_security_hardening.py` |
| Request body floods | WSGI rejects invalid and oversized `Content-Length` and reads at most `limit + 1` | `http/wsgi.py` |
| Secrets/content logging | the reviewed backend modules do not log payloads, tokens or personal data | code search of HTTP/exchange/document boundaries |

## Changes in this slice

- `P6PrimaveraXmlCodec` and `P6MsProjectXmlCodec` now reject DTD/entity declarations (`XML_DECLARATION_REJECTED`) and payloads above 10 MB (`XML_PAYLOAD_TOO_LARGE`) before `ElementTree` parses them.
- XLSX import inspects the archive first: macro projects are rejected (`EXCHANGE_XLSX_MACROS_REJECTED`), uncompressed size is capped at 50 MB (`EXCHANGE_XLSX_TOO_LARGE`), openpyxl runs in read-only mode without links, and rows are capped at 50,000 (`EXCHANGE_XLSX_TOO_MANY_ROWS`). Normal bounded workbooks still decode.
- Negative tests cover XXE, billion-laughs style entity declarations, both size bounds, macro injection, the row bound, header injection and filename normalization.

## Residual risk and external gates

- **Independent review not performed.** CI success is not a security review. A separate reviewer must inspect the Workstream 2/4 changes before a production security sign-off.
- No production antivirus or OCR engine is configured; the reference scanner and decoder are deterministic test adapters.
- No production object storage credentials or bucket policy are exercised; the S3 adapter is contract-tested locally.
- The preview runtime uses SQLite and a local object directory. Deployment transport security, cookie flags, CSRF policy, rate limiting and WAF behavior belong to the production-readiness slice and are not claimed here.
- PDF export emits static rendered content only; no user-supplied active content is embedded, but no dedicated PDF sanitizer is claimed.
