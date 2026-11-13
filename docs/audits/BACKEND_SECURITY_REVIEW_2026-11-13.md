# Backend security review — Issue #1799 Workstream D

**Commit reviewed:** `392326b` (merged `main`)
**Date:** 2026-11-13
**Scope:** Agent 3 backend surface — HTTP operational layer and route authorization,
document storage/object storage/content repository/retention, storage
reconciliation, exchange import, report and tracking persistence, AI action
boundary, metrics export.

## Independence statement

Two isolated reviewer agents were dispatched with read-only, evidence-based
instructions and no access to this coordinator's conclusions:

1. A full-surface reviewer (20 findings maximum, no file changes).
2. A bounded reviewer restricted to ten named files and twelve findings.

Neither returned a findings register within the bounded review window. **No
independent review result exists for this commit.** The register below is
therefore a coordinator review, and it must not be described as independent.
CI success is not independent review. The independent-review gate remains
**OPEN**; see "Open gates".

## Threat model

| Element | Description |
| --- | --- |
| Assets | Tenant documents and extracted text, report definitions/runs, schedule data, exchange payloads, session identifiers, S3 credentials and session tokens, AI action grants, audit records |
| Actors | Browser user with a session cookie; deployment operator; external scanner; S3-compatible endpoint; AI assistant provider; unauthenticated network client |
| Trust boundaries | Browser → WSGI adapter; route layer → application services; application → SQL; application → local/S3 object storage; application → scanner; application → AI provider; operator environment → configuration |
| Assumptions | The deployment terminates TLS, the session store is server-side, and the S3/scanner endpoints are operator-controlled and reached over HTTPS in production |

Threats and primary controls:

| Threat | Primary control | Evidence |
| --- | --- | --- |
| Cross-tenant read via path identifiers | Opaque server-side session; every project route calls `authorize_project`; cross-scope checks reject mismatched tenant/project | `http/project_lifecycle_routes.py` session gate and `CROSS_SCOPE_ACCESS` branches |
| Cross-tenant object access | Scope hash must equal the metadata tenant/project; S3 keys derived from validated scope; reconciliation re-checks scope | `document_storage.py`, `document_object_storage.py`, `document_storage_reconciliation.py` |
| Path traversal / symlink escape | Content-addressed names validated against hex shape; `realpath` containment; symlink rejection; `O_NOFOLLOW` reads | `document_storage.py`, `document_storage_reconciliation.py` |
| SQL injection | Bound parameters in stores; only internal literal DDL uses interpolation | `document_*`, `report_*`, `exchange_*` stores; `report_persistence.py:_ensure_column` fixed literals |
| SSRF via external services | Scanner refuses redirects and enforces a timeout; S3 client now refuses redirects; production validation requires HTTPS | `document_scan_http.py`, `document_object_storage.py`, `production_readiness.py` |
| Upload/import resource exhaustion | WSGI body limits; XLSX uncompressed-size, macro and row bounds; 64 MiB scanner payload cap | `http/wsgi.py`, `exchange_application.py:_decode_xlsx`, `document_scan_http.py` |
| Secret leakage in logs/errors | Static error codes; key-based redaction; correlation ids only; token never echoed | `production_readiness.py`, `metrics_export.py`, `http/operational.py` |
| Scrape endpoint abuse | Disabled by default; constant-time bearer check; bounded bytes/series; no request instrumentation | `metrics_export.py`, `http/operational.py` |
| AI action confused deputy | Default-deny adapter; trusted `subject_id` from the session, never proposal data | `ai_action_boundary.py`, `http/project_lifecycle_routes.py` |

## Findings register

| ID | Severity | Title | Status |
| --- | --- | --- | --- |
| SEC-001 | High | S3 client followed redirects and re-sent signed credentials | Fixed |
| SEC-002 | Medium | Unbounded S3 listing loop on a repeated continuation token | Fixed |
| SEC-003 | Low | `MAX_SERIES` accepted but not enforced at export | Fixed |
| SEC-004 | Low | `CONSTRUCTION_PM_OTEL_ENDPOINT` implied working tracing | Fixed in `ab0f84f` |
| SEC-005 | Info | Internal DDL helper interpolates table names | Accepted (literals only) |

### SEC-001 — S3 client followed redirects and re-sent signed credentials

- **Evidence:** `document_object_storage.py` used `urlopen(request, ...)`, whose
  default opener follows 301/302/303/307/308. A redirect response would be
  re-issued to the new URL with `Authorization`, `x-amz-security-token` and
  `x-amz-date` headers intact.
- **Impact:** A compromised or misconfigured S3-compatible endpoint (or a
  plain-HTTP endpoint outside production) could redirect the client to an
  internal address or attacker host and receive the signed request, including
  a session token. This is SSRF plus credential forwarding.
- **Fix:** `_RejectRedirects` raises `HTTPError` for every redirect and
  `_NO_REDIRECT_OPENER` is used for all object-storage requests. A redirect now
  surfaces as `DocumentStorageError("DOCUMENT_STORAGE_OBJECT_UNAVAILABLE:<code>")`.
- **Negative test:** `test_s3_refuses_redirects_instead_of_forwarding_signed_request`
  asserts the redirect target receives zero requests and the client raises.

### SEC-002 — Unbounded S3 listing loop on a repeated continuation token

- **Evidence:** `S3CompatibleDocumentStorage.list_objects` looped while
  `truncated` and a token were returned, without detecting a repeated token or
  bounding page count.
- **Impact:** A misbehaving endpoint could pin a worker and cause unbounded
  network requests and memory growth during reconciliation.
- **Fix:** page count is capped by `MAX_INVENTORY_PAGES` (10,000) and a repeated
  continuation token raises `DOCUMENT_STORAGE_INVENTORY_INVALID`.
- **Negative test:** `test_s3_listing_rejects_repeated_continuation_token` asserts
  two requests at most and the stable error.

### SEC-003 — `MAX_SERIES` accepted but not enforced at export

- **Evidence:** `MetricsExportSettings.max_series` was parsed and documented but
  `MetricsExportService.scrape` never consulted it; only the byte cap applied.
- **Impact:** A custom or unexpectedly large registry could produce a very large
  exposition within the byte cap, and the documented bound was not true.
- **Fix:** the scrape counts counter and observation series and returns
  `503 METRICS_EXPORT_SERIES_LIMIT_EXCEEDED` when the configured limit is
  exceeded, before rendering.
- **Negative test:** `test_scrape_fails_closed_when_series_limit_is_exceeded`.

### SEC-004 — OTEL endpoint implied working tracing

- **Evidence:** `CONSTRUCTION_PM_OTEL_ENDPOINT` was validated as an optional URL
  while no span exporter, collector, sampling or propagation exists.
- **Impact:** An operator could believe traces were delivered; this is an
  honesty and incident-response risk rather than an exploit.
- **Fix:** setting the variable now yields `OTEL_ENDPOINT_NOT_IMPLEMENTED`; docs
  and the production template mark it reserved. See `ab0f84f`.

### SEC-005 — Internal DDL helper interpolates table names

- **Evidence:** `report_persistence.py:_ensure_column` builds
  `PRAGMA table_info({table})` and `ALTER TABLE {table} ...`.
- **Assessment:** all call sites pass literal table and column names defined in
  the same module; no request value reaches the helper. Recorded as accepted
  risk with a rule to keep call sites literal.

## Examined with no finding

- Session validation is server-side and opaque; project routes authorize before
  dispatch, and cross-scope branches return `403 CROSS_SCOPE_ACCESS`.
- AI action decisions use `session.user_id` as the trusted subject; proposal
  `requested_by` is explicitly not authoritative.
- Scanner client refuses redirects, validates the endpoint, enforces a bounded
  timeout and caps the response payload.
- XLSX import refuses macro projects, caps uncompressed size and row count, and
  rejects malformed archives before workbook load.
- Local object storage validates content-addressed shape, rejects symlinks, uses
  `realpath` containment and `O_NOFOLLOW`, and re-checks scope before deletion.
- Reconciliation safety gates (metadata-first abort, dry-run default,
  two-observation minimum, grace period, conditional lease claim, retention and
  legal-hold protection, append-only audit) match the implementation.
- Metrics scrape uses `hmac.compare_digest`, returns static error codes, and
  never logs the token or request headers.
- Structured logging redacts token, authorization, cookie, credential, payload
  and content keys and logs the path without a query string.

## Open gates

- **Independent review (blocking for the Workstream D claim).** No independent
  reviewer produced a findings register. Re-run this review with a fresh,
  time-bounded reviewer and append its register before claiming independent
  review.
- **Runtime testing.** This is static review only; no DAST, fuzzing, dependency
  CVE scan or penetration test was performed.
- **Production configuration.** No production session store, proxy, TLS terminator,
  S3 bucket or scanner endpoint was inspected.
- **Deployment authentication.** The WSGI adapter assumes a deployment-owned
  authentication/session front end. The in-process route layer enforces session
  and project authorization, but reverse-proxy trust boundaries were not
  reviewed.

## Verdict

No open Critical or High finding remains in the reviewed Agent 3 surface after
SEC-001. The independent-review gate is **OPEN** and must be recorded as such in
the project state ledger.
