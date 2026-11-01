# CUBI Form Designer, Report Layout, Data Binding and Approval Workflow — Architecture Addendum

**Document ID:** CUBI-FORM-DESIGN-002  
**Status:** Mandatory product/architecture requirements; implementation is not implied by this specification  
**Applies to:** Organization and project form libraries, form designer, report templates, daily/weekly/monthly field reports, submissions, approvals, charts, print/PDF and exports  
**Related contract:** `docs/engineering/PMBOK_FORM_BUILDER_AND_FORM_CALCULATIONS.md` (CUBI-FORM-CALC-001)  
**Related execution:** GitHub issue #1481 (actual UI/source/control mapping); issue #1617 (Form Builder end-to-end product capability)

## 1. Binding purpose

This addendum records the product-owner requirements for a professional document-oriented Form Designer. It is part of the Form Builder architecture and must be read together with CUBI-FORM-CALC-001 before design or implementation. It is not permission to duplicate the shared calculation engine, weaken authorization, or claim that a feature exists before it is implemented and tested.

The Form Designer must support both structured data collection and professional multi-page documents. Its editing experience should combine spreadsheet-like tables/formulas with word-processor-like text, images, page layout, headers and footers. It must remain a form/report system backed by typed project data, not a free-form document editor disconnected from project controls.

## 2. Form libraries and ownership

Two distinct libraries are mandatory:

1. **Organization Central Form Library** — organization-owned standard templates reusable across authorized projects. Only authorized organization roles may publish or change canonical versions.
2. **Project Form Library** — project-specific templates and project-owned copies/derivatives of organization templates.

Rules:
- Creating a project copy or tailoring an organization template must never mutate the organization source template.
- Every template has a stable ID, immutable published versions, owner/scope, status, author, reviewer/publisher, timestamps, change reason and source-template/version reference where applicable.
- Project administrators may tailor only within their grants. Organization-locked fields/sections remain locked.
- A project may use an approved organization version while retaining historical submissions against the exact version originally used.
- Library search, category, tags, language, project type/industry applicability, status, owner and version filters are required.
- The UI location is within the project Visual Workspace menu, under the Forms/Form Builder area, consistent with the approved workspace navigation. The organization library is available only in the organization administration context and to authorized users.

## 3. Form Designer workspace

Provide a dedicated designer with these functional areas:
- Header Designer.
- Body/Section Designer.
- Table and Formula Designer.
- Project Data Binding / Reference Picker.
- Chart Designer.
- Footer and Approval Designer.
- Roles, Access and Workflow Designer.
- Page Setup, Print Preview and Export.

Required editing capabilities:
- Add, remove, duplicate, reorder and group components using a structured palette and drag/drop where supported.
- Add text, headings, labels, help/instruction text, images, tables, charts, page breaks, page numbers, dynamic project fields and approval blocks.
- Configure alignment, spacing, dimensions, borders, fills, typography, column widths, row heights and component visibility.
- Support free-layout, table-first and mixed layouts.
- Support reusable sections and repeating sections/rows (for example, one row per activity, work front, contractor, crew, equipment item or material).
- Provide undo/redo, draft autosave/recovery, preview with sample data, validation and version comparison.
- Prevent invalid layouts from publishing; show actionable errors and warnings.
- Provide accessible keyboard operation and localized RTL/LTR behavior.

## 4. Header and document identity

Header components must support:
- Image upload in JPG/JPEG and PNG formats.
- PNG transparency preservation, including transparent-background logos. Provide an optional background-removal operation that produces a transparent result; never silently alter the original uploaded asset.
- Image resize/crop/fit, aspect-ratio preservation, alignment and positioning.
- Organization, project, employer/client, consultant, contractor and other configurable party logos/names.
- Project name/ID, contract title/number, report title/number, work package/WBS, location/work front and other configured metadata.
- Sectioned header layout, columns, borders, separators, fills and locked positioning.
- Repeating header on every page, with explicit first-page/continuation-page variants.
- Optional user-controlled visibility of individual header fields.

Date behavior:
- A date picker must support selecting today, yesterday, two days earlier, or any permitted historical date; this is an example of the date range, not a hard-coded limit.
- Display Gregorian and Jalali dates, with a project/user-selected display preference and optional simultaneous dual-calendar display.
- Store canonical date/time and timezone independently of localized display text. Calendar conversion must not change the underlying instant/date.
- Distinguish report/effective date, record creation timestamp, last-modified timestamp, submission timestamp and approval timestamp.
- Future report dates, backdating limits and corrections are governed by configurable project policy and permission. Backdating must be auditable.
- Do not infer a report date from the workstation clock when the user is explicitly selecting a historical reporting period.

## 5. Body content, tables and cell formatting

The body must support:
- Rich text, headings, paragraphs, numbered/bulleted lists and configurable labels.
- Tables with configurable row/column counts, insert/delete, reorder, merge/split cells, repeatable rows, nested sections where supported, row/column sizing and cell alignment.
- Per-table, per-row, per-column and per-cell borders, fills, typography and number/date formats.
- Fixed, flexible and content-fit column sizing.
- Frozen header rows in interactive table editing where applicable.
- Column visibility, sorting and filtering.
- Filter controls for one table and report-level filters that scope multiple bound tables/charts.
- Filters must affect presentation/query scope only; they must not delete or mutate source records.
- Large tables must paginate predictably and retain column headings on continuation pages.
- Validation and error messages must identify the exact field/cell/row.

## 6. Formula cells and calculation authority

Formula cells are required. They must use the shared CUBI Formula Core and approved domain services under CUBI-FORM-CALC-001. The designer must not evaluate arbitrary code, use eval-like execution, or create a parallel calculation engine in the browser.

Required formula features:
- Formula editor with function/operator assistance, field/column/cell reference picker, syntax/type validation, dependency preview and sample-input/sample-output testing.
- References to other cells, columns, rows, repeating table groups and approved form fields.
- References to prior approved reporting periods/submissions, with explicit period, project, template and approval-state selection.
- References to approved project records, including WBS, Activity ID, activity properties, quantities, resources, labor, equipment, materials, cost and canonical schedule/EVM outputs where permission and domain contracts allow.
- Aggregations and totals over selected rows, filtered sets or repeating groups, with clearly defined inclusion rules.
- Dependency graph, cycle detection, deterministic recalculation and visible stale/error state.
- Formula metadata must include stable formula ID/version, expression/AST, input references, result type, unit/currency, precision/rounding policy, null/missing-data behavior, authority class, source/assumptions, validation and test fixtures.
- A formula that reads a previous report must read the explicitly selected/defined prior approved snapshot, not an arbitrary latest draft.
- Corrections/revisions must not silently rewrite a previously approved or issued report. Recalculation against changed source data creates a traceable new revision or marks the prior result stale according to workflow policy.

Illustrative measured-quantity pattern (not a mandated formula): previous approved cumulative quantity + current-period accepted quantity = new cumulative quantity. Example: left-bank concrete previous 120 m³, current period 30 m³, cumulative 150 m³. The units, source records, acceptance status and reporting period must match. Rejected/unverified quantities must not silently enter accepted cumulative totals.

Schedule and EVM values (including dates, float, criticality, resource capacity/leveling and PV/EV/AC/SPI/CPI) must be read from the canonical shared domain services. A form may display or aggregate only where the domain contract permits; it must never shadow or replace authoritative schedule, calendar, resource, cost or EVM calculations.

## 7. Project data binding and provenance

A typed data-binding layer must connect form components to approved project data. It must:
- Offer a permission-filtered reference picker for project, contract, WBS, activity, location/work front, resource, labor, equipment, material, cost item, quality inspection, HSE observation, issue, risk, change, RFI and other supported entities.
- Store stable entity IDs and source revision/snapshot references, not translated display labels as identifiers.
- Display source, reporting period, unit, approval status, freshness and last-updated information for bound values.
- Distinguish manually entered, imported, calculated, reference-engine and AI-proposed values.
- Reject cross-tenant/cross-project references unless an explicit authorized shared scope exists.
- Preserve provenance in reports, exports and audit records.
- Enforce read/write permissions on the server; hiding a field in the UI is not authorization.
- Support missing-data indicators and never fabricate values to fill empty cells.

## 8. Charts and report visualizations

The designer must allow charts to be created from selected form fields, table columns, cell ranges or approved project-data series.

Required chart families include bar/column, line, pie/donut where meaningful, cumulative progress, planned-versus-actual and S-curve. Availability of a chart type must not imply that every data series is suitable for it.

Requirements:
- Select source fields/ranges and category/series/value mappings explicitly.
- Validate numeric series, units, date ordering, missing values and aggregation rules.
- Keep the source reference and source revision with the chart definition.
- Recompute from authoritative source values when data changes, subject to draft/approved snapshot rules.
- Display actual, planned, forecast, estimate and AI recommendation as distinct series/states.
- Do not render a chart as authoritative when required valid data is absent; explain the missing inputs.
- Support chart title, legend, axes, units, labels, date range, filtering and print-safe sizing.
- A report-level filter may control multiple charts and tables only when their filter mappings are compatible.

## 9. Footer, signatures and approval blocks

Footer Designer must support:
- Fixed/repeating footer and first-page/continuation-page variants.
- Page number and total page count.
- Document/report ID, revision, confidentiality/classification and controlled footer text.
- Configurable approval/signature blocks with name, role/title, organization, action, date/time and status.
- Multiple preparers, reviewers, approvers and final authorizers.
- Configurable approval sequence, parallel approvals, delegation/substitution policy and rejection/return-for-correction paths.
- Optional signature/acknowledgement evidence where the identity/signature service supports it.

Approval rules:
- A visible check mark is generated only from a persisted successful approval event by the authenticated authorized user.
- Users cannot tick or impersonate another person's approval.
- Record actor identity, role/grant, action, timestamp/timezone, document/template version, submission revision and evidence/reference.
- A rejection requires a reason and routes the submission according to workflow.
- Any material edit after approval invalidates or reopens affected approvals according to policy; the previously approved version and events remain immutable.
- Printed/exported documents must distinguish pending, approved, rejected and superseded states.
- A typed name or image of a signature is not, by itself, proof of authenticated approval.

## 10. User assignment, permissions and workflow

The designer must allow authorized owners to select:
- Report preparer/submitter.
- Data-entry contributors.
- Reviewers by role or named user.
- Approvers and final approver.
- Read-only observers and recipients.

Permissions must separately govern create, design, edit draft, fill, attach, view sensitive fields, submit, review, return, approve, reject, publish template, export, print and administer workflow. Support project/organization scope and least privilege.

Workflow states should be explicit and configurable, with a safe baseline such as Draft → Submitted → Under Review → Returned for Correction or Approved/Rejected → Issued/Archived. Not every workflow must use every state. Enforce segregation of duties where configured, optimistic concurrency, idempotency, audit, stale revision checks and server-side authorization.

## 11. Print layout, pagination and export

Provide a dedicated Page Setup and Print Preview experience before printing or issuing a PDF.

Required options:
- Paper sizes: A4, A3, A5 and custom dimensions; allow future locale-specific standards without hard-coded assumptions.
- Portrait and landscape orientation.
- Top/bottom/left/right margins, gutter and printable area.
- Page-specific or shared header/footer settings.
- Scale controls including fit-to-width, fit-to-page and explicit percentage, with warnings when readability is compromised.
- Manual and automatic page breaks.
- Repeat table header rows on subsequent pages.
- Keep-with-next/keep-together options for headings, approval blocks and rows where possible.
- Choose whether a wide table fits to page width, splits across pages, or uses landscape pages; never shrink text below a configurable legibility threshold without an explicit override.
- Page numbering, total pages, print range, selected sections and optional cover page.
- Preview every page with final pagination, fonts, images, headers, footers, charts and approval states.
- Consistent rendering between print preview, PDF and direct print.
- Export to PDF and supported spreadsheet formats while preserving the appropriate structure, formulas, values, units, charts and provenance. Export behavior must clearly distinguish editable formulas from calculated snapshots; do not claim that PDF contains executable formulas.

The print engine must paginate long/repeating tables deterministically and avoid clipping, overlapping, orphaned headings, split approval blocks and missing repeated headers.

## 12. Report families and period aggregation

The Form Designer must support templates/profiles for at least:
- Contractor daily site report.
- Consultant/inspector independent daily diary.
- Weekly progress report.
- Monthly project progress/management report.
- Other organization/project-specific reports.

The contractor's daily report and the consultant/inspector's diary remain separate records with separate authorship and approval; they may cross-reference the same event but must not overwrite each other.

Weekly/monthly reports may aggregate approved daily submissions and other authorized project records. They must show the reporting period, data cut-off, source revisions, unapproved/missing submissions, and whether figures are actual, planned, forecast, estimated or manually reported. Aggregation rules and cut-off timezone are explicit. A monthly report must not silently treat missing daily reports as zero production.

## 13. AI-assisted design

The internal CUBI assistant may draft a form from an authorized natural-language request, propose fields/tables/formulas/charts/header/footer/workflow and suggest data bindings. It must:
- Create a draft only; never publish or approve on behalf of a person.
- Use the same schema validator, formula parser/type checker, dependency checker and test harness as manually created forms.
- Explain every proposed project-data binding, formula source, unit, assumption and authority class.
- Identify unknown/missing data and ask rather than invent.
- Require explicit authorized approval before applying or publishing.
- Respect local-first CUBI AI constraints and all tenant/project permissions.
- Keep confidential project content out of general organizational knowledge unless separately authorized and sanitized under the knowledge-governance policy.

## 14. Localization, accessibility and platform consistency

- Support all CUBI product languages and RTL/LTR layout; Persian/Arabic text direction must not corrupt numeric/formula semantics.
- Support Jalali and Gregorian display with canonical date storage and timezone-aware timestamps.
- Formula results must be identical across locales; localized separators and display formatting are presentation concerns.
- The same template version, field IDs, formula semantics, workflow state and approval audit must be consistent across web, desktop and mobile.
- Mobile may use a responsive field-entry/approval view; the canonical printed layout remains paper-size based.
- Offline-capable desktop/mobile entry, if enabled by the platform policy, must queue changes with revision/conflict checks and must not fabricate successful server approval while disconnected.

## 15. Security, audit, retention and failure behavior

- Validate file type by content as well as extension; enforce size limits, safe image decoding, malware scanning where available and safe storage.
- Preserve originals; generated transparent-background assets are separate derived versions.
- Protect sensitive contract, personal, financial, HSE and signature data with field-level permissions, retention and export policies.
- Record design changes, formula changes, binding changes, submission edits, attachment changes, workflow transitions, exports and publication events.
- Use immutable version references for issued reports and approval events.
- Handle stale project revisions, unavailable source records, formula errors, missing prior periods, incompatible units/currencies and rendering failures explicitly.
- Never silently substitute zero, blank, a different reporting period or an unapproved value for missing/invalid data.

## 16. Non-functional requirements

- Separate definition/layout, formula, data-binding, workflow, persistence/API and rendering/export responsibilities.
- Keep the designer responsive for large forms/tables and reports; use bounded loading/virtualization where appropriate.
- Ensure deterministic document rendering for the same version, data snapshot, locale, fonts and page settings.
- Store fonts/assets or use approved portable font embedding for reproducible PDF output, subject to licensing.
- Keep template schema and output layout versioned independently where required.
- Provide import/export compatibility and migration tests; never break historical submissions.
- Provide observability for failed calculations, bindings, approvals, uploads and rendering without leaking sensitive field values.

## 17. Acceptance criteria and implementation gate

This specification is complete as a requirements record only. Product implementation is accepted feature-by-feature when evidence exists for:

1. Both organization and project libraries, including safe project derivation of organization templates.
2. Header image handling for JPG/JPEG/PNG, PNG transparency and optional background removal without overwriting originals.
3. Gregorian/Jalali date selection, historical dates, timezone and separate report/creation/submission/approval timestamps.
4. Contract/project/report identity fields and repeatable, configurable headers.
5. Rich text, structured tables, cell formatting, repeating rows, table/report filters and stable pagination.
6. Formula editor using shared Formula Core, prior approved period values and authorized project references, with type/unit/provenance/dependency tests.
7. Charts sourced from validated form cells/columns and project data, with no fabricated series.
8. Footer and approval blocks with named users/roles, real authenticated approval events and audit evidence.
9. Permissioned preparer/reviewer/approver assignment and tested role denial/segregation of duties.
10. Page setup for A4/A3/A5/custom, portrait/landscape, margins, scaling, page breaks, repeated headers and print preview.
11. PDF and spreadsheet export parity with source values, units, formulas/snapshots and provenance.
12. Daily contractor report, independent inspector diary, weekly and monthly report profiles with period cut-off and missing-data handling.
13. RTL/LTR, multilingual, accessibility and web/desktop/mobile consistency.
14. Golden tests, integration/PostgreSQL tests, authorization tests, rendering/PDF tests and independent review on the exact final SHA.

Every criterion must be marked separately as NOT REVIEWED, SPECIFIED, IMPLEMENTED—UNVERIFIED, TESTED, INDEPENDENTLY REVIEWED, OPEN or NOT APPLICABLE WITH REASON. Documentation or an open PR is not product implementation credit. No feature may be marked complete solely because it appears in this document.

## 18. Required implementation handoff

Before implementation, the contributor must:
- Read this addendum and CUBI-FORM-CALC-001.
- Review the existing form contract PR #1480 and execution issue #1481.
- Inventory current UI, schema, API, repositories, formula engine, report renderer and tests.
- Map every requirement above to existing source, planned source, permission, validation and test ID.
- Reuse existing shared formula/schedule/calendar/resource/cost/EVM services.
- Preserve the existing v1 field-assurance schema and introduce versioned contracts/migrations where needed.
- Report mapped, partially mapped, unmapped and not-applicable counts.
- Implement only the explicitly scheduled scope; do not claim the full designer is complete from a partial slice.
