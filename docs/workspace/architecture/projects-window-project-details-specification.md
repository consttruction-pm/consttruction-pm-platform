# Projects Window and Project Details — UI Specification

Status: Implemented shell baseline; full data/API parity remains an explicit follow-up gate.
Scope: authenticated CUBI workspace. This document defines the visual structure, field inventory, choices, persistence rules and acceptance criteria. It does not claim unsupported API fields are implemented.

## 1. Object separation

- Projects Window: authorized project register and organization/project navigation.
- Project Structure: Business Domain → optional Portfolio → Project hierarchy.
- Project Register: central table/list for the selected scope.
- Project Details: bottom layout of the Projects Window; never the generic right-side inspector.
- WBS Details: details for the selected WBS node in the WBS context.
- Activity Details: details for the selected activity in Activities.
These are separate selection contexts and must never display one another's fields.

## 2. Page geometry and regions

Desktop composition:
1. Persistent application status bar.
2. Main menu bar and command toolbar.
3. Breadcrumb/context bar showing current organization scope, project, revision and Data Date when available.
4. Window tab strip.
5. Projects layout toolbar (view, columns, filter, group/sort, layout, refresh, import/export).
6. Upper working region: Project Structure on the leading side and Project Register in the remaining width.
7. Bottom Project Details pane spanning the working width.
8. Workspace status bar.

Project Structure target width: default 240 px; adjustable 190–340 px; collapsible to a rail.
Project Details target height: default 240 px; adjustable 150 px to 45% of working height; collapsible to a header.
Project Details is separated by a horizontal splitter with pointer drag, keyboard adjustment and double-click reset.
At widths below 1100 px, Project Structure may collapse to a drawer. Below 768 px, show Structure, Register and Details as stacked views/tabs with touch targets of at least 40 px. No panel may overlap another or force page-level horizontal scrolling.

The current implementation has a Projects module surface and bottom-docked Project Details. Until the service returns the organization-wide project list, the register must clearly identify itself as the currently authorized/open project and must not pretend to be the full organization register.

## 3. Project Structure tree

Conceptual hierarchy:
Organization
- Business Domains
  - Portfolio (optional)
    - Project

Initial domain categories may include Construction, Infrastructure, Industrial, Energy, Oil & Gas and Other. These are configurable classification values, not hard-coded project records.

Tree commands:
- All Projects: search, refresh, create project (permission-gated), choose visible columns.
- Business Domain: create, rename, reorder, archive/delete subject to dependency validation; create Portfolio.
- Portfolio: create, rename, reorder, move authorized Projects.
- Project: Open, Close, Properties, Set Default, Copy, Move, Export, Delete.
- Search by Project ID, Project Name, Domain and Portfolio.
- Expand/collapse, selected node, active project and counts.
- Drag/drop only when a server-side validated move endpoint exists.
- If only a flat project list is returned, render a flat list or unclassified group. Never fabricate domains, portfolios or projects.

## 4. Project Register

Default columns:
Project ID (required), Project Name, Status, Responsible Manager, Business Domain, Portfolio, Planned Start, Planned Finish, Actual Start, Actual Finish, Data Date, Scheduled Finish, Project % Complete, Priority, Currency, Approved Budget, Actual Cost, Remaining Cost, Last Modified.

Column manager:
- available and selected columns;
- add/remove, reorder, show/hide;
- width and alignment;
- pin/freeze;
- display title override;
- reset defaults;
- save in user/project layout scope.

Register interaction:
- single row selection; Ctrl/Cmd multi-select; Shift range;
- Enter or double-click opens selected project;
- selection alone only changes Project Details context and must not open/change project;
- row context menu with Open, Properties, Set Default, Copy, Move, Export and Delete as supported;
- multi-level sorting and grouping;
- named filters and quick search;
- compact/normal/comfortable row density;
- keyboard navigation and visible focus.

Views:
- Project Table (default);
- Project Bar Chart (requires authoritative project start/finish facts);
- Project Gantt (requires authoritative dates; axis is chronological);
- Project Summary (requires server-provided aggregate facts).
Changing a view is presentation-only and never changes project data.

## 5. Project Details pane

Default tab order:
1. General
2. Dates
3. Defaults
4. Resources
5. Settings
6. Codes
7. Notebook
8. Budget Log
9. Spending Plan
10. Budget Summary
11. Funding
12. Baselines
13. Documents
14. History
15. User Defined Fields (UDFs)

Tab controls:
- show/hide;
- reorder;
- restore default order;
- choose initial tab;
- save as personal layout or project layout;
- restore previous layout.
Hiding a tab never deletes its data. Unsupported tabs remain explicitly unavailable or display a truthful empty state; they must not contain fake editable controls.

### General
Project ID; Project Name; Short Name; Business Domain; Portfolio; Responsible Manager; Project Owner; Status; Priority; Project Type; Description; Location; Country; Time Zone; Currency; Created By/At; Modified By/At; Revision.
Status choices: Planned, Active, On Hold, Completed, Inactive, Cancelled.
Only project-service fields may be edited. Current metadata write contract supports name, description, start date, date system and primary calendar. Other fields remain unavailable/read-only until a service contract exists.

### Dates
Planned Start; Planned Finish; Actual Start; Actual Finish; Anticipated Start; Anticipated Finish; Must Finish By; Data Date; Scheduled Start; Scheduled Finish; Baseline Start; Baseline Finish.
Separate manual inputs from calculated facts. Canonical storage is ISO date. Display calendar (Jalali/Gregorian) is independent of language. Data Date edits require permission, revision guard and authoritative rescheduling; the UI never calculates dates.

### Defaults
New Activity defaults:
- Activity Type: Task Dependent, Resource Dependent, Level of Effort, Start Milestone, Finish Milestone, WBS Summary (only where supported).
- Duration Type: Fixed Duration & Units, Fixed Duration & Units/Time, Fixed Units, Fixed Units/Time.
- Percent Complete Type: Duration, Units, Physical.
- Default Calendar, Cost Account, Price per Unit, Activity Priority and Default WBS.

Activity ID numbering:
- Prefix; starting number; increment; auto-numbering on/off;
- increment based on selected activity;
- duplicate-ID policy;
- next-ID preview.
Example only: CIV-1000, CIV-1010, CIV-1020. Preview must come from the authoritative ID allocator before apply.

Assignment defaults:
- Rate Type; Resource Calendar; Units/Time;
- assignment drives activity dates;
- duplicate resource assignment policy;
- default role/resource behavior.

WBS defaults:
- WBS code separator;
- code generation mode;
- numbering prefix and increment;
- default level.
Every default states its scope: current project, new projects, new activities, new assignments, or a separately confirmed bulk change. Existing records are not silently rewritten.

### Resources
Project resource membership; labor, equipment, material, contractor and role categories; default rate type; resource calendar; units/time; availability and over-allocation policy; leveling priority; assignment progress permissions. Resource master data is managed in the Resources window. Cost and leveling calculations remain in the shared calculation core.

### Settings
Scheduling selectors:
- duration basis (working-time/calendar-time where supported);
- project calendar and lag calendar;
- constraint policy;
- criticality definition (Total Float threshold or Longest Path where supported);
- Total Float threshold;
- open-end handling;
- out-of-sequence progress policy;
- Retained Logic / Progress Override;
- actual-date handling;
- resource leveling policy.

Calendar selectors:
- default project calendar;
- working days and work periods;
- holidays and exceptions;
- special working days;
- fiscal year start.
Display selectors:
- Jalali/Gregorian;
- date format;
- number format and digits;
- decimal precision;
- time format.
A setting must map to a versioned server contract; otherwise show unavailable rather than a client-only false setting.

### Codes
Assigned project code/value pairs, dictionary source, assignment scope and permission-aware edit. Values come from organization/project dictionaries; arbitrary uncontrolled values are prohibited.

### Notebook
Project-scoped rich text entries, attachments, author/time and revisions only when a persistent project notebook service exists. Browser-local Comments must be labelled local and must not be represented as project notebook records.

### Budget Log, Spending Plan, Budget Summary and Funding
Display persisted period/budget/funding facts only. Keep Original Budget, Approved Budget, Revised Budget, Commitments, Actual Cost, Remaining Cost, EAC, ETC, Cost Variance, Contract Value, Approved Changes, Pending Claims and Funding Sources as distinct fields. No client-side totals are fabricated.

### Baselines
Primary, Secondary and Tertiary baseline assignment; create, replace, remove; baseline ID/name/description; created by/date; compare with current project. Mutations require baseline service, permission, revision guard and confirmation.

### Documents
Project-linked document list, category, document ID, revision, upload metadata, access, preview/download and audit. Document master operations belong to the Documents window.

### History
Server audit entries: field, old value, new value, actor, timestamp, reason, revision and source. Browser-local notes are not project history.

### UDFs
Project-scoped user-defined fields from the field registry, including data type, unit, validation, visibility and access rules.

## 6. Editing, save and conflict behavior

- Project selection changes the details context but does not open the project.
- Open is a distinct command.
- Dirty form: Save / Discard / Cancel before changing selection or closing.
- Metadata saves use metadata settings revision, not the workspace data revision.
- 409 conflict offers Reload Latest; no silent overwrite.
- Permission denial explains why the control is disabled.
- Calculated facts are read-only and supplied by authoritative services.
- Layout state is separate from project data and settings.
- Only operations with an explicit undo contract may be offered as undoable.

## 7. Toolbar and commands

Project toolbar groups:
Project (New/Open/Close); Edit (Edit/Copy/Paste/Delete); Structure (Add Domain/Add Portfolio/Move); Display (Table/Bar Chart/Gantt/Summary); Layout (Open/Save/Save As); Data (Refresh/Import/Export); Filter (Filter/Group/Sort); Details (Show/Hide/Customize); Print (Preview/Print).

Shortcuts:
Ctrl+N New; Ctrl+O Open; Ctrl+S Save supported edit/layout; Ctrl+F Find; Delete Delete selection; F5 Refresh; Enter Open selected; Alt+Enter Properties. Shortcuts must respect focus inside text editors and permission state.

## 8. Localization and accessibility

English/LTR and Persian/RTL are first-class. Locale controls direction; calendar is independent. Mirror tree placement, tabs and alignment in RTL. Keep numeric precision and canonical dates unchanged. Use semantic tree/table/tablist/tabpanel/splitter roles, keyboard access, visible focus and at least 4.5:1 text contrast. All components consume centralized theme tokens.

## 9. Acceptance criteria

- Structure and Register are separate and display only authorized records.
- Project Details is bottom-docked; Activity Details and WBS Details remain separately scoped.
- Every field has a documented source, type, editability, permission and validation.
- No unsupported editable controls or fabricated facts.
- Project selection, Open, save, cancel, conflict and permission behavior are deterministic.
- Layout preferences persist without changing project data.
- Visual verification at 1440, 1280, 1024, 768 and 390 px in English/LTR and Persian/RTL.
- E2E covers project selection, details tabs, resize/collapse, metadata save/reload, conflict and denied permission.
- Screenshots cover the Projects window and every Project Details tab in both locales.

## 10. Known API boundary

Current project metadata API exposes project ID, tenant ID, name, revision, description, start date, date system, primary calendar and a separate settings revision. It supports metadata update for name, description, start date, date system and primary calendar. The inspected API does not establish organization-wide Business Domain/Portfolio management, full register columns, project defaults persistence, full budget summary, project history, or all detail-tab mutations. Those remain blocked on explicit service contracts.
