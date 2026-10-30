# CUBI Workspace Form and Field Inventory

Status: Phase 3 blueprint.
Purpose: define the fields each surface must render, their source of truth and editability. The authoritative typed activity field list is the existing presentation registry (`apps/client-sync/src/p6-presentation-contract.ts`, `p6-field-registry.v1`, served by the API). This document groups those fields by surface; it does not redefine their types.

## Source and editability rules

| Source | Meaning | UI behaviour |
| --- | --- | --- |
| **User input** | Stored on the project/activity and sent with revision guard | Editable when role allows |
| **Computed** | Produced by the Shared Domain/Calculation Core | Read-only; never evaluated in the client |
| **Derived** | Client projection of stored data (e.g., WBS path label) | Read-only |
| **Dictionary** | Selected from a dictionary (calendar, code, resource) | Picker; read-only text if missing permission |
| **System** | Identity, revision, timestamps | Read-only metadata |

## Project creation

| Step | Field | Type | Required | Validation | Source |
| --- | --- | --- | --- | --- | --- |
| 1 | Business domain | enum | Yes | Construction/Oil & Gas/Infrastructure/Industrial/Energy/Other | User input |
| 1 | Portfolio | picker | No | Must belong to tenant | Dictionary |
| 2 | Project name | text | Yes | 2–120 chars | User input |
| 2 | Project ID | text | Yes | Unique per tenant; pattern `[A-Z0-9][A-Z0-9_-]{1,39}`; suggested from name | User input |
| 2 | Description | textarea | No | ≤2000 chars | User input |
| 3 | Start date | date | Yes | Valid in active calendar; not before calendar epoch | User input |
| 3 | Target finish | date | No | ≥ start | User input |
| 3 | Date system | enum | Yes | `gregorian` / `jalali` | User input |
| 3 | Project calendar | picker | Yes | Must exist in tenant | Dictionary |
| 3 | Responsible organisation | picker | No | Must belong to business domain | Dictionary |
| 3 | Default activity duration type | enum | No | Fixed duration / Fixed units / Fixed units per time | User input |
| 4 | WBS template | picker | No | Blank or template | Dictionary |
| 4 | Seed activities | toggle | No | Create sample WBS/activities | User input |

## Activity table columns (default set)

| Field | Source | Editable inline | Notes |
| --- | --- | --- | --- |
| Activity ID | User input | Yes | Unique per project |
| Activity name | User input | Yes | Required |
| WBS | Dictionary/derived | Via picker | Grouping key |
| Activity type | enum | Yes | Task dependent, resource dependent, level of effort, start/finish milestone, WBS summary |
| Duration | User input/computed | Yes | Working days; duration type rules apply |
| Start / Finish | Computed, editable for constraints | Yes with warning | Recalculated by core |
| Predecessors / Successors | Derived from relationships | Via assign dialog | Not free text |
| Total float / Free float | Computed | No | Read-only badge |
| Critical | Computed | No | Boolean indicator |
| Calendar | Dictionary | Yes | |
| % complete | User input | Yes | 0–100 |
| Status | Derived | No | Not started / in progress / complete |
| Primary constraint | enum + date | Yes | Per constraint semantics matrix |
| Resources | Derived | Via assignments | Summary display |
| Cost / Expense | Computed/input | Mixed | Per field registry disposition |
| Activity code values | Dictionary | Via assign dialog | |
| UDF values | User input/computed | Mixed | Per UDF definition |

All other registry fields remain available through the Columns dialog; the default set is a layout, not a hard limit.

## Activity Details tabs — required fields

### General
Activity ID, name, project, WBS, type, duration, duration type, calendar, responsible manager, primary constraint, secondary constraint, expected finish, description, notebook summary.

### Status
Status, percent complete type, duration % complete, units % complete, physical % complete, actual start, actual finish, remaining duration, remaining start/finish, suspend/resume date, data date.

### Resources
Assignment list (resource/role, units/time, budgeted/actual/remaining units, cost, curve, driving flag), add/remove/replace.

### Predecessors / Successors
Activity, relationship type (FS/SS/FF/SF), lag value and unit, calendar for lag, driving flag.

### Codes
Code dictionary columns and values.

### Steps / Documents / Expenses / Risks / UDFs
Step name, weight, percent complete; document title/type/status/file; expense item/cost account/amount/accrual; risk ID/title/probability/impact/exposure; UDF label/value/type.

### Summary
Duration, start/finish, float, cost, units rolled up from the core.

### Update History
Changed field, old/new value, user, timestamp, revision.

## WBS element form

| Field | Required | Rules |
| --- | --- | --- |
| WBS code | Yes | Unique among siblings; local code, display path derived |
| Name | Yes | 1–200 chars |
| Parent | Yes | Project root or WBS node |
| Sequence | Yes | Integer, ordering within parent |
| Status | No | Not started / active / complete (when status types are enabled) |
| Responsible manager | No | Organisation dictionary |
| Earned value settings | No | Only when EV is enabled for the project |

## Relationship form

Predecessor, successor, type (FS/SS/FF/SF), lag value (decimal text), lag unit (day/hour/…), lag calendar. Validation: no self-link, no duplicate pair, no cycle; tenant/project/revision scope.

## Calendar editor

Name, type (global/project/resource), workweek (7 days × shifts), shifts (start/end, hours), holidays/exceptions (date, name, working flag), default flag (global only). Existing holiday editing is preserved.

## Resource / role forms

Resource ID, name, type (labor/nonlabor/material), unit of measure, default units/time, max units/time, calendar, rates (effective-dated), role assignments, code values. Role ID, name, rates, limits, proficiency.

## Administration forms

User (username, name, email, roles, project access), security profile (privileges), admin preferences (defaults), categories (name/values), currency (code, symbol, decimals, base), financial period calendar (name, period boundaries).

## Localization and formatting

- Dates: project date system; Jalali fields accept Persian digits and convert to canonical ISO on save.
- Numbers: canonical decimal text in storage; display grouped per locale; never round in the client.
- IDs, codes and WBS codes stay LTR even in RTL layouts.
- Validation messages are localized; server codes remain stable for tests.

## Accessibility

Every input has a label, error text linked with `aria-describedby`, and keyboard order matching the visual order. Tables expose row/column semantics. Dialogs trap focus and return it on close.
