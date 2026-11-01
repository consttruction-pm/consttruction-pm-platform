# CUBI Subscription, Identity, Team, Messaging, Storage and Reporting — V1 Contract

**Status:** Product decision approved on 2026-10-27; implementation is not certified until the tracked P0 work passes the acceptance gates in GitHub issue [#1605](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1605).

**Authority:** This document is mandatory for implementation. The versioned schema at `shared/contracts/cubi-identity-team-messaging-entitlements.v1.schema.json` defines stable data shapes; it does not claim that production endpoints, database migrations, billing integrations or user interfaces are already implemented.

## 1. Commercial model — fixed decisions

Only these account subscription plans exist:

- **Free** — no recurring payment; features/quotas follow centrally configured Free entitlements.
- **Pro monthly** — USD 9.99 per monthly unit as the current approved working price. The price is centrally configured; clients must not hard-code separate copies.

The following product models are explicitly forbidden and must not be exposed by checkout, APIs or UI:

- standalone annual subscription;
- standalone Team subscription;
- purchase of one project;
- purchase of multiple projects.

Team creation is a Pro capability, not a separate paid tier. A Pro owner creates and manages a team within the limits declared by the entitlement policy. Do not invent member/project/storage limits in individual clients or use undocumented constants; numeric quotas must come from reviewed central configuration.

### 1.1 Buy several monthly units in one payment

The Pro checkout must include an integer month-quantity selector. Quantity 5 purchases five monthly units and adds five calendar months to the subscription expiry; quantity 12 adds twelve months. Selecting 12 months is **not** an annual plan or a separate annual entitlement.

Rules:

1. Quantity must be a positive whole number and be within the payment provider's/configuration's explicit limit.
2. Amount due is the configured Pro monthly price multiplied by quantity. Any discount must be an explicit separately approved policy, never an implied annual tier.
3. After verified successful payment only, extend from the existing future entitlement expiry. If no active future expiry exists, start at the entitlement activation time defined by the payment contract.
4. Calendar-month addition must be deterministic at month-end and timezone boundaries (for example, adding one month to a date near the end of a long month must use the documented clamp-to-last-valid-day rule); persist UTC instants and use one shared billing implementation.
5. Webhook retries, duplicate provider events and client retries must be idempotent: one successful payment adds its quantity exactly once. Failed, cancelled, pending or unverified payments add no time.
6. Preserve payment-event ID, provider transaction reference, quantity, unit price/currency, decision result, prior expiry, new expiry and timestamps in a scoped audit record. Do not store card secrets.
7. Expiry, cancellation, past-due and grace behavior must reuse the approved license/offline policy; no surprise deletion, corruption, or locking of project data.
8. Subscription status and entitlement are server-authoritative. The web, desktop and mobile clients display them but never decide entitlement locally.

## 2. User identity: unique username plus dedicated CUBI ID

Each registered account receives:
- a unique username, enforced globally by the server and persistent store;
- a generated, immutable, non-sequential public CUBI ID, displayed in a copyable form such as `CUBI-XXXX-XXXX-XXXX`;
- a separate internal database user key, never exposed as the public invite ID;
- a display name, which may duplicate and is not used as an identity key.

### 2.1 Username integrity

- Normalize usernames with a single documented Unicode normalization/case-folding policy and trimmed outer whitespace. Store both the display form and a canonical lookup value.
- Enforce a unique database constraint/index on the canonical value so concurrent registrations cannot claim the same username.
- Reject empty names, control/invisible formatting characters and prohibited/reserved names. Define length and allowed-character policy centrally and use it consistently in registration, profile editing, API validation and import.
- Handle visually confusable usernames safely. Show the immutable CUBI ID wherever users need to verify identity; never suggest that display-name similarity means the same person.
- Username changes, if permitted, must be audited and must not change CUBI ID, memberships, messages or invitation references.

### 2.2 Public CUBI ID integrity

- Generate the public ID using a cryptographically secure random source, a non-ambiguous alphabet and a unique constraint; regenerate on collision.
- The ID is immutable, not derived from email/phone/display name, and never recycled after account closure.
- Normalize only the documented formatting (such as uppercase and separators) during exact ID lookup.
- Rate-limit ID lookup and invite creation; do not expose account email, phone, private profile data or unrelated memberships in lookup responses.
- Avoid account-enumeration leaks. Responses for unauthorized/nonexistent IDs must not reveal more than the documented minimum. Only authorized team managers can initiate invitations.

## 3. Team lifecycle and ownership

- An eligible account with an active Pro entitlement and the required permission can create a team. The team is not a subscription tier and has no separate checkout.
- The team has its own stable ID, name, owner, created/updated timestamps, status and revision. The owner has to transfer ownership before leaving or disabling the account if that would otherwise orphan the team.
- Keep subscription owner, team owner and project owner as distinct concepts even when they are the same person.
- Membership is an explicit persisted relationship. Team membership by itself never means access to every project, form, document, file, report or message in the tenant.
- Entitlement policy supplies any applicable limits for team count, members and storage. No fixed numeric limits are invented in this contract.
- On Pro expiry/downgrade, preserve all project/team data and follow an explicit entitlement/grace policy for new team creation, invitations and writes; never silently delete user data. The precise limited-mode transition and user-facing warning must be explicit and tested.
- Removing or suspending a member blocks new access immediately. Data retention and access to historical messages must follow documented policy and must not be implemented by deleting the audit trail.

## 4. Roles and authorization

Support scoped permissions for at least:
- `owner`: team ownership, transfer and high-level team settings;
- `admin`: delegated member and team administration;
- `project_manager`: only explicitly assigned project-management actions;
- `approver`: approve/reject/request correction on assigned workflow records;
- `field_worker`: submit assigned forms and view own/explicitly shared responses;
- `member`: ordinary capabilities explicitly granted;
- `viewer`: read-only access to explicitly granted resources.

Role names are not a substitute for permission checks. A member may carry different project-scoped roles where needed; permission resolution must combine authenticated actor, team, project/resource, membership state, operation, current revision and explicit grant. Enforce authorization at the application/server boundary on every read, write, search, upload/download, message delivery, export and background job. Hiding a button is not authorization.

All permission-sensitive operations fail closed when actor, scope, membership or entitlement is missing, stale or ambiguous. Re-check permissions when a queued job executes and when a download is requested. Prevent IDOR/cross-tenant access and role escalation. Keep actor-bound append-only audit events for invitation, membership, role, ownership, entitlement and approval changes.

### 4.1 Form-only field access and approval

A project owner/manager assigns a particular form to named member(s). A field worker can open, complete, save/submit and inspect only records/forms permitted by that assignment. They cannot browse unrelated project pages/data by guessing IDs.

Workflow states are explicit (at minimum draft, submitted/pending, approved, rejected, changes requested). A valid approver can decide only records within their scope; each decision stores actor, timestamp, reason, prior/new state and revision. Rejected/changes-requested records can be corrected and resubmitted with history intact. Unapproved submissions must not be presented as authoritative actual quantities, accepted progress, approved consumption or official report totals.

## 5. Invitations by CUBI ID

- Team managers can paste/type a public CUBI ID or select a verified account returned by exact ID search; display name is confirmation context, not the lookup key.
- Show the stable ID and display name together in the confirmation step to avoid inviting the wrong similarly named person.
- Invitation is bound to a team ID, target user ID, inviting actor, granted role/scope, expiry and unique invitation ID. Never bind invitations to a mutable username alone.
- Lifecycle: pending → accepted or declined; inviter may revoke; pending invitations expire. Accepted invitations become membership exactly once.
- Acceptance requires the invited authenticated account. A different account cannot redeem it. Replaying, duplicate concurrent accepts or reusing a revoked/expired invitation must not create duplicate membership.
- Only authorized owners/admins can invite or grant roles within their own authority. Prevent inviting oneself where it would bypass ownership rules; prevent removal of the last owner; transfer ownership atomically.
- Rate-limit invitations and exact-ID lookups. Provide clear localized outcomes without leaking private account data.

## 6. Team member messaging

Provide persisted member-to-member direct messages and team-scoped group/channel conversations.

Minimum behavior:
- conversation creation only for eligible team members;
- send/receive text messages, paginated history, sender ID/name, server timestamp, delivery/error state, unread count and read cursor/receipt;
- notifications and mute preferences, with localized notification preferences and non-sensitive notification previews by default;
- retry-safe sends using an idempotency key; store durably before acknowledging success;
- optional real-time push/WebSocket delivery may improve latency, but persisted conversation/message state is authoritative and must be recoverable after reconnect/offline periods;
- edited/deleted messages follow a visible, versioned policy; use a tombstone/retained audit event where required rather than silently rewriting history;
- safe rate/length limits as centrally configured, with validation and abuse prevention;
- block/report controls consistent with privacy and team-governance policy.

Every conversation and message query/write re-checks authenticated user, current membership, conversation team/project scope and relevant permission. Guessing a conversation/message ID must never grant access. Cross-team direct messaging is not implicitly available: direct messages in this V1 contract require a shared team membership. On membership revocation, stop new access/delivery immediately and apply the approved historic-message retention/read policy.

File attachments are optional and may be enabled only after shared storage checks are integrated. Attachments must use scoped, expiring access and the same quota accounting; no public unscoped object URLs.

## 7. Storage quota and file lifecycle

Use one centralized policy and accounting service for account/team/project usage. The policy must include byte-accurate storage, per-file size rules, allowed types, reserved/in-flight upload handling, retained-version accounting, deletion, trash/retention and temporary upload expiry.

Required behavior:
- show current and maximum configured usage and a warning before reaching the threshold;
- reserve/commit usage safely under concurrent uploads so concurrent requests cannot exceed quota silently;
- reject or pause new uploads at quota with an actionable, localized error; never truncate files or delete previous records silently;
- idempotent upload completion/deletion; retry and failed uploads do not double-count;
- reconcile counters against authoritative stored objects and expose discrepancies to operations rather than conceal them;
- apply scope checks at upload initiation, upload completion, preview, download, report export and background processing;
- clarify whether messages, attachments, project documents, report artifacts and retained versions count toward each quota. Do not choose inconsistent answers in separate clients;
- support backup/export/restore under existing permission-bounded portability policies.

Numeric account/team/project quotas and retention periods are configuration/product decisions and remain unassigned until approved. No UI may advertise unlimited storage unless the server enforces that policy.

## 8. Reports and audit views

Authorized users should have:
- account/billing view: plan, monthly quantity purchased, payment status/reference, expiry, renewal/extension history;
- team view: members, roles, pending/expired/revoked invitations, membership changes and owner;
- messaging view: permitted conversation list/unread counts; private message bodies must not appear in general administrative reports unless explicitly authorized by a documented policy;
- field workflow view: submissions by form/project/member/period and approval/rejection/change-request status, with source revision;
- storage view: used/configured bytes by account/team/project/category, upload failures and quota warnings;
- audit view: actor, action, scope, timestamp, decision, result, revision and correlation/idempotency reference, excluding credentials, private message content where not required, and file contents.

Every report, filter, chart, export and background job applies the same current authorization scope as the underlying records. Include clear time zone/period boundaries and localized formats. Exporting a report cannot widen the user's permissions.

## 9. Versioned technical architecture

Before implementation, inspect current `main` and reuse existing identity/session, authorization, persistence, HTTP routing, event/audit, storage, localization and client-sync abstractions. Do not repurpose the preview database, seed users, or demo fixtures as production identity.

Deliver the vertical slice through:
1. typed versioned domain/data contracts;
2. database migrations, unique indexes and foreign-key constraints;
3. repositories and transaction boundaries with concurrency control;
4. application services for account registration/username, public ID generation/lookup, entitlement and month extension, team/invitation/member lifecycle, messaging/read state and quota accounting;
5. authenticated versioned HTTP endpoints with machine-readable errors, validation, idempotency and authorization;
6. web interaction and shared contracts, with desktop/mobile integration only through the same supported services/contracts;
7. localized UI strings, notifications, help and reports using the existing language registry;
8. observability and append-only audit events without secrets;
9. tests through real persistence and authenticated production composition.

Do not introduce a parallel authentication provider, authorization engine, subscription engine, storage counter or independent client implementation.

## 10. Required executable acceptance tests

- Registration assigns a stable unique CUBI ID; duplicate/case-normalized username claims fail, including concurrent writes.
- Display name duplicates are allowed but do not affect identity or invitations.
- Username edit leaves IDs, memberships, invitations and message ownership unchanged.
- Pro month quantities 1, 5 and 12 generate correct configured totals and extend from a future expiry; payment provider retries and duplicate webhooks extend once only.
- Failed/cancelled/unverified payment does not extend entitlement.
- Calendar-month end, leap year and UTC/time-zone cases follow the shared month-addition rule.
- Checkout/UI/API expose no annual tier, Team tier, single-project purchase or multi-project purchase.
- Free cannot create a team; active Pro can create one without paying for Team. Entitlement/role limits are validated server-side.
- Exact CUBI ID invitation selects the correct account even where display names match; wrong-account acceptance, ID guessing abuse, replay, expiry and revocation are rejected safely.
- A member can access only assigned projects/forms/messages/files/reports; cross-team and cross-tenant IDOR attempts fail.
- Revoking membership stops future reads/writes/delivery immediately; ownership transfer and last-owner safeguards work.
- Field-worker submissions remain pending until accepted by an authorized approver; official totals change only under the authoritative approval rule.
- Message retries do not duplicate records; unread/read cursor and notification state persist; recipient and membership checks protect all read/write paths.
- Concurrent uploads cannot overrun quota; failed/retried/deleted uploads reconcile usage correctly; unscoped file links are denied.
- Reports and exports filter exact authorized scope and don't leak private conversation content or inaccessible object metadata.
- Migrations work against supported production database(s); create → commit → fresh read verifies authoritative persistence.
- Focused unit, API contract, integration, UI/workflow, security tests, typecheck/build and exact-final-SHA CI all pass before the issue or PR is marked complete.

## 11. Release and governance

Track implementation and evidence in [GitHub issue #1605](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1605). No implementation slice is complete based solely on a document, JSON schema, mock, demo database or screenshot. Record changed files, migration IDs, endpoint contracts, exact commit SHA, focused test results, CI run links and independently checked authorization behavior. Keep this document aligned with the Master Reference and amend it through reviewed commits if the product owner approves a change.


---

## 12. Product-owner-approved shared organization storage policy — 2026-11-01

This section records the approved product direction discussed with the product owner. It supplements the configurable quota policy above and is mandatory for implementation. Related tracker: [#1605](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1605).

### 12.1 Shared capacity is earned through active Pro membership

- Do not sell separate storage add-on packs in the current product model.
- Organization/team storage is a shared pool calculated from the number of **unique members with an active Pro entitlement** who are members of that organization/team.
- A user contributes capacity at most once to an organization, regardless of how many projects or workspaces they join within that organization.
- The currently discussed baseline is **2 GB per unique active Pro member** (for example, 10 active Pro members provide a 20 GB organization pool). Keep the per-member amount in centrally managed entitlement configuration; never hard-code it independently in clients or services.
- The quota is shared by all projects in the organization. Project count does not multiply the quota. Show organization total/used/available capacity and per-project consumption breakdown to authorized managers.
- Membership in a team alone does not grant access to every project; storage entitlement and project authorization remain separate decisions.
- If an active Pro count falls and committed usage exceeds the new quota, do not delete or corrupt existing data. Give the organization a **30-day grace period** and clear warnings. During/after the grace policy, prevent new uploads that would increase usage while preserving access to existing data for authorized users, including viewing, downloading and deletion, until usage is brought within quota or entitlement is restored.
- The quota service must account consistently for persisted project files, attachments, retained customer-controlled versions and manual backup packages. Use byte-accurate accounting and safe concurrency handling.

### 12.2 Project manual backups consume customer storage

- An authorized project user can request an immediate/manual backup for a specific project.
- The portable project backup package is stored in the organization/customer storage pool and **counts against that pool**.
- Keep at most **three retained manual backup versions per project**. Before creating a fourth, require the authorized user to select which prior manual version to replace; do not silently remove a version.
- Show the authorized user the project's manual-backup history with project identity, version, creation time, size, status and available download/restore actions.
- Download access is project-scope and permission-bound. Temporary server-side download artifacts/links expire and are cleaned up after **24 hours**; expiry of a temporary download must never remove the retained backup package.
- Support restore-as-new-project to protect the current project. Restore-in-place requires explicit permission, confirmation, a revision guard and a pre-restore recovery checkpoint.
- A project package must be clearly distinguished from a full database/system backup; it must never be described as a complete server backup.

### 12.3 Storage-efficient retention

- Use compression and incremental/version-aware storage where it is safe and supported. Avoid storing identical file payloads repeatedly.
- Deduplication must not create cross-tenant data disclosure, existence/timing side channels or shared authorization shortcuts. Prefer tenant-isolated deduplication unless a stronger design is independently security-reviewed.
- Maintain manifests, checksums, version ancestry and integrity metadata. Deleting/replacing an older version must not break restoration of any retained version that depends on it; compact/rebase chains safely before removing required ancestors.
- Failed, cancelled, retried and concurrent backup/upload operations must not double-count quota or leave orphaned billable objects.

## 13. Product-owner-approved backup ownership and retention — 2026-11-01

Related recovery tracker: [#1439](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1439).

### 13.1 Separate customer backups from CUBI system protection

There are two distinct storage and authorization domains:

1. **Customer-controlled project backups:** manually requested project packages belong to the customer's organization storage pool, count against its quota, and are visible/downloadable only to users with explicit project permissions.
2. **CUBI system/disaster-recovery backups:** automatic server/database/file-system protection is owned and operated by CUBI, uses CUBI-funded infrastructure storage separate from customer quota, and is managed only by explicitly authorized platform operations administrators. Ordinary project users and tenant/team admins must not receive raw full-system backup access merely because they are signed in or manage a project.

Do not duplicate a project backup into the customer quota merely because it is also covered by the CUBI system recovery backup. Conversely, a customer project export is not a substitute for the CUBI disaster-recovery backup.

### 13.2 CUBI system backup schedule and retention

The currently approved retention policy is:

- daily recovery points: retain 7 days;
- weekly recovery points: retain 4 weeks;
- monthly recovery points: retain 3 months.

Store system backups independently from the primary server/storage failure domain. Protect them with appropriate access controls, encryption, integrity manifests/checksums and auditable administrative access. Configure and test recovery procedures. Do not claim point-in-time recovery, a particular RPO/RTO, or complete recovery of a deployment component until the relevant mechanism is configured and an actual restore test proves it.

### 13.3 Backup & Restore user interface

- Add the customer-facing backup controls under the visual workspace's **Settings → Backup & Restore**.
- Show customer-visible manual project backups by permitted project, including latest version, history, size, date, status, quota consumed and download/restore actions.
- Do not expose CUBI-wide database dumps, server snapshots, unrelated tenants' project names, metadata, counts or artifacts in the customer panel.
- Platform-wide backup schedules, retention, integrity monitoring and restore controls belong in a separate restricted CUBI operations/admin interface.
- Enforce permission checks server-side for backup creation, queued work, artifact generation, download, deletion and restore. Re-check permissions at execution and download time; log actor, scope, decision and outcome.

---

## 14. Product-owner-approved project member access model — 2026-11-01

This section refines the scoped-role and form-only access contract in section 4 and issue [#1605](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1605).

### 14.1 Project creator is the initial project administrator

- The account that creates a project is its initial project administrator/project manager and is responsible for granting, changing and revoking project-member permissions.
- Keep project administrator/project manager distinct from subscription owner and team owner. They may be the same person, but the concepts and permissions are not interchangeable.
- The project administrator can assign permissions separately to each member and separately for each project; team membership must never grant blanket access to every project.

### 14.2 Explicit permission scopes and capabilities

The access model must support, at minimum:

- read-only access to the entire project;
- read-only access to selected WBS nodes/branches;
- read-and-write access to the entire project;
- read-and-write access restricted to selected WBS nodes/branches;
- access only to specifically assigned forms, with no general project browsing;
- submit-only access to designated daily field logs/forms for a date/project/work area;
- submit-and-wait-for-approval access for proposed changes to an assigned project section;
- approve, reject or request-correction access only for explicitly assigned workflows and scopes.

Resolve grants by authenticated actor, organization/tenant, project, WBS/form/record scope, requested action, current membership/entitlement and current project revision. A role label is not a substitute for the underlying permission. WBS branch access must be enforced against the canonical WBS hierarchy on the server; the UI must not infer access from activity rows or client-side filters.

### 14.3 Separate data submission from authoritative project mutation

- **Direct editing:** a member with explicit write permission can mutate only the permitted project/WBS scope, subject to validation, revision checks and audit.
- **Submission-only:** a member can enter and submit information using only the assigned form or daily-log interface. The submission is a separate pending record and does not immediately alter authoritative project, schedule, progress, quantity, resource or cost data.
- **Approval and application:** a separately authorized, designated approver reviews the pending submission and may approve, reject or request correction. Only an approved submission can be applied to the specified project record, through the authoritative application/domain services, with fresh permission and project-revision checks, transaction/idempotency protection, read-back and audit.
- A submitter cannot approve their own submission unless an explicit separately reviewed policy allows it; the default is separation of duties.
- Preserve the original submission and the full decision/revision history. Record submitter, submission time, target project/WBS/form/date, approver, decision time, decision reason, applied revision and final outcome.
- Unapproved or rejected field records must not enter official progress, accepted quantities, resource consumption, schedule actuals or management-report totals.

### 14.4 Daily field reporting

- A field worker may be restricted to submitting a daily report for a specified project, work area/WBS and reporting date.
- The form may collect only the fields assigned by the project administrator, such as work performed, quantities, labor, equipment, materials, photos/evidence and notes.
- The worker must not gain access to the activity grid, schedule settings, relationships, calendars, costs or unrelated project records unless separately authorized.
- A daily report is stored under its project/date context. Any requested update to authoritative activity progress, actuals, quantities, resources or costs follows the submit → review → approve → apply boundary above.

### 14.5 Security, revocation and audit

- Enforce permissions at the server/application boundary for every read, search, create, update, delete, form open, submission, attachment upload/download, approval, export, background job and restore. Hiding controls in the UI is not authorization.
- Apply least privilege and fail closed for missing, expired, stale or ambiguous grants.
- Scope-check every object by tenant/team/project and, where applicable, WBS branch, form assignment and record.
- Revoking or changing a member's permissions blocks future unauthorized access immediately while retaining legitimate project history and audit records.
- Pro entitlement expiry follows the existing limited-mode policy: preserve data and history; remove write capabilities that require active Pro and retain only the permitted read-only access until renewed or otherwise resolved by the configured entitlement policy.
- Add tests for cross-tenant/project access, guessed IDs, WBS ancestor/descendant boundaries, form-only users, submitter/approver separation, approval application, stale revisions, revocation and audit completeness.

### 14.6 Implementation status rule

These are approved product requirements, **not claims of completed implementation**. They must be delivered through versioned contracts, persisted authorization grants, server-side application services, UI, audit, migration and end-to-end tests. Do not mark complete based only on documentation, a UI-hidden control or a mock workflow.
