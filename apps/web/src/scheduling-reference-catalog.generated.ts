/** Generated from src/construction_pm/p6_code_reference.py. Do not hand-edit; run scripts/generate_web_scheduling_reference.py. */
export const SCHEDULING_REFERENCE_CATALOG = {
  "version": "0.8.7",
  "asOf": "2026-10-23",
  "requirements": [
    {
      "id": "SCH-001",
      "area": "Scheduling / CPM",
      "feature": "Forward pass and early dates",
      "semantics": "Evaluate network activities using duration, relationship type, signed lag, applicable working calendars, constraints, actual/progress state and Data Date to derive Early Start/Early Finish. Never calculate dates in a UI client.",
      "options": [
        "Schedule mode",
        "Data Date",
        "Activity calendar",
        "Relationship-lag calendar"
      ],
      "status": "MAPPED_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "SCH-002",
      "area": "Scheduling / CPM",
      "feature": "Backward pass and late dates",
      "semantics": "Run a genuine backward pass from the applicable project finish boundary. Preserve relationship feasibility, calendars, constraints and selected float interpretation; never substitute early dates for late dates.",
      "options": [
        "Schedule mode",
        "Project/opened-project finish boundary",
        "Constraint set"
      ],
      "status": "MAPPED_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "SCH-003",
      "area": "Scheduling / Float",
      "feature": "Total Float calculation selection",
      "semantics": "Start Float = Late Start - Early Start. Finish Float = Late Finish - Early Finish. Smallest Float = min(Start Float, Finish Float). Use the selected option consistently for published float and dependent criticality.",
      "options": [
        "Start Float",
        "Finish Float",
        "Smallest of Start Float and Finish Float"
      ],
      "status": "MAPPED_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "SCH-004",
      "area": "Scheduling / Critical path",
      "feature": "Critical activity definition",
      "semantics": "Critical classification must use the selected method, not a hidden fixed rule. Float-threshold mode applies the configured threshold. Longest Path traces driving relationships from the terminal activity/finish boundary; critical and longest-path membership are not interchangeable.",
      "options": [
        "Total Float less than or equal to threshold",
        "Longest Path"
      ],
      "status": "MAPPED_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "SCH-005",
      "area": "Scheduling / Multiple float paths",
      "feature": "Multiple critical float paths and path ordering",
      "semantics": "When enabled, calculate the configured number of paths using the selected endpoint and path method; persist stable path rank/order. These outputs are calculated fields, not manually edited values.",
      "options": [
        "Enable/disable",
        "Maximum path count",
        "Ending activity",
        "Total Float or Free Float method"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "Exact Version 26 advanced-option mapping and end-to-end path regression evidence remain to be completed."
    },
    {
      "id": "SCH-006",
      "area": "Scheduling / Progress boundary",
      "feature": "Data Date and scheduling boundary",
      "semantics": "Treat Data Date as the boundary from which remaining work is scheduled. Progress through the prior work period must be reconciled before advancing it. Data Date, time zone, actuals and remaining work must be explicit in immutable calculation input.",
      "options": [
        "Current Data Date",
        "New Data Date",
        "Manual or automatic scheduling"
      ],
      "status": "MAPPED_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "SCH-007",
      "area": "Scheduling / Out-of-sequence",
      "feature": "Progressed-activity relationship logic",
      "semantics": "Retained Logic keeps remaining work subject to unfinished predecessor logic. Progress Override allows progressed work to advance without that remaining logic. Actual Dates bases passes on recorded actual dates. The selected policy must never silently fall back.",
      "options": [
        "Retained Logic",
        "Progress Override",
        "Actual Dates"
      ],
      "status": "MAPPED_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "SCH-008",
      "area": "Scheduling / Relationships",
      "feature": "Relationship types, lead/lag and selected lag calendar",
      "semantics": "Support FS, SS, FF, SF and signed lag/lead. Boundary constraints are: FS successor start >= predecessor finish + lag; SS successor start >= predecessor start + lag; FF successor finish >= predecessor finish + lag; SF successor finish >= predecessor start + lag. These are working-calendar/time-boundary constraints, not naive Gregorian date arithmetic: resolve duration/lag through the correct activity and lag calendars, actual/progress state and time precision. Use the selected reference scheduler-compatible lag calendar; never discard negative lag.",
      "options": [
        "FS",
        "SS",
        "FF",
        "SF",
        "Positive lag",
        "Negative lag/lead",
        "Successor calendar",
        "Predecessor calendar",
        "24-hour calendar",
        "Project default calendar"
      ],
      "status": "MAPPED_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "SCH-009",
      "area": "Scheduling / Constraints",
      "feature": "Primary, secondary and mandatory constraints",
      "semantics": "Model each supported constraint by its exact early/late-pass semantics. Mandatory Start/Finish are hard constraints; date-window constraints are soft and can distort float. Never clamp negative float to zero or propagate a constraint contrary to reference scheduler semantics.",
      "options": [
        "Start On",
        "Start On or Before",
        "Start On or After",
        "Finish On",
        "Finish On or Before",
        "Finish On or After",
        "Mandatory Start",
        "Mandatory Finish",
        "As Late As Possible where applicable"
      ],
      "status": "MAPPED_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "SCH-010",
      "area": "Scheduling / Advanced options",
      "feature": "Expected Finish, open ends, opened projects and external relationships",
      "semantics": "Keep each option explicit in settings and immutable input. Expected Finish, open-ended activity criticality, open-project finish boundary, external relationships and external resource assignments must not be silently ignored.",
      "options": [
        "Use Expected Finish Dates",
        "Make open-ended activities critical",
        "Each Project vs Opened Projects",
        "Ignore other-project relationships",
        "Include external resource assignments"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "Each advanced setting needs source-to-contract-to-engine-to-test trace, including external-project scenarios."
    },
    {
      "id": "CAL-001",
      "area": "Calendars",
      "feature": "Global, project and resource calendars",
      "semantics": "Represent calendar kind, identity, version, base/inherited calendar, assignment scope, workweek, date exceptions and effective references. Task Dependent uses activity calendar; Resource Dependent uses assigned resource calendars. Never guess a default for an unresolved calendar.",
      "options": [
        "Global calendar",
        "Project calendar",
        "Resource calendar",
        "Calendar assignment",
        "Base/inherited calendar"
      ],
      "status": "MAPPED_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "CAL-002",
      "area": "Calendars",
      "feature": "Work intervals, exceptions and hours-per-time-period conversions",
      "semantics": "Preserve normal workdays, nonwork exceptions, forced workdays, intraday work/nonwork intervals, work hours per day and calendar-specific conversion factors. Use version-bound snapshots for deterministic replay.",
      "options": [
        "Workday",
        "Nonworkday",
        "Standard day",
        "Total work hours/day",
        "Detailed work hours/day",
        "Workweek",
        "Time Periods",
        "Inherit holidays/exceptions"
      ],
      "status": "MAPPED_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "CAL-003",
      "area": "Calendars / Localization",
      "feature": "Jalali display calendar versus calculation calendar",
      "semantics": "Keep stable canonical storage/calculation dates separate from Jalali/Gregorian display. Changing locale must not shift a stored instant or schedule date.",
      "options": [
        "Gregorian display",
        "Jalali display",
        "Project calculation time zone"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "Localization date-boundary and round-trip tests are required; this is a CUBI extension, not a native reference scheduler feature claim."
    },
    {
      "id": "ACT-001",
      "area": "Activities",
      "feature": "Activity types and calendar driving rules",
      "semantics": "Support Task Dependent, Resource Dependent, Level of Effort, Start Milestone, Finish Milestone and WBS Summary with distinct scheduling behavior. They must not share one generic duration algorithm.",
      "options": [
        "Task Dependent",
        "Resource Dependent",
        "Level of Effort",
        "Start Milestone",
        "Finish Milestone",
        "WBS Summary"
      ],
      "status": "MAPPED_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "ACT-002",
      "area": "Activities",
      "feature": "Activity duration type and recalculation relationships",
      "semantics": "Enforce each duration-type invariant across duration, total units and Units/Time. Fixed Units/Time keeps Units/Time fixed as duration changes; Fixed Duration & Units/Time fixes duration and rate so units are derived; Fixed Units keeps total units fixed so duration/rate depend on the edited variable; Fixed Duration & Units keeps duration and units fixed so Units/Time is derived. Implement trigger-specific recalculation when duration, total units or rate changes; respect resource/role assignment calculation preferences and working-time conversions. Milestones must reject duration-type operations where reference scheduler disables them.",
      "options": [
        "Fixed Units/Time",
        "Fixed Duration & Units/Time",
        "Fixed Units",
        "Fixed Duration & Units"
      ],
      "status": "MAPPED_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "ACT-003",
      "area": "Activities / Status",
      "feature": "Original, actual, remaining and at-completion values",
      "semantics": "Keep Original/Planned, Actual, Remaining and At Complete duration distinct. reference scheduler defines At Complete Duration as Actual Duration + Remaining Duration. Validate legal edits by activity state and preserve coherent actual-date/remaining-work invariants.",
      "options": [
        "Original/Planned Duration",
        "Actual Duration",
        "Remaining Duration",
        "At Complete Duration",
        "Actual Start",
        "Actual Finish"
      ],
      "status": "MAPPED_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "ACT-004",
      "area": "Activities / Percent complete",
      "feature": "Duration, Units, Physical and scope percent complete",
      "semantics": "Duration % = 100 × (Original/Planned Duration - Remaining Duration) / Original/Planned Duration, with an explicit reference scheduler-compatible zero-duration/zero-plan rule. Units % = 100 × actual labor+nonlabor units / (actual labor+nonlabor units + remaining labor+nonlabor units), using the applicable reference scheduler labor/nonlabor/unit rules and explicit zero-denominator behavior. Physical % is separately entered/computed from configured weighted steps where applicable. Scope is product/context-specific and must not be equated to Physical. Store the percent-complete type with the value and recalculate only through shared calculation logic.",
      "options": [
        "Duration",
        "Units",
        "Physical",
        "Scope only where supported by selected reference scheduler product/context"
      ],
      "status": "MAPPED_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "ACT-005",
      "area": "Activities / Structure",
      "feature": "WBS, activity identifiers, codes, UDFs, status and hierarchy",
      "semantics": "Keep hierarchy identity separate from display order, preserve stable field/code IDs, validate activity-to-WBS membership and expose editable fields through typed permission-checked contracts. WBS Summary behavior remains distinct from ordinary tasks.",
      "options": [
        "WBS hierarchy",
        "Activity ID/name",
        "Activity codes",
        "UDF/custom fields",
        "Status/status code"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "Full field registry, hierarchy contract, UI column inventory and import/export mapping remain to be reconciled."
    },
    {
      "id": "RES-001",
      "area": "Resources / Resource dependent scheduling",
      "feature": "Driving and nondriving resource assignments",
      "semantics": "A driving resource can determine Resource Dependent activity duration from remaining work and assignment Units/Time. With multiple driving assignments, the limiting/longest completion time determines activity duration. Nondriving assignments are placed using their own schedule rules after activity dates are determined; persisting the flag alone is insufficient.",
      "options": [
        "Default driving flag",
        "Per-assignment driving override",
        "Assignment Units/Time and conversion period"
      ],
      "status": "KNOWN_GAP",
      "gap": "Observed on fix/reference scheduler-resource-assignment-driving-flag / Draft PR #1518: the authoritative composer still rejects Resource Dependent activities with RESOURCE_DEPENDENT_DRIVING_ASSIGNMENT_UNSUPPORTED. Forward/backward date derivation and nondriving placement are not complete. Proposed scheduling/resource-leveling input and its dedicated tests are not yet present on main; do not count them as shipped code."
    },
    {
      "id": "RES-002",
      "area": "Resources / Leveling",
      "feature": "Resource leveling controls and priority order",
      "semantics": "Leveling must respect resource capacity and activity logic. Preserve selected resources, priority rules, float limits, allowed overallocation, whether Early/Late dates are preserved and whether all resources are leveled. It is not just a UI conflict highlight.",
      "options": [
        "Level all resources",
        "Selected resource list",
        "Level within activity Total Float",
        "Minimum float to preserve",
        "Maximum percent to over-allocate",
        "Consider assignments in other projects with priority equal/higher than",
        "Preserve scheduled Early/Late dates",
        "Recalculate assignment costs after leveling",
        "Priority field",
        "Sort: Ascending/Descending/Hierarchy where allowed",
        "Write leveling log / View log",
        "Projects whose scheduling options control leveling"
      ],
      "status": "MAPPED_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "RES-003",
      "area": "Resources / Capacity and calendars",
      "feature": "Max Units/Time, effective rates and unit/time conversion",
      "semantics": "Resource capacity is effective-dated and unit-aware. Use the selected time-period conversion and calendar work hours for each capacity slice. Percentage capacity requires an explicit full-time base. Resource Max Units/Time is not assignment Units/Time.",
      "options": [
        "Max Units/Time",
        "Effective date",
        "Rate time period",
        "Calendar/global time-period source",
        "Unit of measure",
        "Percentage or absolute capacity where supported"
      ],
      "status": "MAPPED_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "RES-004",
      "area": "Resources / Assignment calculations",
      "feature": "Assignment units, actual units, remaining units and Units/Time",
      "semantics": "Preserve assignment Units/Time separately from resource Max Units/Time. When staffing changes, honor preserve-versus-recalculate preference and activity duration type. Validate actual/remaining values against activity state and retain explicit units.",
      "options": [
        "Preserve Units, Duration and Units/Time",
        "Recalculate Units, Duration and Units/Time",
        "Rate type",
        "Role/resource assignment"
      ],
      "status": "MAPPED_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "CST-001",
      "area": "Cost / Resource and role rates",
      "feature": "Resource and role cost calculation",
      "semantics": "For each assigned resource/role, calculate planned/budgeted, actual and remaining cost separately from the applicable quantity × price/unit and selected rate type/source/effective time period. Preserve currency and precision. At-completion cost and variance rollups must identify their source baseline and cost components. Scheduling/leveling recalculates multi-rate costs only when the configured option requests it; never use one current rate for all periods without checking effective dates.",
      "options": [
        "Rate Type",
        "Currency",
        "Recalculate assignment costs after scheduling",
        "Planned/Actual/Remaining values"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "Complete reference scheduler cost field/rate precedence, effective-date and rounding policies need exhaustive reference and formula tests."
    },
    {
      "id": "CST-002",
      "area": "Cost / Expenses",
      "feature": "Project expenses and cost accounts",
      "semantics": "Keep expense item, cost account, accrual timing, planned/actual cost and assignment/resource cost as separate concepts. Activity/WBS/project linkage and rollup rules must be explicit.",
      "options": [
        "Expense item/type",
        "Accrual type",
        "Cost account",
        "Planned/Actual cost"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "Official field-by-field expense semantics and rollup/rounding test cases remain to be completed."
    },
    {
      "id": "EVM-001",
      "area": "Progress / Earned Value",
      "feature": "WBS Earned Value technique settings",
      "semantics": "Honor WBS-level technique for performance percent complete and ETC. Methods such as 0/100, 50/50 and custom percent complete have distinct earning rules; ETC may use remaining cost or configured performance factor. Overrides/default inheritance must be traceable.",
      "options": [
        "Activity Percent Complete",
        "Resource curves/future-period buckets",
        "WBS milestones/weighted milestones",
        "0/100",
        "50/50",
        "Custom Percent Complete",
        "ETC = remaining activity cost",
        "PF=1",
        "PF=1/CPI",
        "PF=1/(CPI*SPI)",
        "User-defined PF",
        "WBS-specific setting"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "Exact mapping of all reference scheduler WBS Earned Value choices to CUBI persistence and EVM calculations needs a dedicated field/formula audit."
    },
    {
      "id": "EVM-002",
      "area": "Progress / Earned Schedule",
      "feature": "Earned Schedule and schedule-performance reconciliation",
      "semantics": "Keep earned-value schedule indicators distinct from time-based Earned Schedule measures. Document each metric's definition, period basis, zero-denominator behavior, calendar/time unit and reconciliation between schedule variance/index and duration/time variance/index.",
      "options": [
        "Reporting period",
        "Baseline selection",
        "Calculation date/Data Date",
        "Time unit and calendar"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "CUBI Earned Schedule extension formulas and native reference scheduler metric boundaries must be documented separately."
    },
    {
      "id": "BAS-001",
      "area": "Baselines",
      "feature": "Create, maintain and assign baselines",
      "semantics": "Separate baseline snapshot creation from assignment for summarization/comparison. Support project, primary, secondary and tertiary roles as applicable, with immutable identity and audit semantics.",
      "options": [
        "Create current-project copy",
        "Convert another project to baseline",
        "Project baseline",
        "Primary",
        "Secondary",
        "Tertiary"
      ],
      "status": "MAPPED_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "BAS-002",
      "area": "Baselines",
      "feature": "Selective baseline update and comparison",
      "semantics": "Updating a baseline must preserve selected scope: project details, all activities or filtered subset, plus activity/resource-assignment data choices. Never overwrite data excluded by the user's selection.",
      "options": [
        "Project details",
        "All activities",
        "Filtered activities",
        "Add/Delete/Update records",
        "Activity data types",
        "Resource assignment data types"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "Per-tab/per-field baseline update mapping and variance formula test matrix remain to be enumerated."
    },
    {
      "id": "VIEW-001",
      "area": "Views / Activity grid and Gantt",
      "feature": "Configurable columns, sorting, grouping, filters and timeline scales",
      "semantics": "Separate stored field identity from each view's column settings. Persist stable field IDs, order, visibility, width, sort/group/filter definitions and timescale. Timeline/grid edits must call authoritative typed APIs and must not calculate schedule dates in the UI.",
      "options": [
        "Show/hide columns",
        "Reorder/resize",
        "Sort",
        "Group",
        "Filter",
        "Gantt timescale",
        "Layout scope and persistence"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "Full menu/column/field inventory, persistence and end-to-end timeline edit tests are still required."
    },
    {
      "id": "VIEW-002",
      "area": "Views / Reports and print",
      "feature": "Saved report profiles, output layout and printable reports",
      "semantics": "A saved report profile is configuration, not output. Bind reports to project revision/Data Date/baseline and selected fields; preserve units/localization and report missing/unsupported fields instead of silently dropping them.",
      "options": [
        "Report profile",
        "Selected fields",
        "Project/revision",
        "Baseline",
        "Date range",
        "Locale",
        "Page layout/output format"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "reference scheduler report menu inventory and CUBI A4/PDF/XLSX output parity are not certified by this registry."
    },
    {
      "id": "DATA-001",
      "area": "Interoperability",
      "feature": "reference scheduler project/resource import-export mapping",
      "semantics": "Maintain versioned field maps for project XER, resource-only XER, XLSX and APIs where supported. Record type, units, nullable/default behavior, read/write capability, version provenance and round-trip behavior. Report unsupported data rather than silently dropping it.",
      "options": [
        "Format/version",
        "Project vs resource-only export",
        "Selected scope",
        "Conflict/update behavior",
        "Import validation report"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "Current official portals list project XER, resource-only XER, role-only XER, XLSX, MPX/XML, CPP, IPMDAR, UN/CEFACT and Unifier maps as applicable. Every field and round-trip rule still needs a concrete CUBI mapping."
    },
    {
      "id": "DATA-002",
      "area": "Data model / Field registry",
      "feature": "Complete field, column, enum and formula catalog",
      "semantics": "For every field record stable ID, display name, business object, type, unit, read/write status, null/default rule, calculated/stored status, sort/filter support, product context, version, API/database/import/export mapping and test evidence.",
      "options": [
        "Filter/sort",
        "Editable/read-only",
        "Calculated/stored",
        "Version/context",
        "UDF/custom field"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "The full reference scheduler Professional UI/field inventory must remain separate from EPPM data dictionary/API objects; exhaustive field-level mapping remains open."
    },
    {
      "id": "DATA-003",
      "area": "Data model / Custom formulas",
      "feature": "Safe formula engine and recalculation dependencies",
      "semantics": "If custom formulas are offered, compile through tokenizer/parser/typed AST/dependency graph, detect cycles, enforce units/null behavior, evaluate deterministically and never execute arbitrary Python/JavaScript via eval-style execution.",
      "options": [
        "Formula definition",
        "Result type",
        "Units",
        "Null behavior",
        "Dependency/recalculation policy"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "The CUBI formula field catalog and executable evaluator path must be linked and tested before any formula-parity claim."
    },
    {
      "id": "AUTH-001",
      "area": "Authoritative input / Reproducibility",
      "feature": "Persisted records to immutable schedule snapshot",
      "semantics": "Read authoritative activities, relationships, constraints, settings, calendars and resources within tenant/project/revision scope; validate them; bind exact versions to an immutable snapshot/hash; calculate from that snapshot; publish with revision checks. Unsupported semantics must fail closed rather than be omitted.",
      "options": [
        "Project revision",
        "Schedule mode",
        "Calculation time zone",
        "Calendar versions",
        "Resource/relationship settings",
        "Snapshot identity"
      ],
      "status": "MAPPED_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "SCH-011",
      "area": "Scheduling / General controls",
      "feature": "Automatic scheduling and coupled schedule actions",
      "semantics": "Represent automatic recalculation after date-affecting changes, automatic resource leveling during scheduling, and cost recalculation after scheduling as separate user-selected settings. Do not silently turn on leveling or cost recalculation merely because schedule calculation runs. Record which open project's schedule options control a multi-project scheduling run.",
      "options": [
        "Schedule automatically when a change affects dates",
        "Level resources during scheduling",
        "Recalculate assignment costs after scheduling",
        "Use scheduling options from selected open project",
        "Default settings/reset"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "Each general-option persisted value must be traced into production composition and tested for both enabled and disabled behavior."
    },
    {
      "id": "SCH-012",
      "area": "Scheduling / Out-of-sequence SS logic",
      "feature": "Start-to-start lag expiry basis",
      "semantics": "When an SS predecessor is out of sequence, the chosen basis changes how expired and remaining lag are computed. Early Start bases expiry on the predecessor internal Early Start and elapsed work periods; Actual Start bases it on the recorded actual start and elapsed time. This selector is disabled when Actual Dates mode is used and must not be treated as active in that mode.",
      "options": [
        "Early Start",
        "Actual Start",
        "Disabled under Actual Dates mode"
      ],
      "status": "MAPPED_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "SCH-013",
      "area": "Scheduling / Schedule dialog",
      "feature": "Multi-project Data Date, forecast start and scheduling log",
      "semantics": "Support each project's own Data Date or applying one selected Data Date to all open projects. The forecast-start option, when selected, uses the forecast date rather than the project's planned start/current Data Date. Scheduling logs must report the run and distinguish append/overwrite and HTML/plain output where offered.",
      "options": [
        "All projects use their own Data Date",
        "Apply selected Data Date to all opened projects",
        "Set Data Date and Project Planned Start to Project Forecast Start during scheduling",
        "Log to file",
        "HTML/plain log",
        "Overwrite/append existing log",
        "Schedule/Cancel/View Log"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "Multi-project run orchestration, forecast-start handling and schedule-log fidelity require dedicated contracts and end-to-end tests."
    },
    {
      "id": "RES-005",
      "area": "Resources / Cross-project leveling",
      "feature": "Leveler project priority, resource selection and result log",
      "semantics": "In addition to per-activity priority, record the selected project settings source and any threshold for including assignments from other projects. Project leveling priority is ranked 1 (highest) through 100 (lowest). Respect hierarchical priority sort where available, output the requested leveling log, and never hide remaining over-allocation.",
      "options": [
        "Scheduling options source project",
        "Include other projects with priority at or above configured threshold",
        "Project leveling priority 1-100",
        "Field priorities",
        "Ascending/Descending/Hierarchy",
        "Level all/selected resources",
        "Write/View log",
        "Default settings"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "Cross-project priority thresholds and leveling-log behavior are not yet proven by the current registry's test mapping."
    },
    {
      "id": "PRJ-001",
      "area": "Projects / EPS",
      "feature": "EPS hierarchy, project properties, defaults and project-level controls",
      "semantics": "Preserve the EPS hierarchy and project identity separately from displayed project names. Record project planned start/finish, forecast start where applicable, responsible organization, project calendar, Data Date, status and project-level defaults. The selected project context must determine settings without cross-project leakage.",
      "options": [
        "EPS parent/child",
        "Project ID/name",
        "Planned Start/Finish",
        "Forecast Start",
        "Project Calendar",
        "Data Date",
        "Project status",
        "Default project/template"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "A complete Version 26 project/EPS field registry and end-to-end inheritance/default-resolution test matrix still need to be enumerated."
    },
    {
      "id": "WBS-001",
      "area": "WBS / Work breakdown",
      "feature": "WBS hierarchy, status, earned-value defaults and rollups",
      "semantics": "Maintain stable WBS identity, parent/child relationships, responsible organization, WBS dates/status and hierarchy-specific defaults. WBS summarization and Earned Value must use explicit rollup rules and selected baseline/technique; never treat WBS Summary activity as a regular task.",
      "options": [
        "WBS hierarchy/order",
        "WBS code/name",
        "Responsible OBS",
        "WBS status/dates",
        "Earned Value technique",
        "WBS milestones/weight",
        "Activity assignment to WBS"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "The current scan did not verify a dedicated WBS master domain/repository. Field-level WBS persistence, authorization and summary-rollup mapping must be established before parity is claimed."
    },
    {
      "id": "CODE-001",
      "area": "Codes / Custom fields",
      "feature": "Activity, project, resource and role codes; UDFs",
      "semantics": "Keep code dictionary, code value and assignment as separate entities; preserve hierarchy, scope, stable IDs, data types, applicable subject area and assignment cardinality. UDFs must retain typed value/null semantics, and code changes must not corrupt saved layouts or filters.",
      "options": [
        "Global vs project/activity scope",
        "Code hierarchy",
        "Code value/description",
        "UDF data type",
        "Required/default/read-only rules",
        "Assignment/unassignment",
        "Sort/filter/group"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "The complete Version 26 code/UDF types, scopes, import/export mappings and UI catalog are not yet cross-referenced to all subject-area repositories."
    },
    {
      "id": "ACT-006",
      "area": "Activities / Steps",
      "feature": "Activity Steps, weighted progress and templates",
      "semantics": "Keep activity steps as identifiable child records with their own names, sequence, weight and completion state. For weighted Physical Percent Complete, calculate from the defined step-weight method and prevent invalid sums/ambiguous empty-step behavior. Template application must preserve chosen scope and avoid duplicate step identities.",
      "options": [
        "Add/reorder/delete steps",
        "Step weight",
        "Step completion",
        "Weighted physical progress",
        "Create/apply step template",
        "Selected activity scope"
      ],
      "status": "MAPPED_NOT_PROVEN",
      "gap": "Step-template persistence has code/test mappings; exact Version 26 editing rules and weighted-progress recalculation still need field-by-field acceptance evidence."
    },
    {
      "id": "RES-006",
      "area": "Resources / Distribution",
      "feature": "Resource curves and future-period bucket values",
      "semantics": "Preserve planned/remaining assignment units and costs by bucket, selected curve and bucket calendar/time basis. Curve distribution rules and manually entered future-period bucket values must remain distinguishable. Resource leveling must not silently reinterpret a curve as actual bucket data.",
      "options": [
        "Resource curve selection",
        "Curve shape/distribution",
        "Future-period bucket edit",
        "Time interval",
        "Units/cost display",
        "Manual bucket overrides"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "A complete curve library, per-bucket formula mapping, UI spreadsheet mapping and round-trip tests were not verified in this pass."
    },
    {
      "id": "PROG-001",
      "area": "Progress / Update workflow",
      "feature": "Update progress, apply actuals and close periods",
      "semantics": "Distinguish entered status/progress from a scheduling run and from applying actuals. Update Progress uses Current Data Date and New Data Date; the user can update all activities highlighted by Progress Spotlight or only selected activities. When actuals are applied from timesheets, remaining duration can be recalculated based on activity Duration Type, or always recalculated under the documented Fixed Units and Fixed Units/Time behavior. Reconcile actual start/finish, actual/remaining units/cost/duration and out-of-sequence policy. Store Period Performance is a period-addressed operation distinct from an ordinary current-state update.",
      "options": [
        "Current Data Date",
        "New Data Date",
        "Update all highlighted activities / selected activities",
        "Apply actuals from timesheets",
        "Recalculate remaining duration based on activity Duration Type",
        "Always recalculate remaining duration (activities treated as Fixed Units and Fixed Units/Time)",
        "Remaining Duration/Units",
        "Actual Start/Finish",
        "Out-of-sequence policy",
        "Store period performance",
        "Financial period"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "The exact Update Progress dialog operations, apply-actuals rules and closed-period performance records need a complete menu-to-domain-to-test map."
    },
    {
      "id": "PORT-001",
      "area": "Portfolio / Budget",
      "feature": "Project budgets, funding sources and budget change controls",
      "semantics": "Keep original budget, approved changes, current budget, funding source/period and forecast cost as distinct values. Rollups must preserve project/WBS ownership, currency, approval history and the difference between budget and schedule-derived cost.",
      "options": [
        "Budget amount",
        "Funding source",
        "Funding period",
        "Approved/unapproved change",
        "Project/WBS rollup",
        "Currency",
        "Forecast vs budget"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "This scan did not find a verified complete reference scheduler budget/funding implementation path; domain schemas, currency/period behavior and audit tests must be identified or built."
    },
    {
      "id": "RISK-001",
      "area": "Project controls / Risks and issues",
      "feature": "Issues, thresholds, risks and linked project documents",
      "semantics": "Maintain a risk as a distinct entity with stable identity, risk category, cause/event/effect, probability, impact, response/owner/status and linked activity/WBS scope. Risk assessment and response state must be auditable and must not be conflated with threshold-generated issues or ordinary issues.",
      "options": [
        "Risk category",
        "Probability/impact",
        "Response/owner/status",
        "Assign/remove risk from activity",
        "Linked WBS/activity/evidence"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "reference scheduler Professional Help labels this risk feature as Professional-only; the risk model, risk assignment behavior and response history do not yet have a verified dedicated CUBI domain/path and end-to-end tests."
    },
    {
      "id": "VIEW-003",
      "area": "Views / Timeline",
      "feature": "Gantt editing, data-date/progress lines, bars and timescale",
      "semantics": "A Gantt drag/edit must submit a domain mutation and then recalculate with the same authoritative engine as all other clients. Distinguish planned/early/late/actual/baseline/remaining dates and progress from drawing coordinates. Zoom/timescale and line/bar visibility are presentation state, not calculation settings.",
      "options": [
        "Edit start/finish/duration where permitted",
        "Data Date line",
        "Progress line",
        "Baseline bars",
        "Early/Late bars",
        "Timescale unit/interval",
        "Nonwork display",
        "Bar styles and visibility",
        "Zoom/scroll"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "A production Gantt/timeline read-edit-write-recalculate path and visual regression tests have not been proven through the current mapping."
    },
    {
      "id": "VIEW-004",
      "area": "Views / Analysis",
      "feature": "Activity Network, Trace Logic, usage profiles and tracking layouts",
      "semantics": "Views must render from versioned schedule, relationship and time-phased assignment facts. Trace Logic should show the actual driving predecessor/successor chain from the calculation result. Usage profile values must reconcile to assignment-period data; zoom/scale must not alter underlying values.",
      "options": [
        "Activity Network display",
        "Trace Logic path",
        "Activity/resource usage profile",
        "Spreadsheet time scale",
        "Unit/cost display",
        "Tracking layout",
        "Baseline/actual/remaining series"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "No exhaustive source-to-renderer map for Activity Network, Trace Logic, profiles, and tracking layouts has yet been established."
    },
    {
      "id": "VIEW-005",
      "area": "Views / Layout operations",
      "feature": "Group, sort, filter, summarize and reusable layouts",
      "semantics": "Keep field identity, view layout and filter definition separate. Support stable criteria, grouping levels, sort direction, WBS/project rollups, user/project/global scope and persistence. Calculated columns use the typed shared calculation engine. A filter must not mutate or delete records.",
      "options": [
        "Saved layouts",
        "Column selection/order/width",
        "Group levels",
        "Sort field/direction",
        "Filter rules",
        "User/project/global scope",
        "Summary/rollup behavior"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "Exact reference scheduler saved-layout scope, filter operators, group/sort fields and rollup behavior need a complete menu/field matrix."
    },
    {
      "id": "REPORT-001",
      "area": "Reports / Publishing",
      "feature": "Reports, project website publishing and summary services",
      "semantics": "Report definitions must record selected fields, grouping, filters, baseline, project revision, Data Date, locale and output format. Published output and summarization must be reproducible from identified source data; unsupported fields must be reported rather than omitted silently.",
      "options": [
        "Report definition",
        "Report fields/grouping/filter",
        "Output format",
        "Publishing scope",
        "Schedule/period",
        "Summary service policy",
        "Locale and page settings"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "reference scheduler report catalog, website publishing and summary-service schedule need exact implementation paths and reproducible output tests."
    },
    {
      "id": "TOOLS-001",
      "area": "Tools / Global change",
      "feature": "Global Change, date arithmetic and safe custom updates",
      "semantics": "Any bulk-change feature must model target object, filter criteria, old-value conditions, assignment expressions, arithmetic/date arithmetic, preview, affected-record count and explicit commit. Validate types/units and tenant/project scope; keep an audit of before/after values. Never evaluate arbitrary Python or JavaScript expressions.",
      "options": [
        "Select target subject/field",
        "Filter condition",
        "Assignment expression",
        "Arithmetic/date arithmetic",
        "Preview changes",
        "Apply/cancel",
        "Audit"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "No verified safe Global Change evaluator/transaction path was found in this source scan; do not expose the capability as complete before it exists and is tested."
    },
    {
      "id": "TOOLS-002",
      "area": "Tools / Quality checking",
      "feature": "Project Checker and top-down estimation",
      "semantics": "Quality checks must be deterministic, versioned and explain every finding with affected entity and evidence. Top-down estimates must record allocation rule, total, WBS scope and allocation basis; they must not overwrite detailed estimates without explicit confirmation.",
      "options": [
        "Check profile",
        "Severity thresholds",
        "Run scope",
        "Estimate total",
        "WBS/activity allocation basis",
        "Preview/accept"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "Exact Project Checker and Top-Down Estimation implementation mappings and acceptance suites remain unverified."
    },
    {
      "id": "FIN-001",
      "area": "Administration / Units and finance",
      "feature": "Admin preferences, currencies and financial periods",
      "semantics": "Central defaults such as hours/day, hours/week, hours/month, hours/year, currency precision/exchange rate and financial period definitions must be versioned and explicit in calculations. A user locale or UI preference must not silently change a project calculation's persisted unit conversions.",
      "options": [
        "Hours per day/week/month/year",
        "Standard time period",
        "Currency/precision/exchange rate",
        "Financial periods",
        "Week start/day preferences",
        "Default duration/EV settings"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "Admin-category complete list, currency/time-period precedence, precision and financial period rules are not fully mapped to source and tests."
    },
    {
      "id": "AUTH-002",
      "area": "Administration / Security",
      "feature": "Users, global/project profiles and resource security",
      "semantics": "Enforce least privilege at the domain/API layer, with project and organization scope checked for every read/write. UI hiding is not authorization. Changing profiles must not mutate project data; all denied writes must have no side effects and privileged operations must be auditable.",
      "options": [
        "User account",
        "Global profile",
        "Project profile",
        "OBS scope",
        "Resource access",
        "Field/operation permission"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "reference scheduler security profile and resource-access matrix must be compared to CUBI authorization contracts action by action."
    },
    {
      "id": "OFFLINE-001",
      "area": "Projects / Offline and multi-project",
      "feature": "Project checkout/check-in, local cache and multi-project boundaries",
      "semantics": "Treat online authoritative revision, local cached revision, pending edits and conflicts as distinct state. Check-in must use optimistic concurrency, preserve immutable mutation identity and reject conflicting reuse. Multi-project calculations must explicitly bind external relationships and resource assumptions instead of combining arbitrary cached snapshots.",
      "options": [
        "Open one/multiple projects",
        "Check out/check in",
        "Offline cache",
        "Refresh/reconcile",
        "Conflict resolution",
        "Retry queue",
        "Project revision"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "CUBI offline contracts exist in the architecture; full reference scheduler workflow equivalence and multi-project cache consistency remain unverified."
    },
    {
      "id": "ROLE-001",
      "area": "Resources / Roles",
      "feature": "Roles, proficiency, limits and role-rate calculations",
      "semantics": "Keep role definitions, proficiency, role limits, role-to-resource mapping, assignment role, role rate and actual assigned resource distinct. Role-based planning differs from assigning a named resource; substitution must preserve quantities, rate source and cost basis.",
      "options": [
        "Role",
        "Proficiency",
        "Role limit by time",
        "Price/unit rates over time",
        "Assign role to activity",
        "Assign resource from role",
        "Rate type",
        "Rate source",
        "Replace resource/role"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "No verified full role-master, role-rate and role-limit persistence chain was found in the current source inventory."
    },
    {
      "id": "PREF-001",
      "area": "Preferences / Calculation defaults",
      "feature": "User and project resource/role assignment calculation options",
      "semantics": "Calculation preferences must be explicit and versioned. Assignment changes must honor preserve/recalculate rules for duration, units and Units/Time. Project defaults for activity type, duration type, percent complete, rate type and calendar apply to new records unless the user explicitly requests a bulk change.",
      "options": [
        "Preserve Units, Duration and Units/Time",
        "Recalculate Units, Duration and Units/Time",
        "Default activity type",
        "Default duration type",
        "Default percent complete type",
        "Default activity calendar",
        "Default resource rate type",
        "Default cost account",
        "Hours per time period"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "Each preference needs schema/version, persisted setting, UI binding and regression proving a changed default does not silently mutate existing data."
    },
    {
      "id": "REFL-001",
      "area": "Projects / Reflection and what-if",
      "feature": "Reflection creation, comparison and controlled merge",
      "semantics": "A what-if/reflection copy preserves source identity and revision; differences are compared by typed entities; merge requires explicit scope and conflict policy; stale updates are rejected and accepted changes audited. A reflection must not silently overwrite authoritative activity/relationship data.",
      "options": [
        "Create reflection",
        "Compare differences",
        "Print difference report",
        "Select merge scope",
        "Conflict handling",
        "Merge/cancel"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "No complete reflection entity, difference-report or merge-conflict implementation was verified in this review."
    },
    {
      "id": "NOTE-001",
      "area": "Activities / Notes and documents",
      "feature": "Activity notebooks, topics and timeline attachments",
      "semantics": "Keep a notebook record separate from the activity, support topic/sequence and access context, and link attachments through stable references. Hiding/removing a visual Gantt attachment must not delete its source note/document unless explicitly requested.",
      "options": [
        "Notebook topic",
        "Note text",
        "Activity/WBS/project association",
        "Gantt text attachment",
        "Curtain attachment",
        "Show/hide attachment",
        "Permission and audit"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "Dedicated notebook/topic/attachment domain and storage paths are not yet mapped; activity-grid support does not prove notebook parity."
    },
    {
      "id": "ANALYSIS-001",
      "area": "Resource analysis / Forecasting",
      "feature": "Resource explorer, analysis profiles and dynamic leveling",
      "semantics": "Forecast capacity and demand as a time-phased view bound to assignment periods, current rates, calendar snapshots and project scope. Dynamic leveling proposals explain assumed availability and do not change the authoritative schedule until explicitly applied.",
      "options": [
        "Resource/project scope",
        "Profile/spreadsheet display",
        "Availability/limits/overtime",
        "Time scale",
        "Forecast/dynamic leveling",
        "Save tracking layout",
        "Apply/cancel proposal"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "Profiles and dynamic resource-analysis forecasting need a dedicated read model and UI/contract/test mapping; existing leveling code alone does not prove parity."
    },
    {
      "id": "VIZ-001",
      "area": "Visualization / reference scheduler Visualizer",
      "feature": "Time-scaled logic diagrams and advanced visual output",
      "semantics": "Visualizer outputs derive from the same schedule snapshot as the activity grid/Gantt. Relationship logic, calendar-scaled duration, path highlighting and selected baseline remain consistent; visual positioning cannot recalculate the network.",
      "options": [
        "Timescaled logic diagram",
        "Selected activities/relationships",
        "Calendar/time scale",
        "Critical/float-path highlighting",
        "Baseline/actual/remaining display",
        "Export/print layout"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "A separate visualizer-equivalent layout/output and logic-diagram regression suite are not mapped in this catalog."
    },
    {
      "id": "DATA-004",
      "area": "Interoperability / API",
      "feature": "REST, SOAP and data dictionary contracts",
      "semantics": "Maintain API endpoint/entity/field mappings separately from UI fields. Record HTTP operation, read/write behavior, ID mapping, nullability, enumerations, date/time serialization, errors, paging and concurrency. Do not infer that the API exposes every Professional UI field.",
      "options": [
        "API release/version",
        "Endpoint/entity",
        "Read/write capability",
        "Authentication/permission",
        "Paging/filtering",
        "Error mapping",
        "Date/time serialization"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "Endpoint-by-endpoint API coverage, data-dictionary field mapping and contract round-trip evidence remain unenumerated."
    },
    {
      "id": "DATA-005",
      "area": "Interoperability / Exchange formats",
      "feature": "Format-specific import/export semantics and loss reporting",
      "semantics": "For each supported format map relevant fields, dependencies, enums, calendars, baselines, assignments, codes and custom fields. Report unsupported/transformed information before exchange; round-trip tests distinguish intentionally nonportable values from implementation loss.",
      "options": [
        "XER project",
        "XER resource-only",
        "XER role-only",
        "XLSX",
        "reference scheduler XML",
        "Microsoft Project MPX/XML where supported",
        "CPP",
        "IPMDAR",
        "UN/CEFACT",
        "Unifier schedule-sheet integration",
        "Conflict/update option",
        "Validation report"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "No format should be treated as implemented until a versioned field map and fixture-based round-trip tests exist."
    },
    {
      "id": "ISSUE-001",
      "area": "Project controls / Issues",
      "feature": "Issues, ownership, history and linked tracking layouts",
      "semantics": "An issue is its own record with status, priority/owner, dates/duration, history and linked project/WBS/activity/resource references. Issue duration and risk duration are not activity duration. Status changes and responsibility reassignment must be audited.",
      "options": [
        "Create/edit/delete issue",
        "Issue status",
        "Assign responsible OBS/resource",
        "Link activity/WBS/resource",
        "Tracking layout",
        "Issue history",
        "Email/notification"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "A dedicated issue record/repository, duration/history behavior and every issue UI operation were not verified in the current CUBI code scan."
    },
    {
      "id": "THRESH-001",
      "area": "Project controls / Thresholds",
      "feature": "Threshold definitions and threshold-generated issues",
      "semantics": "A threshold includes a specific monitored parameter, comparison rule/value, applicable project/WBS scope, responsible owner and assigned tracking layout. Monitoring must evaluate the selected period/revision deterministically and create/update/remove alerts according to explicit lifecycle rules; never rely on hard-coded UI warning logic.",
      "options": [
        "Parameter",
        "Comparison/operator",
        "Threshold value",
        "Project/WBS scope",
        "Responsible OBS",
        "Tracking layout",
        "Enable/disable",
        "Monitor/delete generated issue"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "No verified threshold definition model/evaluator or threshold-to-issue lifecycle path is mapped to CUBI yet."
    },
    {
      "id": "DOC-001",
      "area": "Project controls / Work products and documents",
      "feature": "Document library, deliverables, status and activity/WBS association",
      "semantics": "A document/work product record holds stable identity, category/status, location/version reference and deliverable flag; associations to activity, WBS and project are separate links. Removing a link must not delete the underlying stored file or record. Access, revision and integrity checks are required for every attachment.",
      "options": [
        "Create/delete document record",
        "Category/status",
        "Work product/deliverable flags",
        "Location reference",
        "Assign/remove activity/WBS link",
        "Open document",
        "Document revision/access"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "CUBI has general document-control domains, but reference scheduler-style Work Products and Documents fields/associations need an explicit parity mapping and round-trip tests."
    },
    {
      "id": "ORG-001",
      "area": "Organization / OBS",
      "feature": "OBS hierarchy, WBS responsibility and scope security",
      "semantics": "Keep OBS hierarchy and responsible-manager assignment independent of WBS and user profile records. Responsibility and security scope must be enforced in API/domain authorization, not only by hiding UI items. Moving an OBS node must preserve valid assignments and audit scope changes.",
      "options": [
        "Create/edit/delete OBS node",
        "Hierarchy/order",
        "Assign OBS to WBS",
        "Issue responsibility",
        "Resource/project security scope"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "A dedicated OBS domain/repository and the complete reference scheduler OBS-to-user/resource-security matrix are not verified in this reference pass."
    },
    {
      "id": "PORTFOLIO-001",
      "area": "Portfolio / Project selection",
      "feature": "Portfolios, included projects and project-window scope",
      "semantics": "Portfolio membership, access and displayed portfolio details are distinct from the EPS hierarchy. Any portfolio-level summary or calculation must explicitly state which projects and revisions are included; it must not silently alter project membership or schedule calculations.",
      "options": [
        "Create/edit/delete portfolio",
        "Add/remove projects",
        "Portfolio membership",
        "Add/remove users",
        "Change current portfolio",
        "Portfolio scope for summaries"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "Portfolio data model, membership permissions and summary aggregation have not been verified as an end-to-end CUBI feature."
    },
    {
      "id": "RES-007",
      "area": "Resources / Shifts",
      "feature": "Resource shifts and shift-aware leveling",
      "semantics": "Shift capacity and shift time windows must be explicit, time-zone-aware, calendar-versioned and associated with a resource/rate. Leveling cannot silently treat multiple shifts as a single default shift or aggregate overlapping shift capacity twice.",
      "options": [
        "Shift definition",
        "Working interval",
        "Resource/shift assignment",
        "Calendar version",
        "Shift effective period",
        "Capacity/unit rate per shift"
      ],
      "status": "KNOWN_GAP",
      "gap": "The current resource-leveling input contract explicitly lacks full shift-level leveling support; do not model multiple shifts as the generic default calendar."
    },
    {
      "id": "EVM-003",
      "area": "Progress / EVM formulas",
      "feature": "EV, PV, AC, CV/SV, CPI/SPI, EAC/ETC/VAC formula definitions",
      "semantics": "For a selected status date and selected baseline, preserve the definitions EV (earned budget value), PV (planned budget value), AC (actual cost), CV=EV-AC, SV=EV-PV, CPI=EV/AC and SPI=EV/PV. EAC/ETC must follow the selected WBS ETC technique and performance-factor choice; do not impose one universal EAC formula. VAC=BAC-EAC. Each denominator-zero, missing-baseline, currency and period rule must be explicit and tested.",
      "options": [
        "Baseline",
        "Status/Data Date",
        "WBS EV technique",
        "ETC method",
        "Performance factor",
        "Cost currency",
        "Financial/reporting period"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "Native EV field definitions and each WBS ETC/performance-factor formula are not yet traced to exact CUBI calculation functions and denominator/rounding tests."
    },
    {
      "id": "SCH-014",
      "area": "Scheduling / Schedule checks",
      "feature": "Check Schedule diagnostics",
      "semantics": "Run explicit schedule-quality checks against the selected project revision and schedule settings. Each finding identifies the rule, affected activities/relationships and actionable evidence. A diagnostic check does not silently rewrite the schedule and is distinct from a separate Project Checker workflow.",
      "options": [
        "Check selected project/scope",
        "Selected check rules where supported",
        "Severity/report results",
        "Open affected activities",
        "Re-run after fixes"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "reference scheduler Check Schedule rule catalog, severity mapping and result presentation are not yet enumerated against a CUBI checker implementation."
    },
    {
      "id": "ADMIN-003",
      "area": "Administration / Category dictionaries",
      "feature": "Baseline, expense, WBS, document, risk, notebook and units-of-measure categories",
      "semantics": "Treat category dictionaries as their own versioned domain/enum with stable IDs, allowed usages, rename/delete constraints and reference checks. Renaming/deleting must not orphan assigned values or silently change semantic meaning.",
      "options": [
        "Baseline types",
        "Expense categories",
        "WBS categories",
        "Document categories/statuses",
        "Risk categories",
        "Notebook topics",
        "Units of Measure",
        "Create/edit/rename/delete/assign"
      ],
      "status": "INVENTORY_REQUIRED",
      "gap": "A complete Version 26 admin-category schema and foreign-reference behavior matrix remains required; the shared code repository does not prove every category exists."
    }
  ],
  "formulas": [
    {
      "id": "FRM-TF-001",
      "feature": "Total Float — selected calculation option",
      "algorithm": "Start Float = Late Start - Early Start; Finish Float = Late Finish - Early Finish; Smallest Float = min(Start Float, Finish Float). Publish the value selected by Tools > Schedule > Options > General.",
      "inputs": [
        "Early Start",
        "Late Start",
        "Early Finish",
        "Late Finish"
      ],
      "options": [
        "Compute Total Float as: Start Float / Finish Float / Smallest of Start Float and Finish Float",
        "Hours-per-time-period administrative/calendar policy"
      ],
      "calendarRules": "Convert the date/time difference using the reference scheduler-compatible working-time and hours-per-time-period policy. Do not assume that a calendar-day subtraction equals reference scheduler duration hours.",
      "edgeCases": [
        "Missing early/late dates",
        "Different activity calendars",
        "Negative float",
        "Time-aware versus date-only calculation",
        "Hours/day, hours/week and hours/month policy changes"
      ],
      "status": "FORMULA_DOCUMENTED_PARITY_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "FRM-CRIT-001",
      "feature": "Critical activity classification",
      "algorithm": "Threshold mode: activity is critical when selected Total Float <= configured threshold. Longest Path mode: identify terminal activities with the latest calculated Early Finish and trace all driving relationships back through the network. Multiple Float Paths is a separate path-analysis feature and does not replace the General-tab criticality option.",
      "inputs": [
        "Early/Late dates",
        "Selected Total Float",
        "Finish boundary",
        "Relationships and driving relationships"
      ],
      "options": [
        "Total Float <= threshold",
        "Longest Path",
        "Each Project / Opened Projects",
        "Multiple paths: Total Float / Free Float; endpoint and count"
      ],
      "calendarRules": "The threshold must be converted with the selected reference scheduler time-period rules. Longest Path must respect multi-calendar scheduling and the selected project/open-project boundary.",
      "edgeCases": [
        "Open-ended activities",
        "Non-driving relationships",
        "Hard/soft constraints",
        "Multiple open projects",
        "Multiple calendars"
      ],
      "status": "FORMULA_DOCUMENTED_PARITY_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "FRM-REL-001",
      "feature": "Relationship lower bounds in the scheduling passes",
      "algorithm": "FS: Successor Start >= Predecessor Finish + Lag; SS: Successor Start >= Predecessor Start + Lag; FF: Successor Finish >= Predecessor Finish + Lag; SF: Successor Finish >= Predecessor Start + Lag. These are boundary constraints; date/time boundaries and lag are resolved with the configured reference scheduler calendar rules, then evaluated in forward/backward passes.",
      "inputs": [
        "Predecessor Start/Finish",
        "Successor Start/Finish",
        "Relationship type",
        "Signed lag",
        "Predecessor/successor/project/24-hour lag calendar choice"
      ],
      "options": [
        "FS / SS / FF / SF",
        "Signed Lag/Lead",
        "Calendar for scheduling Relationship Lag",
        "SS lag expiry basis"
      ],
      "calendarRules": "Do not add raw calendar days. Convert lag through the selected lag calendar and duration through the applicable activity/resource calendar; preserve date-only or time-aware precision required by the schedule mode.",
      "edgeCases": [
        "Negative lag",
        "Zero-duration milestones",
        "Different calendars",
        "Out-of-sequence status",
        "Actual Dates mode disabling the SS lag-expiry selector"
      ],
      "status": "FORMULA_DOCUMENTED_PARITY_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "FRM-DURTYPE-001",
      "feature": "Activity duration type dependency rules",
      "algorithm": "Fixed Units/Time: hold Units/Time constant and derive quantity/duration according to the edited independent value. Fixed Duration & Units/Time: duration and Units/Time are fixed; total units are derived. Fixed Units: total units are fixed and duration/Units-Time adjust according to the edited value. Fixed Duration & Units: duration and units are fixed; Units/Time is derived. Apply the selected reference scheduler assignment recalculation preference and do not use one generic equation for all change events.",
      "inputs": [
        "Original/remaining duration",
        "Budgeted/planned units",
        "Units/Time",
        "Activity duration type",
        "Resource/role assignment",
        "Edit operation"
      ],
      "options": [
        "Fixed Units/Time",
        "Fixed Duration & Units/Time",
        "Fixed Units",
        "Fixed Duration & Units",
        "Preserve or recalculate Units/Duration/Units-Time"
      ],
      "calendarRules": "Units/Time is a rate whose time-period conversion must be explicit. Working-time duration must use the applicable calendar; resource/role rate types are separate cost settings.",
      "edgeCases": [
        "Add/remove resource",
        "Change duration",
        "Change total units",
        "Change Units/Time",
        "Milestones",
        "Zero duration",
        "Multiple resources and roles"
      ],
      "status": "FORMULA_DOCUMENTED_PARITY_NOT_PROVEN",
      "gap": "Change-event-specific reference scheduler recalculation behavior requires reference test vectors for all four duration types and resource/role assignment paths."
    },
    {
      "id": "FRM-ACDUR-001",
      "feature": "At Complete Duration",
      "algorithm": "At Complete Duration = Actual Duration + Remaining Duration.",
      "inputs": [
        "Actual Duration",
        "Remaining Duration"
      ],
      "options": [
        "Progress state",
        "Duration percent complete type",
        "Data Date"
      ],
      "calendarRules": "Both durations must share the same normalized unit and calendar interpretation before summing.",
      "edgeCases": [
        "Not-started activity",
        "In-progress activity",
        "Completed activity",
        "Milestone/zero duration",
        "Missing/invalid actuals"
      ],
      "status": "FORMULA_DOCUMENTED_PARITY_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "FRM-PC-001",
      "feature": "Duration Percent Complete",
      "algorithm": "Duration % Complete = 100 * (Original/Planned Duration - Remaining Duration) / Original/Planned Duration when Original/Planned Duration is non-zero. The zero-denominator behavior must follow a separately verified reference scheduler rule rather than an assumed default.",
      "inputs": [
        "Original/Planned Duration",
        "Remaining Duration",
        "Percent Complete Type"
      ],
      "options": [
        "Duration percent complete",
        "Schedule Data Date",
        "Progress update method"
      ],
      "calendarRules": "Normalize duration units before arithmetic. Do not compute date subtraction in the UI or mix elapsed hours with working-day durations.",
      "edgeCases": [
        "Original duration zero",
        "Negative remaining duration",
        "Duration beyond original",
        "Completed activity",
        "Milestone"
      ],
      "status": "FORMULA_DOCUMENTED_EDGE_RULE_REQUIRED",
      "gap": "The zero-original-duration result and boundary clamping must be verified against reference scheduler Version 26 behavior before copying as production logic."
    },
    {
      "id": "FRM-PC-002",
      "feature": "Units Percent Complete",
      "algorithm": "Units % Complete = 100 * Actual Labor and Nonlabor Units / (Actual Labor and Nonlabor Units + Remaining Labor and Nonlabor Units), subject to the applicable reference scheduler unit/assignment rules.",
      "inputs": [
        "Actual labor units",
        "Actual nonlabor units",
        "Remaining labor units",
        "Remaining nonlabor units"
      ],
      "options": [
        "Percent Complete Type = Units",
        "Resource/role assignments",
        "Assignment units and conversions"
      ],
      "calendarRules": "Normalize compatible unit-of-measure quantities before summation. Material units cannot be added to hours without an explicit unit conversion.",
      "edgeCases": [
        "Zero total units",
        "Mixed unit types",
        "No resource assignments",
        "Negative/invalid remaining units",
        "Multiple resource rates"
      ],
      "status": "FORMULA_DOCUMENTED_EDGE_RULE_REQUIRED",
      "gap": "Exact handling of zero total units and eligible assignment units must be verified with reference scheduler Version 26 fixtures."
    },
    {
      "id": "FRM-RESOURCE-DUR-001",
      "feature": "Resource Dependent activity duration from driving resources",
      "algorithm": "For each driving assignment, estimate remaining duration from quantity/work remaining divided by the driving assignment's Units/Time on its applicable resource calendar. When multiple driving resources exist, the resource taking the longest to complete governs activity duration; then place nondriving assignments under their own calendar/date rules.",
      "inputs": [
        "Remaining work/units",
        "Assignment Units/Time",
        "Driving flag",
        "Resource calendar/version",
        "Effective rate/period conversion"
      ],
      "options": [
        "Activity Type = Resource Dependent",
        "Drive Activity Dates by Default",
        "Per-assignment driving override",
        "Assignment units/time period"
      ],
      "calendarRules": "Calendar-aware inverse-rate calculation is required; never use resource Max Units/Time as a substitute for assignment Units/Time.",
      "edgeCases": [
        "Missing driving flag",
        "No driving assignments",
        "Multiple driving resources",
        "Different resource calendars",
        "Rate changes/effective dates",
        "Actual/remaining work",
        "Nondriving placement"
      ],
      "status": "KNOWN_GAP",
      "gap": "Current authoritative composer explicitly rejects Resource Dependent assignments with RESOURCE_DEPENDENT_DRIVING_ASSIGNMENT_UNSUPPORTED; this formula must not be treated as implemented."
    },
    {
      "id": "FRM-CAP-001",
      "feature": "Resource capacity normalization from rate and available work hours",
      "algorithm": "For absolute rate basis: Capacity = Max Units/Time * Available Work Hours / Hours per rate period. For percent capacity where supported: Capacity = Percent/100 * Full-Time Units per rate period * Available Work Hours / Hours per rate period.",
      "inputs": [
        "Max Units/Time",
        "Available work hours",
        "Hours per rate period",
        "Capacity basis",
        "Full-time capacity base",
        "Unit of measure"
      ],
      "options": [
        "Resource rate time period",
        "Calendar/global conversion source",
        "Resource calendar",
        "Absolute/percentage capacity basis"
      ],
      "calendarRules": "The conversion period and work-hours factor must be explicitly versioned with the resource/calendar snapshot; no assumed 8-hour day. Output remains in the same unit of measure as capacity input.",
      "edgeCases": [
        "Zero availability",
        "Percent basis without full-time base",
        "Mismatched units",
        "Rate effective-date transition",
        "Shift-specific capacity",
        "Nonworking calendar exceptions"
      ],
      "status": "FORMULA_DOCUMENTED_PARITY_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "FRM-EVM-001",
      "feature": "Earned Value cost and schedule variances / performance indices",
      "algorithm": "CV = EV - AC; SV = EV - PV; CPI = EV / AC; SPI = EV / PV. EV, PV and AC must be drawn from the selected baseline, status date, WBS Earned Value technique and applicable activity/resource values.",
      "inputs": [
        "Earned Value EV",
        "Planned Value PV",
        "Actual Cost AC",
        "Baseline",
        "Data Date",
        "WBS Earned Value technique"
      ],
      "options": [
        "Selected baseline",
        "WBS performance percent-complete technique",
        "Status/Data Date",
        "Currency and reporting period"
      ],
      "calendarRules": "Money values must be converted/compared in a consistent project currency and financial period. SPI is a ratio of value measures; it is not automatically identical to an Earned Schedule time index.",
      "edgeCases": [
        "AC=0",
        "PV=0",
        "No baseline",
        "WBS override",
        "Different currencies",
        "Unclosed financial period"
      ],
      "status": "FORMULA_DOCUMENTED_EDGE_RULE_REQUIRED",
      "gap": "CUBI must explicitly define zero-denominator behavior and prove source values/rollups using Version 26 acceptance fixtures."
    },
    {
      "id": "FRM-EVM-002",
      "feature": "ETC, EAC and VAC under selected WBS technique",
      "algorithm": "VAC = BAC - EAC. If the selected ETC technique is performance-factor based: ETC = PF * (BAC - EV); EAC = AC + ETC. The selected WBS ETC method determines whether PF=1, PF=1/CPI, PF=1/(CPI*SPI) or a user-entered PF is used; a single universal EAC formula is not valid for all reference scheduler settings.",
      "inputs": [
        "BAC",
        "EV",
        "AC",
        "CPI",
        "SPI",
        "Remaining activity cost",
        "PF",
        "WBS EV technique"
      ],
      "options": [
        "ETC = Remaining Activity Cost",
        "PF=1",
        "PF=1/CPI",
        "PF=1/(CPI*SPI)",
        "User-defined PF",
        "WBS-specific override"
      ],
      "calendarRules": "BAC, EV, AC, ETC and EAC must be comparable cost values in the same currency and reporting context.",
      "edgeCases": [
        "CPI=0",
        "SPI=0",
        "Missing BAC/EV/AC",
        "WBS-specific method override",
        "Resource curve/manual future bucket methods"
      ],
      "status": "FORMULA_DOCUMENTED_EDGE_RULE_REQUIRED",
      "gap": "Implement and test each reference scheduler WBS ETC option separately; zero-index and missing-input behavior must be confirmed from Version 26 behavior."
    },
    {
      "id": "FRM-DATA-DATE-001",
      "feature": "Data Date as the start boundary of the next work period",
      "algorithm": "Treat Data Date as the start of the current scheduling workperiod. Reconcile progress through the end of the preceding period, record actual dates/quantities and remaining work, then advance Data Date and reschedule. Work performed on the Data Date itself belongs to the work period beginning at that date and is not counted as pre-Data-Date progress by default.",
      "inputs": [
        "Current Data Date",
        "New Data Date",
        "Actual Start/Finish",
        "Actual quantities/costs",
        "Remaining duration/units",
        "Calculation time zone"
      ],
      "options": [
        "Data Date",
        "Apply selected Data Date to open projects or use each project's own date",
        "Retained Logic / Progress Override / Actual Dates"
      ],
      "calendarRules": "Treat the date as a configured workperiod boundary; do not derive progress from wall-clock elapsed time without project/resource calendar and actual-value evidence.",
      "edgeCases": [
        "Data Date on nonworkday",
        "Update through prior period close",
        "Actual on/after Data Date",
        "Time-aware schedules",
        "Different project Data Dates",
        "Data Date and forecast-start option"
      ],
      "status": "FORMULA_DOCUMENTED_PARITY_NOT_PROVEN",
      "gap": ""
    },
    {
      "id": "FRM-CPM-PASS-001",
      "feature": "CPM early/late date passes",
      "algorithm": "Forward pass: derive each Early Start from the project boundary, applicable start constraints and all predecessor relationship lower bounds; derive Early Finish by advancing the activity's duration on its applicable scheduling calendar. Backward pass: derive each Late Finish from the project finish boundary, applicable finish constraints and successor relationship upper bounds; derive Late Start by subtracting duration on the correct calendar. Then compute selected float from early/late values. A date-only shortcut is not a valid replacement for calendar-aware/time-aware passes.",
      "inputs": [
        "Activity duration/type",
        "Relationships and lag",
        "Activity/resource calendars",
        "Constraints",
        "Data Date/progress policy",
        "Project/opened-project finish boundary"
      ],
      "options": [
        "Schedule mode",
        "Retained Logic / Progress Override / Actual Dates",
        "Total Float method",
        "Critical activity method",
        "Relationship lag calendar",
        "Open-ended activity and expected-finish options"
      ],
      "calendarRules": "All date boundaries and durations must be resolved through shared calendar logic; record both calendar reference/version and date/time precision in the snapshot.",
      "edgeCases": [
        "Multiple predecessors/successors",
        "Negative lag",
        "Mandatory and soft constraints",
        "Different calendars",
        "Open ends",
        "Out-of-sequence progress",
        "Zero-duration milestones",
        "Time-aware schedules"
      ],
      "status": "FORMULA_DOCUMENTED_PARITY_NOT_PROVEN",
      "gap": "Exact reference scheduler reference scenario coverage for every option interaction is still required; this contract is not an assertion that all interactions already pass."
    },
    {
      "id": "FRM-MFP-001",
      "feature": "Multiple critical float paths",
      "algorithm": "When enabled, identify a configured number of paths to the selected endpoint. Record path rank and within-path activity order. Total Float mode uses relationship float-path selection; Free Float mode selects the path by longest-path semantics. The result ranks/analyses paths; it does not replace the General-tab critical-activity method.",
      "inputs": [
        "Calculated early/late dates",
        "Relationship graph",
        "Selected endpoint",
        "Number of paths",
        "Float values"
      ],
      "options": [
        "Calculate multiple float paths",
        "Number of paths",
        "Total Float / Free Float",
        "Endpoint activity"
      ],
      "calendarRules": "Consume the completed calendar-aware schedule and its driving-relationship facts; never compute paths from displayed Gantt coordinates.",
      "edgeCases": [
        "No endpoint selected",
        "Multiple terminal activities",
        "Tied paths",
        "Open ends",
        "Multi-project boundary",
        "Activities critical but outside selected paths"
      ],
      "status": "FORMULA_DOCUMENTED_PARITY_NOT_PROVEN",
      "gap": "Version 26 Total Float versus Free Float selection behavior needs targeted end-to-end documented source fixtures and stable path-order tests."
    },
    {
      "id": "FRM-LEVEL-001",
      "feature": "Resource leveling decision loop",
      "algorithm": "For every resource/time period, compare time-phased demand with effective available capacity. For an overallocated period, rank competing assignments using the selected priority fields/order, then apply delay/placement decisions subject to activity relationships, selected float limits, maximum over-allocation and preserve-Early/Late settings. Recalculate dates and demand after each accepted change; publish a result/log that explains unresolved overallocations.",
      "inputs": [
        "Time-phased resource demand",
        "Effective capacity",
        "Activity network and float",
        "Leveling priorities",
        "Selected resource scope"
      ],
      "options": [
        "Level all/selected resources",
        "Level within activity Total Float",
        "Minimum float to preserve",
        "Max percent to over-allocate",
        "Preserve early/late dates",
        "Priority fields/order",
        "Cross-project priority threshold",
        "Recalculate assignment costs"
      ],
      "calendarRules": "Demand and capacity use the same resource unit/time-period basis and versioned resource calendar/rate inputs. Never level against a guessed capacity or silently collapse shift calendars.",
      "edgeCases": [
        "Unresolvable overload",
        "Priority ties",
        "Cross-project assignments",
        "Resource Dependent activities",
        "WBS Summary assignments",
        "Resource shifts",
        "No float",
        "Max over-allocation threshold reached"
      ],
      "status": "FORMULA_DOCUMENTED_PARITY_NOT_PROVEN",
      "gap": "reference scheduler leveling heuristic/order and output parity must be established with reference fixtures; current presence of a leveling engine is not proof of equivalent results."
    },
    {
      "id": "FRM-ACT-TYPES-001",
      "feature": "Activity type-specific scheduling behavior",
      "algorithm": "Do not run every activity type through the task-duration algorithm: milestones represent zero-duration events; Task Dependent timing follows the activity calendar; Resource Dependent timing follows assigned driving resource calendars; Level of Effort and WBS Summary derive timing from their supported relationship/child-activity semantics. Exact type-specific constraints and invalid operations must be enforced at the domain boundary.",
      "inputs": [
        "Activity Type",
        "Activity/resource calendar",
        "Relationships",
        "Child WBS activities",
        "Driving resource assignments"
      ],
      "options": [
        "Task Dependent",
        "Resource Dependent",
        "Level of Effort",
        "Start Milestone",
        "Finish Milestone",
        "WBS Summary"
      ],
      "calendarRules": "Milestone date conventions, resource calendars and start/finish boundaries must be handled by the shared scheduler; never assign fictitious working duration to a milestone.",
      "edgeCases": [
        "Milestone duration edit",
        "WBS Summary with child activities",
        "Level of Effort start/finish relationships",
        "Resource Dependent with missing driving flag",
        "Mixed calendars"
      ],
      "status": "FORMULA_DOCUMENTED_EDGE_RULE_REQUIRED",
      "gap": "Level of Effort and WBS Summary date-derivation rules still require type-specific Version 26 fixtures; this entry deliberately does not invent a single formula for them."
    },
    {
      "id": "FRM-COST-001",
      "feature": "Resource/role assignment costs with multiple rates",
      "algorithm": "For each cost component and period: calculate cost from the applicable quantity (budgeted/planned, actual, or remaining) × the rate selected by rate type/source and effective date; then aggregate periods/components in the selected currency. Resource/role, labor/nonlabor/material, expense and cost-account values remain distinct until the documented rollup stage.",
      "inputs": [
        "Budgeted/planned units",
        "Actual units",
        "Remaining units",
        "Rate type/source",
        "Price per unit",
        "Effective date",
        "Currency",
        "Cost component"
      ],
      "options": [
        "Rate type",
        "Rate source",
        "Multiple effective-dated rates",
        "Recalculate assignment costs after scheduling/leveling",
        "Currency/precision",
        "Resource curve/future-period buckets"
      ],
      "calendarRules": "The quantity and rate units must be compatible; effective dates and bucket time periods must be honored. Do not apply one current price to all historical/future periods unless selected source semantics require it.",
      "edgeCases": [
        "Rate change in the middle of an assignment",
        "Zero units",
        "Material units",
        "Role/resource substitution",
        "Currency conversion",
        "Expense accrual timing",
        "Future-period manual values"
      ],
      "status": "FORMULA_DOCUMENTED_EDGE_RULE_REQUIRED",
      "gap": "Rate-source precedence, component rollups, currency precision and multi-rate acceptance vectors still require full Version 26 field/formula mapping."
    },
    {
      "id": "FRM-EVM-003",
      "feature": "Earned Value when resource curves or future-period buckets are selected",
      "algorithm": "For eligible activities assigned a resource curve, the Version 26 WBS Earned Value option specifies EV = Units Percent Complete × Budget at Completion (BAC), overriding the ordinary Activity Percent Complete technique. The WBS option also covers manually entered future-period bucket values; curve-assigned activity behavior and manually entered bucket behavior must be verified separately rather than assumed identical.",
      "inputs": [
        "WBS Earned Value technique",
        "BAC",
        "Units Percent Complete",
        "Assigned resource curve",
        "Manual future-period bucket values"
      ],
      "options": [
        "Use resource curves/future-period buckets",
        "Activity Percent Complete",
        "WBS milestone percent complete",
        "0/100",
        "50/50",
        "Custom percent complete"
      ],
      "calendarRules": "Units Percent Complete uses eligible assignment quantities and the time-phased bucket/calendar basis. BAC and EV must refer to the selected baseline and cost structure.",
      "edgeCases": [
        "Curve assigned to one of multiple resource assignments",
        "Manual future-period values",
        "No curve/bucket data",
        "WBS milestone technique",
        "Zero BAC",
        "Missing baseline"
      ],
      "status": "FORMULA_DOCUMENTED_EDGE_RULE_REQUIRED",
      "gap": "Curve-only and manually-entered-bucket scenarios must be tested separately against Version 26; this formula is documented, not claimed implemented."
    }
  ],
  "documentation": [
    {
      "id": "DOC-PRO-TOC-V26",
      "title": "reference scheduler Professional Help Version 26 — full topic tree",
      "scope": "reference scheduler Professional desktop Help",
      "status": "DOC_TOPIC_MAP_PARTIAL",
      "reviewed": "Topic tree scanned to establish feature families; leaf pages are not all reviewed line by line yet.",
      "remaining": "Enumerate every menu, submenu, dialog, tab, option, field and linked help topic from the entire TOC; assign a stable requirement ID and exact page URL to each.",
      "requirements": [
        "SCH-001",
        "SCH-008",
        "ACT-001",
        "CAL-001",
        "RES-001",
        "DATA-002"
      ]
    },
    {
      "id": "DOC-PRO-USER-GUIDE-V26",
      "title": "reference scheduler Professional User Guide Version 26",
      "scope": "reference scheduler Professional desktop workflows and UI behavior",
      "status": "DOC_INDEXED_NOT_LINE_REVIEWED",
      "reviewed": "Official current guide entry point identified; chapter-by-chapter and figure/table-level behavior review remains open.",
      "remaining": "Review every chapter and each linked detailed topic, including project/WBS setup, activities, layouts, tracking, import/export and multi-project workflows.",
      "requirements": []
    },
    {
      "id": "DOC-PRO-SCHEDULING-V26",
      "title": "Scheduling Projects and Schedule Options",
      "scope": "reference scheduler Professional scheduling calculation and settings",
      "status": "DOC_CORE_RULES_EXTRACTED",
      "reviewed": "Core CPM flow, Data Date, criticality modes, multiple float paths, constraints, progressed activities and scheduling entry points summarized into the register.",
      "remaining": "Extract every General and Advanced tab option including enabled/disabled conditions, default values, interactions, precision/calendar rules and test vectors; prove behavior against reference scheduler reference fixtures.",
      "requirements": [
        "SCH-001",
        "SCH-002",
        "SCH-003",
        "SCH-004",
        "SCH-005",
        "SCH-006",
        "SCH-007",
        "SCH-008",
        "SCH-009",
        "SCH-010",
        "SCH-011",
        "SCH-012",
        "SCH-013",
        "SCH-014"
      ]
    },
    {
      "id": "DOC-PRO-ACTIVITY-V26",
      "title": "Activity Details, Activity Types, Duration Types and Status",
      "scope": "reference scheduler Professional activity editor and activity scheduling semantics",
      "status": "DOC_CORE_RULES_EXTRACTED",
      "reviewed": "Activity type/calendar differences and core duration/percent-complete concepts entered in the code reference.",
      "remaining": "Enumerate every activity field across every tab, status-specific editability, duration type recomputation triggers, remaining units/duration and zero-denominator rules.",
      "requirements": [
        "ACT-001",
        "ACT-002",
        "ACT-003",
        "ACT-004",
        "ACT-005"
      ]
    },
    {
      "id": "DOC-PRO-RELATIONSHIPS-V26",
      "title": "Relationships, Lag and Relationship Lag Calendar",
      "scope": "reference scheduler Professional activity dependencies and scheduling",
      "status": "DOC_CORE_RULES_EXTRACTED",
      "reviewed": "FS/SS/FF/SF, signed lag and calendar choice are in the rule register.",
      "remaining": "Audit each relationship field, predecessor/successor UI operation, external relationship behavior, circular logic rejection and all calendar/actual-progress edge cases.",
      "requirements": [
        "SCH-008",
        "SCH-012"
      ]
    },
    {
      "id": "DOC-PRO-CALENDAR-V26",
      "title": "Calendars, Work Time, Exceptions and Conversion Factors",
      "scope": "reference scheduler Professional global/project/resource calendar pools",
      "status": "DOC_CORE_RULES_EXTRACTED",
      "reviewed": "Calendar pools, assignment differences, exceptions and default work-time conversion recorded at a high level.",
      "remaining": "Line-review calendar editing dialogs, inheritance/linked calendars, holidays, work intervals, default hours per period, DST/time-zone assumptions and date round-trips.",
      "requirements": [
        "CAL-001",
        "CAL-002",
        "CAL-003"
      ]
    },
    {
      "id": "DOC-PRO-CONSTRAINTS-V26",
      "title": "Activity Constraints",
      "scope": "reference scheduler Professional forward/backward calculation rules",
      "status": "DOC_CORE_RULES_EXTRACTED",
      "reviewed": "Hard versus soft constraints and the named constraint families are inventoried.",
      "remaining": "Verify exact boundary handling, secondary constraints, ALAP context, conflicting constraints, negative float and each constraint/calendar combination.",
      "requirements": [
        "SCH-009"
      ]
    },
    {
      "id": "DOC-PRO-RESOURCE-DRIVING-V26",
      "title": "Driving and Nondriving Resource Assignments",
      "scope": "reference scheduler Professional Resource Dependent activities and assignment placement",
      "status": "DOC_CORE_RULES_EXTRACTED",
      "reviewed": "Driving resources determine duration from quantity/rate; multiple drivers and nondriving assignments are identified as separate algorithms.",
      "remaining": "Build and pass multiple-driving-resource, calendar-specific duration, unit/time conversion, nondriving placement, out-of-sequence and backward-pass fixtures. The existing Draft PR blocker remains open.",
      "requirements": [
        "RES-001",
        "RES-002",
        "RES-003",
        "RES-004",
        "RES-005",
        "RES-006"
      ]
    },
    {
      "id": "DOC-PRO-PROGRESS-EVM-V26",
      "title": "Update Progress, Earned Value, Resource Curves and Future Period Buckets",
      "scope": "reference scheduler Professional progress update and native earned-value options",
      "status": "DOC_TOPIC_MAP_PARTIAL",
      "reviewed": "Core Data Date/progress and selected WBS Earned Value options are summarized; this is not yet a line-by-line formula catalog.",
      "remaining": "For every EV method and ETC/performance-factor selector, record baseline basis, numerator/denominator, period, currency/unit, defaults, overrides, null/zero handling and a numeric reference fixture.",
      "requirements": [
        "PROG-001",
        "EVM-001",
        "EVM-002",
        "RES-006"
      ]
    },
    {
      "id": "DOC-PRO-BASELINE-V26",
      "title": "Maintain, Assign, Update and Compare Baselines",
      "scope": "reference scheduler Professional baseline and variance workflows",
      "status": "DOC_TOPIC_MAP_PARTIAL",
      "reviewed": "Baseline creation/assignment/update scope has requirement entries; every field and calculation has not been enumerated.",
      "remaining": "Trace primary/secondary/tertiary baseline roles, assignment scope, selective update, variance formulas and baseline selection per project/user.",
      "requirements": [
        "BAS-001",
        "BAS-002"
      ]
    },
    {
      "id": "DOC-PRO-RESOURCE-CALCULATIONS-V26",
      "title": "Resource/Roles Units, Rates and Cost Calculations",
      "scope": "reference scheduler Professional resource assignment and cost calculation",
      "status": "DOC_TOPIC_MAP_PARTIAL",
      "reviewed": "Assignment Units/Time is explicitly distinguished from resource Max Units/Time; multi-rate cost and resource curves remain incomplete.",
      "remaining": "Audit all resource/role fields, price/unit type precedence, effective dates, assignment calculation preferences, resource curve shapes and cost roll-up precision.",
      "requirements": [
        "RES-003",
        "RES-004",
        "CST-001",
        "CST-002",
        "ROLE-001"
      ]
    },
    {
      "id": "DOC-PRO-REPORTING-ADMIN-V26",
      "title": "Reporting Guide, Administration Guide and Admin Categories",
      "scope": "reference scheduler Professional reports and configuration dictionaries",
      "status": "DOC_INDEXED_NOT_LINE_REVIEWED",
      "reviewed": "Official all-guides landing page identified; individual guides and details have not all been read line by line.",
      "remaining": "Open each applicable guide and all its chapters; enumerate Reports, Admin Preferences, calendars/time periods, currencies, categories, UDFs, security, project publishing and summary services.",
      "requirements": []
    },
    {
      "id": "DOC-PRO-VISUALIZER-V26",
      "title": "reference scheduler Visualizer Help",
      "scope": "Standalone charts, Gantt and Timescaled Logic Diagrams",
      "status": "DOC_INDEXED_NOT_LINE_REVIEWED",
      "reviewed": "Visualizer identified as a separate guide family; its own chart/report options have not been exhaustively inventoried.",
      "remaining": "Trace visualizer data sources, time scales, chart series, logic diagrams, export/print options and which configuration is distinct from the reference scheduler Activities Gantt.",
      "requirements": []
    },
    {
      "id": "DOC-EPPM-API-V26",
      "title": "reference scheduler EPPM REST API and Integration Guides",
      "scope": "reference scheduler EPPM APIs/integration; not automatically equivalent to reference scheduler Professional UI",
      "status": "DOC_PRODUCT_SCOPE_PENDING",
      "reviewed": "Version-26 API entry point found and kept separate from the desktop UI specification.",
      "remaining": "Map each API resource/property/enum/version and import/export contract only where CUBI needs interoperability; do not infer an undocumented desktop calculation rule from an API schema.",
      "requirements": []
    },
    {
      "id": "DOC-EPPM-IMPORT-EXPORT-V26",
      "title": "reference scheduler EPPM Import/Export and Data Maps",
      "scope": "Import/export interoperability, product/version specific",
      "status": "DOC_PRODUCT_SCOPE_PENDING",
      "reviewed": "Official import/export entry point identified; per-format and per-field round-trip mappings are not complete.",
      "remaining": "Catalog XER, resource-only XER, XLSX, XML/MPX and other documented formats separately; map field, nullable/default semantics, read/write support, version, precision and loss reporting.",
      "requirements": [
        "DATA-001",
        "DATA-002"
      ]
    },
    {
      "id": "DOC-P6-ALL-GUIDES-V26",
      "title": "documented source reference scheduler Professional Version 26 — All Guides Index",
      "scope": "Official version-26 documentation-set inventory",
      "status": "DOC_TOPIC_MAP_PARTIAL",
      "reviewed": "The guide-family listing has been checked to establish source inventory; each guide's contents remain tracked separately above.",
      "remaining": "Mark every guide as intentionally applicable/not applicable and keep product version/context on every requirement.",
      "requirements": []
    }
  ]
} as const;

export type SchedulingReferenceCatalog = typeof SCHEDULING_REFERENCE_CATALOG;
