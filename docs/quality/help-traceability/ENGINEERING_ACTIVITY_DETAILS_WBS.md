# Engineering — Activity Details and Work Breakdown Structure

Section 3 of the Help traceability workstream.
Verified: 2026-11-21 · Canonical rows: `docs/traceability/engineering-v26.json`
(`ENG-WS-DETAILS`, `ENG-WS-WBS`, `ENG-WS-STEPS`, `ENG-WS-ACTIVITY-CODES`,
`ENG-WS-UDF`).
Help baseline: P6 Professional V26 HTML Help (`G48902-01`) and User Guide
(`G57529-01`). Every Help URL below returned HTTP 200 and is listed in the
official TOC; every User Guide URL returned HTTP 200 with a matching `<title>`
(see `OFFICIAL_HELP_BASELINE.md` and the section report).

## 1. Scope

This section covers the Activity Details pane of the Activities window
(`/app/activities/`) and the Work Breakdown Structure window (`/app/wbs/`):
the sixteen Version 26 detail tabs plus the CUBI calendar tab, tab
customization, each tab's read/write behavior, the WBS hierarchy, table and
chart views, element add/edit/delete, clipboard operations, WBS details,
status, weighted milestones, and the activity-to-WBS assignment.

It does **not** restate the activity table, columns, sorting or exports
(Section 2), the Gantt chart or relationships editor (Section 4), or the
resources/costs windows (Section 5). Row IDs reuse the canonical index where
one exists.

Status semantics:

- **Doc status** — `DOCUMENTED`, `HELP_VERIFIED`, `TEST_SPECIFIED`.
- **Product status** — the observed implementation state in this repository:
  `IMPLEMENTED`, `PARTIAL`, `NOT_IMPLEMENTED`. It is never derived from this
  document. `FUNCTIONALLY_VERIFIED` requires an executed run and is not
  claimed in this section.

`Env` is **Engineering** for every row.

## 2. Traceability matrix

| Row ID | Page | Functional item | Help topic · section | Direct Help URL | User Guide · URL | Expected behavior (from Help) | Inputs and validation | Scenario | Doc status | Product status · evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ENG-WS-DETAILS | `/app/activities/` | Open the Details pane | Display window details · Getting Started > Workspace Basics | https://docs.oracle.com/cd/G48902_01/client_help/en_US/display_window_details.htm | Display window details · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/displaywindowdetails-18627a.html | Details for the selected record are displayed below the window; the same pane is available for projects, resources and activities. | A record must be selected; with no selection the pane states that a selection is required. | ENG-ACT-DET-01 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-activity-details.test.ts` |
| ENG-WS-DETAILS | `/app/activities/` | Customize the detail tab set and order | Customize Activity Details · Customizing Activity Layouts > Overview | https://docs.oracle.com/cd/G48902_01/client_help/en_US/customize_activity_details.htm | No verified direct section URL | Tabs move between the Available and Display lists; Add, Add All, Remove, Remove All, Move Up, Move Down change the display set; Apply previews and OK commits. | At least one tab stays displayed; a removed tab stays listed as available; the order is the tab order. | ENG-ACT-DET-02 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-activity-details.test.ts` |
| ENG-WS-DETAILS | `/app/activities/` | General tab | Define general activity information · Developing Projects > Adding Activities to a Project | https://docs.oracle.com/cd/G48902_01/client_help/en_US/define_general_activity_information.htm | Define general activity information · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/definegeneralactivityinformation-19531a.html | The tab shows the activity's general information (type, duration type, cost account, calendar, WBS, responsible manager, description and similar fields). | Values are read from the authoritative record; a field the read model does not return is shown as not available, never estimated. | ENG-ACT-DET-03 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-activity-details.test.ts` |
| ENG-WS-DETAILS | `/app/activities/` | Status tab — progress facts | Update progress for individual activities · Managing Projects > Updating Projects | https://docs.oracle.com/cd/G48902_01/client_help/en_US/update_progress_for_individual_activities_manually.htm | Update progress for individual activities · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/updateprogressforindividualactivities-19629a.html | The Status tab shows durations, started/finished, actual dates, percent complete, units and costs for the selected activity. | Progress figures are read from the authoritative record; editing progress happens through the progress service, not by local recalculation. | ENG-ACT-DET-04 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `PARTIAL` · read-only values plus a constraint editor; `apps/web/src/workspace-activity-details.test.ts` |
| ENG-WS-DETAILS | `/app/activities/` | Resources tab | Assign resources to activities · Developing Projects > Assigning Resources and Roles to Activities | https://docs.oracle.com/cd/G48902_01/client_help/en_US/assign_resources_to_activities.htm | Assign resources to activities · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/assignresourcestoactivities-18731a.html | The Resources tab lists the selected activity's assignments and adds a resource assignment. | A resource must be selected and permitted by resource security; the new assignment is written to the authoritative list. | ENG-ACT-DET-05 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `PARTIAL` · list plus add form; remove and assign-by-role disabled · `apps/web/src/workspace-activity-details.test.ts`, `apps/web/src/workspace-assignments.test.ts` |
| ENG-WS-DETAILS | `/app/activities/` | Resource tab columns | Change Resources tab columns · Structuring Projects > Defining Resources and Roles > Resources | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_resources_tab_columns.htm | No verified direct section URL | Right-clicking the Resources tab customizes which columns are shown. | Column set is presentation state; removing a column never removes the assignment. | ENG-ACT-DET-05 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `NOT_IMPLEMENTED` · fixed column set in `apps/web/src/workspace-activity-details.ts` |
| ENG-WS-DETAILS | `/app/activities/` | Predecessors, Successors and Relationships tabs | View activity relationships in Activity Details · Developing Projects > Linking Activities with Relationships > Viewing activity relationships | https://docs.oracle.com/cd/G48902_01/client_help/en_US/19567.htm | View activity relationships in Activity Details · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/viewactivityrelationshipsinactivitydetails-19567a.html | The tabs list the selected activity's incoming and outgoing relationships with type and lag; the combined tab shows both. | A predecessor row has the selected activity as its successor and vice versa; lag keeps its unit. | ENG-ACT-DET-06 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-activity-details.test.ts` |
| ENG-WS-DETAILS | `/app/activities/` | Predecessor/Successor tab columns | Change Predecessors tab columns · Developing Projects > Linking Activities with Relationships | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_predecessors_tab_columns.htm | No verified direct section URL | The Predecessors and Successors tabs have customizable column sets. | Column customization changes only presentation. | ENG-ACT-DET-06 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `NOT_IMPLEMENTED` · fixed relationship columns |
| ENG-WS-ACTIVITY-CODES | `/app/activities/` | Codes tab | Assign activity codes and values to activities · Structuring Projects > Defining Project, Resource, and Activity Codes > Activity Codes | https://docs.oracle.com/cd/G48902_01/client_help/en_US/assign_activity_codes_and_values_to_activities.htm | Activity codes and values · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/activitycodesandvalues-18851a.html | The Codes tab shows the activity's code/value assignments and allows assigning or removing them. | Assignment needs a defined code and value; removing an assignment keeps the activity. | ENG-ACT-DET-07 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `PARTIAL` · reads show no assignments and Assign/Remove are disabled · canonical `ENG-WS-ACTIVITY-CODES` is `PARTIAL` |
| ENG-WS-DETAILS | `/app/activities/` | Notebook tab | Assign notebooks to activities · Developing Projects > Assigning Notebooks to Activities | https://docs.oracle.com/cd/G48902_01/client_help/en_US/assign_notebooks_to_activities.htm | Assign notebooks to activities · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/assignnotebookstoactivities-19605a.html | Notebook topics attached to the activity are shown and can be added, modified or deleted. | A notebook topic must exist; notes are project records, not a local scratchpad. | ENG-ACT-DET-08 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `PARTIAL` · browser-local notes only; Modify/Add/Delete disabled · `apps/web/src/workspace-activity-details.test.ts` |
| ENG-WS-STEPS | `/app/activities/` | Steps tab | Activity steps · Developing Projects > Adding Activity Steps | https://docs.oracle.com/cd/G48902_01/client_help/en_US/activity_steps.htm | Activity steps · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/activitysteps-19435a.html | Steps break the activity into ordered units with a name, weight, dates and completion. | Steps read in stored sequence order; a weight is a positive number; completion changes roll up through the step rules. | ENG-ACT-DET-09 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `PARTIAL` · read-only list with weights; no add/edit/template/complete in the pane · `apps/web/src/workspace-activity-details.test.ts`, `apps/web/src/workspace-activity-steps.test.ts` |
| ENG-WS-STEPS | `/app/activities/` | Add, update and remove steps; step weights | Add steps to activities · Developing Projects > Adding Activity Steps | https://docs.oracle.com/cd/G48902_01/client_help/en_US/add_steps_to_activities.htm | Add steps to activities · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/addstepstoactivities-19589a.html | Add appends a step to the tab; Update marks completion or sets Step % Complete; Delete removes the selected step; Add weights sets significance. | A step needs a description; deleting a step removes only that step; marked completion re-rolls the activity percent complete. | ENG-ACT-DET-09 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `NOT_IMPLEMENTED` · Add/Add from template/Delete/Modify are disabled |
| ENG-WS-STEPS | `/app/activities/` | Update, weight and remove steps | Update activity steps · Developing Projects > Adding Activity Steps | https://docs.oracle.com/cd/G48902_01/client_help/en_US/update_activity_steps.htm | Update activity steps · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/updateactivitysteps-19595a.html | Completion can be marked or cleared, and Step % Complete drives Physical % Complete. | Step % Complete 100 marks Completed and vice versa. | ENG-ACT-DET-09 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `NOT_IMPLEMENTED` · the step record stores no completion percentage, so no such column is shown |
| ENG-WS-STEPS | `/app/activities/` | Step weights | Add weights to steps · Developing Projects > Adding Activity Steps | https://docs.oracle.com/cd/G48902_01/client_help/en_US/add_weights_to_steps.htm | No verified direct section URL | Each step carries a weight used for weighted progress. | A new step defaults to weight 1; weights are numbers. | ENG-ACT-DET-09 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `PARTIAL` · weight is displayed, not editable |
| ENG-WS-DETAILS | `/app/activities/` | WPs & Docs tab | Display work product and document details in the Activities window · Managing Projects > Adding and Assigning Work Products and Documents | https://docs.oracle.com/cd/G48902_01/client_help/en_US/display_work_product_and_doc_details_in_the_activities_window.htm | Display work product and document details in the Activities window · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/displayworkproductanddocumentdetailsintheactivitieswindow-19615a.html | The WPs & Docs tab lists the work products and documents linked to the selected activity. | Only documents whose stored link references this activity are listed; a failed read is not shown as an empty list. | ENG-ACT-DET-10 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · read-only; `apps/web/src/workspace-activity-details.test.ts` |
| ENG-WS-DETAILS | `/app/activities/` | Expenses tab | Expenses · Developing Projects > Adding Expenses and Entering Cost Information for Activities | https://docs.oracle.com/cd/G48902_01/client_help/en_US/expenses.htm | Expenses · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/expenses-20786a.html | The Expenses tab lists the activity's expenses with category, planned/actual/remaining cost and accrual. | An expense needs a name, category and currency; currency is required. | ENG-ACT-DET-11 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `PARTIAL` · list plus add form; delete and column customization disabled · `apps/web/src/workspace-expenses.test.ts` |
| ENG-WS-DETAILS | `/app/activities/` | Add an expense from the Activities window | Add expenses from the Activities window · Developing Projects > Adding Expenses and Entering Cost Information for Activities > Expenses | https://docs.oracle.com/cd/G48902_01/client_help/en_US/add_expenses_from_the_activities_window.htm | Add expenses from the Activities window · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/addexpensesfromtheactivitieswindow-19597a.html | A new expense is recorded against the selected activity and appears in the authoritative list. | Blank name is rejected; category is required. | ENG-ACT-DET-11 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · add form reloads the authoritative list |
| ENG-WS-DETAILS | `/app/activities/` | Expenses tab columns | Change expenses tab columns · Developing Projects > Adding Expenses and Entering Cost Information for Activities > Expenses | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_expenses_tab_columns.htm | No verified direct section URL | The Expenses tab has a customizable column set. | Presentation only. | ENG-ACT-DET-11 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `NOT_IMPLEMENTED` · fixed expense columns |
| ENG-WS-DETAILS | `/app/activities/` | Issues tab | Assign an issue to an activity · Managing Projects > Adding and Assigning Issues | https://docs.oracle.com/cd/G48902_01/client_help/en_US/assign_an_issue_to_an_activity.htm | No verified direct section URL | An issue identifies the activity it applies to; the activity view lists the issues whose stored reference is this activity. | Issue link is a stored project record; only matching references are listed. | ENG-ACT-DET-12 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `PARTIAL` · lists linked issues and creates a new linked issue; cannot assign an existing one · `apps/web/src/workspace-issues.test.ts` |
| ENG-WS-DETAILS | `/app/activities/` | Risks tab and risk-to-activity assignment | Assigning a risk to an activity · Managing Projects > Adding and Assigning Risks (P6 Professional Only) | https://docs.oracle.com/cd/G48902_01/client_help/en_US/48839.htm | Assigning a risk to an activity · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/assigningarisktoanactivityp6professionalonly-48839a.html | A risk can be assigned to the activity it impacts and removed again, and the activity view shows the risks assigned to it. | Assignment and removal are project record changes. | ENG-ACT-DET-13 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `NOT_IMPLEMENTED` · risk records carry no activity reference; the tab shows the project register read-only · `apps/web/src/workspace-activity-details.test.ts` |
| ENG-WS-DETAILS | `/app/activities/` | Remove a risk assignment | Removing risk assignments from activities · Managing Projects > Adding and Assigning Risks (P6 Professional Only) | https://docs.oracle.com/cd/G48902_01/client_help/en_US/48842.htm | No verified direct section URL | A risk assignment can be removed from the Risks window or the Activities window. | Removal deletes the link, not the risk. | ENG-ACT-DET-13 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `NOT_IMPLEMENTED` · no risk assignment exists to remove |
| ENG-WS-DETAILS | `/app/activities/` | Summary tab | NO DIRECT P6 HELP EQUIVALENT — CUBI-SPECIFIC REQUIREMENT (nearest: Customize Activity Details, which lists the available tabs) | https://docs.oracle.com/cd/G48902_01/client_help/en_US/customize_activity_details.htm | No verified direct section URL | CUBI shows unit, cost and date summaries derived from the authoritative activity projection, with missing values left empty. | Summaries are calculated by the shared core; this pane never estimates a value. | ENG-ACT-DET-14 | `HELP_VERIFIED` (nearest), `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-activity-details.ts` |
| ENG-WS-UDF | `/app/activities/` | UDFs tab | User-defined fields · Structuring Projects > Defining Custom Fields | https://docs.oracle.com/cd/G48902_01/client_help/en_US/user_defined_fields.htm | User-defined fields · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/user-definedfields-21123a.html | User-defined fields for the activity subject area are shown on a detail tab and can be edited in writable sessions. | Only writable definitions are editable; a blank value clears a nullable definition and is otherwise rejected; typed values keep their type. | ENG-ACT-DET-15 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-activity-details.test.ts`, `apps/web/src/p6-udf-http.test.ts` |
| ENG-WS-DETAILS | `/app/activities/` | Update History tab | NO DIRECT P6 HELP EQUIVALENT — CUBI-SPECIFIC REQUIREMENT | — (CUBI-owned; no Oracle topic) | No verified direct section URL | CUBI lists append-only progress-history events for the activity with actor, revision transition, field changes and sequence review. | History is written only by the progress service; this pane never synthesizes an event or edits one. | ENG-ACT-DET-16 | `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-activity-details.test.ts` |
| ENG-WS-DETAILS | `/app/activities/` | Calendar tab | NO DIRECT P6 HELP EQUIVALENT — CUBI-SPECIFIC REQUIREMENT | — (CUBI-owned; no Oracle topic) | No verified direct section URL | CUBI adds a seventeenth tab after the sixteen Version 26 tabs; it shows the activity calendar, project calendar display and data date. | It never replaces or reorders an official tab; unknown calendar assignments are shown as not available. | ENG-ACT-DET-17 | `TEST_SPECIFIED` | `PARTIAL` · read model does not yet return activity calendar assignments |
| ENG-WS-WBS | `/app/wbs/` | WBS hierarchy and purpose | Work Breakdown Structure · Structuring Projects > Defining the WBS | https://docs.oracle.com/cd/G48902_01/client_help/en_US/work_breakdown_structure.htm | Work Breakdown Structure · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/workbreakdownstructure-18683a.html | The WBS is a multi-level hierarchy of the project's work; the top element equals the project and activities are assigned to elements. | Each project has its own hierarchy; cycles and missing parents are rejected or surfaced, not invented. | ENG-WBS-01 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-wbs-hierarchy.test.ts` |
| ENG-WS-WBS | `/app/wbs/` | Top-down planning with the WBS | Using a WBS for top-down planning · Structuring Projects > Defining the WBS | https://docs.oracle.com/cd/G48902_01/client_help/en_US/using_a_wbs_for_top_down_planning.htm | Using a WBS for top-down planning · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/usingawbsfortop-downplanning-19101a.html | WBS elements can carry anticipated dates, budgets and summary values for planning before activities exist. | Summary values roll up from real children; the view never invents a summary record. | ENG-WBS-01 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `PARTIAL` · hierarchy and activity counts only; no WBS-level budgets yet |
| ENG-WS-WBS | `/app/wbs/` | Table and chart views | View the WBS · Structuring Projects > Defining the WBS | https://docs.oracle.com/cd/G48902_01/client_help/en_US/view_the_wbs.htm | No verified direct section URL | The WBS opens as a chart, a table, or a table with a bar chart; both representations show the same hierarchy. | Both views read one ordered projection; selecting a row or card selects the same record. | ENG-WBS-01 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · table and chart share `buildWbsHierarchy` · `apps/web/src/workspace-wbs-hierarchy.test.ts` |
| ENG-WS-WBS | `/app/wbs/` | WBS table display options | Change the work breakdown structure table display · Structuring Projects > Defining the WBS | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_the_work_breakdown_structure_table_display.htm | Change the work breakdown structure table display · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/changetheworkbreakdownstructuretabledisplay-19129a.html | Table font, color and row height are configurable. | Presentation only; the hierarchy order is unchanged. | ENG-WBS-01 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `NOT_IMPLEMENTED` · fixed table presentation |
| ENG-WS-WBS | `/app/wbs/` | Chart navigation | Move around the WBS chart · Structuring Projects > Defining the WBS | https://docs.oracle.com/cd/G48902_01/client_help/en_US/move_around_the_wbs_chart.htm | No verified direct section URL | Zoom in, zoom out and zoom-to-fit change the chart's level of detail. | Navigation changes only the viewport. | ENG-WBS-01 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `NOT_IMPLEMENTED` · chart renders indented cards only |
| ENG-WS-WBS | `/app/wbs/` | Change the WBS chart display | Change the work breakdown structure chart display · Structuring Projects > Defining the WBS | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_the_work_breakdown_structure_chart_display.htm | Change the work breakdown structure chart display · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/changetheworkbreakdownstructurechartdisplay-19127a.html | Chart fonts and colors are configurable. | Presentation only. | ENG-WBS-01 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `NOT_IMPLEMENTED` · fixed chart presentation |
| ENG-WS-WBS | `/app/wbs/` | Add a WBS element | Add a WBS element · Structuring Projects > Defining the WBS | https://docs.oracle.com/cd/G48902_01/client_help/en_US/add_a_wbs_element.htm | Add a WBS element · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/addawbselement-19113a.html | A new child element is created one level under the selected element and placed by sequence. | Code and name are required; the parent must exist; the maximum level limit applies. | ENG-WBS-02 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · parent/code/name/sequence form · `apps/web/src/main.ts` |
| ENG-WS-WBS | `/app/wbs/` | Edit or move a WBS element | Edit a work breakdown structure element · Structuring Projects > Defining the WBS | https://docs.oracle.com/cd/G48902_01/client_help/en_US/edit_a_work_breakdown_structure_element.htm | Edit a work breakdown structure element · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/editaworkbreakdownstructureelement-19137a.html | Code, name, parent and sequence can be changed; position is changed with the move controls. | Stale `expected_revision` is rejected with a conflict and never overwritten; a move cannot create a cycle. | ENG-WBS-03 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · optimistic revision on PATCH |
| ENG-WS-WBS | `/app/wbs/` | Delete a WBS element | Delete a work breakdown structure element · Structuring Projects > Defining the WBS | https://docs.oracle.com/cd/G48902_01/client_help/en_US/delete_a_work_breakdown_structure_element.htm | Delete a work breakdown structure element · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/deleteaworkbreakdownstructureelement-19139a.html | When the element is assigned to activities the user chooses to delete the element with its activities or reassign the activities. | The decision is explicit; a rejected delete changes nothing. | ENG-WBS-04 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `PARTIAL` · rejects or reassigns to parent; cascade activity deletion is not offered · `apps/web/src/main.ts` |
| ENG-WS-WBS | `/app/wbs/` | Copy and paste a WBS element | Copy and paste a work breakdown structure element · Structuring Projects > Defining the WBS | https://docs.oracle.com/cd/G48902_01/client_help/en_US/copy_and_paste_a_work_breakdown_structure_element.htm | Copy and paste a work breakdown structure element · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/copyandpasteaworkbreakdownstructureelement-19131a.html | Copy takes the selected element and pastes a subtree under the selected target, with documented copy options. | The pasted root code must be unique among siblings; a collision is resolved or rejected by the server. | ENG-WBS-05 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · browser-local clipboard, server-side subtree copy · `apps/web/src/workspace-wbs-clipboard.test.ts` |
| ENG-WS-WBS | `/app/wbs/` | Cut and paste a WBS element | Cut and paste a work breakdown structure element · Structuring Projects > Defining the WBS | https://docs.oracle.com/cd/G48902_01/client_help/en_US/cut_and_paste_a_work_breakdown_structure_element.htm | No verified direct section URL | Cut and paste move the element and its activity assignments under the selected target. | An element cannot be pasted into itself; the move preserves activity assignments. | ENG-WBS-05 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · cut is a parent change with the pinned revision |
| ENG-WS-WBS | `/app/wbs/` | WBS details pane | Display work breakdown structure details · Structuring Projects > Defining the WBS | https://docs.oracle.com/cd/G48902_01/client_help/en_US/display_work_breakdown_structure_details.htm | Display work breakdown structure details · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/displayworkbreakdownstructuredetails-19121a.html | Details for the selected WBS element are shown below the window. | A tab with no authoritative records says so instead of inventing values. | ENG-WBS-06 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · General and Milestones populated; other tabs state no records · `apps/web/src/workspace-view.ts` |
| ENG-WS-WBS | `/app/wbs/` | WBS status | WBS status types · Structuring Projects > Defining the WBS | https://docs.oracle.com/cd/G48902_01/client_help/en_US/wbs_status_types.htm | WBS status types · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/wbsstatustypes-19111a.html | An element status is Planned, Active, Inactive or What-If. | The status is one of the four values; saving advances the record revision. | ENG-WBS-06 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-wbs-milestones.test.ts` |
| ENG-WS-WBS | `/app/wbs/` | Determine or change a WBS element's status | Determine a WBS element's status · Structuring Projects > Defining the WBS | https://docs.oracle.com/cd/G48902_01/client_help/en_US/determine_a_wbs_elements_status.htm | No verified direct section URL | The status is viewed and changed on the General tab of WBS details. | A stale revision is rejected; the four status types are the only values. | ENG-WBS-06 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · status and technique form |
| ENG-WS-WBS | `/app/wbs/` | WBS weighted milestones | Assign WBS weighted milestones · Structuring Projects > Defining the WBS | https://docs.oracle.com/cd/G48902_01/client_help/en_US/assign_wbs_weighted_milestones.htm | Using weighted milestones in the work breakdown structure · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/usingweightedmilestonesintheworkbreakdownstructure-19105a.html | Milestones carry a name, weight and completed flag; the technique for computing percent complete selects milestones. | Each milestone needs an id and name; weight is greater than zero; saving replaces the element's list and advances its revision. | ENG-WBS-07 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-wbs-milestones.test.ts` |
| ENG-WS-WBS | `/app/wbs/` | Weighted percent complete calculation | Using weighted milestones in the work breakdown structure · Structuring Projects > Defining the WBS | https://docs.oracle.com/cd/G48902_01/client_help/en_US/using_weighted_milestones_in_the_wbs.htm | Using weighted milestones in the work breakdown structure · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/usingweightedmilestonesintheworkbreakdownstructure-19105a.html | Weighted percent complete is completed weight divided by total weight. | Zero total weight yields 0, not a division error. | ENG-WBS-07 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `weightedPercentComplete` |
| ENG-WS-WBS | `/app/wbs/` | Change an activity's WBS assignment | Change an activity's work breakdown structure assignment · Developing Projects > Adding Activities to a Project | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_an_activitys_work_breakdown_structure_assignment.htm | No verified direct section URL | Editing an activity lets the user choose a different WBS element. | A WBS element must be chosen; assigning never changes the element hierarchy. | ENG-WBS-08 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · required WBS select in the activity edit form · `apps/web/src/main.ts` |
| ENG-WS-WBS | `/app/wbs/` | Group activities by WBS path | Group activities by WBS path · Grouping, Filtering, and Summarizing Data > Grouping and Sorting | https://docs.oracle.com/cd/G48902_01/client_help/en_US/group_activities_by_wbs_path.htm | Group activities by WBS path · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/groupactivitiesbywbspath-19471a.html | Grouping by WBS path orders activities under their WBS bands with sortable direction. | Only bands that contain at least one filtered activity are emitted; collapsing changes only the visible rows. | ENG-WBS-08 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-wbs-display.test.ts` |

## 3. Page specifications

### 3.1 Activity Details pane (`/app/activities/`, bottom pane)

- **Purpose** — read and act on the selected activity's official detail tabs
  without leaving the Activities window.
- **Entry conditions** — a project is open, the workspace read model is loaded,
  and an activity is selected in the table or Gantt.
- **Permissions** — `viewer` reads every tab; write forms appear only when the
  session role is `planner` or `project_admin` (`canWrite`).
- **Structure** — header with the selected activity and Customize Tabs; tab
  strip in the stored order; only the active tab's content is materialized;
  previous/next activity navigation keeps the table scroll position.
- **Tabs** — General, Status, Resources, Predecessors, Successors,
  Relationships, Codes, Notebook, Steps, WPs & Docs, Expenses, Issues, Risks,
  Summary, UDFs, Update History, then the CUBI-only Calendar tab.
- **Customize** — Available/Display lists, Add, Add All, Remove, Remove All,
  Move Up, Move Down, Default, Apply, OK, Cancel. At least one tab remains
  displayed; removed tabs stay available; the display order is the tab order.
- **Persistence** — the display set is stored under
  `cubi:activity-details-visible-tabs:v2` (legacy `:v1` is read and migrated);
  the active tab is stored under `cubi:activity-details-tab`; both are
  browser-local presentation preferences. Hiding Details is scoped per user,
  tenant, project and window.
- **Reads** — assignments, expenses, issues, risks, steps, UDF metadata and
  values, progress history, documents and constraints are read once per
  project revision and activity, in parallel. A tab distinguishes
  "not read yet", "loaded but empty", "error" and "unauthorized".
- **Writes** — add constraint, add resource assignment, add expense, add issue
  and save UDF values. Each requires the pinned revision where the record has
  one; a rejected write shows the server code and leaves the pane unchanged.
- **Validation** — required resource/category/currency/owner/title; UDF typed
  conversion; nullable clear rules; malformed history payloads are rejected,
  never rendered as events.
- **Expected results** — after a successful write the authoritative list is
  reloaded; after a selection change the identity, tabs and data follow the
  new activity; a reload restores the tab set and active tab.
- **Error scenarios** — unauthorized read, failed tab read, stale revision on
  a constraint, rejected UDF value, missing required form field.

### 3.2 Work Breakdown Structure window (`/app/wbs/`)

- **Purpose** — maintain the project WBS hierarchy and its details.
- **Entry conditions** — project open; WBS nodes loaded by the workspace read
  model.
- **Permissions** — every role reads; add/edit/delete/clipboard require
  `planner` or `project_admin`.
- **Structure** — toolbar (Add WBS, Cut, Copy, Paste, Delete, clipboard state,
  Table/Chart toggle); hierarchy table or chart; WBS Details pane with General,
  Notebook, Budget Log, Spending Plan, Budget Summary, WBS Milestones,
  WPs & Docs, Earned Value, Planning Resources and UDFs tabs.
- **Table** — treegrid columns WBS Code, WBS Name, Activities, Sequence, Rev;
  indentation by depth; `aria-level`; a node whose parent is missing is shown
  at root with a "Parent not loaded" note instead of being dropped.
- **Chart** — the same ordered projection rendered as indented cards; selecting
  a card selects the same record.
- **Ordering** — siblings by sequence number, then local code, then id;
  descendants depth-first. This single order feeds table, chart and grouping.
- **Add/edit** — parent, code, name and sequence; PATCH carries
  `expected_revision`; a stale revision is rejected as `REVISION_CONFLICT`.
- **Delete** — first attempt uses `activity_action: reject`; `WBS_IN_USE`
  reveals guidance and, when the element has a WBS parent and no children,
  a "reassign activities to parent and delete" action. Cascading activity
  deletion is intentionally not offered.
- **Clipboard** — browser-local entry (copy or cut); paste targets the selected
  element; pasting into itself is blocked; copy derives a sibling-unique code
  (`code (copy)`, `code (copy 2)`, …) and the server remains the authority.
- **Details** — General shows the authoritative fields and a status/technique
  editor; Milestones shows weight, completed and the weighted roll-up; other
  tabs state that no authoritative records are loaded rather than showing an
  empty grid as if data were lost.
- **Expected results** — after any mutation the workspace is re-read, the same
  window stays open and the mutated element is reselected when it still exists.
- **Error scenarios** — `WBS_IN_USE`, `REVISION_CONFLICT`, unknown parent,
  duplicate sibling code, forbidden role, cross-tenant project.

## 4. Acceptance scenarios

### ENG-ACT-DET-01 — Details pane follows the selection

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` bottom pane |
| Feature | Details pane open and selection |
| Preconditions | Planner; project with two activities; Details visible |
| Test data | Select `A-100`, then clear the selection |
| User action | Select an activity in the table; then clear selection |
| Expected result | Header and identity show the activity code and name; the General tab is active by default; with no selection the pane states a selection is required |
| Negative | A selection from another project is never displayed |
| Permission | Viewer sees the same pane read-only |
| Persistence | Reload keeps the last active tab, not the selection |
| Related Help | Display window details — https://docs.oracle.com/cd/G48902_01/client_help/en_US/display_window_details.htm |

### ENG-ACT-DET-02 — Customize the tab set and order

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` bottom pane |
| Feature | Customize Activity Details |
| Preconditions | Planner; all 17 tabs available |
| Test data | Remove Notebook; move Calendar up; apply; reopen and restore Default |
| User action | Customize Tabs → move items → Apply → OK; reload the page |
| Expected result | Notebook leaves the tab strip but stays in Available Tabs; the new order persists through reload; Default restores all 17 |
| Negative | Removing the last displayed tab is disabled |
| Permission | Viewer may customize locally; it writes no project record |
| Persistence | `cubi:activity-details-visible-tabs:v2` retains the order; a v1 set is migrated |
| Related Help | Customize Activity Details — https://docs.oracle.com/cd/G48902_01/client_help/en_US/customize_activity_details.htm |

### ENG-ACT-DET-03 — General tab shows only authoritative values

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` bottom pane |
| Feature | General tab |
| Preconditions | Activity with type, duration type, calendar and WBS; one field absent from the projection |
| Test data | Activity `A-100` |
| User action | Open General |
| Expected result | Present fields match the read model; the absent field reads "Not available" and is never filled with an estimate |
| Negative | No field is derived from its key name |
| Permission | Read-only for every role |
| Persistence | Values change only when the project record changes |
| Related Help | Define general activity information — https://docs.oracle.com/cd/G48902_01/client_help/en_US/define_general_activity_information.htm |

### ENG-ACT-DET-04 — Status facts and constraints, no local scheduling

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` bottom pane |
| Feature | Status tab and constraints |
| Preconditions | Planner; activity with no constraint |
| Test data | Add constraint type Start No Earlier Than on 2026-12-01 |
| User action | Open Status → add the constraint → reload the tab |
| Expected result | Duration, dates, percent complete and units match the projection; the stored constraint appears with its revision; stored dates are not recalculated by the pane |
| Negative | Empty constraint date is rejected; a rejected write changes nothing |
| Permission | Viewer sees constraints without the write form |
| Persistence | Constraint survives reload and is read by the scheduling core |
| Related Help | Update progress for individual activities — https://docs.oracle.com/cd/G48902_01/client_help/en_US/update_progress_for_individual_activities_manually.htm |

### ENG-ACT-DET-05 — Resources tab lists and adds assignments

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` bottom pane |
| Feature | Resources tab |
| Preconditions | Planner; one stored assignment; a resource permitted by security |
| Test data | Add resource `R-100`, 8 units, planned cost 1000 USD |
| User action | Open Resources → Add assignment → save |
| Expected result | Only this activity's assignments are listed; the new row appears after the authoritative reload; role, units and cost are stored as entered |
| Negative | Missing resource id is rejected; a forbidden resource is rejected |
| Permission | Viewer sees the list; no write form |
| Persistence | Reload and new session read the same assignments |
| Related Help | Assign resources to activities — https://docs.oracle.com/cd/G48902_01/client_help/en_US/assign_resources_to_activities.htm |

### ENG-ACT-DET-06 — Relationship tabs have the correct direction

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` bottom pane |
| Feature | Predecessors, Successors, Relationships |
| Preconditions | `A-100` (predecessor) → `A-200` (successor), finish-to-start, lag 2 days |
| Test data | Select `A-200` |
| User action | Open Predecessors, then Successors, then Relationships |
| Expected result | Predecessors lists `A-100` with FS and 2d; Successors is empty for `A-200`; Relationships shows both areas |
| Negative | A link is never listed in the wrong direction |
| Permission | Read-only for every role |
| Persistence | Links are read from the relationship records |
| Related Help | View activity relationships in Activity Details — https://docs.oracle.com/cd/G48902_01/client_help/en_US/19567.htm |

### ENG-ACT-DET-07 — Codes tab is honest about unread assignments

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` bottom pane |
| Feature | Codes tab |
| Preconditions | Activity with no code assignments in the read model |
| Test data | Open Codes |
| User action | Open Codes and inspect Assign/Remove |
| Expected result | Activity id, WBS code and project code are shown; the assignments grid states that no assignments are returned; Assign/Remove are disabled |
| Negative | No fabricated code row is shown |
| Permission | Disabled controls explain the reason |
| Persistence | Nothing changes |
| Related Help | Assign activity codes and values to activities — https://docs.oracle.com/cd/G48902_01/client_help/en_US/assign_activity_codes_and_values_to_activities.htm |

### ENG-ACT-DET-08 — Steps are read in stored order

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` bottom pane |
| Feature | Steps tab |
| Preconditions | Activity with three stored steps, weights 3, 2, 1 |
| Test data | Steps `S1`, `S2`, `S3` |
| User action | Open Steps |
| Expected result | Rows appear in stored sequence with name, weight, start, finish and step UDFs; no completion % column is invented |
| Negative | A failed step read shows an error, not an empty list |
| Permission | Add/Modify/Delete remain disabled with a reason |
| Persistence | Nothing changes from this pane |
| Related Help | Activity steps — https://docs.oracle.com/cd/G48902_01/client_help/en_US/activity_steps.htm |

### ENG-ACT-DET-09 — WPs & Docs lists only linked documents

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` bottom pane |
| Feature | WPs & Docs |
| Preconditions | Two project documents, one linked to the activity by id or code |
| Test data | Linked document `DOC-1`; unlinked `DOC-2` |
| User action | Open WPs & Docs |
| Expected result | Only `DOC-1` is listed with status, type and revision; expanding it shows id, content hash and revision |
| Negative | A failed document read shows a notice, not "no documents" |
| Permission | Upload/download stays on the Documents page |
| Persistence | Read-only |
| Related Help | Display work product and document details in the Activities window — https://docs.oracle.com/cd/G48902_01/client_help/en_US/display_work_product_and_doc_details_in_the_activities_window.htm |

### ENG-ACT-DET-10 — Add an expense to the selected activity

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` bottom pane |
| Feature | Expenses tab |
| Preconditions | Planner; activity selected |
| Test data | Name `Concrete`, category material, 5000 USD; then blank name |
| User action | Add expense → save; repeat with a blank name |
| Expected result | The first expense appears after reload with budgeted cost; the blank name is rejected and nothing is written |
| Negative | Missing category or currency is rejected |
| Permission | Viewer sees the list only |
| Persistence | Expense survives reload; delete is not offered |
| Related Help | Add expenses from the Activities window — https://docs.oracle.com/cd/G48902_01/client_help/en_US/add_expenses_from_the_activities_window.htm |

### ENG-ACT-DET-11 — Issues linked to the activity

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` bottom pane |
| Feature | Issues tab |
| Preconditions | Planner; one issue already linked to the activity, one linked to another |
| Test data | Create issue `Pour delay`, owner, high priority |
| User action | Open Issues → add the issue → reload |
| Expected result | Only issues whose stored activity reference matches are listed; the new issue appears with status Open |
| Negative | Missing title or owner is rejected |
| Permission | Viewer reads; the add form is hidden |
| Persistence | Issue survives reload with its own revision |
| Related Help | Assign an issue to an activity — https://docs.oracle.com/cd/G48902_01/client_help/en_US/assign_an_issue_to_an_activity.htm |

### ENG-ACT-DET-12 — Risks are not claimed as activity-linked

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` bottom pane |
| Feature | Risks tab |
| Preconditions | Project with two risks that store no activity reference |
| Test data | Open Risks |
| User action | Open Risks |
| Expected result | The project register is shown with a notice that it makes no activity-link claim; no risk is presented as assigned to this activity |
| Negative | The tab never filters the register to imply a link |
| Permission | Read-only; assign/remove disabled with a reason |
| Persistence | Nothing changes |
| Related Help | Assigning a risk to an activity — https://docs.oracle.com/cd/G48902_01/client_help/en_US/48839.htm |

### ENG-ACT-DET-13 — UDF values are typed and nullable rules apply

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` bottom pane |
| Feature | UDFs tab |
| Preconditions | Planner; one nullable writable text UDF, one non-nullable writable text UDF, one read-only UDF |
| Test data | Set the nullable text; clear the non-nullable text; set an invalid duration value |
| User action | Edit values → Save values |
| Expected result | Writable UDFs render typed controls; a blank value clears only the nullable definition; the non-nullable clear and the malformed duration report a field error and write nothing |
| Negative | Read-only definitions have no input |
| Permission | Viewer sees values without the form |
| Persistence | Saved values are read back at the current project revision |
| Related Help | User-defined fields — https://docs.oracle.com/cd/G48902_01/client_help/en_US/user_defined_fields.htm |

### ENG-ACT-DET-14 — Update History is append-only

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` bottom pane |
| Feature | Update History |
| Preconditions | Activity with one progress event |
| Test data | Event `R1 → R2`, field `percent_complete` |
| User action | Open Update History |
| Expected result | Recorded time, actor, revision transition and field changes are shown; revision numbers and before/after values match the event |
| Negative | A malformed payload is rejected rather than rendered as an event |
| Permission | Read-only for every role |
| Persistence | History is never edited or deleted here |
| Related Help | NO DIRECT P6 HELP EQUIVALENT — CUBI-SPECIFIC REQUIREMENT |

### ENG-ACT-DET-15 — A denied details read is a permission state

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` bottom pane |
| Feature | Authorization on detail reads |
| Preconditions | Viewer without access to the requested detail collection |
| Test data | Denied code `AUTHORIZATION_DENIED` |
| User action | Open the affected tab |
| Expected result | The tab states that the records are not available to this user; it does not print a transport error or an empty grid |
| Negative | A transient error is distinguished from a permission error |
| Permission | Retry is not offered for a permission failure |
| Persistence | Nothing changes |
| Related Help | Display window details — https://docs.oracle.com/cd/G48902_01/client_help/en_US/display_window_details.htm |

### ENG-WBS-01 — Table and chart share one order

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/wbs/` |
| Feature | Table and chart parity |
| Preconditions | Root with two children; second child has a grandchild; siblings with different sequence numbers |
| Test data | Codes `1.1`, `1.2`, `1.2.1`, `1.3` |
| User action | Open Table View, then Chart View |
| Expected result | Both show the same nodes in the same order and depth; the activity count per node matches the activities assigned |
| Negative | A node with a missing parent appears at root with a "Parent not loaded" note, never dropped |
| Permission | Read-only for viewer |
| Persistence | Order comes from the stored sequence and codes |
| Related Help | View the WBS — https://docs.oracle.com/cd/G48902_01/client_help/en_US/view_the_wbs.htm |

### ENG-WBS-02 — Add a child element

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/wbs/` |
| Feature | Add WBS element |
| Preconditions | Planner; parent element exists |
| Test data | Code `2.1`, name `Substructure`, sequence 10; then blank code |
| User action | Add WBS → choose parent → save; repeat with blank code |
| Expected result | The new element appears one level under the parent at the chosen sequence; the blank code is rejected and nothing is created |
| Negative | An unknown parent is rejected |
| Permission | Viewer cannot open the form; a direct POST is `403` |
| Persistence | Reload shows the new element with revision 1 |
| Related Help | Add a WBS element — https://docs.oracle.com/cd/G48902_01/client_help/en_US/add_a_wbs_element.htm |

### ENG-WBS-03 — Edit and move with optimistic locking

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/wbs/` |
| Feature | Edit WBS element |
| Preconditions | Element at revision 3; second editor holds revision 3 |
| Test data | Rename to `Superstructure`; move under another parent |
| User action | Save from editor A → save from editor B with revision 3 |
| Expected result | A commits revision 4; B receives `REVISION_CONFLICT` and no overwrite; the tree keeps acyclic order |
| Negative | Moving into a descendant is rejected |
| Permission | Viewer edit is `403` |
| Persistence | Reload reads the new name and parent |
| Related Help | Edit a work breakdown structure element — https://docs.oracle.com/cd/G48902_01/client_help/en_US/edit_a_work_breakdown_structure_element.htm |

### ENG-WBS-04 — Delete an element that has activities

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/wbs/` |
| Feature | Delete with activities |
| Preconditions | Element with two assigned activities and a WBS parent, no children |
| Test data | Delete → `WBS_IN_USE` → reassign to parent and delete |
| User action | Delete the element, then use the reassignment action |
| Expected result | The first attempt changes nothing and shows guidance; the second moves both activities to the parent and deletes the element |
| Negative | Cascading activity deletion is not offered; no activity is silently deleted |
| Permission | Viewer delete is `403` |
| Persistence | Reload shows the parent with the two activities and no deleted element |
| Related Help | Delete a work breakdown structure element — https://docs.oracle.com/cd/G48902_01/client_help/en_US/delete_a_work_breakdown_structure_element.htm |

### ENG-WBS-05 — Copy and cut targets and code collisions

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/wbs/` |
| Feature | Clipboard |
| Preconditions | Source `1.1` with a descendant; target parent already has `1.1` |
| Test data | Copy `1.1` → paste under `2`; then cut `1.2` → paste under `2` |
| User action | Copy, select target, paste; then cut, select target, paste |
| Expected result | Copy creates a sibling-unique code (`1.1 (copy)`); cut moves `1.2` with its assignments; paste into itself is blocked |
| Negative | Paste with no clipboard entry or no target is disabled |
| Permission | Viewer clipboard actions are disabled |
| Persistence | Reload shows the copied subtree and the moved element |
| Related Help | Copy and paste a work breakdown structure element — https://docs.oracle.com/cd/G48902_01/client_help/en_US/copy_and_paste_a_work_breakdown_structure_element.htm |

### ENG-WBS-06 — WBS status and technique

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/wbs/` |
| Feature | WBS General details |
| Preconditions | Element status Planned, technique Activities |
| Test data | Change to Active and WBS Milestones |
| User action | Edit both selects → Save WBS settings |
| Expected result | Values save and the record revision advances; reload shows Active and Milestones |
| Negative | A stale revision is rejected with a conflict |
| Permission | Viewer sees the values without the form |
| Persistence | Status and technique survive reload |
| Related Help | Determine a WBS element's status — https://docs.oracle.com/cd/G48902_01/client_help/en_US/determine_a_wbs_elements_status.htm |

### ENG-WBS-07 — Weighted milestones and roll-up

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/wbs/` |
| Feature | WBS Milestones |
| Preconditions | Technique Milestones; no milestones |
| Test data | `M1` weight 3 completed; `M2` weight 1 not completed |
| User action | Add both → Save milestones → reload |
| Expected result | Total weight 4; weighted percent complete 75.00%; the list is replaced by the saved list and the revision advances |
| Negative | Weight 0 is rejected; blank name is rejected |
| Permission | Viewer sees the list without the form |
| Persistence | Reload reads the same milestones and roll-up |
| Related Help | Assign WBS weighted milestones — https://docs.oracle.com/cd/G48902_01/client_help/en_US/assign_wbs_weighted_milestones.htm |

### ENG-WBS-08 — Reassign an activity and group by WBS path

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` and `/app/wbs/` |
| Feature | Activity WBS assignment and WBS grouping |
| Preconditions | Activity assigned to `1.1`; group by WBS path |
| Test data | Move the activity to `1.2` |
| User action | Edit the activity → choose `1.2` → save; group by WBS path |
| Expected result | The activity leaves the `1.1` band and appears under `1.2`; counts follow; a band never appears without a matching activity |
| Negative | Saving without a WBS is rejected |
| Permission | Viewer cannot reassign |
| Persistence | Reload keeps the new assignment and the group order |
| Related Help | Group activities by WBS path — https://docs.oracle.com/cd/G48902_01/client_help/en_US/group_activities_by_wbs_path.htm |

## 5. Documented divergences and gaps

| Divergence | Official Help | CUBI behavior | Reason |
| --- | --- | --- | --- |
| Notebook storage | Notebook topics are project records attached to the activity | CUBI shows browser-local notes and states they are not audit records | No notebook persistence surface in the current read model |
| Codes tab | Activity codes and values are assigned and removed here | Assignments are not returned by the read model; the tab is an honest empty state | Canonical `ENG-WS-ACTIVITY-CODES` is `PARTIAL` |
| Steps editing | Steps can be added, updated, weighted and removed in the tab | CUBI reads steps and weights only; completion percentage is not shown because the record does not store it | Read-only step API |
| Risk-to-activity assignment | A risk is assigned to the activity it impacts and can be removed | Risk records carry no activity reference; the tab shows the project register read-only | Gap: no risk-assignment record in the read model |
| WBS delete cascade | Deleting an element offers delete-with-activities or reassignment | Only reject or reassign-to-parent; cascading activity delete is not offered | No audited activity-delete path |
| Tab column customization | Resources, Predecessors, Successors and Expenses tab columns are customizable | Fixed columns | Presentation scope |
| WBS table/chart presentation | Fonts, colors, row height, zoom and fit are configurable | Fixed presentation; chart is an indented card list | Presentation scope |
| Summary tab | No dedicated V26 topic located | CUBI derives unit, cost and date summaries from the authoritative projection | CUBI-specific composition |

The Codes, Steps, risk-link and WBS-cascade rows above are capability gaps, not
claims that the implementation is wrong: the UI states what it cannot do and
never invents a value. No product defect is asserted in this section. The
risk-assignment and step-editing gaps contradict documented P6 capabilities and
are recorded here for Agent 1 to scope; they are not fixed by this workstream.

## 6. Verification

| Item | Result |
| --- | --- |
| Help URLs opened, HTTP 200 and listed in the official TOC | all unique topics cited above (see the section report) |
| User Guide URLs opened and title-matched | all unique URLs cited above |
| Link report | `evidence/section-03-activity-details-wbs-links.json` |
| Existing product tests cited | `workspace-activity-details.test.ts`, `workspace-activity-steps.test.ts`, `workspace-assignments.test.ts`, `workspace-expenses.test.ts`, `workspace-issues.test.ts`, `workspace-constraints.test.ts`, `workspace-wbs-hierarchy.test.ts`, `workspace-wbs-display.test.ts`, `workspace-wbs-clipboard.test.ts`, `workspace-wbs-milestones.test.ts`, `p6-activity-wbs-grid.test.ts`, `p6-udf-http.test.ts` |
| Executed acceptance | Not run by this workstream; scenarios are `TEST_SPECIFIED` |
