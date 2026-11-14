# P6 EPPM V26 vs P6 Professional V26 — Team Member, Status Update, Timesheet and Approval Lifecycle Matrix

- **Status:** Topic-level comparison completed for the cited V26 lifecycle pages; exhaustive field-by-field Team Member/API parity remains open.
- **Prepared:** 2026-11-14
- **Parent audit:** `PRIMAVERA_P6_EPPM_V26_VS_PROFESSIONAL_V26_DIFFERENCE_AUDIT.md`
- **Related child matrix:** `EPPM_V26_SECURITY_USER_ACCESS_OBS_DASHBOARD_PERMISSION_MATRIX.md`
- **Scope:** Oracle product/documentation analysis only. No CUBI Workspace, scheduler, menu, data flow, or Professional V26 implementation changes.

## 1. Critical interpretation

“P6 EPPM Only” in Professional Help identifies a workflow tied to the EPPM database/application context; it does **not** mean the feature is unusable from the P6 Professional desktop client. Oracle's V26 Professional Help explicitly includes:
- Tools > Approvals (P6 EPPM Only), including Timesheets.
- Status Updates dialog box (P6 EPPM only), allowing review of Team Member updates.
- Reflection + Activity Owner status collection (P6 EPPM Only).

Professional connected to an EPPM database can therefore participate in these EPPM-backed approval workflows. The P6 Team Member Web/mobile applications and EPPM browser approval pages remain separate user surfaces; they are not embedded in the Professional desktop merely because it connects to an EPPM database.

## 2. Lifecycle comparison matrix

| ID | Lifecycle area | EPPM V26 documented behavior | Professional V26 documented behavior | Classification / exact conclusion |
|---|---|---|---|---|
| TM-001 | Team Member product surface | P6 Team Member Web is a status/time reporting application; users see assigned activities and report progress through activity lists or timesheets. Mobile apps are also supported. | Professional is a desktop client. It is not the Team Member Web/mobile interface. | EPPM WEB/MOBILE SURFACE — CONFIRMED |
| TM-002 | Activity assignment visibility | Team Member Web shows activities assigned to the user; project manager customizes available status fields and views. | Professional exposes full project/activity management subject to project/resource security, not the constrained Team Member worklist. | BOTH / DIFFERENT SURFACE — CONFIRMED |
| TM-003 | Activity status capture | Team Member can report time spent, time left, percent complete, remaining duration, dates and steps according to project preferences and configured view. | Professional can directly edit activity progress using its own activity and assignment forms. EPPM Team Member-specific status capture is a separate flow. | BOTH / DIFFERENT WORKFLOW — CONFIRMED |
| TM-004 | Update channels | EPPM progress can be captured through P6 browser, Team Member Web, iOS/Android apps and Email Statusing Service; organizations may combine methods. | Professional supports direct desktop updates and can participate in EPPM-backed Team Member/approval workflows when connected to EPPM DB. | BOTH / DIFFERENT CHANNELS — CONFIRMED |
| TM-005 | Status review default | Status update reviews are off by default; when disabled, Team Member updates are automatically approved. | Professional's EPPM-only Status Updates dialog is available in the EPPM DB context; no separate Professional-DB equivalent of the Team Member approval lifecycle was established. | EPPM DB WORKFLOW — CONFIRMED |
| TM-006 | Project-level review setup | Project Preferences > Team Member > Status Reviews enables reviews, default review requirement for new activities, review type and reviewers. | Professional Help labels Reflection + Activity Owner status collection/review EPPM Only. | EPPM DB WORKFLOW — CONFIRMED |
| TM-007 | Activity-level review requirement | Review Required can be set per activity; new-activity default can be inherited from project preference. Activities not requiring review are automatically approved. | Professional connected to EPPM DB can access the EPPM-backed review flow; Professional DB context not established as equivalent. | EPPM DB WORKFLOW — CONFIRMED |
| TM-008 | Review type | EPPM supports “Anyone can review” or “Everyone must review”. | Professional EPPM-only Status Updates dialog groups by Review type; this reflects EPPM review semantics. | EPPM DB WORKFLOW — CONFIRMED |
| TM-009 | Reviewer scope at WBS | A WBS reviewer can view/edit/approve/reject updates only for activities in that WBS node; not its child, sibling or parent nodes unless separately assigned. | EPPM-connected Professional uses the same EPPM status-review authority model. | EPPM DB SECURITY — CONFIRMED |
| TM-010 | Project-level reviewer inheritance | Project reviewer can review top-level activities and WBS nodes without a more specific reviewer; assignment to all WBS nodes is an explicit choice. | Same EPPM database-backed review model applies; desktop access does not bypass scope. | EPPM DB SECURITY — CONFIRMED |
| TM-011 | Required reviewer privilege | Status reviewers need Add/Edit Activities Except Relationships project privilege; Admin Superuser and Project Superuser can also review/update/approve. | Professional connected to EPPM DB invokes the EPPM permission model; no UI-only bypass. | EPPM DB SECURITY — CONFIRMED |
| TM-012 | Pending update actions | EPPM reviewer can approve, reject, override/edit or hold an update for later reconciliation. | Professional V26 Status Updates dialog explicitly supports approve, reject, hold and override for EPPM. | EPPM DB WORKFLOW — CONFIRMED |
| TM-013 | Multiple reviewers | Review type determines whether any one reviewer or all assigned reviewers must approve. | Professional's EPPM-only dialog exposes review type as a grouping dimension; underlying rule is EPPM-defined. | EPPM DB WORKFLOW — CONFIRMED |
| TM-014 | Pending/held updates and ongoing edits | Team members may continue updating activities while an earlier update is pending or held; displayed status reflects latest Team Member updates. | Professional reviewer sees EPPM update queue; a pending queue item is not a lock preventing Team Member changes. | EPPM DB WORKFLOW — CONFIRMED |
| TM-015 | Project checkout/exclusive lock | Pending updates for a project checked out in Professional or opened exclusively are not displayed until check-in or release of exclusive lock. | Professional checkout/exclusive-open state directly affects when EPPM review updates appear. | CROSS-CLIENT DEPENDENCY — CONFIRMED |
| TM-016 | Update History | EPPM captures Team Member activity update history; detail window can show Activity, Activity Codes, Assignments, Notebooks, Steps and UDFs. Pending/held updates remain visible regardless of approved-history time filter. | Professional connected to EPPM DB can work with EPPM project state; no claim is made that all desktop edits are represented as Team Member status submissions. | EPPM DB AUDIT — CONFIRMED |
| TM-017 | Overridden values in history | When a PM overrides a Team Member value, original value is shown in parentheses beside new value; clearing Actual Finish is represented as blank. | This is an EPPM status-update history semantic, not a generic Professional edit log. | EPPM DB AUDIT — CONFIRMED |
| TM-018 | Steps exception | Steps added/deleted by Team Members do not go through the status update approval process. | Professional can edit activity steps through its own desktop workflow; do not assume step changes enter the Team Member approval queue. | EPPM WORKFLOW EXCEPTION — CONFIRMED |
| TM-019 | Timesheet eligibility | Resource must be assigned to project activities and linked to a user account with Timesheet module access. | Professional V26 User Guide describes timesheet submission through optional Team Member Web module; Professional acts as an approval client, not the submitter interface. | BOTH / DIFFERENT SURFACE — CONFIRMED |
| TM-020 | Approval manager eligibility | Approval manager must be assigned as Approval Manager for resource; full Timesheet access is needed for full timesheet features, while dashboard Timesheet Approval page access can suffice for strictly reviewing. | Professional EPPM-only Approvals workflow can approve/reject for assigned responsibilities. | EPPM DB WORKFLOW — CONFIRMED |
| TM-021 | Timesheet approval roles | Project Manager and Resource Manager can be approval roles; manager or active delegate reviews resources within assigned scope. | Professional Tools > Approvals (EPPM Only) includes timesheet approvals, delegates and notes. | EPPM DB WORKFLOW — CONFIRMED |
| TM-022 | Approval levels | EPPM supports no approval/auto submission, auto approval, one approval level (Resource Manager), or two levels (Project + Resource Manager); PM-first sequencing is configurable. | Professional timesheet overview describes periods and approval levels from none through two; desktop approval action follows configured EPPM settings. | BOTH / SAME EPPM CONFIGURATION — CONFIRMED |
| TM-023 | Two-stage state semantics | PM Approved and RM Approved are intermediate states valid only when two approval levels are required; the second manager's Action Required view reflects the pending step. | Professional can process EPPM timesheets under the configured approval role; status semantics are not Professional-only. | EPPM DB WORKFLOW — CONFIRMED |
| TM-024 | Approval action | EPPM Approvals > Timesheets lets manager/delegate filter Action Required or All Timesheets, select multiple records and approve/reject. | Professional Tools > Approvals includes Approving or Rejecting Timesheets (EPPM Only). | EPPM DB WORKFLOW — CONFIRMED |
| TM-025 | Timesheet delegates | Project Manager delegates by project; Resource Manager delegates for resources assigned to that manager. Delegate approval rights can be activated/deactivated. | Professional includes assign Project Manager Delegate and Resource Manager Delegate actions in EPPM-only Approvals. | EPPM DB WORKFLOW — CONFIRMED |
| TM-026 | Delegate scope | Project Manager delegate can review resources assigned to activities in projects for which PM has approval rights; Resource Manager delegate follows resources assigned to that manager. | Professional client uses same underlying EPPM delegate scopes. | EPPM DB SECURITY — CONFIRMED |
| TM-027 | Timesheet notes and communication | Manager/delegate can add notes and notify resources of status; reports can be run from P6 Reports. | Professional V26 timesheet overview explicitly includes notifying resource and adding notes. | BOTH / EPPM WORKFLOW — CONFIRMED |
| TM-028 | Timesheet audit | EPPM setting can retain submission, approval, rejection, reviewer and date history; reporting software is used to view historical data. | No separate Professional-only timesheet audit ledger established; connected Professional operates on EPPM timesheet records. | EPPM DB AUDIT — CONFIRMED |
| TM-029 | Email notifications | Application settings can send notifications for submissions, approvals and rejections; administrator settings include daily status emails. Rejection notifications may go to relevant managers/delegates and superusers. | Professional can notify resources from EPPM timesheet approval workflow; mail delivery depends on EPPM/admin configuration. | EPPM CONFIGURATION-DEPENDENT — CONFIRMED |
| TM-030 | Rejection restrictions | Administrator can prevent rejection of timesheets submitted before current week/month, or prevent rejection altogether; approved-timesheet rejection can have configurable time window. | Professional approval UI is subject to the EPPM application settings and server rules. | EPPM CONFIGURATION-DEPENDENT — CONFIRMED |
| TM-031 | Timesheet auto-approval | If auto-approval is configured, manager approval is not required for submission; managers may still review and reject in supported workflow. | Professional approval feature remains present in EPPM context; no manual approval requirement should be assumed. | EPPM CONFIGURATION-DEPENDENT — CONFIRMED |
| TM-032 | Timesheet unit variance | Approval page can show Approved Units, Planned Units and Variance Units to detect approved work exceeding plan. | Professional Timesheets approval view supports review of timesheets; exact column parity in each Professional client release should be checked in UI/topic details. | BOTH / DIFFERENT SURFACE — PARTIALLY VERIFIED |
| TM-033 | Team Member activity update field controls | Project preferences define which activity updates are allowed, including completion/date behavior and owner assignment; project manager customizes Team Member view fields. | Professional full editing permissions are separate from Team Member field-level restrictions. | EPPM WEB CONFIGURATION — CONFIRMED |
| TM-034 | Activity owner assignment | Team Member Web may allow self-assignment as owner, assignment of others, reassignment, and outside-OBS access depending on project settings. | Professional Help labels Designating an Activity Owner EPPM Only; available through EPPM DB context. | EPPM DB FEATURE — CONFIRMED |
| TM-035 | Reflection collection/review | EPPM supports Reflection + Activity Owner status collection/review workflow. | Professional Help explicitly labels “Using Reflection projects and Activity Owner features to collect and review activity status” P6 EPPM Only. | EPPM DB FEATURE — CONFIRMED |
| TM-036 | API representation | EPPM guide set provides REST API, SOAP and data dictionary; TimesheetDelegate is a read-only business object in Integration API and carries delegation scope. | Professional UI evidence does not establish endpoint/field parity; API contract must be taken from EPPM V26 API docs. | EPPM API — CONFIRMED existence; full endpoint parity NOT VERIFIED |

## 3. State and approval lifecycle

### 3.1 Team Member activity status

1. Project manager configures Team Member fields, permissions and whether review is enabled.
2. Resource/owner receives assigned activities in Team Member Web/mobile or other configured channel.
3. Team Member submits/saves status. The update appears in the EPPM Status Updates page.
4. If review is disabled or activity is not marked Review Required, the update is auto-approved.
5. If review is required, authorized reviewer(s) can inspect, edit/override, approve, reject or hold.
6. Team Member may continue to send later updates while a previous update is pending/held.
7. Activity Update History records changes and exposes pending/held updates even when approved-history date filters are used.
8. A Professional checkout/exclusive lock can delay visibility of pending EPPM updates until check-in/unlock.

### 3.2 Timesheet

1. Resource is assigned to activities and has a P6 user account with Timesheet module access.
2. Resource enters work in Team Member Web timesheet for a configured period.
3. The timesheet is submitted, auto-submitted, or auto-approved according to application settings.
4. Approval routing is configured as none/automatic, Resource Manager only, or Project Manager + Resource Manager; PM-first may be required.
5. Assigned manager or active delegate reviews Action Required timesheets, checks hours/variance and adds notes if needed.
6. Manager approves or rejects; notifications depend on configured email settings.
7. Timesheet audit setting can preserve submission/approval/rejection/reviewer/date history for reporting.

## 4. Product conclusions

1. **Timesheets are not absent from Professional.** Professional V26 explicitly documents Tools > Approvals (P6 EPPM Only), timesheet overview, approval/rejection, delegates and notes. Professional is an approval client for the EPPM-backed workflow; Team Member Web is the time-entry surface.
2. **Status Updates are an EPPM DB capability surfaced in Professional.** Professional Help has a dedicated EPPM-only Status Updates dialog. This is not a Professional-database-only feature.
3. **Team Member Web/mobile is not the Professional desktop UI.** Both can interact with the same EPPM project data through distinct roles and interfaces.
4. **Activity status review and timesheet approval are separate workflows.** Status review applies Team Member activity-field changes; timesheet approval processes time records/units. They must not be merged into one generic approval status.
5. **Approval routing is configurable.** No approval, auto approval, one-level and two-level flows exist. A generic “pending approval” label loses critical state information (PM Approved vs RM Approved).
6. **Review authority is scope-bound.** WBS reviewer, project reviewer, Admin Superuser and Project Superuser have different reach. A user should not see all pending items merely because they are labelled “manager”.
7. **A pending status update is not a write lock.** New Team Member updates can arrive before the previous update is resolved; the current status card reflects latest updates.
8. **Some changes bypass status approval.** Team Member step additions/deletions do not go through status update approval.
9. **Audit is configurable and differs by record type.** Activity Update History and Timesheet Audit are distinct stores/reporting paths; enabling one must not be assumed to enable the other.
10. **Professional checkout state affects review visibility.** A checked-out/exclusively opened project can temporarily hide pending updates until check-in/release.
11. **Email notification is not the source of truth.** It depends on administrator/application settings; the authoritative state remains the approval record and history in P6.
12. **Personal dashboard/menu implications:** a “My Actions” count must separately calculate activity status updates, timesheets, delegates, review type and role scope; it must not combine them or leak records outside project/resource authorization.

## 5. Direct Oracle Version 26 sources

### EPPM Help / User Guide / Team Member
- About P6 Team Member Status Updates:
  https://docs.oracle.com/cd/G48897_01/p6help/en/50904_1.htm
- Configuring P6 Team Member Status Update Reviews:
  https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_user/50915.htm
- Reviewing Team Member Status Updates:
  https://docs.oracle.com/cd/G48897_01/p6help/pt_BR/51331.htm
- Viewing Team Member Status Updates History:
  https://docs.oracle.com/cd/G48897_01/p6help/en/51471_1.htm
- About Updating Progress:
  https://docs.oracle.com/cd/G48897_01/p6help/en/6626.htm
- Team Member tab / Project Preferences:
  https://docs.oracle.com/cd/G48897_01/p6help/en/91692.htm
- Working with Timesheets:
  https://docs.oracle.com/cd/G48897_01/p6help/en/6670.htm
- Approving or Rejecting Timesheets:
  https://docs.oracle.com/cd/G48897_01/p6help/en/7847_1.htm
- Timesheets Page:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/5972.html
- Configuring Timesheets Settings:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/configuringtimesheetssettings-36211a.html
- P6 Team Member Web Overview:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-tm/p6-tmw_overview-51690a.html
- Updating Activities:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-tm/updatingactivities-50734a.html
- Configuring Application Settings (Team Member):
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-tm/configuringapplicationsettings-88584a.html
- TimesheetDelegate Integration API object:
  https://docs.oracle.com/cd/G48897_01/English/Integration_Documentation/p6_eppm_api_reference/com/primavera/integration/client/bo/object/TimesheetDelegate.html

### Professional V26 Help / User Guide
- Professional V26 Help TOC (Approvals EPPM Only, Status Updates dialog EPPM Only, Activity Owner/Reflection EPPM Only):
  https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm
- Status Updates dialog box (P6 EPPM only):
  https://docs.oracle.com/cd/G48902_01/client_help/en_US/113059.htm
- Timesheets overview:
  https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/102615.htm

## 6. Open technical gaps — do not overclaim

- Full V26 Team Member field matrix across Web, iOS and Android, including every project preference toggle and editable field.
- Exact state transition diagram and persistence semantics for repeated pending/rejected/held updates, including concurrency and stale cards.
- Complete email statusing message formats, parser rules, supported fields, and error/retry behavior.
- Full REST/SOAP endpoint and Data Dictionary mapping for Timesheet, TimesheetPeriod, TimesheetApproval, TimesheetDelegate, StatusUpdate and history entities.
- Complete timesheet validation rules: future periods, negative hours, date bounds, assignment-level vs activity-level entry, rounding and unit conversion.
- Exact report schema and retention behavior for timesheet audit and activity update history.
- Independent review against the complete V26 Team Member and Professional guide pages.

These gaps remain explicitly NOT VERIFIED; this child matrix is topic-level lifecycle comparison, not complete field/API parity.

## 7. CUBI boundary

This is a reference analysis artifact only. It does not change current CUBI Workspace, menus, APIs, scheduler, database schema, project/activity flows, or Professional V26 parity implementation. Any future EPPM-inspired workflow requires separate product-owner approval and a separately reviewed security/data contract.
