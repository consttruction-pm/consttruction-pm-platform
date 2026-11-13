# Backend security review — Issue #1799 Workstream D

**Coordinator review commit:** `392326b` (merged `main`)
**Independent review A:** `d56152e` (read-only, full Agent 3 backend surface)
**Independent review B:** `392326b` (read-only, bounded file set, 11 findings)
**Date:** 2026-11-13
**Scope:** Agent 3 backend surface — HTTP operational layer and route authorization,
document storage/object storage/content repository/retention, storage
reconciliation, exchange import, report and tracking persistence, AI action
boundary, metrics export.

## Independence statement

Two isolated reviewer agents were dispatched with read-only, evidence-based
instructions and no access to this coordinator's conclusions:

1. Reviewer A — full Agent 3 backend surface, threat-model plus findings register.
2. Reviewer B — bounded set of named files, twelve findings maximum.

Both registers were delivered after the coordinator register below was first
written, and both are recorded here verbatim in substance. They are independent
of this coordinator: neither reviewer saw the coordinator findings, and each
reviewer's own findings were reconciled against the other's afterwards.
Reviewer B separately re-tested the coordinator's S3-redirect hypothesis and
confirmed the merged client now refuses redirects.

Neither review is a substitute for runtime testing: both were static, read-only
reviews with no DAST, fuzzing, dependency CVE scan or penetration test.

## Review identifier mapping

| Register ID | Reviewer A | Reviewer B |
| --- | --- | --- |
| SEC-001 | corrected: redirect handling now refuses | F-01 (High) |
| SEC-002 | — | F-06 |
| SEC-003 | — | — |
| SEC-004 | — | — |
| SEC-005 | — | — |
| SEC-006 | SEC-001 (High) | — |
| SEC-007 | SEC-002 | — |
| SEC-008 | SEC-003 | F-05 |
| SEC-009 | SEC-004 | — |
| SEC-010 | SEC-005 | — |
| SEC-011 | SEC-006 | F-01 (scheme half) |
| SEC-012 | — | F-02 |
| SEC-013 | — | F-03 |
| SEC-014 | — | F-04 |
| SEC-015 | — | F-07 |
| SEC-016 | SEC-007 | — |
| SEC-017 | SEC-008 | F-08 |
| SEC-018 | SEC-009 | — |
| SEC-019 | SEC-010 | — |
| SEC-020 | SEC-011 | — |
| SEC-021 | SEC-012 | — |
| SEC-022 | SEC-013 | — |
| SEC-023 | — | F-09 |
| SEC-024 | — | F-10 |
| SEC-025 | — | F-11 |

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
| SSRF via external services | Scanner refuses redirects and enforces a timeout; S3 client refuses redirects; production validation requires HTTPS for scanner/OCR/provider | `document_scan_http.py`, `document_object_storage.py`, `production_readiness.py` |
| Upload/import resource exhaustion | WSGI body limits; XLSX declared-size, macro and row bounds; 64 MiB scanner payload cap | `http/wsgi.py`, `exchange_application.py:_decode_xlsx`, `document_scan_http.py` |
| Destructive retention/reconciliation | Metadata-first abort, dry-run default, two-observation minimum, conditional lease, legal-hold protection, live-reference counting before deletion | `document_retention.py`, `document_storage_reconciliation.py` |
| Secret leakage in logs/errors | Static error codes at most boundaries; key-based redaction; correlation ids only; token never echoed | `production_readiness.py`, `metrics_export.py`, `http/operational.py` |
| Scrape endpoint abuse | Disabled by default; constant-time bearer check; bounded bytes/series; no request instrumentation | `metrics_export.py`, `http/operational.py` |
| AI action confused deputy | Default-deny adapter; trusted `subject_id` from the session, never proposal data | `ai_action_boundary.py`, `http/project_lifecycle_routes.py` |

## Findings register

| ID | Severity | Title | Status |
| --- | --- | --- | --- |
| SEC-001 | High | S3 client followed redirects and re-sent signed credentials | Fixed `07d3c5e` |
| SEC-002 | Medium | Unbounded S3 listing loop on a repeated continuation token | Fixed `07d3c5e` |
| SEC-003 | Low | `MAX_SERIES` accepted but not enforced at export | Fixed `07d3c5e` |
| SEC-004 | Low | `CONSTRUCTION_PM_OTEL_ENDPOINT` implied working tracing | Fixed `ab0f84f` |
| SEC-005 | Info | Internal DDL helper interpolates table names | Accepted (literals only) |
| SEC-006 | High | Retention disposal deleted a shared content-addressed object | Fixed `cdc9999` |
| SEC-007 | Medium | Legal-hold changes and disposition need only `PROJECT_WRITE` | Fixed `d2aa3419` |
| SEC-008 | Medium | XLSX decompression bound trusts attacker-declared archive sizes | Fixed `8581697` |
| SEC-009 | Medium | Formula parser recursion is unbounded and escapes all handlers | Fixed `8581697` |
| SEC-010 | Medium | Unscoped, unlimited metadata loads (`list_all`, document list) | Open |
| SEC-011 | Medium | S3 endpoint may be cleartext HTTP; readiness does not apply its HTTPS rule | Fixed `8581697` |
| SEC-012 | Medium | Client-supplied `storage_ref` bypasses version-scoped disposal | Fixed `afb18263` |
| SEC-013 | Medium | Reconciliation treats document-record-only references as orphans | Fixed `c921ac8b` |
| SEC-014 | Medium | Delete completion is not bound to the claim token | Fixed `8581697` |
| SEC-015 | Medium | `GET /api/session` reflects the session credential | Fixed `67dd5ed` |
| SEC-016 | Low | Document-list `search` is unescaped and length-unbounded in `LIKE` | Fixed `2b2873b3` |
| SEC-017 | Low | Internal exception text reflected as the response `code` | Open |
| SEC-018 | Low | `error_dto` catch-alls turn unexpected faults into client 4xx codes | Open |
| SEC-019 | Low | AI action propose/approve/execute can be one subject | Fixed `9c362d15` |
| SEC-020 | Low | Knowledge ingestion follows redirects (operator CLI only) | Fixed `c55b6535` |
| SEC-021 | Low | `/api/metrics` auth failures are unlogged and unmetered; token policy is length-only | Fixed `8581697` |
| SEC-022 | Low | Composition reads `CUBI_AI_ENABLED` from `os.environ`, ignoring its config mapping | Fixed `8581697` |
| SEC-023 | Low | Anonymous readiness probe returns per-component detail | Fixed `9dbe8e17` |
| SEC-024 | Low | WSGI short-read body is accepted as complete | Fixed `8581697` |
| SEC-025 | Info | `ReferenceAIToolPermissionAdapter` authorizes on tool name only (unused) | Fixed `3754a0af` |

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
- **Reviewer B** independently proposed the same defect from committed line
  numbers and confirmed after `07d3c5e` that the client refuses redirects; the
  remaining cleartext-scheme half is tracked as SEC-011.

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

### SEC-006 — Retention disposal deleted a shared content-addressed object (High)

- **Evidence:** `DocumentRetentionService.dispose` called
  `storage.delete(content.storage_ref, ...)` for one `(document_id, version)`
  without checking sibling references. Object paths are digest-derived per
  project (`document_storage.py:document_object_parts`), so identical bytes
  share one object. Reconciliation already carries the correct predicate
  (`live = [reference for reference in referencing if not reference.disposed]`),
  but the disposition path did not. `tests/test_document_retention.py` had no
  shared-object case.
- **Impact:** Any project writer disposing one matured version irreversibly
  destroyed bytes still served by other live documents/versions in the same
  project — cross-document data loss and permanent download failure for
  content the system still reports as present.
- **Fix:** before deleting, `_shared_storage_reference` snapshots
  `content_repository.list_all(tenant_id, project_id)` and
  `retention_store.list_all_dispositions(tenant_id, project_id)` and returns
  true when any other version with the same `storage_ref` has no disposition.
  The disposition is recorded in all cases; bytes are removed only when this
  disposition is the last live reference. A snapshot failure raises
  `DocumentRetentionReferenceCheckFailed` (`500
  DOCUMENT_RETENTION_REFERENCE_CHECK_FAILED`) and deletes nothing — fail
  closed, retryable, no partial write.
- **Residual risk:** a concurrent upload of identical bytes that commits
  metadata between the reference snapshot and the delete can still race; that
  window is bounded by the operation, and a live reference with missing bytes
  is reported by reconciliation as `metadata_only`. Eliminating it requires a
  cross-store lease, which is out of scope for this fix.
- **Negative tests:**
  - `test_dispose_preserves_bytes_shared_with_a_live_sibling` uploads
    identical bytes to two documents, disposes one, and asserts the object is
    still readable and downloadable for the sibling; disposing the last live
    reference then removes it.
  - `test_dispose_refuses_to_guess_when_reference_metadata_is_unreadable`
    injects a failing snapshot and asserts the bytes survive and no disposition
    row is written.
  - `test_dispose_keeps_bytes_shared_with_a_live_sibling_live` (PostgreSQL,
    live server) proves the same reference-counting on the PostgreSQL adapters.

### SEC-007 — Legal-hold changes and disposition need only `PROJECT_WRITE` (Medium)

- **Resolution:** `set_policy` now requires `PROJECT_ADMIN` when a legal hold is
  placed, lifted or modified while active; `dispose` requires `PROJECT_ADMIN`
  unconditionally. Ordinary retention-window changes keep `PROJECT_WRITE`.
  Covered by `test_legal_hold_and_disposition_require_project_admin`: a
  planner-only context is denied when placing a hold, lifting a hold and
  disposing, while the project-admin context succeeds and the lift is audited.
- **Evidence:** `document_retention.py` `set_policy` and `dispose` both call
  `_check(..., Permission.PROJECT_WRITE)`; `set_policy` replaces the whole
  policy including `legal_hold`, and `retain_days=0` is valid. The default
  `planner` role holds `PROJECT_WRITE`, while document approval in the same
  aggregate requires `project_admin` (`document_persistence.py`).
- **Impact:** A planner can lift another actor's legal hold and immediately
  destroy matured content; the hold is not an evidentiary control.
- **Recommendation:** require an administrative permission for legal-hold
  changes and irreversible disposition, keeping maturity/reason/actor audit.
- **Negative test:** planner on a held document receives
  `403 DOCUMENT_AUTHORIZATION_REQUIRED` for both operations.

### SEC-008 — XLSX decompression bound trusts attacker-declared archive sizes (Medium)

- **Resolution:** `_assert_xlsx_inflates_within_bound` reads every member
  through the decompressor in 64 KiB chunks and fails closed at
  `MAX_XLSX_UNCOMPRESSED_BYTES`; forged sizes surface as `EXCHANGE_XLSX_INVALID`.
  Covered by `test_xlsx_actual_inflated_bytes_are_counted` and
  `test_xlsx_declared_member_sizes_are_not_trusted`.

- **Evidence:** `exchange_application.py:_decode_xlsx` sums `ZipInfo.file_size`
  from the central directory before parsing; actual inflated bytes are never
  counted. Reviewer A and B independently reported this.
- **Impact:** A small upload can inflate to gigabytes during
  `load_workbook`, exhausting worker memory inside the 50 MiB import route
  limit.
- **Recommendation:** count real inflated bytes per member against
  `MAX_XLSX_UNCOMPRESSED_BYTES` and cap cells per sheet.
- **Negative test:** forged `file_size` totals with a real payload above the cap
  must raise `EXCHANGE_XLSX_TOO_LARGE`.

### SEC-009 — Formula parser recursion is unbounded (Medium)

- **Resolution:** expressions longer than 4096 characters are rejected and
  recursive descent is bounded at 64 nesting levels, both raising
  `FormulaSyntaxError("FORMULA_EXPRESSION_TOO_COMPLEX")`. Covered by
  `test_excessive_nesting_fails_as_a_formula_error_not_recursion`.

- **Evidence:** `p6_formula_engine.parse_formula` tokenizes and recursively
  descends with no expression-length or nesting bound; `RecursionError` is not
  in the form-route handlers, so it becomes a 500. Reviewer A confirmed the
  `RecursionError` empirically.
- **Impact:** An authenticated form designer can drive repeated 500s and CPU
  churn, and malformed input escapes the `FORMULA_INVALID` contract.
- **Recommendation:** cap expression length and nesting depth, raise
  `FormulaError`, and map `RecursionError` in the route to 400.
- **Negative test:** 20,000 nested parentheses raise
  `FORMULA_EXPRESSION_TOO_COMPLEX`, never `RecursionError`.

### SEC-010 — Unscoped, unlimited metadata loads (Medium)

- **Evidence:** `list_all(tenant_id=None, project_id=None)` in both content
  repositories has no `LIMIT` and materialises every row; reconciliation calls
  it unscoped, and `DocumentStore.list` (Postgres/SQLite) is also unbounded.
- **Impact:** Growth-driven memory failure of a reconciliation run and
  arbitrarily large list responses.
- **Recommendation:** require a scope argument or keyset pagination; bound the
  document list route.
- **Negative test:** `list_all()` with no scope raises; `store.list` never
  exceeds the page size.
- **Resolution:** document and content `list_all` now require a tenant
  (`DOCUMENT_SCOPE_REQUIRED`) and fetch at most
  `MAX_REFERENCE_SNAPSHOT_ROWS + 1`, raising
  `DOCUMENT_REFERENCE_SNAPSHOT_TOO_LARGE` so reconciliation fails closed instead
  of truncating its reference set. `DocumentStorageReconciler.reconcile`
  requires a tenant scope (`INVALID_RECONCILIATION_SCOPE`). `DocumentStore.list`
  and the document list route accept `limit` (default 200, max 500) and reject
  invalid values with `INVALID_DOCUMENT_PAGE_LIMIT`. Tests:
  `test_list_is_bounded_to_a_page_and_validates_the_limit`,
  `test_list_all_requires_a_tenant_scope`,
  `test_content_reference_snapshot_requires_a_tenant_and_stays_bounded`,
  `test_unscoped_reconciliation_is_refused`,
  `test_document_list_route_is_bounded_and_validates_the_page_limit`.

### SEC-011 — S3 endpoint may be cleartext HTTP; readiness does not apply its HTTPS rule (Medium)

- **Resolution:** `_validate_storage` now validates
  `CONSTRUCTION_PM_S3_ENDPOINT_URL` with `require_https=True` in production and
  reports `INVALID_DOCUMENT_STORAGE_ENDPOINT`. Covered by
  `test_production_environment_rejects_cleartext_s3_endpoint`; staging still
  warns (`URL_NOT_HTTPS`) rather than failing.

- **Evidence:** `DocumentObjectStorageSettings.validate` accepts `http`, and
  `production_readiness._validate_storage` never applies `_validate_url(...,
  require_https=True)`, unlike scanner, OCR and provider endpoints.
- **Impact:** A deployment can pass production validation while sending SigV4
  credentials, session tokens and document bytes unencrypted.
- **Recommendation:** validate the S3 endpoint with `require_https=True` in
  production and reject `http` unless an explicit insecure opt-out is set.
- **Negative test:** production environment with `http://` S3 endpoint reports
  the HTTPS configuration issue.

### SEC-012 — Client-supplied `storage_ref` bypasses version-scoped disposal (Medium)

- **Evidence:** document create/update accept `storage_ref`/`content_hash` from
  the request with only shape checks; the legacy serve branch in
  `document_application.download_content` returns those bytes without
  consulting dispositions.
- **Impact:** A project writer can bind a document to any object in their own
  project scope, serving bytes that never passed sniff/scan/versioning, and
  content bound this way is unreachable by version-scoped disposal.
- **Recommendation:** mint the reference server-side or resolve and validate it
  through the storage adapter; make the legacy branch consult dispositions.
- **Negative test:** an update carrying a foreign/invalid `storage_ref` is
  rejected and persisted references always equal a server-minted ref.
- **Resolution:** `DocumentApplicationService.create` resolves every
  `local:v1/` reference through the storage adapter in the caller's own
  tenant/project scope and rejects a missing, out-of-scope or digest-mismatched
  object with `DOCUMENT_CONTENT_REFERENCE_UNVERIFIED`. `update` now refuses any
  change to `storage_ref`/`content_hash` with
  `DOCUMENT_CONTENT_REFERENCE_IMMUTABLE`; only `upload_content` (which mints the
  reference from scanned bytes) may change them. The legacy download branch
  consults recorded dispositions before checking the scan policy and refuses a
  disposed document with `DOCUMENT_CONTENT_DISPOSED`. Tests:
  `test_create_rejects_a_legacy_reference_that_does_not_resolve`,
  `test_create_accepts_a_legacy_reference_that_resolves_in_scope`,
  `test_update_cannot_retarget_the_content_reference`,
  `test_legacy_reference_is_never_served_after_a_disposition`. Non-`local:v1`
  placeholders remain inert because the legacy branch never serves them.

### SEC-013 — Reconciliation treats document-record-only references as orphans (Medium)

- **Evidence:** `_metadata_references` builds the reference set only from
  content versions; an object referenced solely by
  `DocumentRecord.storage_ref` therefore classifies as `orphan_object` and is
  deletable in a non-dry-run pass.
- **Impact:** Latent irreversible destruction of bytes still served by the
  legacy branch. No route currently invokes the reconciler, so it is not
  remotely reachable.
- **Recommendation:** include document-level references in the snapshot, or
  treat any ref present in document metadata as non-orphan.
- **Negative test:** non-dry run preserves such an object and writes no cleanup
  audit row.
- **Resolution:** `DocumentStore` gained `list_all(tenant_id=..., project_id=...)`
  (SQLite and PostgreSQL) for scope-wide snapshots; `list` remains the bounded
  route query. `DocumentStorageReconciler` accepts an optional `document_store`,
  snapshots `DocumentRecord.storage_ref`, and classifies a version-less object
  held by a document record as `match` (`document_record_reference`) instead of
  `orphan_object`. Snapshot failures still abort before any listing. Tests:
  `test_document_record_only_reference_is_never_treated_as_an_orphan` (control
  run sees one orphan; the fixed run sees two matches, deletes nothing and
  writes no cleanup row) and `test_document_list_all_respects_scope`.

### SEC-014 — Delete completion is not bound to the claim token (Medium)

- **Resolution:** `claim()` returns `(attempts, claim_token)` and
  `mark_deleted`/`mark_failed` require the matching token with
  `status='deleting'`; `mark_resolved` requires no outstanding lease. A lost
  lease returns `lease_lost` and writes no cleanup audit row. Covered by
  `test_stale_worker_cannot_complete_a_reclaimed_lease` and the live
  PostgreSQL lease test.

- **Evidence:** `claim()` writes `claim_token`, but `mark_deleted`,
  `mark_failed` and `mark_resolved` update by `(tenant, project, object_ref)`
  and status only.
- **Impact:** A stale worker whose lease expired can clear a newer lease and
  stamp an outcome for another worker's deletion.
- **Recommendation:** add `AND claim_token = ?` and treat `rowcount == 0` as a
  lost lease.
- **Negative test:** re-claim with token B, call `mark_deleted` with token A;
  status stays `deleting` and `claim_token` remains B.

### SEC-015 — `GET /api/session` reflects the session credential (Medium)

- **Resolution:** the response carries identity fields only (`user_id`,
  `tenant_id`, `roles`, `expires_at`); the session id stays in the HttpOnly
  cookie. Covered by `test_session_response_never_reflects_the_session_credential`.
  No client code read the removed field.

- **Evidence:** the response body includes `session_id`, the same value stored
  in the HttpOnly `cp_session` cookie.
- **Impact:** Any script, extension or proxy capturing the JSON body obtains a
  bearer credential the cookie flags were chosen to hide.
- **Recommendation:** return identity fields only, or a keyed digest.
- **Negative test:** the body omits `session_id` and never equals the cookie
  value.

### SEC-016 — Document-list `search` is unescaped in `LIKE` (Low)

- **Resolution:** `_escape_like` escapes backslash, `%` and `_`, both the
  Postgres and SQLite queries declare `ESCAPE '\'`, and the term is capped at
  `MAX_DOCUMENT_SEARCH_LENGTH` (200). Covered by
  `test_search_treats_percent_and_underscore_as_literals` and the over-length
  rejection in `test_list_rejects_invalid_filters`; `"%"` and `"_"` now match
  no documents in the fixture.
- **Evidence:** `_validate_document_filters` accepts any non-empty string;
  `%{search}%` is bound without `ESCAPE`.
- **Impact:** Wildcard injection widens matching inside the caller's own
  project and forces non-indexable scans.
- **Recommendation:** escape `%`, `_` and the escape character; cap length.
- **Negative test:** `"%"` does not match every document; a literal `50%`
  matches only titles containing it.

### SEC-017 — Internal exception text reflected as the response `code` (Low)

- **Evidence:** 125 `self._error(<status>, str(exc), ...)` sites, including
  authorization messages that name the required permission and catch-alls that
  reclassify `TypeError`/`KeyError` as 400.
- **Impact:** Permission probing and internal detail disclosure; server defects
  hidden from 5xx alerting.
- **Recommendation:** fixed codes per raise site; log the message only.
- **Negative test:** an internal `KeyError` yields the documented constant and
  no exception text.

### SEC-018 — `error_dto` catch-alls turn unexpected faults into 4xx (Low)

- **Resolution:** the document and report `error_dto` fall-throughs now return
  a fixed `DOCUMENT_INTERNAL_ERROR` / `REPORT_INTERNAL_ERROR` persistence error
  with an empty message instead of `validation_error(type(exc).__name__, str(exc))`.
  Known domain errors keep their existing mappings. Covered by the updated
  `test_document_application` assertion and
  `test_unexpected_report_fault_is_a_server_error_without_internal_text`.
  SEC-017 (per-site reflected codes) remains open; this closes only the two
  catch-all fall-throughs.
- **Evidence:** `document_application.error_dto` and
  `report_application.error_dto` fall through to
  `validation_error(type(exc).__name__, str(exc))`, and `DocumentAPI` wraps
  every call in `except Exception`.
- **Impact:** Adapter/driver failures surface as client errors whose code is an
  internal class name.
- **Recommendation:** a fixed `*_REQUEST_INVALID` / `*_UNAVAILABLE` code plus
  server-side logging.
- **Negative test:** a non-domain store exception yields the constant code.

### SEC-019 — AI action propose/approve/execute can be one subject (Low)

- **Evidence:** approval records `actor_id == subject_id == proposer`;
  `_decide_in_transaction` performs no separation check, unlike the forms
  domain's `allow_self_approval` policy.
- **Impact:** "separate human approval" offers no protection against one
  compromised account.
- **Recommendation:** optional policy refusing self-approval, default deny for
  destructive tools.
- **Negative test:** with the policy on, the proposer's decision raises
  `AI_ACTION_SELF_APPROVAL_FORBIDDEN` and the proposal stays `proposed`.
- **Resolution:** `AIActionApprovalPolicy` adds `allow_self_approval` (default
  `True`) and `require_distinct_approver_for` (tool allow-list for destructive
  actions). `AIActionApprovalService` refuses an approval when the authenticated
  actor equals `proposal.requested_by` under the policy. The policy is threaded
  through `AIActionRuntime` and composed from
  `CUBI_AI_REQUIRE_DISTINCT_APPROVER` in the preview runtime. Tests:
  `test_policy_refuses_self_approval_and_audits_the_denial`,
  `test_policy_can_require_a_distinct_approver_for_listed_tools_only`,
  `test_self_approval_policy_denies_proposer_and_leaves_proposal_proposed`.
  The default is unchanged, so the recommendation's destructive-tool default
  remains an operator decision listed in `require_distinct_approver_for`.

### SEC-020 — Knowledge ingestion follows redirects (Low)

- **Evidence:** `knowledge/ingest.py` uses `urlopen` with default redirect
  handling; the allowlist is checked per call but not per redirect hop. No HTTP
  route exposes ingestion.
- **Impact:** A compromised allow-listed host could pivot the operator CLI fetch
  to another HTTPS target. Not attacker-reachable through the HTTP surface.
- **Recommendation:** reuse the existing redirect-refusing opener.
- **Negative test:** a cross-host redirect yields
  `KNOWLEDGE_FETCH_REDIRECT_REFUSED` with no second request.
- **Resolution:** `UrllibFetcher` now uses an `HTTPRedirectHandler` subclass that
  raises instead of following a redirect; 301/302/303/307/308 map to the static
  code `KNOWLEDGE_FETCH_REDIRECT_REFUSED`. The scheme and host allowlist still
  run before the request. Tests:
  `test_urllib_fetcher_refuses_a_redirect_without_a_second_request` (local
  redirect server, target receives zero requests) and
  `test_urllib_fetcher_maps_a_refused_redirect_to_a_static_code`.

### SEC-021 — `/api/metrics` auth failures are unlogged and unmetered (Low)

- **Resolution:** the 401 path increments an unlabelled
  `metrics_export_unauthorized_total` counter and emits one bounded
  `metrics_export_unauthorized` event without credential material; configuration
  now requires at least eight distinct token characters. Covered by
  `test_metrics_endpoint_meters_and_logs_unauthorized_scrapes` and the weak-token
  cases. No throttling is added here: rate limiting belongs to the deployment
  front end.

- **Evidence:** the metrics path is dispatched before instrumentation, so 401s
  produce no request event or metric; token acceptance is length-only
  (16–512 printable ASCII); no throttle exists.
- **Impact:** Unlimited untraced bearer guessing against the scrape endpoint.
- **Recommendation:** bounded unauthorised counter/event and a stronger token
  policy.
- **Negative test:** repeated bad-token scrapes increment
  `METRICS_EXPORT_UNAUTHORIZED` and emit one bounded event.

### SEC-022 — Composition reads `CUBI_AI_ENABLED` from `os.environ` (Low)

- **Resolution:** composition reads the supplied `environment` mapping and
  falls back to `os.environ` only when none is given. Covered by
  `test_production_composition_reads_the_assistant_flag_from_its_environment`.

- **Evidence:** `production_composition` honours its `environment` mapping for
  other settings but reads the assistant flag directly from `os.environ`.
- **Impact:** An isolated/test composition can silently wire the assistant
  provider from ambient process state.
- **Recommendation:** read the flag from the resolved mapping.
- **Negative test:** `environment={"CUBI_AI_ENABLED": "false"}` wires no
  provider even when the process environment says true.

### SEC-023 — Anonymous readiness probe returns component detail (Low)

- **Evidence:** health paths are routed before authentication and return the
  per-component readiness payload including `detail`.
- **Impact:** Anonymous callers learn dependency names and failure modes.
- **Recommendation:** keep the aggregate status public and redact component
  detail unless authenticated.
- **Negative test:** an anonymous `/ready` response omits component detail.
- **Resolution:** `OperationalMiddleware` returns only the aggregate status,
  generated time, and each component's name/requirement/state unless the
  deployment injects `readiness_detail_allowed`, an authentication callback. A
  missing or raising callback is treated as anonymous. The unconfigured-readiness
  503 body no longer carries a `detail` field. Tests:
  `test_anonymous_readiness_probe_omits_component_detail`,
  `test_readiness_detail_is_returned_only_when_the_auth_callback_approves`,
  `test_readiness_auth_callback_failure_is_redacted_and_does_not_break_the_probe`,
  `test_unconfigured_readiness_reports_no_component_detail`.

### SEC-024 — WSGI short-read body is accepted as complete (Low)

- **Resolution:** bodies are read in a loop until the declared length or end
  of stream; a short read now returns `400 REQUEST_BODY_INCOMPLETE` instead of
  dispatching. Covered by
  `test_wsgi_rejects_truncated_body_instead_of_dispatching` and
  `test_wsgi_reads_a_body_delivered_in_several_short_chunks`.

- **Evidence:** the adapter calls `stream.read(min(length, limit + 1))` once and
  only checks the over-limit case; a short read is passed to handlers.
- **Impact:** Handlers can act on truncated payloads; byte-upload paths would
  store a truncated blob whose digest matches the truncated bytes.
- **Recommendation:** loop to `length` or EOF and return
  `400 REQUEST_BODY_INCOMPLETE`.
- **Negative test:** a `length-1` body yields 400 rather than handler
  invocation.

### SEC-025 — `ReferenceAIToolPermissionAdapter` authorizes on tool name only (Info)

- **Resolution:** the adapter is documented as test-only and now returns `False`
  for a missing or blank `subject_id`, so it cannot authorize on a tool name
  alone. Covered by
  `test_reference_adapter_never_authorizes_a_tool_without_a_subject`.
- **Evidence:** `ai_action_boundary.py` returns
  `proposal.tool_name in self.allowed_tools`, ignoring `subject_id` and scope
  fields, unlike the default-deny adapter. Nothing in `src/` or `apps/`
  instantiates it.
- **Impact:** Zero today; would weaken tenant runtime grants if wired.
- **Recommendation:** document as test-only or require subject and scope.
- **Negative test:** `allowed(proposal, subject_id=None)` returns `False`.

## Findings from the reviews that produced no change

- Reviewer A's `SimpleCookie.load()` leniency note produced no finding: the
  session cookie is looked up by exact session id and unknown ids are rejected.
- Reviewer A recorded tenant/project isolation, path handling, SQL
  construction, upload typing, response headers, body limits, deserialisation,
  observability bounding, secret redaction and export formula-escaping as
  examined with no finding; reviewer B independently confirmed the same areas
  and additionally validated the metrics exporter's constant-time comparison,
  byte/series caps and label gating.
- Reviewer B noted the working tree was mid-edit during its review (its F-01
  and F-06 line numbers predate the uncommitted redirect/page-cap patch); this
  is expected — the bounded reviewer started while `07d3c5e` was being built.

## Open gates

- **Runtime testing.** Both reviews are static, read-only, with no DAST,
  fuzzing, dependency CVE scan or penetration test. Two claims were validated
  by interpreter calls only (formula `RecursionError`, cookie parsing).
- **Production configuration.** No production session store, proxy, TLS
  terminator, S3 bucket or scanner endpoint was inspected; several findings
  (SEC-011, SEC-021) depend on deployment configuration.
- **Deployment authentication.** The WSGI adapter assumes a deployment-owned
  authentication/session front end. The in-process route layer enforces session
  and project authorization, but reverse-proxy trust boundaries were not
  reviewed.
- **Unassessed modules.** `scheduling/*`, `multilingual/*`,
  `document_backup_consistency.py`, `staging_smoke.py` and `p6_*` calculators
  outside `p6_formula_engine.py` received little or no review and must be
  treated as unassessed rather than clean.
- **Open Medium/Low findings.** SEC-017 remains open;
  SEC-007, SEC-008, SEC-009, SEC-011, SEC-014, SEC-016, SEC-018, SEC-019,
  SEC-020, SEC-021, SEC-022, SEC-023, SEC-024 and SEC-025 are fixed with
  negative tests. Open findings are recorded here rather than
  silently closed, and the fixed ones are marked in the register above.

## Verdict

Independent review is complete: two isolated reviewers produced registers, both
reconciled above. No Critical finding was reported by either reviewer. The one
open High (SEC-006, retention shared-object deletion) is fixed with negative
tests at SQLite and live PostgreSQL level. Eight Medium/Low findings are also
fixed and the rest remain open and tracked; no High or Critical finding is being
merged unresolved. Gate status for Workstream D: independent review
**satisfied**, runtime and production verification **open**.
