# ENG-11 / ENG-12 — P6 Team Member Contributor & Timesheet Contract V1

**Recorded:** 2026-11-16  
**Parent program:** #1990  
**Capability register:** ENG-11 (activity-centric Team Member updates), ENG-12 (project timesheets and actual labor posting)  
**Architecture/menu/path contract:** `docs/architecture/CUBI_ENGINEERING_CAPABILITY_MENU_ACCESS_AND_PATH_OWNERSHIP_V1.md`  
**Source baseline:** main `0fc0d80ece1d3f495564fa20e32d6f2f21f10a1b`  
**Status:** documentation-first contract and source crosswalk. No implementation or parity completion is claimed.

## 1. Decision: two distinct contributor capabilities

ENG-11 and ENG-12 are related user journeys but must not be implemented as one record type:

- **ENG-11 Activity Status Update** is an assignment-scoped progress submission for a specific activity and optionally its assigned steps. It changes Engineering activity/assignment progress only through the authoritative activity status/actuals path.
- **ENG-12 Timesheet** is a period-scoped collection of time entries for a designated timesheet user, with configurable save/submit/withdraw/review/approval behavior. Approved actual labor is posted through Engineering's authoritative actuals API.
- **Enterprise generic Task** is not an activity, Team Member status update, field commitment or timesheet. It remains an organizational task domain.
- **ENG-10 Field Work Plan** remains a schedule-linked commitment/work-package lifecycle, not a substitute for either ENG-11 or ENG-12.

Do not add Team Member workflow to Enterprise Task Center and do not create parallel actual-hours storage in Progress, Resources and Workbench.

## 2. Normative source crosswalk

### P6 Team Member Web Help V26 — normative for contributor journeys

| Capability / behavior | Official V26 topic | Evidence status / implication |
|---|---|---|
| Team Member role, landing and shortcuts | [Team Member Web Overview](https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/toc.htm) | TOC verified. Includes separate My Activities and Timesheets navigation and keyboard shortcut topics. |
| Assigned activity update | [Updating Activities](https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/50734.htm) | Topic verified. Project manager configures available fields; status may include Time Spent, % Complete or Remaining Duration; steps may contribute to activity progress; save is explicit. |
| Step progress | [Updating Progress on Steps](https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/50747.htm) | Topic verified. Step progress can be updated independently; weighted/equal step contribution may affect activity % complete; step UDF visibility is configured. |
| Resubmitting status updates | [Team Member TOC entry](https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/toc.htm) → Updating Activities → Resubmitting Status Updates | TOC entry verified; target topic URL discovered as `98808.htm`, content fetch returned cache miss. Detailed rejection/resubmit semantics remain MISSING / VERIFY. |
| Timesheet eligibility and overall behavior | [Working with Timesheets](https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/88358.htm) | Topic verified. Timesheet view is available only to designated timesheet users; submission/approval settings control whether submit/withdraw is available; hours count against activities only after submission unless configured for auto-submit/approval. |
| Opening and initializing a timesheet | [Opening a Timesheet](https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/38811.htm) | Topic verified. New timesheet may auto-add current activities, manually add, or copy previous period; completed activities and copied hours depend on settings. |
| Adding activities | [Adding Activities to a Timesheet](https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/38813.htm) | TOC target discovered; detailed page fetch returned cache miss. Do not implement additional semantics until page is re-opened. |
| Recording actual work time | [Recording Actual Work Time on a Timesheet](https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/38816.htm) | TOC target discovered; detailed page fetch returned cache miss. Daily vs period entry and regular/overtime rules must be reverified from the exact topic before parity acceptance. |
| Reporting completed assignment | [Reporting a Completed Assignment](https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/38873.htm) | TOC target discovered; detailed page fetch returned cache miss. |
| Submit | [Submitting a Timesheet](https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/38818.htm) | Topic verified. Auto-submission can disable manual Submit; rejection can return timesheet for correction/resubmission. |
| Withdraw | [Withdrawing a Timesheet](https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/99142.htm) | Topic verified. A submitted timesheet may be withdrawn only before it has been approved or rejected. |
| Other-resource timesheet editing, notes, print/save, date updates | [Team Member TOC](https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/toc.htm) | TOC entries verified; exact option/privilege details remain MISSING / VERIFY until individual pages are fetched. |

### P6 EPPM V26 — project-side source

- [EPPM V26 global Help TOC](https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm) and [Activities feature-family TOC](https://docs.oracle.com/cd/G48897_01/p6help/en/44475.htm) include activity progress, Team Member status updates, timesheets and financial-period/actual concepts.
- [EPPM Timesheets page](https://docs.oracle.com/cd/G48897_01/p6help/en/5972.htm) and [About Timesheets](https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_user/6610.htm) are registered in the master crosswalk. Exact project-manager approval configuration, security privileges and actuals-application details still need row-level topic extraction.
- Team Member Web Help is a separate normative contributor surface; EPPM project configuration and calculation semantics complement it but do not replace it.

### Primavera Cloud

Cloud Timesheets is a comparative source only where the behavior adds an extension. It must not replace the EPPM V26 + Team Member V26 semantics or be used as the sole source for parity.

## 3. Current-main foundation and boundary

At the inspected main SHA:

- `src/construction_pm/p6_activity_period_actual_api.py` exposes `p6-activity-period-actual-api.v1`, with project-scoped create/get/list and PROJECT_WRITE / PROJECT_READ checks. It stores immutable activity-period actual facts (units/cost, unit, currency, note).
- The Web Progress workspace already has a Stored Period Performance flow backed by this API. The state ledger records idempotent identity `SPP-<activity>-<period>` and a deterministic replay contract.
- This is **not** a timesheet aggregate: it has no timesheet header, period status, line lifecycle, submit/withdraw, approver/rejection state, overtime/day allocation, or Team Member eligibility.
- PR #1974 currently touches `p6_activity_period_actual_api.py`, period actual persistence and broad production composition / identity / schema / main.ts. Do not modify these paths while that PR is open without explicit handoff.
- PR #1929 owns Enterprise Task domain paths. Do not reuse or alter its task entity to represent timesheets.
- PR #1711 / #1971 / #1983 also occupy main workspace, authorization, production composition and activity-related surfaces. Recheck changed files before any implementation.

The actual-period API is a downstream posting boundary, not the timesheet source-of-truth.

## 4. Domain contract

### ENG-11 — Activity Status Update

A proposed typed aggregate must include:
- `status_update_id`, `tenant_id`, `project_id`, `activity_id`, assigned `resource_id`, submitting `actor_id`;
- source `activity_revision`, optional assignment revision, permitted field-set/version and project progress configuration version;
- typed status payload: started/completed state, time spent or additional time, remaining duration or configured percent complete, expected/finish-by date, step progress and allowed UDFs;
- lifecycle state: draft → submitted → accepted/rejected → resubmitted, with withdrawn only where source semantics permit;
- immutable submission/review events, reviewer, decision, timestamp, reason, correlation ID and idempotency key.

Rules:
1. Server resolves actor, tenant, project and assignment; client-supplied IDs are references only and are reauthorized.
2. Only assigned resources may update their own activity unless a separately granted delegate privilege is present.
3. Field availability is driven by project configuration and explicit permission; do not expose every P6 field unconditionally.
4. A locked project, stale activity/assignment revision, closed period or already-approved status update must fail closed with typed conflict codes.
5. Step completion/weighted progress must use the existing Engineering step and progress semantics. Do not calculate activity % complete a second time in the browser.
6. Status submission/review workflow can be orchestrated by Shared/Enterprise workflow infrastructure, but Engineering validates and commits the activity mutation.

### ENG-12 — Timesheet

A proposed typed aggregate must include:
- `timesheet_id`, tenant/project/resource owner, period start/end and calendar/time-zone context;
- designated timesheet-user eligibility snapshot and period/configuration version;
- lines referencing either a project activity/assignment or an explicitly permitted overhead code; never free-form untyped task links;
- line values for work date or reporting bucket, regular/overtime hours, configured unit representation, optional note and source assignment/activity revisions;
- lifecycle state: `NOT_STARTED`, `DRAFT`, `SUBMITTED`, `WITHDRAWN`, `REJECTED`, `APPROVED`, `POSTED` (final states and transitions must be reconciled with exact EPPM/Team Member approval configuration before implementation);
- approval/rejection event history, reviewer, decision, reason, notification/outbox event, posting receipt and immutable audit trail.

Rules:
1. A user without timesheet designation must not see or call timesheet operations. Eligibility is checked server-side for every read/write/submit.
2. Period range, allowed project/activity set, overhead codes, decimal vs HH:MM vs quarter-hour rounding, regular/overtime and day-vs-period entry are configuration-driven. Exact source option semantics remain a pre-implementation verification gate.
3. Save draft never posts actuals. Submit freezes the submitted revision; withdrawal is permitted only while source workflow allows it. Rejection reopens only the explicitly rejected revision for correction and resubmission.
4. Auto-submit and auto-approval are explicit administrator configuration. When enabled, the corresponding manual command is unavailable; do not show a fake enabled button.
5. Approval must be idempotent. Only an approved/auto-approved timesheet posts Engineering actual labor, and each source line maps exactly once to the authoritative activity-period actual posting boundary.
6. Never silently overwrite a previously posted actual. Corrections require a new revision/adjustment or an explicit compensating transaction with full provenance.
7. Actual labor posting uses Engineering's authoritative activity/period actuals and progress/EVM pipeline. Timesheet is the contributor workflow; it does not become a second actuals or EVM engine.

## 5. Ownership, menus and access

| Concern | Owner | Entry point |
|---|---|---|
| Activity, assignment, step, progress and actual labor facts | Engineering | Project → Activities / Schedule; Activity Details → Team Update; Project → Progress |
| Timesheet entry and contributor review journey | Engineering | Workbench → My Work → Timesheets |
| Organization membership, user identity and team assignment authority | Enterprise Organization & Access / Shared identity primitives | Organization & Access; no duplicate Engineering identity store |
| Approval workflow definitions, delegation, notification policy | Enterprise Workflow Studio / Shared durable workflow runtime | Workflow Studio; embedded approval actions in Timesheets |
| Actuals posting and EVM recalculation | Engineering | Existing authoritative Progress/actuals service |
| Workbench navigation/presentation | Shared Workbench | Permission-filtered projection; not the business-data owner |

Permission actions must be distinct: `timesheet.view_own`, `timesheet.create_own`, `timesheet.update_own_draft`, `timesheet.submit_own`, `timesheet.withdraw_own`, `timesheet.view_team`, `timesheet.edit_other`, `timesheet.review`, `timesheet.approve`, `timesheet.configure`, and `activity.status_update.submit`. These are proposed action identifiers, not claims that the current authorization enum already supports them. Map them to canonical CUBI grants before code.

## 6. API and persistence boundaries — proposed, not yet implemented

- `engineering-team-member-api.v1`: assigned activity list, allowed field schema, status-update draft/submit/withdraw/resubmit and review outcomes.
- `engineering-timesheet-api.v1`: eligible period list, timesheet create/open, line add/remove/update, draft save, submit, withdraw, rejection correction and status/history reads.
- `engineering-timesheet-approval-api.v1`: approval task resolution and decision event; may be backed by shared workflow runtime but the final mutation remains Engineering-owned.
- `p6-activity-period-actual-api.v1`: downstream posting adapter only. Keep its existing scope/revision/idempotency contract; do not overload it with timesheet lifecycle.

Persistence must separate timesheet aggregate/lines from activity-period actual facts. Required invariants include unique period/resource identity, line-to-assignment validation, no cross-tenant/project references, expected revision on mutation, transactionally recorded approval + posting intent, outbox/idempotency for posting, and recoverable failure states. Schema changes wait until PR #1974 path ownership is resolved.

## 7. Required acceptance matrix

| Journey | Positive proof | Negative / edge proof |
|---|---|---|
| Eligibility | Designated user sees only their allowed timesheets and periods | Non-designated user receives no list/data and cannot call direct API |
| Open/create | New period initializes using configured current/previous/manual activity selection | Inactive project, wrong period, invalid assignment, completed activity rule |
| Entry | Daily/period, regular/overtime and configured numeric representation round-trip exactly | Invalid precision, quarter-hour rounding, negative/overflow values, timezone/day-boundary |
| Draft | Save/read-back is revision-safe and does not post actuals | Stale revision, duplicate request, partial line write rollback |
| Submit | Submission freezes the exact revision and emits one review event | Auto-submit configured, duplicate submit, unauthorized actor |
| Withdraw | Allowed before approval under configured workflow | Already approved/rejected/posted; withdrawal after finalization |
| Reject/resubmit | Rejection reason preserved; corrected revision can be resubmitted | Wrong reviewer, stale rejected revision, silent mutation of submitted snapshot |
| Approve/post | One approved timesheet maps once to correct activity-period actuals | Retry, duplicate approval, posting outage, partial failure, altered source line |
| Team Member activity update | Allowed configured fields and steps save with revision/audit | Unassigned actor, locked project, stale revision, unauthorized UDF/field |
| Cross-domain isolation | Workbench and Enterprise approvals show permission-filtered projections | Cross-tenant/project/WBS/object leakage; generic Task cannot mutate Activity or Timesheet |

## 8. Non-interference and execution handoff

This packet is documentation-only. Before code:
1. Re-fetch main SHA, all open PR heads/files/checks and root/nested `AGENTS.md` from the canonical checkout.
2. Resolve PR #1974 ownership for activity-period actual API/repository/schema/production composition; resolve PR #1929 for Enterprise Task separation; refresh #1711/#1971/#1983 workspace/activity/authorization overlaps.
3. Assign one exact allowed path set to one Qoder task. Do not touch shared `main.ts`, workspace model/view, authorization, production composition or schema until explicit handoff.
4. Re-open Team Member TOC child pages with cache misses (Resubmit, Add Activities, Recording Actual Work Time, Reporting Completed Assignment, Editing Other Resource Timesheets, Notes) and EPPM approval/privilege topics; record exact page-level option semantics.
5. Only then split ENG-11 and ENG-12 into independent implementation PRs. Do not bundle both aggregates into one broad implementation.

Qoder had no available tokens at the last coordination check. This packet does not claim code execution, tests, UI parity, approval parity or shipped functionality.


## 9. Additional P6 EPPM V26 review and timesheet configuration evidence (2026-11-16)

The following official V26 topics were retrieved and checked after the initial contract packet. These close several previously open questions, but do not remove the need to verify every linked procedure and UI option.

### ENG-11 — status-update review

- [About P6 Team Member Status Updates](https://docs.oracle.com/cd/G48897_01/p6help/en/50904_1.htm): the project manager can review, update, approve and reject activity progress before it is committed to the schedule. Project Preferences controls whether review is enabled, required by default, the review type and assigned reviewers. Search result verified; direct page retrieval returned cache miss.
- [Configuring P6 Team Member Status Update Reviews](https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_user/50915.htm): review is off by default; review type supports Anyone can review or Everyone must review; pending reviews prevent changing review type; reviewers can be assigned at project/WBS scope; activity-level Review Required can disable review, causing auto-approval; reviewers can continue receiving updates while a prior review is pending. The assigned reviewers or Admin/Project Superuser can view/edit/approve; only designated reviewers receive pending-review notifications.
- [Reviewing Team Member Status Updates](https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_user/51331.htm): review can approve, reject, edit or hold updates; multiple reviewers may be configured with any-reviewer or all-reviewer acceptance; pending/held updates can receive further team-member updates; pending updates are hidden while the project is checked out in P6 Professional or exclusively locked; step additions/deletions do not go through the activity status approval process.
- [Team Member project preference fields](https://docs.oracle.com/cd/G48897_01/p6help/en/91692.htm): project configuration determines whether primary resources can complete activities without approval or update activity dates; controls step add/delete, notebook updates and status for other resource assignments; review settings and status reviewer privilege requirements are project-configurable. Search result verified; exact detail should be re-opened during implementation source review.

**Contract refinement:** ENG-11 must model the configured review policy at project/WBS/activity scope, including Anyone vs Everyone reviewer semantics, hold, edit/override, reject, activity auto-approval when review is not required, and continuing updates while review is pending. Step add/delete is a separate permissioned operation and must not be assumed to be covered by activity status approval. Exclusive lock/checkout visibility is a source behavior that must be handled explicitly, not silently bypassed.

### ENG-12 — timesheet settings and approval

- [Configuring Timesheets Settings](https://docs.oracle.com/cd/G48897_01/p6help/en/36211.htm): the V26 application settings include resource self-assignment defaults, matching Team Member role assignment, timesheet auditing and approval configuration. Search result verified; direct page retrieval returned cache miss.
- [Timesheets Implementation](https://docs.oracle.com/cd/G48897_01/English/Admin/p6_eppm_application_admin/7532.htm): the V26 administrator guide identifies setup topics for timesheet resources, periods, overhead codes and Timesheet Approval access. Search result verified.
- [Timesheets (P6 EPPM Only)](https://docs.oracle.com/cd/F88968_01/client_help/en_US/102615.htm): timesheets are period-based and have approval levels; the period may range from one week to one month; approval levels range from no approval to two levels; designated project/resource approval managers or delegates can approve/reject, notify resources, inspect started/submitted state and add notes. This is a P6 Professional V26 comparative source, not a replacement for EPPM/Team Member semantics.
- [Working with Timesheets](https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/88358.htm): designated-user eligibility, submission/withdrawal, auto-submission/auto-approval behavior, adding activities/overhead time and privilege-gated editing of other resources' timesheets are confirmed.

**Contract refinement:** ENG-12 must not hard-code one approval step. The source includes period and approval-level configuration, manager/delegate roles, auditing, overhead codes, resource eligibility and conditional manual commands. The exact V26 EPPM settings page and the linked approval/privilege procedures remain an implementation source gate where direct retrieval was unavailable. P6 Professional material is supplementary evidence only.

## 10. Source status after this pass

| Source area | Status | Remaining gate |
|---|---|---|
| Team Member V26 activity update, steps, open/submit/withdraw timesheets | PARTIALLY VERIFIED | Child pages still missing/cache-miss: resubmit, add activities, recording actual work time, completed assignment, edit other resource timesheets, notes |
| EPPM V26 status review | VERIFIED for high-level review model | Re-open exact linked accept/reject/hold/history/override and project preference topics during implementation |
| EPPM V26 timesheet settings | PARTIALLY VERIFIED | Direct settings page cache miss; retrieve detailed option semantics and approval application privilege pages |
| P6 Professional V26 timesheet approval | COMPARATIVE ONLY | Do not use as normative replacement for EPPM/Team Member |
| Cloud Timesheets | COMPARATIVE ONLY | Use only for additive extension behavior |

The packet remains documentation-only. These source findings improve contract readiness; they do not authorize edits to the activity/actuals API, approval runtime, schema, authorization or workspace paths occupied by active PRs.
