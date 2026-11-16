# ENT-13 Claim Day Archive — V26 HTML Help Crosswalk and Implementation Contract

**Status:** implementation design baseline; not a claim of runtime completion.  
**Parent:** Issue #2002; ENT-13 governance in PR #2001; environment ownership in merged PR #1988.  
**Reviewed main:** `ee9753e692eb319f98824ecf7e6084a92f814b7b` (2026-11-16).  
**Priority:** Enterprise P2. Do not consume or block Engineering P0/P1 capacity.  
**CUBI placement:** Enterprise → Contracts & Commercial → Claims & Disputes → Evidence & Day Archive.

## 1. Source authority and exact HTML Help set

The source hierarchy is binding:

1. P6 EPPM V26 English HTML is the universal primary parity baseline for concepts it actually documents.
2. P6 Team Member V26 HTML is a separate contributor-workflow authority where field/team-member activity reporting is involved.
3. Unifier V26 HTML is the primary comparative source for contract/commercial business-process forms, workflows, record permissions, document manager revisions and audit.
4. Primavera Cloud HTML is an additive source for cloud-only project/field/file workflows; it cannot replace EPPM V26 semantics.
5. AACE RP 29R-03 and SCL Delay and Disruption Protocol 2nd Edition inform forensic schedule-analysis method, not product UI or contractual entitlement.
6. Contract terms and governing law determine notice compliance, entitlement, liability, valuation and dispute resolution.

Canonical official HTML roots:
- P6 EPPM V26 Help TOC: https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm
- P6 EPPM V26 documentation library: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/user.html
- P6 Team Member V26 TOC: https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/toc.htm
- Unifier V26 All Guides: https://docs.oracle.com/en/industries/construction-engineering/primavera-unifier/26/books.html
- Unifier V26 User Help (October 2026): https://docs.oracle.com/en/industries/construction-engineering/primavera-unifier/26/user-help/index.html
- Unifier V26 Business Processes User Guide (October 2026): https://docs.oracle.com/en/industries/construction-engineering/primavera-unifier/26/business-process/index.html
- Unifier V26 Managers User Guide (October 2026): https://docs.oracle.com/en/industries/construction-engineering/primavera-unifier/26/managers/index.html
- Primavera Cloud current HTML Help TOC: https://primavera.oraclecloud.com/help/en/user/toc.htm

### 1.1 Verified P6 EPPM V26 topics

| Topic | Exact official HTML | Relevance and CUBI disposition |
|---|---|---|
| About Security | https://docs.oracle.com/cd/G48897_01/p6help/en/9001.htm | Secure logins, security profiles, access settings, module access, OBS access and UI views. CUBI must enforce permissions at API/read/download boundary; UI visibility alone is insufficient. |
| Assigning Documents to Activities | https://docs.oracle.com/cd/G48897_01/p6help/en/41625.htm | Documents may be related to activities, projects and WBS. CUBI Engineering remains owner of activity/WBS references; Enterprise stores revision-pinned links only. |
| Creating Project Issues | https://docs.oracle.com/cd/G48897_01/p6help/en/7963.htm | Schedule issues are created in project context. A delay event may link to an Engineering issue but must not be equated automatically with a contractual claim. |
| General Detail Window of the Issues Page | https://docs.oracle.com/cd/G48897_01/p6help/en/93728.htm | Issue name, responsible manager, identified date, project, owner, resolution date, applies-to, status, identified-by, priority and description. Use as the schedule-event/issue reference field inventory where applicable. |
| P6 EPPM V26 TOC | https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm | Inspected Projects → Activities/Issues/Documents, issue related items, document repository/reviews, security and audit topics. |

**Explicit product boundary:** the inspected EPPM V26 TOC documents project/activity issues, risks, documents, document reviews and schedule references. It does not expose a full multi-party contract claim/dispute lifecycle (claim submissions, counterclaims, contractual determinations, settlement and party disclosure). Record this as **NOT PRESENT IN EPPM V26 Help**, not as a missing CUBI parity feature. ENT-13 is an Enterprise commercial capability whose workflow source is Unifier V26 and contract/forensic standards; EPPM provides the authoritative schedule facts and links.

### 1.2 Verified Unifier V26 topics

| Topic | Exact official HTML | Requirement carried into CUBI |
|---|---|---|
| Filling Out a Business Process Form | https://docs.oracle.com/en/industries/construction-engineering/primavera-unifier/26/business-process/fillingoutabusinessprocessform-73223a.html | Upper form, line items, comments, comment attachments; draft/save/submit; workflow Send; terminal/read-only state; action details and assignee routing. |
| Completing a Business Process Form | https://docs.oracle.com/en/industries/construction-engineering/primavera-unifier/26/user-help/completingabusinessprocessform-73280a.html | Review/edit permitted fields, line items, attachments, comments, workflow actions, save draft, send; undo action and view received content. |
| Business Process Forms | https://docs.oracle.com/en/industries/construction-engineering/primavera-unifier/26/user-help/businessprocessforms-73165a.html | View vs action form, accept/decline, workflow progress, drafts, attachment/line-item handling, permissions and terminal operations. |
| About Workflows | https://docs.oracle.com/en/industries/construction-engineering/primavera-unifier/26/business-process/aboutworkflows-73172a.html | Creation → review → revision → approval → end; return for revision, forward, reject/approve and terminal-state handling. |
| Granting or Updating Record Permissions for Non-Workflow Business Processes | https://docs.oracle.com/en/industries/construction-engineering/primavera-unifier/26/business-process/grantingorupdatingrecordpermissionsfornon-workflowbusinessprocesses-73300a.html | Record-scoped View/Edit/Modify/Modify Permissions grants. CUBI must add tenant/project/contract/party/evidence scopes and fail closed. |
| Creating a Business Process (BP) Record | https://docs.oracle.com/en/industries/construction-engineering/primavera-unifier/26/business-process/creatingabusinessprocessbprecord-73191a.html | Records can be created from a BP log, template, another record or Document Manager attachments; creation requires configured BP and permissions. |
| Update Step | https://docs.oracle.com/en/industries/construction-engineering/primavera-unifier/26/business-process/updatestep-10292180a.html | Save Draft, Send, Submit, More Actions, Print, Review, Terminate, Transfer Ownership and BP-specific actions are configuration/permission dependent. |
| Assigning Users for the Next Step or Sending a Copy | https://docs.oracle.com/en/industries/construction-engineering/primavera-unifier/26/business-process/assigningusersforthenextsteporsendingacopy-73281a.html | To recipients are next workflow assignees; Cc receives a copy without workflow action. CUBI disclosure and notification must be explicit, logged and separate. |
| Revising Documents | https://docs.oracle.com/en/industries/construction-engineering/primavera-unifier/26/managers/revisingdocuments-73757a.html | Each new revision is stored separately; old file remains untouched and earlier versions remain accessible. CUBI pins exact source version/hash and never overwrites bytes. |
| Viewing Previous Revisions | https://docs.oracle.com/en/industries/construction-engineering/primavera-unifier/26/managers/viewingpreviousrevisions-10293974a.html | Previous revisions can be viewed/downloaded and linked records inspected. CUBI evidence manifest must pin exact revision rather than “latest”. |
| View Document Manager Audit log | https://docs.oracle.com/en/industries/construction-engineering/primavera-unifier/26/user-help/viewdocumentmanagerauditlog-10293989a.html | Upload and other actions are audited, with event details and entry mode. CUBI chain of custody must include source audit references and its own access/disclosure events. |
| Document Manager | https://docs.oracle.com/en/industries/construction-engineering/primavera-unifier/26/managers/documentmanager-73699a.html | Project/shell and company-level document manager; business-process integration. CUBI reuses its authoritative document store and only indexes evidence links. |
| Business Process permissions reference | https://docs.oracle.com/en/industries/construction-engineering/primavera-unifier/26/reference/information.html | View All Records / View Company Records / View User Records and ownership/termination permissions; CUBI adds party-level confidentiality, not a broad role shortcut. |

### 1.3 Verified Primavera Cloud HTML topics

| Topic | Exact official HTML | Requirement carried into CUBI |
|---|---|---|
| Navigation Overview | https://primavera.oraclecloud.com/help/en/user/86731.htm | Apps, object selector, page selectors, menus, dashboards, favorites and recent objects; responsive/viewport reference only, CUBI retains its approved single workspace shell. |
| Primavera Cloud Help TOC | https://primavera.oraclecloud.com/help/en/user/toc.htm | Current TOC includes files, object links, project settings, field/task apps, reports, forms/workflows and mobile topics. Use as an extension inventory, not an EPPM substitute. |

Further Cloud feature-specific topics must be added by exact URL when the related field/photo/reporting flow is implemented. Do not infer a Help topic from a TOC label alone.

## 2. Repository evidence at reviewed main SHA

Verified source paths:
- `src/construction_pm/backend_p0/models.py`: `BackendScope`, timezone-aware `AuditMetadata`, `EvidenceRef`, `FieldDailyLog` and `ClaimRecord`/change domain models.
- `tests/backend_p0/test_backend_p0.py`: field daily log round-trip, evidence refs, persistence atomicity, revision conflict and idempotency coverage.
- `tests/backend_p0/test_change_claim_core.py`: `ClaimRecord` decision metadata validation, generic resource round-trip, evidence refs, schedule/cost/impact references and claim close-after-decision rule.
- `apps/web/src/workspace-site-log.ts`: `field-daily-log.v1` projection/status surface.
- `apps/web/src/workspace-change-claim.ts`: `change-notice.v1`, `change-case.v1`, `claim-record.v1`, `change-claim-impact.v1` projections.
- `src/construction_pm/document_persistence.py`: `DocumentRecord`, immutable revision records, document lifecycle and audit abstractions; supported types include contract, drawing, correspondence, RFI, submittal, delay_claim and evidence.
- `src/construction_pm/document_storage.py`: content-addressed bytes, SHA-256 validation, tenant/project storage scoping and content-type validation.
- `src/construction_pm/document_retention.py`: per-document retention, legal hold, eligibility and deliberate disposition.
- `src/construction_pm/form_builder_templates.py`: validated shared form templates and organization/project library foundations.

### 2.1 Current state classification

| Capability | Evidence-backed state | What is not yet proven |
|---|---|---|
| Daily site log | Existing domain model and web projection | Claim-day grouping, timezone calendar policy, exact approved source revision pinning, completeness review and multi-party visibility. |
| Claim | Existing `ClaimRecord` model and generic backend resource tests | Contract-party-specific submission versions, response/objection/counterclaim workflow, immutable submitted package and party isolation. |
| Evidence | Existing generic `EvidenceRef` | Claim evidence lifecycle, SHA-bound source version resolution, chain-of-custody and scoped disclosure. |
| Documents | Existing versioned metadata/storage/retention foundations | Claims integration, immutable manifest pinning and claim-level legal-hold composition. |
| Form Builder | Existing reusable template infrastructure | ENT-13 party-specific templates, immutable submission snapshot binding and claims workflow configuration. |
| Engineering schedule | Existing Engineering-owned schedule/CPM domain | Versioned request/response adapter for claim-period forensic analysis; no Enterprise CPM is allowed. |

No API route, end-to-end UI, party confidentiality, claim-day archive or immutable submission is considered implemented until the exact route/component and its tests are located and executed. The model/projection evidence above is not an end-to-end completion claim.

## 3. Target domain and versioned contract

The archive is a **claims-domain index and immutable manifest over authoritative source records**, not a second file repository.

### 3.1 Aggregates

- `ClaimParty`: tenant, project, contract, claim, party identity/type, participation role and active status.
- `ClaimDay`: claim, reporting date, timezone identifier, local day boundaries, party scope, status, linked delay events, completeness findings and optimistic revision.
- `ClaimEvidenceLink`: claim-day, source system/type/id, exact source revision/content version, content hash (binary sources), effective timestamp, capture timestamp/timezone, server-received timestamp, author/uploader, location/work-front, activity/WBS/cost refs, evidence classification and link status.
- `EvidenceDisclosure`: exact evidence-link revision, recipient party/grant, disclosure actor, reason, timestamp, channel and revocation/supersession state. No implicit disclosure from project membership.
- `ClaimSubmission`: claim revision, submitting party, submission number, exact form template/version, canonical serialized form snapshot, evidence manifest digest, schedule/baseline snapshot IDs, submitted actor/time and immutable state.
- `ClaimWorkflowEvent`: transition, actor, role/grant, from/to state, reason, timestamp/timezone, idempotency key and referenced submission.
- `ClaimHoldBinding`: claim/contract/legal-hold scope and the source document versions it protects; composed with the existing document retention authority.

### 3.2 Claim Day Archive v1 JSON shape

```json
{
  "contract_version": "claim-day-archive.v1",
  "claim_day_id": "opaque-id",
  "tenant_id": "tenant-id",
  "project_id": "project-id",
  "contract_id": "contract-id",
  "claim_id": "claim-id",
  "reporting_date": "2026-11-16",
  "timezone": "Europe/Berlin",
  "day_start_at": "2026-11-15T23:00:00Z",
  "day_end_at": "2026-11-16T23:00:00Z",
  "calendar_policy": "contract-reporting-calendar-v1",
  "party_scope": "party-id",
  "delay_event_ids": [],
  "evidence_links": [],
  "completeness": {"state": "incomplete", "missing_required_types": []},
  "revision": 1
}
```

The sample is illustrative, not a persisted schema. Canonical timestamps are UTC instants plus an IANA timezone identifier; the reporting date is a contract/project-local calendar date. DST day boundaries must be calculated from timezone rules (a local day is not always 24 hours). Jalali is a display/calendar conversion only; it never changes canonical timestamps or the reporting-date identity.

Evidence link minimum:
```json
{
  "evidence_link_id": "opaque-id",
  "source": {"system": "cubi-document-management", "type": "document", "id": "doc-id", "revision": 4, "content_version": "v4"},
  "content_sha256": "sha256:<64-hex>",
  "effective_at": "2026-11-16T08:30:00Z",
  "captured_at": "2026-11-16T08:35:00+01:00",
  "server_received_at": "2026-11-16T08:42:00Z",
  "actor_id": "user-id",
  "party_visibility": "private",
  "activity_refs": [],
  "wbs_refs": [],
  "delay_event_refs": [],
  "chain_of_custody_refs": []
}
```

### 3.3 Immutable package rule

At formal submission, persist a canonical manifest containing sorted evidence-link identities, exact source revisions/content hashes, disclosure state, form template ID/version, form snapshot hash, schedule/baseline snapshot IDs and a manifest SHA-256. The submission record is append-only. A correction creates a new claim submission revision and explicitly supersedes the prior package; it never mutates the submitted package. Every export must include the manifest, digest, verification outcome and source-reference availability.

## 4. Party confidentiality and authorization matrix

Authorization must be enforced before any data lookup, list count, search result, download, preview, export, notification payload or link resolution. Opaque IDs do not replace authorization.

| Actor | Private draft | Own submitted package | Other party submitted package | Disclosed evidence | Determination/settlement |
|---|---:|---:|---:|---:|---:|
| Claim originating party | Read/write own | Read | Only explicitly disclosed | Read exact grants | Read per contract role |
| Responding party | Read/write own response | Read only if disclosed to it | Read disclosed subset | Read exact grants | Read per contract role |
| Independent reviewer/expert | No party-private access by default | Read assigned scope | Read assigned scope | Read assigned scope | Read assigned scope |
| Contract administrator | Policy-configured; not automatic | Policy-configured | Policy-configured | Policy-configured | Manage only granted workflow |
| Tenant/project admin | No implicit evidence access | No implicit access | No implicit access | No implicit access | No implicit access |
| Auditor/legal hold officer | Metadata/audit only unless explicit grant | Metadata/audit only | Metadata/audit only | Explicit scope only | Explicit scope only |

Required tests: cross-tenant, cross-project, cross-contract, cross-party, guessed-ID, linked-document URL, list-count/search side channel, download/preview/export, revoked disclosure, role removal, reassignment and stale authorization cache. All failures must be fail-closed and non-enumerating.

## 5. Day archive UI and behavior contract

Primary Enterprise page: Claims & Disputes → Evidence & Day Archive.

- Claim selector and claim identity summary; role/party context must always be visible.
- Date-first archive navigator (calendar/list), timezone and reporting-calendar label, day status and completeness.
- Day workspace: linked delay events, daily site reports, drawing/document revisions, correspondence/notices/RFIs/submittals, photos/videos (only where source support exists), meeting minutes, inspections/tests, permits, delivery records, weather/plant/labour evidence, Engineering schedule/baseline references.
- Each evidence row shows source type, title, exact revision, effective/capture/received times, uploader, work-front/location, activity/WBS links, party visibility, disclosure status, hash verification, retention/hold state and audit trail.
- Actions: link existing source, upload through authoritative document/photo source, unlink only while package is mutable, add contextual metadata, request disclosure, disclose, download if authorized, compare revisions, verify manifest, print/export package.
- Missing evidence indicators must be factual (e.g. “no daily report linked for this date”), never fabricate a report or assume missing evidence proves non-performance.
- Party-private working papers stay in the originating party's private view. Shared page layout does not mean shared evidence.
- Reuse CUBI Form Builder for party-specific claim forms; reuse Document Management for bytes/revisions; reuse daily log and Engineering for source records. Do not create a parallel document upload stack or duplicate form designer.
- Keep the approved CUBI shell and brand. No Oracle/Primavera names, icons, URLs or visual assets in product UI.

## 6. Engineering adapter — no duplicate schedule engine

Enterprise submits a typed request to the Engineering-owned service containing tenant/project/contract/claim IDs, schedule revision, baseline revision, data date, analysis window, delay-event IDs, activity/relationship references, requested method and method version. Engineering validates authorization and returns a provenance-rich immutable result with run ID, engine/version, input hashes, schedule/baseline IDs, data date, method, assumptions, calendar/timezone, activity-level findings, relationship/critical-path/float context, calculation timestamp and limitations. Enterprise stores the result reference and presents the output; it never recomputes CPM, critical path, float, resource leveling or schedule impact.

A schedule finding is not a legal determination. Entitlement, causation responsibility, notice compliance, concurrency treatment and recoverability remain contract/legal review decisions.

## 7. Delivery sequence and merge gates

1. **Source/API inventory:** locate actual route handlers, auth middleware, repository methods, migrations and tests for daily logs, claim/change, documents, storage, photos, retention, audit, forms and Engineering snapshots. Do not infer routes from UI types.
2. **Domain contract:** add versioned schema, validation, serialization, canonical hashing, date/time policy, state machine and migration plan. Keep source ownership boundaries.
3. **Persistence:** PostgreSQL repository, tenant/contract scoping, optimistic locking, idempotency, append-only submission/manifest and transactional audit events.
4. **Authorization:** policy service and negative tests across every read/write/list/download/export route; party isolation is a merge blocker.
5. **Source adapters:** daily log exact revision, document exact version/hash, photo metadata and Engineering snapshot adapter. If a source capability is unavailable, show an explicit unavailable state and keep the integration contract deferred.
6. **Workflow/forms:** organization/project Form Builder templates, party-specific drafts, submit/response/objection/counterclaim/expert/determination/settlement transitions.
7. **UI:** date-first archive, completeness, evidence linking, visibility/disclosure, manifest verification and export.
8. **QA:** unit, repository/PostgreSQL integration, API contract, security/threat, migration, concurrency/idempotency, browser E2E, RTL/LTR and multilingual tests; attach screenshots and exact SHA.
9. **Release:** only merge-main, green exact-head CI and runtime evidence can be called implemented. Do not merge the ENT-13 manifest as implementation-ready until every declared path/test and the full Help crosswalk are evidenced.

## 8. Acceptance test catalogue

- Create claim day under contract timezone; prove DST-short/long day boundaries and Jalali display preserve canonical date/time.
- Attach exact approved daily report revision and verify source ID/revision/hash; later source revision does not alter the claim day.
- Attach multiple drawing revisions including superseded version; both remain retrievable and distinguishable.
- Attach photo with original bytes, capture timestamp/timezone, uploader, location/work-front and SHA-256; reject mismatched hash.
- Link evidence to multiple delay events, Engineering activities/WBS and cost references without mutating source records.
- Backdated report/capture correction requires actor, reason and audit trail; received time remains distinct.
- Formal submit freezes sorted manifest and form version; any change requires new submission revision.
- Two parties maintain private drafts; neither can enumerate, infer or download the other's private evidence.
- Selective disclosure exposes only selected evidence revision to the specified recipient; revoke future access without rewriting historical disclosure audit.
- Reviewer sees only assigned claim scope; project admin does not receive implicit privileged evidence access.
- Claim-level legal hold prevents disposal of all referenced document versions; clearing claim hold does not bypass source-level hold.
- Export verifies manifest digest and reports missing/unavailable source content without substituting “latest”.
- Engineering delay analysis references pinned schedule/baseline/data date and records exact engine/method/input provenance.
- Full audit covers create, edit, link, unlink, view/download where policy requires, disclose/revoke, submit, respond, revise, approve/reject, determine, settle, hold and export.

## 9. Known blockers and honest status

- Existing main has a claim record and change/claim projection, but not a verified claim submission/versioning/party-scope model.
- Existing `EvidenceRef` is a locator/revision reference; it is not a complete source-version/hash/visibility/chain-of-custody record.
- Existing document content store and retention are reusable foundations; claim-level hold composition and submission pinning are not yet proven.
- Existing daily logs are project-scoped; claim-day timezone aggregation and exact approved revision linking are not proven.
- Existing form templates are reusable; ENT-13 forms/workflows and frozen submission snapshots are not proven.
- Exact API route inventory and runtime browser/security tests remain mandatory before implementation-ready status.
- PR #2001 remains open and defines ENT-13 as source-mapped, not implementation-ready. This document does not bypass its CI governance gate.

**Exit criterion:** ENT-13 becomes implementation-ready only when sections 1–8 have traceable exact Help topics, verified code paths, versioned contracts, authorization threat tests, end-to-end acceptance evidence and approved ownership. Full production implementation is a subsequent isolated Enterprise P2 delivery, never a documentation-only claim.
