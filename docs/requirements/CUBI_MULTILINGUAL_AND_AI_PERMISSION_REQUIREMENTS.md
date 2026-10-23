# CUBI Multilingual Experience and AI Assistant Permission Contract

**Status:** Binding product requirement; implementation completion must be proven separately.  
**Applies to:** Public website, authenticated Web workspace first, Desktop second, Mobile when delivered, shared APIs/services, reports/exports/help, offline workflows and the embedded CUBI assistant.

## 1. Multilingual is a product-wide capability—not a two-language toggle

- The language system must be extensible to **all languages explicitly declared as supported**; it must not be hard-coded to Persian and English. Persian and English are initial baseline languages, not the product's maximum language set.
- A language may be advertised as supported only after its end-to-end acceptance suite passes. A language selector, partial translation file, machine-translated page or pack download alone is not evidence of full support.
- Language-neutral stable keys and centralized, versioned locale resources are required. No user-facing strings may be hard-coded into screens, charts, server errors, assistant prompts/actions, reports or generated documents.
- Coverage includes every menu/submenu, field, grid/column, dialog, validation/error/notification, permission prompt, onboarding/settings, WBS/activity editor, Gantt/timeline/network, calendars, resource/cost/EVM views, dashboards, charts/legends, filters/sort/grouping, imports/exports, PDFs/A4 reports, help, audit views, email/notifications and AI flows.
- Support locale-specific pluralization, grammatical forms, collation/search/sort, date/number/decimal/currency/unit/percentage formatting, accessibility names, text expansion, line wrapping, and appropriate fonts.
- Support true RTL and LTR, including mixed-script content, cursor/selection behavior, bidirectional punctuation/numbers, table/grid alignment, chart labels, navigation and responsive layouts. Persian font support must be deliberate and legible.
- Language, locale, time zone, calendar system and scheduling settings are separate dimensions. Switching display language must never rewrite stored project text, IDs, dates, Jalali/Gregorian calendar identity, durations, money, schedule settings or calculated results.
- Preserve original user-authored text. Translation/transliteration of project records must be explicit, reversible where applicable, and authorized; never silently overwrite source text.
- Every supported language must have an explicit fallback policy. Never silently mix languages; visibly identify missing pack/resource/capability and avoid claiming unsupported behavior.
- SEO for public pages must use real per-language content, localized metadata and canonical language routes, with correct `hreflang` and language-aware sitemaps where applicable. A translated URL alone is insufficient.
- Web is first delivery priority, Desktop second, Mobile later; shared language contracts must not force these clients to launch simultaneously.

## 2. Downloadable/offline language packs

- Language packs are versioned, integrity-checked artifacts with a manifest, locale identifier, supported product/app versions, resource catalog, capability declarations and dependency/version metadata.
- Users can inspect the active pack and available version, download/update, activate, roll back to a valid prior version and remove non-required packs, with explicit loading/progress/error states.
- Pack integrity must be checked before activation; failed, incompatible or tampered packs must fail closed without corrupting the active pack.
- Cached UI, help, validation messages, reports and offline workflows must use the selected verified pack where supported. Offline support is capability-specific, not an assumption that every AI/model/voice provider works without a network.
- Synchronization and generated outputs must preserve locale and source-language provenance. Conflicts or unavailable translations must be reported clearly.
- Pack lifecycle support does not itself prove every application screen or language is translated. The release matrix must track infrastructure, per-client integration and per-language coverage separately.

## 3. Assistant capability and permission model

The CUBI assistant is a project-aware, action-capable product assistant—not merely a chat window. It may analyze authorized project data, interpret user-provided documents/spreadsheets, propose project initialization and help create or edit WBS, activities, relationships, calendars, resources, schedule scenarios/results, charts and reports. The actual available operations must be backed by real application tools and the authoritative Shared Domain/Calculation Core; a documented intention or UI button is not implementation evidence.

### 3.1 User-controlled permission grants

- Permission is explicitly configured by an authorized human for the assistant, and is bounded by that human's own effective permissions. The assistant can never grant itself more access or exceed the actor's tenant/project permissions.
- Permissions are granular by **tenant, project, project revision/context, data domain, operation and tool**. At minimum distinguish: discover/list; read/view; search; analyze; propose/draft; create; update; delete/archive; import; export/share; run authoritative calculations; and administer users/roles/settings. Do not collapse these into one generic “AI enabled” flag.
- Provide clear profiles such as **Off**, **Read-only analysis**, **Proposal-only**, **Write with approval**, and **Explicitly granted bounded automation**. Profiles are presets, not substitutes for per-domain/per-operation grants.
- Default is deny. Missing, expired, ambiguous, revoked or unverifiable permission must block the operation. Read access does not imply write access; permission to propose does not imply permission to execute.
- The user must be able to inspect and revoke grants, choose project/data scope and permitted operations, and see what the assistant can and cannot do before use. Revocation must be enforced on the next operation and at execution time, not merely hidden in the UI.
- The assistant must not access another tenant/project, hidden data, credentials, secrets or external services unless the actor and a separate explicit integration grant authorize that access.

### 3.2 Proposal, approval and execution

- Any mutation must be represented as a typed, scoped, versioned proposal before execution. The proposal identifies target project/revision, operation, affected records, expected changes, source/evidence, risks, and whether approval is required.
- The application re-checks identity, tenant/project scope, current revision, operation-level permission, tool allowlist, policy and approval immediately before execution. Never trust model-generated permission claims or a prior UI-only check.
- Human approval is required for consequential actions, including destructive changes, baseline/publication changes, bulk edits, changes to actual/progress records, permission/security changes, external sharing and other configured high-impact operations. Approval must identify the human actor and bind to the exact proposal/revision; stale proposals require revalidation and renewed approval.
- Bounded automatic execution is permitted only for operations explicitly granted by the user/admin, with scope and limits visible, and only where policy permits. Never infer automatic-write consent from a general chat request or a read-only grant.
- Reject, cancellation, timeout, permission denial, stale revision and partial failure must be explicit and auditable. Multi-record changes require defined transaction/compensation behavior and idempotency.
- Every attempted and completed action records an audit event with actor, assistant/model/tool identity, tenant/project/revision, permission decision, proposal ID, approval actor/time, affected records, evidence references, outcome/error and correlation/idempotency IDs. Sensitive data must not be copied unnecessarily into audit logs.
- Assistant actions may request schedule calculation but may not implement their own CPM/P6, calendar, Progress/EVM, Resource/Cost or financial formulas. Calculation results must come from the one authoritative Shared Core.
- Assistant must distinguish retrieved facts, calculated facts, assumptions, estimates and recommendations; cite project/document evidence where available; ask clarifying questions when required inputs are missing; never invent project facts or claim an action succeeded before confirming the persisted result.
- Importing or extracting content is not permission to mutate the project. Show a preview/mapping/errors and require the permission/approval applicable to the resulting writes.
- Voice commands have exactly the same scope, grants, approval and audit requirements as typed commands. Transcription confidence/language/source provenance is retained; ambiguous or low-confidence consequential commands must be clarified, not executed.
- Offline assistant behavior is capability-declared and fail-closed when required models, language packs, authorization context or verified tools are missing. Offline queued mutations must be re-authorized against current server policy and revision before synchronization/execution.

## 4. Language parity for the assistant

- For every language declared supported by the assistant, support the declared capability subset for input/output, project terminology, document extraction, clarifying questions, proposals, approvals/rejections, citations, uncertainty, errors, voice and audit summaries.
- Text/voice input language, response language, project language, locale, terminology profile and voice language are distinct fields. Users can select them; automatic detection must be surfaced when uncertain.
- Translation must not alter action meaning, target scope, numeric/date values, relationship types, lag/lead, permissions, approvals or calculation results. Structured actions must be validated from typed language-neutral data, not reconstructed from translated display text.
- If a language/capability is unsupported or offline-unavailable, state that limitation and offer a safe supported path; do not silently fall back to a different language for a consequential action.

## 5. Mandatory acceptance evidence

- A language-by-surface matrix for website, workspace, reports/help and assistant, with pack version and test evidence.
- Automated and manual RTL/LTR, mixed-script, accessibility, long-string, pluralization, locale-formatting and language-switch regression tests.
- Language-pack checksum/signature/incompatibility/rollback/fallback tests.
- Permission matrix tests for every operation × role/grant profile × tenant/project scope, including default deny, revocation, cross-tenant attempts, stale revision, approval identity, denied writes and audit persistence.
- End-to-end assistant tests for read → grounded answer; document/spreadsheet import preview → approved write; project/WBS/activity/relationship/calendar/resource draft → approval → authoritative schedule calculation → persisted read-back; reports/charts; rejected action; stale proposal; partial failure; and offline-to-online reauthorization.
- Evidence must be tied to the exact tested commit and CI/runtime run. Mark specification, implementation, integration and release acceptance separately; never infer implementation completion from this document.
