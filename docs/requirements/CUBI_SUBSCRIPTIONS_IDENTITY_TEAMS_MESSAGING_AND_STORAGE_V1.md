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
