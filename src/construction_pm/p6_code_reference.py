"""CUBI P6 Code Reference — versioned requirement-to-code registry.

Machine-readable compatibility register, not a second scheduling engine. Calculation
formulas belong in the Shared Scheduling/Calculation Core. This module records the
required semantics, P6 UI options, official sources, CUBI code/test locations and
evidence status. Descriptions are original summaries; Oracle documentation is linked,
not reproduced verbatim.

Authority set: Oracle Primavera P6 Professional Help/User Guide, Version 26, plus
related version-26 API and data-map guides as applicable.

Status definitions:
* MAPPED_NOT_PROVEN: likely code path located; parity has NOT been proven by exhaustive
  review and passing tests.
* KNOWN_GAP: concrete unsupported behavior observed.
* INVENTORY_REQUIRED: exhaustive options/fields and exact test mapping remain open.
A class, API field, UI control, or isolated test does not alone prove parity.
Every change affecting a requirement must update this register and regression evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Iterable

REFERENCE_ID: Final[str] = "CUBI-P6-CODE-REFERENCE"
REFERENCE_VERSION: Final[str] = "0.3.0"
REFERENCE_AS_OF: Final[str] = "2026-10-23"
TARGET_P6_VERSION: Final[str] = "Oracle Primavera P6 Professional Help / User Guide Version 26"
REPOSITORY: Final[str] = "consttruction-pm/consttruction-pm-platform"

MAPPED_NOT_PROVEN: Final[str] = "MAPPED_NOT_PROVEN"
KNOWN_GAP: Final[str] = "KNOWN_GAP"
INVENTORY_REQUIRED: Final[str] = "INVENTORY_REQUIRED"


@dataclass(frozen=True, slots=True)
class P6CodeReference:
    """One traceable requirement in the P6-to-CUBI compatibility register."""

    id: str
    area: str
    feature: str
    p6_ui_entry: str
    required_semantics: str
    user_options: tuple[str, ...]
    official_sources: tuple[str, ...]
    cubi_code_paths: tuple[str, ...]
    regression_tests: tuple[str, ...]
    coverage: str = INVENTORY_REQUIRED
    known_gap: str = ""
    acceptance_evidence: tuple[str, ...] = ()


ORACLE_ROOT: Final[str] = "https://docs.oracle.com/cd/G48902_01/client_help/en_US/"
ORACLE_USER_GUIDE: Final[str] = "https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/"
ORACLE_SOURCES: Final[dict[str, str]] = {
    "schedule": ORACLE_ROOT + "scheduling_projects.htm",
    "schedule_dialog": ORACLE_ROOT + "schedule_dialog_box.htm",
    "schedule_options_advanced": ORACLE_ROOT + "advanced_tab_-_schedule_options_dialog_box.htm",
    "leveling_dialog": ORACLE_ROOT + "level_resources_dialog_box.htm",
    "multiple_float_paths": ORACLE_ROOT + "analyzing_the_schedule_using_multiple_critical_float_paths.htm",
    "relationship_lag": ORACLE_ROOT + "choose_a_calendar_for_relationship_lag.htm",
    "schedule_options": ORACLE_ROOT + "general_tab_-_schedule_options_dialog_box.htm",
    "constraints": ORACLE_ROOT + "types_of_constraints.htm",
    "critical": ORACLE_ROOT + "define_critical_activities.htm",
    "data_date": "https://docs.oracle.com/cd/F74771_01/client_help/en_US/using_the_data_date.htm",
    "relationships": ORACLE_ROOT + "relationships.htm",
    "relationship_details": ORACLE_ROOT + "relationships_tab_-_activity_details.htm",
    "activity_general": ORACLE_ROOT + "general_tab_-_activity_details.htm",
    "duration_types": ORACLE_ROOT + "define_activity_duration_types.htm",
    "activity_status": ORACLE_ROOT + "status_tab_-_activity_details.htm",
    "resources": ORACLE_ROOT + "resources_tab_-_activity_details.htm",
    "driving": ORACLE_ROOT + "driving_resource.htm",
    "nondriving": ORACLE_ROOT + "scheduling__nondriving__resource_assignments.htm",
    "calendars": ORACLE_ROOT + "calendar_dialog_box.htm",
    "edit_calendar": ORACLE_ROOT + "edit_a_global_calendar.htm",
    "assignment_calculations": "https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/select_calculation_options_for_resource_and_role_assignments.htm",
    "unit_entry": "https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/enter_unit_information_for_resource_assignments.htm",
    "progress": ORACLE_ROOT + "update_progress_dialog_box.htm",
    "physical_percent": "https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/enter_a_physical_percent_complete_for_activities.htm",
    "wbs_earned_value": ORACLE_ROOT + "earned_value_tab_-_wbs_details.htm",
    "create_baseline": ORACLE_ROOT + "create_a_baseline.htm",
    "assign_baseline": ORACLE_ROOT + "assign_baselines_to_projects.htm",
    "update_baseline": ORACLE_ROOT + "update_baseline_dialog_box.htm",
    "resource_planning": ORACLE_ROOT + "planning_tab_-_resource_assignments_details.htm",
    "parity_baseline": "https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/p6_pro_user.pdf",
}


P6_CODE_REFERENCE: Final[tuple[P6CodeReference, ...]] = (
    P6CodeReference(
        id="SCH-001", area="Scheduling / CPM", feature="Forward pass and early dates",
        p6_ui_entry="Tools > Schedule; Activities / Gantt early dates",
        required_semantics="Evaluate network activities using duration, relationship type, signed lag, applicable working calendars, constraints, actual/progress state and Data Date to derive Early Start/Early Finish. Never calculate dates in a UI client.",
        user_options=("Schedule mode", "Data Date", "Activity calendar", "Relationship-lag calendar"),
        official_sources=(ORACLE_SOURCES["schedule"], ORACLE_SOURCES["schedule_options"]),
        cubi_code_paths=("src/construction_pm/scheduling/forward_pass.py", "src/construction_pm/scheduling/time_forward_pass.py", "src/construction_pm/scheduling/schedule.py", "src/construction_pm/schedule_evaluator.py", "src/construction_pm/authoritative_schedule_input_composer.py"),
        regression_tests=("tests/scheduling/test_schedule.py", "tests/scheduling/test_time_schedule.py"),
        coverage=MAPPED_NOT_PROVEN,
        acceptance_evidence=("Date-based and time-aware modes checked separately", "Calendar/constraint interaction tests pass"),
    ),
    P6CodeReference(
        id="SCH-002", area="Scheduling / CPM", feature="Backward pass and late dates",
        p6_ui_entry="Tools > Schedule; Activities / Gantt late dates",
        required_semantics="Run a genuine backward pass from the applicable project finish boundary. Preserve relationship feasibility, calendars, constraints and selected float interpretation; never substitute early dates for late dates.",
        user_options=("Schedule mode", "Project/opened-project finish boundary", "Constraint set"),
        official_sources=(ORACLE_SOURCES["schedule"], ORACLE_SOURCES["constraints"]),
        cubi_code_paths=("src/construction_pm/scheduling/schedule.py", "src/construction_pm/scheduling/time_schedule.py", "src/construction_pm/scheduling/constraints.py", "src/construction_pm/scheduling/multi_project_float.py"),
        regression_tests=("tests/scheduling/test_schedule.py", "tests/scheduling/test_time_schedule.py"),
        coverage=MAPPED_NOT_PROVEN,
    ),
    P6CodeReference(
        id="SCH-003", area="Scheduling / Float", feature="Total Float calculation selection",
        p6_ui_entry="Tools > Schedule > Options > General > Compute Total Float as",
        required_semantics="Start Float = Late Start - Early Start. Finish Float = Late Finish - Early Finish. Smallest Float = min(Start Float, Finish Float). Use the selected option consistently for published float and dependent criticality.",
        user_options=("Start Float", "Finish Float", "Smallest of Start Float and Finish Float"),
        official_sources=(ORACLE_SOURCES["schedule_options"], ORACLE_SOURCES["critical"]),
        cubi_code_paths=("src/construction_pm/scheduling/schedule_options.py", "src/construction_pm/scheduling/schedule.py", "src/construction_pm/scheduling/time_schedule.py"),
        regression_tests=("tests/scheduling/test_schedule.py", "tests/scheduling/test_time_schedule.py"),
        coverage=MAPPED_NOT_PROVEN,
    ),
    P6CodeReference(
        id="SCH-004", area="Scheduling / Critical path", feature="Critical activity definition",
        p6_ui_entry="Tools > Schedule > Options > General",
        required_semantics="Critical classification must use the selected method, not a hidden fixed rule. Float-threshold mode applies the configured threshold. Longest Path traces driving relationships from the terminal activity/finish boundary; critical and longest-path membership are not interchangeable.",
        user_options=("Total Float less than or equal to threshold", "Longest Path"),
        official_sources=(ORACLE_SOURCES["critical"], ORACLE_SOURCES["schedule_options"]),
        cubi_code_paths=("src/construction_pm/scheduling/schedule_options.py", "src/construction_pm/scheduling/p6_activity_scheduler_outputs.py", "src/construction_pm/scheduling/schedule.py"),
        regression_tests=("tests/scheduling/test_schedule.py",),
        coverage=MAPPED_NOT_PROVEN,
    ),
    P6CodeReference(
        id="SCH-005", area="Scheduling / Multiple float paths", feature="Multiple critical float paths and path ordering",
        p6_ui_entry="Tools > Schedule > Options > Advanced; Activity fields FloatPath / FloatPathOrder",
        required_semantics="When enabled, calculate the configured number of paths using the selected endpoint and path method; persist stable path rank/order. These outputs are calculated fields, not manually edited values.",
        user_options=("Enable/disable", "Maximum path count", "Ending activity", "Total Float or Free Float method"),
        official_sources=(ORACLE_SOURCES["critical"], ORACLE_SOURCES["schedule"]),
        cubi_code_paths=("src/construction_pm/scheduling/schedule_options.py", "src/construction_pm/scheduling/p6_activity_scheduler_outputs.py"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="Exact Version 26 advanced-option mapping and end-to-end path regression evidence remain to be completed.",
    ),
    P6CodeReference(
        id="SCH-006", area="Scheduling / Progress boundary", feature="Data Date and scheduling boundary",
        p6_ui_entry="Project > Activities / Schedule dialog / Update Progress",
        required_semantics="Treat Data Date as the boundary from which remaining work is scheduled. Progress through the prior work period must be reconciled before advancing it. Data Date, time zone, actuals and remaining work must be explicit in immutable calculation input.",
        user_options=("Current Data Date", "New Data Date", "Manual or automatic scheduling"),
        official_sources=(ORACLE_SOURCES["data_date"], ORACLE_SOURCES["progress"]),
        cubi_code_paths=("src/construction_pm/scheduling/schedule_options.py", "src/construction_pm/scheduling/remaining_work.py", "src/construction_pm/scheduling/progress_state.py", "src/construction_pm/scheduling/authoritative_schedule.py", "src/construction_pm/authoritative_schedule_input_composer.py"),
        regression_tests=("tests/scheduling/test_schedule.py",), coverage=MAPPED_NOT_PROVEN,
    ),
    P6CodeReference(
        id="SCH-007", area="Scheduling / Out-of-sequence", feature="Progressed-activity relationship logic",
        p6_ui_entry="Tools > Schedule > Options > General > When scheduling progressed activities use",
        required_semantics="Retained Logic keeps remaining work subject to unfinished predecessor logic. Progress Override allows progressed work to advance without that remaining logic. Actual Dates bases passes on recorded actual dates. The selected policy must never silently fall back.",
        user_options=("Retained Logic", "Progress Override", "Actual Dates"),
        official_sources=(ORACLE_SOURCES["schedule_options"], ORACLE_SOURCES["schedule"]),
        cubi_code_paths=("src/construction_pm/scheduling/schedule_options.py", "src/construction_pm/scheduling/out_of_sequence.py", "src/construction_pm/scheduling/oos_policy.py", "src/construction_pm/scheduling/remaining_work.py"),
        regression_tests=("tests/scheduling/test_schedule.py",), coverage=MAPPED_NOT_PROVEN,
    ),
    P6CodeReference(
        id="SCH-008", area="Scheduling / Relationships", feature="Relationship types, lead/lag and selected lag calendar",
        p6_ui_entry="Project > Activities > Activity Details > Relationships / Tools > Schedule > Options",
        required_semantics="Support FS, SS, FF, SF and signed lag/lead. Lag duration must be converted with the selected P6-compatible lag calendar; do not use a single global weekday rule or discard negative lag.",
        user_options=("FS", "SS", "FF", "SF", "Positive lag", "Negative lag/lead", "Successor calendar", "Predecessor calendar", "24-hour calendar", "Project default calendar"),
        official_sources=(ORACLE_SOURCES["relationships"], ORACLE_SOURCES["relationship_details"], ORACLE_SOURCES["schedule_options"], ORACLE_SOURCES["relationship_lag"]),
        cubi_code_paths=("src/construction_pm/scheduling/relationships.py", "src/construction_pm/scheduling/forward_pass.py", "src/construction_pm/scheduling/time_forward_pass.py", "src/construction_pm/scheduling/calendar_context.py", "src/construction_pm/scheduling/calendar_resolution.py", "src/construction_pm/scheduling/schedule_options.py"),
        regression_tests=("tests/scheduling/test_schedule.py", "tests/scheduling/test_time_schedule.py"),
        coverage=MAPPED_NOT_PROVEN,
    ),
    P6CodeReference(
        id="SCH-009", area="Scheduling / Constraints", feature="Primary, secondary and mandatory constraints",
        p6_ui_entry="Project > Activities > Activity Details > Status / Constraints",
        required_semantics="Model each supported constraint by its exact early/late-pass semantics. Mandatory Start/Finish are hard constraints; date-window constraints are soft and can distort float. Never clamp negative float to zero or propagate a constraint contrary to P6 semantics.",
        user_options=("Start On", "Start On or Before", "Start On or After", "Finish On", "Finish On or Before", "Finish On or After", "Mandatory Start", "Mandatory Finish", "As Late As Possible where applicable"),
        official_sources=(ORACLE_SOURCES["constraints"],),
        cubi_code_paths=("src/construction_pm/scheduling/constraints.py", "src/construction_pm/scheduling/time_constraints.py", "src/construction_pm/scheduling/schedule.py", "src/construction_pm/constraint_master_repository.py"),
        regression_tests=("tests/test_authoritative_schedule_snapshot_composer.py", "tests/scheduling/test_schedule.py"),
        coverage=MAPPED_NOT_PROVEN,
    ),
    P6CodeReference(
        id="SCH-010", area="Scheduling / Advanced options", feature="Expected Finish, open ends, opened projects and external relationships",
        p6_ui_entry="Tools > Schedule > Options > General / Advanced",
        required_semantics="Keep each option explicit in settings and immutable input. Expected Finish, open-ended activity criticality, open-project finish boundary, external relationships and external resource assignments must not be silently ignored.",
        user_options=("Use Expected Finish Dates", "Make open-ended activities critical", "Each Project vs Opened Projects", "Ignore other-project relationships", "Include external resource assignments"),
        official_sources=(ORACLE_SOURCES["schedule_options"], ORACLE_SOURCES["schedule"]),
        cubi_code_paths=("src/construction_pm/scheduling/schedule_options.py", "src/construction_pm/scheduling/multi_project_float.py", "src/construction_pm/scheduling/authoritative_schedule.py"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="Each advanced setting needs source-to-contract-to-engine-to-test trace, including external-project scenarios.",
    ),
    P6CodeReference(
        id="CAL-001", area="Calendars", feature="Global, project and resource calendars",
        p6_ui_entry="Enterprise > Calendars; Project Details; Activity Details; Resource Details",
        required_semantics="Represent calendar kind, identity, version, base/inherited calendar, assignment scope, workweek, date exceptions and effective references. Task Dependent uses activity calendar; Resource Dependent uses assigned resource calendars. Never guess a default for an unresolved calendar.",
        user_options=("Global calendar", "Project calendar", "Resource calendar", "Calendar assignment", "Base/inherited calendar"),
        official_sources=(ORACLE_SOURCES["calendars"], ORACLE_SOURCES["activity_general"], ORACLE_SOURCES["driving"]),
        cubi_code_paths=("src/construction_pm/scheduling/calendar.py", "src/construction_pm/scheduling/time_calendar.py", "src/construction_pm/scheduling/calendar_context.py", "src/construction_pm/scheduling/calendar_resolution.py", "src/construction_pm/calendar_master_repository.py", "src/construction_pm/p6_calendar_api.py", "src/construction_pm/p6_versioned_resource_calendar_resolver.py"),
        regression_tests=("tests/test_calendar_exception_repository.py", "tests/test_authoritative_schedule_snapshot_composer.py"),
        coverage=MAPPED_NOT_PROVEN,
    ),
    P6CodeReference(
        id="CAL-002", area="Calendars", feature="Work intervals, exceptions and hours-per-time-period conversions",
        p6_ui_entry="Enterprise > Calendars > Modify / Calendar dialog > Workweek / Time Periods",
        required_semantics="Preserve normal workdays, nonwork exceptions, forced workdays, intraday work/nonwork intervals, work hours per day and calendar-specific conversion factors. Use version-bound snapshots for deterministic replay.",
        user_options=("Workday", "Nonworkday", "Standard day", "Total work hours/day", "Detailed work hours/day", "Workweek", "Time Periods", "Inherit holidays/exceptions"),
        official_sources=(ORACLE_SOURCES["calendars"], ORACLE_SOURCES["edit_calendar"]),
        cubi_code_paths=("src/construction_pm/scheduling/calendar.py", "src/construction_pm/scheduling/time_calendar.py", "src/construction_pm/scheduling/calendar_periods.py", "src/construction_pm/calendar_exception_repository.py", "src/construction_pm/calendar_work_hours_repository.py", "src/construction_pm/calendar_snapshot_repository.py"),
        regression_tests=("tests/test_calendar_exception_repository.py",), coverage=MAPPED_NOT_PROVEN,
    ),
    P6CodeReference(
        id="CAL-003", area="Calendars / Localization", feature="Jalali display calendar versus calculation calendar",
        p6_ui_entry="Project calendar settings / localized date fields / timeline",
        required_semantics="Keep stable canonical storage/calculation dates separate from Jalali/Gregorian display. Changing locale must not shift a stored instant or schedule date.",
        user_options=("Gregorian display", "Jalali display", "Project calculation time zone"),
        official_sources=(ORACLE_SOURCES["parity_baseline"],),
        cubi_code_paths=("src/construction_pm/scheduling/calendar_system.py", "src/construction_pm/scheduling/time_calendar.py"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="Localization date-boundary and round-trip tests are required; this is a CUBI extension, not a native P6 feature claim.",
    ),
    P6CodeReference(
        id="ACT-001", area="Activities", feature="Activity types and calendar driving rules",
        p6_ui_entry="Project > Activities > Activity Details > General",
        required_semantics="Support Task Dependent, Resource Dependent, Level of Effort, Start Milestone, Finish Milestone and WBS Summary with distinct scheduling behavior. They must not share one generic duration algorithm.",
        user_options=("Task Dependent", "Resource Dependent", "Level of Effort", "Start Milestone", "Finish Milestone", "WBS Summary"),
        official_sources=(ORACLE_SOURCES["activity_general"],),
        cubi_code_paths=("src/construction_pm/scheduling/activity.py", "src/construction_pm/authoritative_schedule_input_composer.py"),
        regression_tests=("tests/scheduling/test_schedule.py",), coverage=MAPPED_NOT_PROVEN,
    ),
    P6CodeReference(
        id="ACT-002", area="Activities", feature="Activity duration type and recalculation relationships",
        p6_ui_entry="Project > Activities > Activity Details > General > Duration Type",
        required_semantics="Implement each duration-type invariant across duration, total units and Units/Time. Updating a variable must recalculate other values according to the selected duration type and assignment preference.",
        user_options=("Fixed Units/Time", "Fixed Duration & Units/Time", "Fixed Units", "Fixed Duration & Units"),
        official_sources=(ORACLE_SOURCES["duration_types"], ORACLE_SOURCES["assignment_calculations"]),
        cubi_code_paths=("src/construction_pm/scheduling/activity.py", "src/construction_pm/p6_resource_assignment_repository.py", "src/construction_pm/p6_resource_write_api.py"),
        regression_tests=("tests/test_p6_resource_assignment_repository.py",), coverage=MAPPED_NOT_PROVEN,
    ),
    P6CodeReference(
        id="ACT-003", area="Activities / Status", feature="Original, actual, remaining and at-completion values",
        p6_ui_entry="Project > Activities > Activity Details > Status",
        required_semantics="Keep Original/Planned, Actual, Remaining and At Complete duration distinct. P6 defines At Complete Duration as Actual Duration + Remaining Duration. Validate legal edits by activity state and preserve coherent actual-date/remaining-work invariants.",
        user_options=("Original/Planned Duration", "Actual Duration", "Remaining Duration", "At Complete Duration", "Actual Start", "Actual Finish"),
        official_sources=(ORACLE_SOURCES["activity_status"], ORACLE_SOURCES["progress"]),
        cubi_code_paths=("src/construction_pm/scheduling/activity.py", "src/construction_pm/scheduling/progress_state.py", "src/construction_pm/scheduling/remaining_work.py"),
        regression_tests=("tests/scheduling/test_schedule.py",), coverage=MAPPED_NOT_PROVEN,
    ),
    P6CodeReference(
        id="ACT-004", area="Activities / Percent complete", feature="Duration, Units, Physical and scope percent complete",
        p6_ui_entry="Project > Activities > Activity Details > General / Status",
        required_semantics="Duration % = (Original/Planned Duration - Remaining Duration) / Original/Planned Duration with explicit zero-duration handling. Units % is actual labor plus nonlabor units divided by total actual plus remaining labor/nonlabor units. Physical is user-entered. Scope is product/context-specific and must not be equated to Physical.",
        user_options=("Duration", "Units", "Physical", "Scope only where supported by selected P6 product/context"),
        official_sources=(ORACLE_SOURCES["activity_general"], ORACLE_SOURCES["activity_status"], ORACLE_SOURCES["physical_percent"]),
        cubi_code_paths=("src/construction_pm/scheduling/activity.py", "src/construction_pm/scheduling/progress_state.py", "src/construction_pm/scheduling/remaining_work.py"),
        regression_tests=("tests/scheduling/test_schedule.py",), coverage=MAPPED_NOT_PROVEN,
    ),
    P6CodeReference(
        id="ACT-005", area="Activities / Structure", feature="WBS, activity identifiers, codes, UDFs, status and hierarchy",
        p6_ui_entry="Project > WBS; Project > Activities; activity columns and codes",
        required_semantics="Keep hierarchy identity separate from display order, preserve stable field/code IDs, validate activity-to-WBS membership and expose editable fields through typed permission-checked contracts. WBS Summary behavior remains distinct from ordinary tasks.",
        user_options=("WBS hierarchy", "Activity ID/name", "Activity codes", "UDF/custom fields", "Status/status code"),
        official_sources=(ORACLE_SOURCES["activity_general"], ORACLE_SOURCES["parity_baseline"]),
        cubi_code_paths=("src/construction_pm/activity_master_repository.py", "src/construction_pm/p6_code_repository.py", "src/construction_pm/http/project_lifecycle_routes.py", "apps/web/src/p6-activity-wbs-grid.ts"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="Full field registry, hierarchy contract, UI column inventory and import/export mapping remain to be reconciled.",
    ),
    P6CodeReference(
        id="RES-001", area="Resources / Resource dependent scheduling", feature="Driving and nondriving resource assignments",
        p6_ui_entry="Project Details > Resources > Drive Activity Dates by Default; Activity Details > Resources",
        required_semantics="A driving resource can determine Resource Dependent activity duration from remaining work and assignment Units/Time. With multiple driving assignments, the limiting/longest completion time determines activity duration. Nondriving assignments are placed using their own schedule rules after activity dates are determined; persisting the flag alone is insufficient.",
        user_options=("Default driving flag", "Per-assignment driving override", "Assignment Units/Time and conversion period"),
        official_sources=(ORACLE_SOURCES["driving"], ORACLE_SOURCES["nondriving"], ORACLE_SOURCES["resource_planning"]),
        cubi_code_paths=("src/construction_pm/p6_resource_assignment_repository.py", "src/construction_pm/p6_resource_write_api.py", "src/construction_pm/p6_resource_read_api.py", "src/construction_pm/authoritative_schedule_input_composer.py", "src/construction_pm/scheduling/resource_leveling_input.py", "src/construction_pm/scheduling/authoritative_schedule.py"),
        regression_tests=("tests/test_p6_resource_assignment_repository.py", "tests/test_p6_postgres_resource_assignment.py", "tests/scheduling/test_resource_leveling_input.py", "tests/test_authoritative_schedule_snapshot_composer.py"),
        coverage=KNOWN_GAP,
        known_gap="Observed on fix/p6-resource-assignment-driving-flag: the authoritative composer still rejects Resource Dependent activities with RESOURCE_DEPENDENT_DRIVING_ASSIGNMENT_UNSUPPORTED. Forward/backward date derivation and nondriving placement are not complete.",
        acceptance_evidence=("Driving flag traverses persistence/read/write/snapshot/hash", "Multiple-driver limiting-duration tests pass", "Nondriving placement is calendar-aware", "SQLite/PostgreSQL parity passes"),
    ),
    P6CodeReference(
        id="RES-002", area="Resources / Leveling", feature="Resource leveling controls and priority order",
        p6_ui_entry="Tools > Level Resources / Tools > Schedule > Options > Level Resources",
        required_semantics="Leveling must respect resource capacity and activity logic. Preserve selected resources, priority rules, float limits, allowed overallocation, whether Early/Late dates are preserved and whether all resources are leveled. It is not just a UI conflict highlight.",
        user_options=("Level all resources", "Selected resource list", "Level within activity Total Float", "Minimum float to preserve", "Maximum percent to over-allocate", "Consider assignments in other projects with priority equal/higher than", "Preserve scheduled Early/Late dates", "Recalculate assignment costs after leveling", "Priority field", "Sort: Ascending/Descending/Hierarchy where allowed", "Write leveling log / View log", "Projects whose scheduling options control leveling"),
        official_sources=(ORACLE_SOURCES["schedule"], "https://docs.oracle.com/cd/F88968_01/client_help/en_US/leveling_resources.htm", ORACLE_SOURCES["leveling_dialog"]),
        cubi_code_paths=("src/construction_pm/scheduling/resource_leveling.py", "src/construction_pm/scheduling/leveling_scheduler.py", "src/construction_pm/p6_resource_leveling_read_adapter.py", "src/construction_pm/scheduling/resource_leveling_input.py", "src/construction_pm/scheduling/schedule_options.py"),
        regression_tests=("tests/scheduling/test_resource_leveling_input.py",), coverage=MAPPED_NOT_PROVEN,
    ),
    P6CodeReference(
        id="RES-003", area="Resources / Capacity and calendars", feature="Max Units/Time, effective rates and unit/time conversion",
        p6_ui_entry="Enterprise > Resources > Resource Details > Units & Prices / Calendar",
        required_semantics="Resource capacity is effective-dated and unit-aware. Use the selected time-period conversion and calendar work hours for each capacity slice. Percentage capacity requires an explicit full-time base. Resource Max Units/Time is not assignment Units/Time.",
        user_options=("Max Units/Time", "Effective date", "Rate time period", "Calendar/global time-period source", "Unit of measure", "Percentage or absolute capacity where supported"),
        official_sources=(ORACLE_SOURCES["calendars"], ORACLE_SOURCES["resource_planning"], ORACLE_SOURCES["resources"]),
        cubi_code_paths=("src/construction_pm/p6_resource_rate_repository.py", "src/construction_pm/p6_resource_capacity_contract.py", "src/construction_pm/p6_versioned_resource_calendar_resolver.py", "src/construction_pm/scheduling/resource_leveling_input.py"),
        regression_tests=("tests/scheduling/test_resource_leveling_input.py",), coverage=MAPPED_NOT_PROVEN,
    ),
    P6CodeReference(
        id="RES-004", area="Resources / Assignment calculations", feature="Assignment units, actual units, remaining units and Units/Time",
        p6_ui_entry="Edit > User Preferences > Calculations / Activity Details > Resources",
        required_semantics="Preserve assignment Units/Time separately from resource Max Units/Time. When staffing changes, honor preserve-versus-recalculate preference and activity duration type. Validate actual/remaining values against activity state and retain explicit units.",
        user_options=("Preserve Units, Duration and Units/Time", "Recalculate Units, Duration and Units/Time", "Rate type", "Role/resource assignment"),
        official_sources=(ORACLE_SOURCES["assignment_calculations"], ORACLE_SOURCES["unit_entry"], ORACLE_SOURCES["resources"]),
        cubi_code_paths=("src/construction_pm/p6_resource_assignment_repository.py", "src/construction_pm/p6_resource_write_api.py", "src/construction_pm/p6_resource_read_api.py", "src/construction_pm/scheduling/resource_leveling_input.py"),
        regression_tests=("tests/test_p6_resource_assignment_repository.py", "tests/test_p6_postgres_resource_assignment.py"),
        coverage=MAPPED_NOT_PROVEN,
    ),
    P6CodeReference(
        id="CST-001", area="Cost / Resource and role rates", feature="Resource and role cost calculation",
        p6_ui_entry="Activity Details > Resources > Rate Type / Resource Details > Units & Prices",
        required_semantics="Costs derive from typed units, applicable rate type, currency, resource/role price per unit and effective period. Planned, actual and remaining costs are distinct; scheduling triggers cost recalculation only when selected.",
        user_options=("Rate Type", "Currency", "Recalculate assignment costs after scheduling", "Planned/Actual/Remaining values"),
        official_sources=(ORACLE_SOURCES["resources"], ORACLE_SOURCES["schedule_options"]),
        cubi_code_paths=("src/construction_pm/p6_resource_rate_repository.py", "src/construction_pm/p6_resource_assignment_repository.py", "src/construction_pm/p6_cost_account_repository.py"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="Complete P6 cost field/rate precedence, effective-date and rounding policies need exhaustive reference and formula tests.",
    ),
    P6CodeReference(
        id="CST-002", area="Cost / Expenses", feature="Project expenses and cost accounts",
        p6_ui_entry="Project > Activities > Activity Details > Expenses / Cost Accounts",
        required_semantics="Keep expense item, cost account, accrual timing, planned/actual cost and assignment/resource cost as separate concepts. Activity/WBS/project linkage and rollup rules must be explicit.",
        user_options=("Expense item/type", "Accrual type", "Cost account", "Planned/Actual cost"),
        official_sources=(ORACLE_SOURCES["parity_baseline"],),
        cubi_code_paths=("src/construction_pm/p6_expense_repository.py", "src/construction_pm/p6_cost_account_repository.py"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="Official field-by-field expense semantics and rollup/rounding test cases remain to be completed.",
    ),
    P6CodeReference(
        id="EVM-001", area="Progress / Earned Value", feature="WBS Earned Value technique settings",
        p6_ui_entry="Project > WBS > WBS Details > Earned Value",
        required_semantics="Honor WBS-level technique for performance percent complete and ETC. Methods such as 0/100, 50/50 and custom percent complete have distinct earning rules; ETC may use remaining cost or configured performance factor. Overrides/default inheritance must be traceable.",
        user_options=("Activity Percent Complete", "Resource curves/future-period buckets", "WBS milestones/weighted milestones", "0/100", "50/50", "Custom Percent Complete", "ETC = remaining activity cost", "PF=1", "PF=1/CPI", "PF=1/(CPI*SPI)", "User-defined PF", "WBS-specific setting"),
        official_sources=(ORACLE_SOURCES["wbs_earned_value"],),
        cubi_code_paths=("src/construction_pm/scheduling/earned_schedule.py", "src/construction_pm/scheduling/progress_state.py", "src/construction_pm/project_schedule_settings_repository.py"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="Exact mapping of all P6 WBS Earned Value choices to CUBI persistence and EVM calculations needs a dedicated field/formula audit.",
    ),
    P6CodeReference(
        id="EVM-002", area="Progress / Earned Schedule", feature="Earned Schedule and schedule-performance reconciliation",
        p6_ui_entry="Project control reports / progress and performance analysis",
        required_semantics="Keep earned-value schedule indicators distinct from time-based Earned Schedule measures. Document each metric's definition, period basis, zero-denominator behavior, calendar/time unit and reconciliation between schedule variance/index and duration/time variance/index.",
        user_options=("Reporting period", "Baseline selection", "Calculation date/Data Date", "Time unit and calendar"),
        official_sources=(ORACLE_SOURCES["parity_baseline"],),
        cubi_code_paths=("src/construction_pm/scheduling/earned_schedule.py", "src/construction_pm/scheduling/__init__.py"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="CUBI Earned Schedule extension formulas and native P6 metric boundaries must be documented separately.",
    ),
    P6CodeReference(
        id="BAS-001", area="Baselines", feature="Create, maintain and assign baselines",
        p6_ui_entry="Project > Maintain Baselines / Project > Assign Baselines",
        required_semantics="Separate baseline snapshot creation from assignment for summarization/comparison. Support project, primary, secondary and tertiary roles as applicable, with immutable identity and audit semantics.",
        user_options=("Create current-project copy", "Convert another project to baseline", "Project baseline", "Primary", "Secondary", "Tertiary"),
        official_sources=(ORACLE_SOURCES["create_baseline"], ORACLE_SOURCES["assign_baseline"]),
        cubi_code_paths=("src/construction_pm/p6_baseline_api.py", "src/construction_pm/p6_baseline_repository.py", "shared/contracts/p6-baseline-api.v1.schema.json"),
        regression_tests=(), coverage=MAPPED_NOT_PROVEN,
    ),
    P6CodeReference(
        id="BAS-002", area="Baselines", feature="Selective baseline update and comparison",
        p6_ui_entry="Project > Maintain Baselines > Update / Activities baseline variance columns",
        required_semantics="Updating a baseline must preserve selected scope: project details, all activities or filtered subset, plus activity/resource-assignment data choices. Never overwrite data excluded by the user's selection.",
        user_options=("Project details", "All activities", "Filtered activities", "Add/Delete/Update records", "Activity data types", "Resource assignment data types"),
        official_sources=(ORACLE_SOURCES["update_baseline"], ORACLE_SOURCES["assign_baseline"]),
        cubi_code_paths=("src/construction_pm/p6_baseline_api.py", "src/construction_pm/p6_baseline_repository.py"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="Per-tab/per-field baseline update mapping and variance formula test matrix remain to be enumerated.",
    ),
    P6CodeReference(
        id="VIEW-001", area="Views / Activity grid and Gantt", feature="Configurable columns, sorting, grouping, filters and timeline scales",
        p6_ui_entry="Project > Activities; Layout / columns / filters / group and sort / Gantt timescale",
        required_semantics="Separate stored field identity from each view's column settings. Persist stable field IDs, order, visibility, width, sort/group/filter definitions and timescale. Timeline/grid edits must call authoritative typed APIs and must not calculate schedule dates in the UI.",
        user_options=("Show/hide columns", "Reorder/resize", "Sort", "Group", "Filter", "Gantt timescale", "Layout scope and persistence"),
        official_sources=(ORACLE_SOURCES["parity_baseline"],),
        cubi_code_paths=("apps/web/src/p6-activity-wbs-grid.ts", "apps/web/src/workspace-model.ts", "docs/architecture/P6_26_4_PARITY_AND_NO_OMISSION.md"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="Full menu/column/field inventory, persistence and end-to-end timeline edit tests are still required.",
    ),
    P6CodeReference(
        id="VIEW-002", area="Views / Reports and print", feature="Saved report profiles, output layout and printable reports",
        p6_ui_entry="Reports / Layouts / print-preview and export workflows",
        required_semantics="A saved report profile is configuration, not output. Bind reports to project revision/Data Date/baseline and selected fields; preserve units/localization and report missing/unsupported fields instead of silently dropping them.",
        user_options=("Report profile", "Selected fields", "Project/revision", "Baseline", "Date range", "Locale", "Page layout/output format"),
        official_sources=(ORACLE_SOURCES["parity_baseline"],),
        cubi_code_paths=("src/construction_pm/p6_report_profile_repository.py", "docs/architecture/P6_REPORT_PROFILE_MAPPING_PERSISTENCE_V1.md"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="P6 report menu inventory and CUBI A4/PDF/XLSX output parity are not certified by this registry.",
    ),
    P6CodeReference(
        id="DATA-001", area="Interoperability", feature="P6 project/resource import-export mapping",
        p6_ui_entry="File > Import / Export and supported integration APIs",
        required_semantics="Maintain versioned field maps for project XER, resource-only XER, XLSX and APIs where supported. Record type, units, nullable/default behavior, read/write capability, version provenance and round-trip behavior. Report unsupported data rather than silently dropping it.",
        user_options=("Format/version", "Project vs resource-only export", "Selected scope", "Conflict/update behavior", "Import validation report"),
        official_sources=(ORACLE_SOURCES["parity_baseline"],),
        cubi_code_paths=("docs/architecture/P6_26_4_PARITY_AND_NO_OMISSION.md", "src/construction_pm/activity_master_repository.py", "src/construction_pm/p6_resource_assignment_repository.py", "src/construction_pm/p6_baseline_repository.py"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="Official Version 26 XER/XLSX data-map guides and API catalogs must be enumerated field-by-field; this is not yet a completed mapping.",
    ),
    P6CodeReference(
        id="DATA-002", area="Data model / Field registry", feature="Complete field, column, enum and formula catalog",
        p6_ui_entry="All P6 menus, tabs, dialogs, Activity/WBS/resource tables and layouts",
        required_semantics="For every field record stable ID, display name, business object, type, unit, read/write status, null/default rule, calculated/stored status, sort/filter support, product context, version, API/database/import/export mapping and test evidence.",
        user_options=("Filter/sort", "Editable/read-only", "Calculated/stored", "Version/context", "UDF/custom field"),
        official_sources=(ORACLE_SOURCES["parity_baseline"],),
        cubi_code_paths=("docs/architecture/P6_26_4_PARITY_AND_NO_OMISSION.md", "src/construction_pm/p6_code_repository.py"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="The complete source-topic inventory and exhaustive field-level mapping remain open. This registry is an index, not a claim that all P6 fields are already listed.",
    ),
    P6CodeReference(
        id="DATA-003", area="Data model / Custom formulas", feature="Safe formula engine and recalculation dependencies",
        p6_ui_entry="Formula-capable fields/columns and project-control calculations",
        required_semantics="If custom formulas are offered, compile through tokenizer/parser/typed AST/dependency graph, detect cycles, enforce units/null behavior, evaluate deterministically and never execute arbitrary Python/JavaScript via eval-style execution.",
        user_options=("Formula definition", "Result type", "Units", "Null behavior", "Dependency/recalculation policy"),
        official_sources=(ORACLE_SOURCES["parity_baseline"],),
        cubi_code_paths=("docs/architecture/P6_26_4_PARITY_AND_NO_OMISSION.md",),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="The CUBI formula field catalog and executable evaluator path must be linked and tested before any formula-parity claim.",
    ),
    P6CodeReference(
        id="AUTH-001", area="Authoritative input / Reproducibility", feature="Persisted records to immutable schedule snapshot",
        p6_ui_entry="Schedule/recalculation command and every action that changes scheduling inputs",
        required_semantics="Read authoritative activities, relationships, constraints, settings, calendars and resources within tenant/project/revision scope; validate them; bind exact versions to an immutable snapshot/hash; calculate from that snapshot; publish with revision checks. Unsupported semantics must fail closed rather than be omitted.",
        user_options=("Project revision", "Schedule mode", "Calculation time zone", "Calendar versions", "Resource/relationship settings", "Snapshot identity"),
        official_sources=(ORACLE_SOURCES["parity_baseline"], ORACLE_SOURCES["schedule"]),
        cubi_code_paths=("src/construction_pm/authoritative_schedule_input_composer.py", "src/construction_pm/schedule_snapshot_materializer.py", "src/construction_pm/scheduling/authoritative_schedule.py", "src/construction_pm/http/production_composition.py", "src/construction_pm/http/project_lifecycle_routes.py"),
        regression_tests=("tests/test_authoritative_schedule_snapshot_composer.py",),
        coverage=MAPPED_NOT_PROVEN,
    ),

    P6CodeReference(
        id="SCH-011", area="Scheduling / General controls", feature="Automatic scheduling and coupled schedule actions",
        p6_ui_entry="Tools > Schedule > Options > General",
        required_semantics="Represent automatic recalculation after date-affecting changes, automatic resource leveling during scheduling, and cost recalculation after scheduling as separate user-selected settings. Do not silently turn on leveling or cost recalculation merely because schedule calculation runs. Record which open project's schedule options control a multi-project scheduling run.",
        user_options=("Schedule automatically when a change affects dates", "Level resources during scheduling", "Recalculate assignment costs after scheduling", "Use scheduling options from selected open project", "Default settings/reset"),
        official_sources=(ORACLE_SOURCES["schedule_options"], ORACLE_SOURCES["schedule_dialog"]),
        cubi_code_paths=("src/construction_pm/scheduling/schedule_options.py", "src/construction_pm/schedule_evaluator.py", "src/construction_pm/project_schedule_settings_repository.py", "src/construction_pm/http/project_lifecycle_routes.py"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="Each general-option persisted value must be traced into production composition and tested for both enabled and disabled behavior.",
    ),
    P6CodeReference(
        id="SCH-012", area="Scheduling / Out-of-sequence SS logic", feature="Start-to-start lag expiry basis",
        p6_ui_entry="Tools > Schedule > Options > General > Calculate start-to-start lag from",
        required_semantics="When an SS predecessor is out of sequence, the chosen basis changes how expired and remaining lag are computed. Early Start bases expiry on the predecessor internal Early Start and elapsed work periods; Actual Start bases it on the recorded actual start and elapsed time. This selector is disabled when Actual Dates mode is used and must not be treated as active in that mode.",
        user_options=("Early Start", "Actual Start", "Disabled under Actual Dates mode"),
        official_sources=(ORACLE_SOURCES["schedule_options"], ORACLE_SOURCES["relationship_lag"]),
        cubi_code_paths=("src/construction_pm/scheduling/schedule_options.py", "src/construction_pm/scheduling/out_of_sequence.py", "src/construction_pm/scheduling/relationships.py", "src/construction_pm/scheduling/time_forward_pass.py"),
        regression_tests=("tests/scheduling/test_schedule.py", "tests/scheduling/test_time_schedule.py"),
        coverage=MAPPED_NOT_PROVEN,
        acceptance_evidence=("SS out-of-sequence tests distinguish Early Start from Actual Start", "Actual Dates mode rejects/ignores no user option silently; behavior matches official rule"),
    ),
    P6CodeReference(
        id="SCH-013", area="Scheduling / Schedule dialog", feature="Multi-project Data Date, forecast start and scheduling log",
        p6_ui_entry="Tools > Schedule dialog",
        required_semantics="Support each project's own Data Date or applying one selected Data Date to all open projects. The forecast-start option, when selected, uses the forecast date rather than the project's planned start/current Data Date. Scheduling logs must report the run and distinguish append/overwrite and HTML/plain output where offered.",
        user_options=("All projects use their own Data Date", "Apply selected Data Date to all opened projects", "Set Data Date and Project Planned Start to Project Forecast Start during scheduling", "Log to file", "HTML/plain log", "Overwrite/append existing log", "Schedule/Cancel/View Log"),
        official_sources=(ORACLE_SOURCES["schedule_dialog"], ORACLE_SOURCES["schedule"]),
        cubi_code_paths=("src/construction_pm/scheduling/schedule_options.py", "src/construction_pm/scheduling/authoritative_schedule.py", "src/construction_pm/authoritative_schedule_input_composer.py", "src/construction_pm/schedule_evaluator.py"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="Multi-project run orchestration, forecast-start handling and schedule-log fidelity require dedicated contracts and end-to-end tests.",
    ),
    P6CodeReference(
        id="RES-005", area="Resources / Cross-project leveling", feature="Leveler project priority, resource selection and result log",
        p6_ui_entry="Tools > Level Resources dialog",
        required_semantics="In addition to per-activity priority, record the selected project settings source and any threshold for including assignments from other projects. Project leveling priority is ranked 1 (highest) through 100 (lowest). Respect hierarchical priority sort where available, output the requested leveling log, and never hide remaining over-allocation.",
        user_options=("Scheduling options source project", "Include other projects with priority at or above configured threshold", "Project leveling priority 1-100", "Field priorities", "Ascending/Descending/Hierarchy", "Level all/selected resources", "Write/View log", "Default settings"),
        official_sources=(ORACLE_SOURCES["leveling_dialog"], ORACLE_SOURCES["schedule"]),
        cubi_code_paths=("src/construction_pm/scheduling/resource_leveling.py", "src/construction_pm/scheduling/leveling_scheduler.py", "src/construction_pm/scheduling/schedule_options.py", "src/construction_pm/p6_resource_leveling_read_adapter.py"),
        regression_tests=("tests/scheduling/test_resource_leveling_input.py",), coverage=INVENTORY_REQUIRED,
        known_gap="Cross-project priority thresholds and leveling-log behavior are not yet proven by the current registry's test mapping.",
    ),

    P6CodeReference(
        id="PRJ-001", area="Projects / EPS", feature="EPS hierarchy, project properties, defaults and project-level controls",
        p6_ui_entry="Projects window / Enterprise Project Structure / Project Details",
        required_semantics="Preserve the EPS hierarchy and project identity separately from displayed project names. Record project planned start/finish, forecast start where applicable, responsible organization, project calendar, Data Date, status and project-level defaults. The selected project context must determine settings without cross-project leakage.",
        user_options=("EPS parent/child", "Project ID/name", "Planned Start/Finish", "Forecast Start", "Project Calendar", "Data Date", "Project status", "Default project/template"),
        official_sources=("https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm", ORACLE_SOURCES["schedule_dialog"]),
        cubi_code_paths=("src/construction_pm/http/project_lifecycle_routes.py", "src/construction_pm/project_schedule_settings_repository.py", "src/construction_pm/authoritative_schedule_input_composer.py"),
        regression_tests=("tests/test_project_lifecycle_http_routes.py",),
        coverage=INVENTORY_REQUIRED,
        known_gap="A complete Version 26 project/EPS field registry and end-to-end inheritance/default-resolution test matrix still need to be enumerated.",
    ),
    P6CodeReference(
        id="WBS-001", area="WBS / Work breakdown", feature="WBS hierarchy, status, earned-value defaults and rollups",
        p6_ui_entry="Project > WBS > WBS Details",
        required_semantics="Maintain stable WBS identity, parent/child relationships, responsible organization, WBS dates/status and hierarchy-specific defaults. WBS summarization and Earned Value must use explicit rollup rules and selected baseline/technique; never treat WBS Summary activity as a regular task.",
        user_options=("WBS hierarchy/order", "WBS code/name", "Responsible OBS", "WBS status/dates", "Earned Value technique", "WBS milestones/weight", "Activity assignment to WBS"),
        official_sources=("https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm", ORACLE_SOURCES["wbs_earned_value"]),
        cubi_code_paths=("apps/web/src/p6-activity-wbs-grid.ts", "apps/web/src/workspace-model.ts", "src/construction_pm/http/project_lifecycle_routes.py", "docs/architecture/P6_26_4_PARITY_AND_NO_OMISSION.md"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="The current scan did not verify a dedicated WBS master domain/repository. Field-level WBS persistence, authorization and summary-rollup mapping must be established before parity is claimed.",
    ),
    P6CodeReference(
        id="CODE-001", area="Codes / Custom fields", feature="Activity, project, resource and role codes; UDFs",
        p6_ui_entry="Enterprise > Project Codes / Resource Codes / Activity Codes / User Defined Fields",
        required_semantics="Keep code dictionary, code value and assignment as separate entities; preserve hierarchy, scope, stable IDs, data types, applicable subject area and assignment cardinality. UDFs must retain typed value/null semantics, and code changes must not corrupt saved layouts or filters.",
        user_options=("Global vs project/activity scope", "Code hierarchy", "Code value/description", "UDF data type", "Required/default/read-only rules", "Assignment/unassignment", "Sort/filter/group"),
        official_sources=("https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm",),
        cubi_code_paths=("src/construction_pm/p6_code_repository.py", "src/construction_pm/activity_master_repository.py", "apps/web/src/p6-activity-wbs-grid.ts"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="The complete Version 26 code/UDF types, scopes, import/export mappings and UI catalog are not yet cross-referenced to all subject-area repositories.",
    ),
    P6CodeReference(
        id="ACT-006", area="Activities / Steps", feature="Activity Steps, weighted progress and templates",
        p6_ui_entry="Project > Activities > Activity Details > Steps / Activity Step Templates",
        required_semantics="Keep activity steps as identifiable child records with their own names, sequence, weight and completion state. For weighted Physical Percent Complete, calculate from the defined step-weight method and prevent invalid sums/ambiguous empty-step behavior. Template application must preserve chosen scope and avoid duplicate step identities.",
        user_options=("Add/reorder/delete steps", "Step weight", "Step completion", "Weighted physical progress", "Create/apply step template", "Selected activity scope"),
        official_sources=("https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm",),
        cubi_code_paths=("src/construction_pm/p6_activity_step_template_repository.py",),
        regression_tests=("tests/test_p6_activity_step_template_repository.py", "tests/integration/test_p6_activity_step_template_postgres_live.py"),
        coverage=MAPPED_NOT_PROVEN,
        known_gap="Step-template persistence has code/test mappings; exact Version 26 editing rules and weighted-progress recalculation still need field-by-field acceptance evidence.",
    ),
    P6CodeReference(
        id="RES-006", area="Resources / Distribution", feature="Resource curves and future-period bucket values",
        p6_ui_entry="Enterprise > Resources > Resource Curves; Activity Details > Resources > Spreadsheet / Future Period Buckets",
        required_semantics="Preserve planned/remaining assignment units and costs by bucket, selected curve and bucket calendar/time basis. Curve distribution rules and manually entered future-period bucket values must remain distinguishable. Resource leveling must not silently reinterpret a curve as actual bucket data.",
        user_options=("Resource curve selection", "Curve shape/distribution", "Future-period bucket edit", "Time interval", "Units/cost display", "Manual bucket overrides"),
        official_sources=("https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm", ORACLE_SOURCES["resources"], ORACLE_SOURCES["resource_planning"]),
        cubi_code_paths=("src/construction_pm/p6_resource_spread_repository.py", "src/construction_pm/p6_resource_spread_api.py", "src/construction_pm/p6_resource_assignment_repository.py"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="A complete curve library, per-bucket formula mapping, UI spreadsheet mapping and round-trip tests were not verified in this pass.",
    ),
    P6CodeReference(
        id="PROG-001", area="Progress / Update workflow", feature="Update progress, apply actuals and close periods",
        p6_ui_entry="Tools > Update Progress / Tools > Store Period Performance",
        required_semantics="Distinguish entered status/progress from a scheduling run and from applying actuals. Changes must reconcile actual start/finish, actual and remaining units/cost/duration, Data Date and out-of-sequence policy. Stored period performance must be immutable/period-addressed and must not be silently recalculated from current state.",
        user_options=("Update selected/all applicable activities", "Apply actuals", "Data Date advance", "Store period performance", "Financial period", "Remaining Duration/Units", "Actual Start/Finish", "Out-of-sequence policy"),
        official_sources=("https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm", ORACLE_SOURCES["progress"], ORACLE_SOURCES["data_date"]),
        cubi_code_paths=("src/construction_pm/scheduling/progress_state.py", "src/construction_pm/scheduling/remaining_work.py", "src/construction_pm/scheduling/out_of_sequence.py", "src/construction_pm/scheduling/authoritative_schedule.py", "src/construction_pm/authoritative_schedule_input_composer.py"),
        regression_tests=("tests/scheduling/test_schedule.py",),
        coverage=INVENTORY_REQUIRED,
        known_gap="The exact Update Progress dialog operations, apply-actuals rules and closed-period performance records need a complete menu-to-domain-to-test map.",
    ),
    P6CodeReference(
        id="PORT-001", area="Portfolio / Budget", feature="Project budgets, funding sources and budget change controls",
        p6_ui_entry="Project > Budget Summary / Funding / Project Details",
        required_semantics="Keep original budget, approved changes, current budget, funding source/period and forecast cost as distinct values. Rollups must preserve project/WBS ownership, currency, approval history and the difference between budget and schedule-derived cost.",
        user_options=("Budget amount", "Funding source", "Funding period", "Approved/unapproved change", "Project/WBS rollup", "Currency", "Forecast vs budget"),
        official_sources=("https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm",),
        cubi_code_paths=("docs/architecture/P6_26_4_PARITY_AND_NO_OMISSION.md", "src/construction_pm/http/project_lifecycle_routes.py"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="This scan did not find a verified complete P6 budget/funding implementation path; domain schemas, currency/period behavior and audit tests must be identified or built.",
    ),
    P6CodeReference(
        id="RISK-001", area="Project controls / Risks and issues", feature="Issues, thresholds, risks and linked project documents",
        p6_ui_entry="Project > Issues / Thresholds / Risks / Project Documents",
        required_semantics="Maintain stable object identity, project/activity/WBS links, ownership, status, due/target dates, risk probability/impact and evidence/document relationships. Threshold warnings must be reproducible from explicit metrics and configurable thresholds; a risk score must not be hard-coded in the UI.",
        user_options=("Issue status/priority/owner", "Target date", "Threshold metric/operator/value", "Risk probability/impact/response", "Linked activity/WBS/document", "Alert/report settings"),
        official_sources=("https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm",),
        cubi_code_paths=("docs/architecture/P6_26_4_PARITY_AND_NO_OMISSION.md", "src/construction_pm/http/project_lifecycle_routes.py"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="Dedicated P6 issue/threshold/risk menu inventories, canonical schemas and end-to-end behavior mappings are not verified by this registry.",
    ),
    P6CodeReference(
        id="VIEW-003", area="Views / Timeline", feature="Gantt editing, data-date/progress lines, bars and timescale",
        p6_ui_entry="Project > Activities > Gantt Chart > Timescale / Bars / Progress Line / Data Date Line",
        required_semantics="A Gantt drag/edit must submit a domain mutation and then recalculate with the same authoritative engine as all other clients. Distinguish planned/early/late/actual/baseline/remaining dates and progress from drawing coordinates. Zoom/timescale and line/bar visibility are presentation state, not calculation settings.",
        user_options=("Edit start/finish/duration where permitted", "Data Date line", "Progress line", "Baseline bars", "Early/Late bars", "Timescale unit/interval", "Nonwork display", "Bar styles and visibility", "Zoom/scroll"),
        official_sources=("https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm", ORACLE_SOURCES["schedule"]),
        cubi_code_paths=("apps/web/src/p6-activity-wbs-grid.ts", "apps/web/src/workspace-model.ts", "src/construction_pm/http/project_lifecycle_routes.py", "src/construction_pm/schedule_evaluator.py"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="A production Gantt/timeline read-edit-write-recalculate path and visual regression tests have not been proven through the current mapping.",
    ),
    P6CodeReference(
        id="VIEW-004", area="Views / Analysis", feature="Activity Network, Trace Logic, usage profiles and tracking layouts",
        p6_ui_entry="Project > Activities > Activity Network / Trace Logic / Activity Usage / Resource Usage / Tracking Layout",
        required_semantics="Views must render from versioned schedule, relationship and time-phased assignment facts. Trace Logic should show the actual driving predecessor/successor chain from the calculation result. Usage profile values must reconcile to assignment-period data; zoom/scale must not alter underlying values.",
        user_options=("Activity Network display", "Trace Logic path", "Activity/resource usage profile", "Spreadsheet time scale", "Unit/cost display", "Tracking layout", "Baseline/actual/remaining series"),
        official_sources=("https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm", ORACLE_SOURCES["critical"], ORACLE_SOURCES["resource_planning"]),
        cubi_code_paths=("src/construction_pm/scheduling/p6_activity_scheduler_outputs.py", "src/construction_pm/scheduling/resource_leveling_input.py", "src/construction_pm/p6_resource_assignment_repository.py", "src/construction_pm/p6_resource_spread_repository.py", "docs/architecture/P6_26_4_PARITY_AND_NO_OMISSION.md"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="No exhaustive source-to-renderer map for Activity Network, Trace Logic, profiles, and tracking layouts has yet been established.",
    ),
    P6CodeReference(
        id="VIEW-005", area="Views / Layout operations", feature="Group, sort, filter, summarize and reusable layouts",
        p6_ui_entry="Project > Activities > Layout / Group and Sort / Filters / Summarize",
        required_semantics="Keep field identity, view layout and filter definition separate. Support stable criteria, grouping levels, sort direction, WBS/project rollups, user/project/global scope and persistence. Calculated columns use the typed shared calculation engine. A filter must not mutate or delete records.",
        user_options=("Saved layouts", "Column selection/order/width", "Group levels", "Sort field/direction", "Filter rules", "User/project/global scope", "Summary/rollup behavior"),
        official_sources=("https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm",),
        cubi_code_paths=("apps/web/src/p6-activity-wbs-grid.ts", "apps/web/src/workspace-model.ts", "docs/architecture/P6_26_4_PARITY_AND_NO_OMISSION.md"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="Exact P6 saved-layout scope, filter operators, group/sort fields and rollup behavior need a complete menu/field matrix.",
    ),
    P6CodeReference(
        id="REPORT-001", area="Reports / Publishing", feature="Reports, project website publishing and summary services",
        p6_ui_entry="Tools > Reports / Tools > Publish / Summary services",
        required_semantics="Report definitions must record selected fields, grouping, filters, baseline, project revision, Data Date, locale and output format. Published output and summarization must be reproducible from identified source data; unsupported fields must be reported rather than omitted silently.",
        user_options=("Report definition", "Report fields/grouping/filter", "Output format", "Publishing scope", "Schedule/period", "Summary service policy", "Locale and page settings"),
        official_sources=("https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm",),
        cubi_code_paths=("src/construction_pm/p6_report_profile_repository.py", "docs/architecture/P6_REPORT_PROFILE_MAPPING_PERSISTENCE_V1.md", "docs/architecture/P6_26_4_PARITY_AND_NO_OMISSION.md"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="P6 report catalog, website publishing and summary-service schedule need exact implementation paths and reproducible output tests.",
    ),
    P6CodeReference(
        id="TOOLS-001", area="Tools / Global change", feature="Global Change, date arithmetic and safe custom updates",
        p6_ui_entry="Tools > Global Change",
        required_semantics="Any bulk-change feature must model target object, filter criteria, old-value conditions, assignment expressions, arithmetic/date arithmetic, preview, affected-record count and explicit commit. Validate types/units and tenant/project scope; keep an audit of before/after values. Never evaluate arbitrary Python or JavaScript expressions.",
        user_options=("Select target subject/field", "Filter condition", "Assignment expression", "Arithmetic/date arithmetic", "Preview changes", "Apply/cancel", "Audit"),
        official_sources=("https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm",),
        cubi_code_paths=("docs/architecture/P6_26_4_PARITY_AND_NO_OMISSION.md", "src/construction_pm/http/project_lifecycle_routes.py"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="No verified safe Global Change evaluator/transaction path was found in this source scan; do not expose the capability as complete before it exists and is tested.",
    ),
    P6CodeReference(
        id="TOOLS-002", area="Tools / Quality checking", feature="Project Checker and top-down estimation",
        p6_ui_entry="Tools > Check Schedule / Project Checker / Top-Down Estimation",
        required_semantics="Quality checks must be deterministic, versioned and explain every finding with affected entity and evidence. Top-down estimates must record allocation rule, total, WBS scope and allocation basis; they must not overwrite detailed estimates without explicit confirmation.",
        user_options=("Check profile", "Severity thresholds", "Run scope", "Estimate total", "WBS/activity allocation basis", "Preview/accept"),
        official_sources=("https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm",),
        cubi_code_paths=("docs/architecture/P6_26_4_PARITY_AND_NO_OMISSION.md", "docs/roadmap/STAGE_STATUS.md"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="Exact Project Checker and Top-Down Estimation implementation mappings and acceptance suites remain unverified.",
    ),
    P6CodeReference(
        id="FIN-001", area="Administration / Units and finance", feature="Admin preferences, currencies and financial periods",
        p6_ui_entry="Admin Preferences / Admin Categories > Currencies / Financial Periods / Time Periods",
        required_semantics="Central defaults such as hours/day, hours/week, hours/month, hours/year, currency precision/exchange rate and financial period definitions must be versioned and explicit in calculations. A user locale or UI preference must not silently change a project calculation's persisted unit conversions.",
        user_options=("Hours per day/week/month/year", "Standard time period", "Currency/precision/exchange rate", "Financial periods", "Week start/day preferences", "Default duration/EV settings"),
        official_sources=("https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm", ORACLE_SOURCES["calendars"]),
        cubi_code_paths=("src/construction_pm/scheduling/calendar_periods.py", "src/construction_pm/scheduling/calendar.py", "src/construction_pm/project_schedule_settings_repository.py", "src/construction_pm/p6_resource_rate_repository.py", "src/construction_pm/p6_cost_account_repository.py"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="Admin-category complete list, currency/time-period precedence, precision and financial period rules are not fully mapped to source and tests.",
    ),
    P6CodeReference(
        id="AUTH-002", area="Administration / Security", feature="Users, global/project profiles and resource security",
        p6_ui_entry="Admin Categories > Users / Security Profiles / Global Profiles / Project Profiles / OBS",
        required_semantics="Enforce least privilege at the domain/API layer, with project and organization scope checked for every read/write. UI hiding is not authorization. Changing profiles must not mutate project data; all denied writes must have no side effects and privileged operations must be auditable.",
        user_options=("User account", "Global profile", "Project profile", "OBS scope", "Resource access", "Field/operation permission"),
        official_sources=("https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm",),
        cubi_code_paths=("src/construction_pm/http/project_lifecycle_routes.py", "src/construction_pm/http/production_composition.py", "docs/architecture/P6_26_4_PARITY_AND_NO_OMISSION.md"),
        regression_tests=("tests/test_project_lifecycle_http_routes.py",),
        coverage=INVENTORY_REQUIRED,
        known_gap="P6 security profile and resource-access matrix must be compared to CUBI authorization contracts action by action.",
    ),
    P6CodeReference(
        id="OFFLINE-001", area="Projects / Offline and multi-project", feature="Project checkout/check-in, local cache and multi-project boundaries",
        p6_ui_entry="File > Open / Check Out / Check In / Multiple Projects / Local Cache",
        required_semantics="Treat online authoritative revision, local cached revision, pending edits and conflicts as distinct state. Check-in must use optimistic concurrency, preserve immutable mutation identity and reject conflicting reuse. Multi-project calculations must explicitly bind external relationships and resource assumptions instead of combining arbitrary cached snapshots.",
        user_options=("Open one/multiple projects", "Check out/check in", "Offline cache", "Refresh/reconcile", "Conflict resolution", "Retry queue", "Project revision"),
        official_sources=("https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm", ORACLE_SOURCES["schedule"]),
        cubi_code_paths=("src/construction_pm/http/project_lifecycle_routes.py", "src/construction_pm/scheduling/authoritative_schedule.py", "src/construction_pm/scheduling/multi_project_float.py", "docs/architecture/P6_26_4_PARITY_AND_NO_OMISSION.md"),
        regression_tests=(), coverage=INVENTORY_REQUIRED,
        known_gap="CUBI offline contracts exist in the architecture; full P6 workflow equivalence and multi-project cache consistency remain unverified.",
    ),
)


def validate_registry(items: Iterable[P6CodeReference] = P6_CODE_REFERENCE) -> tuple[str, ...]:
    """Return catalog defects without filesystem, network, or project-data access."""
    errors: list[str] = []
    seen: set[str] = set()
    allowed = {MAPPED_NOT_PROVEN, KNOWN_GAP, INVENTORY_REQUIRED}
    for item in items:
        if item.id in seen:
            errors.append(f"DUPLICATE_ID:{item.id}")
        seen.add(item.id)
        if item.coverage not in allowed:
            errors.append(f"INVALID_COVERAGE:{item.id}:{item.coverage}")
        if not item.official_sources:
            errors.append(f"MISSING_OFFICIAL_SOURCE:{item.id}")
        if not item.cubi_code_paths:
            errors.append(f"MISSING_CODE_MAPPING:{item.id}")
        if item.coverage == KNOWN_GAP and not item.known_gap:
            errors.append(f"MISSING_GAP_EXPLANATION:{item.id}")
    return tuple(errors)


def get_reference(reference_id: str) -> P6CodeReference:
    """Look up a requirement by stable registry ID."""
    for item in P6_CODE_REFERENCE:
        if item.id == reference_id:
            return item
    raise KeyError(reference_id)


def references_for_area(area: str) -> tuple[P6CodeReference, ...]:
    """Return all requirements whose area label matches exactly."""
    return tuple(item for item in P6_CODE_REFERENCE if item.area == area)


def coverage_summary() -> dict[str, int]:
    """Summarize evidence labels; these are not project completion percentages."""
    result = {MAPPED_NOT_PROVEN: 0, KNOWN_GAP: 0, INVENTORY_REQUIRED: 0}
    for item in P6_CODE_REFERENCE:
        result[item.coverage] += 1
    result["TOTAL_REGISTERED"] = len(P6_CODE_REFERENCE)
    return result


if __name__ == "__main__":
    defects = validate_registry()
    if defects:
        raise SystemExit("\n".join(defects))
    print(f"{REFERENCE_ID} v{REFERENCE_VERSION}: {coverage_summary()}")
