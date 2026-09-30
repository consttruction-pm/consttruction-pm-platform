from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class P6FieldType(str, Enum):
    STRING = "string"
    DATE = "date"
    DATETIME = "datetime"
    DURATION = "duration"
    DECIMAL = "decimal"
    PERCENTAGE = "percentage"
    BOOLEAN = "boolean"
    ENUM = "enum"
    INTEGER = "integer"
    DOUBLE = "double"
    COST = "cost"
    UNIT = "unit"
    OBJECT_ID = "object-id"
    OBJECT_ID_ARRAY = "object-id-array"
    STRING_ARRAY = "string-array"
    COMPLEX = "complex"
    SPREAD = "spread"


@dataclass(frozen=True)
class P6FieldDefinition:
    field_id: str
    subject_area: str
    p6_field: str
    display_name: str
    data_type: P6FieldType
    writable: bool
    computed: bool
    unit: str | None = None
    source: str = "Oracle P6 Version 26 / 26.4"
    reference_url: str = (
        "https://docs.oracle.com/cd/F51303_01/English/Integration/"
        "p6_pro_api_reference/FieldSummary.html"
    )
    read_only: bool | None = None
    filterable: bool | None = None
    orderable: bool | None = None
    nullable: bool | None = None
    disposition: str = "seeded_not_certified"

    def __post_init__(self) -> None:
        if not all((self.field_id, self.subject_area, self.p6_field, self.display_name)):
            raise ValueError("field identity and display name are required")
        if self.writable and self.computed:
            raise ValueError("a field cannot be both writable and computed")
        if self.disposition not in {
            "seeded_not_certified",
            "implemented",
            "equivalent_superset",
            "outside_scope",
            "pending",
        }:
            raise ValueError(f"invalid field disposition: {self.disposition}")


# Core seed catalog. This is intentionally versioned and incomplete until
# every applicable P6 Version 26 / 26.4 field receives a disposition.
_ROWS = (
    ("activity.activity_id","Activity","ActivityId","Activity ID","string",True,False,None),
    ("activity.activity_name","Activity","ActivityName","Activity Name","string",True,False,None),
    ("activity.activity_status","Activity","ActivityStatus","Activity Status","enum",True,False,None),
    ("activity.activity_type","Activity","ActivityType","Activity Type","enum",True,False,None),
    ("activity.calendar","Activity","Calendar","Calendar","string",True,False,None),
    ("activity.planned_start","Activity","PlannedStartDate","Planned Start","date",True,False,None),
    ("activity.planned_finish","Activity","PlannedFinishDate","Planned Finish","date",True,False,None),
    ("activity.actual_start","Activity","ActualStartDate","Actual Start","date",True,False,None),
    ("activity.actual_finish","Activity","ActualFinishDate","Actual Finish","date",True,False,None),
    ("activity.remaining_start","Activity","RemainingStartDate","Remaining Start","date",True,False,None),
    ("activity.remaining_finish","Activity","RemainingFinishDate","Remaining Finish","date",True,False,None),
    ("activity.planned_duration","Activity","PlannedDuration","Planned Duration","duration",False,True,"working-time"),
    ("activity.remaining_duration","Activity","RemainingDuration","Remaining Duration","duration",False,True,"working-time"),
    ("activity.actual_duration","Activity","ActualDuration","Actual Duration","duration",False,True,"working-time"),
    ("activity.duration_percent_complete","Activity","DurationPercentComplete","Duration % Complete","percentage",False,True,"percent"),
    ("activity.physical_percent_complete","Activity","PhysicalPercentComplete","Physical % Complete","percentage",True,False,"percent"),
    ("activity.percent_complete_type","Activity","PercentCompleteType","Percent Complete Type","enum",True,False,None),
    ("activity.total_float","Activity","TotalFloat","Total Float","duration",False,True,"working-time"),
    ("activity.free_float","Activity","FreeFloat","Free Float","duration",False,True,"working-time"),
    ("activity.float_path","Activity","FloatPath","Float Path","integer",False,True,None),
    ("activity.float_path_order","Activity","FloatPathOrder","Float Path Order","integer",False,True,None),
    ("activity.early_start","Activity","EarlyStartDate","Early Start","date",False,True,None),
    ("activity.early_finish","Activity","EarlyFinishDate","Early Finish","date",False,True,None),
    ("activity.late_start","Activity","LateStartDate","Late Start","date",False,True,None),
    ("activity.late_finish","Activity","LateFinishDate","Late Finish","date",False,True,None),
    ("activity.primary_constraint_type","Activity","PrimaryConstraintType","Primary Constraint Type","enum",True,False,None),
    ("activity.primary_constraint_date","Activity","PrimaryConstraintDate","Primary Constraint Date","date",True,False,None),
    ("activity.expected_finish","Activity","ExpectedFinishDate","Expected Finish","date",True,False,None),
    ("activity.owner","Activity","ActivityOwner","Activity Owner","string",True,False,None),
    ("activity.primary_resource","Activity","PrimaryResourceName","Primary Resource","string",True,False,None),
    ("activity.project_id","Activity","ProjectId","Project ID","string",False,True,None),
    ("activity.project_name","Activity","ProjectName","Project Name","string",False,True,None),
    ("activity.wbs","Activity","WBSPath","WBS","string",False,True,None),
    ("activity.baseline_start","Activity","BaselineStartDate","Baseline Start","date",False,True,None),
    ("activity.baseline_finish","Activity","BaselineFinishDate","Baseline Finish","date",False,True,None),
    ("activity.baseline_duration","Activity","BaselineDuration","Baseline Duration","duration",False,True,"working-time"),
    ("activity.duration_variance","Activity","Duration1Variance","Duration Variance","duration",False,True,"working-time"),
    ("activity.created_by","Activity","CreateUser","Created By","string",False,True,None),
    ("activity.updated_by","Activity","UpdateUser","Updated By","string",False,True,None),
    ("activity_code.type","Codes","ActivityCodeType","Activity Code Type","string",True,False,None),
    ("activity_code.value","Codes","ActivityCodeValue","Activity Code Value","string",True,False,None),
    ("wbs.code","WBS","WBSCode","WBS Code","string",True,False,None),
    ("wbs.name","WBS","WBSName","WBS Name","string",True,False,None),
    ("wbs.path","WBS","WBSPath","WBS Path","string",False,True,None),
    ("wbs.responsible_manager","WBS","ResponsibleManager","Responsible Manager","string",True,False,None),
    ("wbs.obs","WBS","OBSName","OBS","string",False,True,None),
    ("wbs.start","WBS","WBSStartDate","Start Date","date",False,True,None),
    ("wbs.finish","WBS","WBSFinishDate","Finish Date","date",False,True,None),
    ("project.id","Project","ProjectId","Project ID","string",True,False,None),
    ("project.name","Project","ProjectName","Project Name","string",True,False,None),
    ("project.status","Project","Status","Project Status","enum",True,False,None),
    ("project.planned_start","Project","PlannedStartDate","Planned Start","date",True,False,None),
    ("project.planned_finish","Project","PlannedFinishDate","Planned Finish","date",True,False,None),
    ("project.data_date","Project","DataDate","Data Date","date",True,False,None),
    ("project.calendar","Project","ProjectCalendar","Project Calendar","string",True,False,None),
    ("project.finish","Project","ProjectFinishDate","Project Finish","date",False,True,None),
    ("resource.id","Resource/Assignment","ResourceId","Resource ID","string",True,False,None),
    ("resource.name","Resource/Assignment","ResourceName","Resource Name","string",True,False,None),
    ("resource.type","Resource/Assignment","ResourceType","Resource Type","enum",True,False,None),
    ("resource.calendar","Resource/Assignment","ResourceCalendar","Resource Calendar","string",True,False,None),
    ("resource.price","Resource/Assignment","ResourcePrice","Price / Unit","decimal",True,False,"currency/unit"),
    ("resource.max_units_time","Resource/Assignment","MaxUnitsTime","Max Units/Time","decimal",True,False,"units/time"),
    ("resource.primary_role","Resource/Assignment","PrimaryRole","Primary Role","string",True,False,None),
    ("assignment.activity_id","Resource/Assignment","ActivityId","Activity ID","string",True,False,None),
    ("assignment.planned_units","Resource/Assignment","PlannedUnits","Planned Units","decimal",True,False,"units"),
    ("assignment.actual_units","Resource/Assignment","ActualUnits","Actual Units","decimal",True,False,"units"),
    ("assignment.remaining_units","Resource/Assignment","RemainingUnits","Remaining Units","decimal",True,False,"units"),
    ("assignment.planned_cost","Resource/Assignment","PlannedCost","Planned Cost","decimal",True,False,"currency"),
    ("assignment.actual_cost","Resource/Assignment","ActualCost","Actual Cost","decimal",True,False,"currency"),
    ("assignment.remaining_cost","Resource/Assignment","RemainingCost","Remaining Cost","decimal",True,False,"currency"),
    ("step.name","Activity Step","StepName","Step Name","string",True,False,None),
    ("step.description","Activity Step","StepDescription","Step Description","string",True,False,None),
    ("step.weight","Activity Step","StepWeight","Step Weight","decimal",True,False,None),
    ("step.percent_complete","Activity Step","StepPercentComplete","Step % Complete","percentage",True,False,"percent"),
    ("step.completed","Activity Step","StepCompleted","Completed","boolean",True,False,None),
    ("step.start","Activity Step","StepStartDate","Step Start","date",True,False,None),
    ("step.finish","Activity Step","StepFinishDate","Step Finish","date",True,False,None),
    ("expense.name","Expense","ExpenseName","Expense Name","string",True,False,None),
    ("expense.category","Expense","ExpenseCategory","Expense Category","string",True,False,None),
    ("expense.planned_cost","Expense","PlannedExpenseCost","Planned Expense Cost","decimal",True,False,"currency"),
    ("expense.actual_cost","Expense","ActualExpenseCost","Actual Expense Cost","decimal",True,False,"currency"),
    ("expense.remaining_cost","Expense","RemainingExpenseCost","Remaining Expense Cost","decimal",True,False,"currency"),
    ("baseline.primary","Baseline","PrimaryBaseline","Primary Baseline","string",True,False,None),
    ("baseline.secondary","Baseline","SecondaryBaseline","Secondary Baseline","string",True,False,None),
    ("baseline.tertiary","Baseline","TertiaryBaseline","Tertiary Baseline","string",True,False,None),
    ("financial_period.name","Financial Period","FinancialPeriodName","Financial Period","string",True,False,None),
    ("financial_period.actual_cost","Financial Period","ActualThisPeriodCost","Actual This Period Cost","decimal",False,True,"currency"),
    ("financial_period.actual_units","Financial Period","ActualThisPeriodUnits","Actual This Period Units","decimal",False,True,"units"),
    ("schedule_options.calculate_float_based_on_finish_date","ScheduleOptions","CalculateFloatBasedOnFinishDate","Calculate Float Based on Finish Date","boolean",True,False,None),
    ("schedule_options.compute_total_float_type","ScheduleOptions","ComputeTotalFloatType","Compute Total Float Type","enum",True,False,None),
    ("schedule_options.create_date","ScheduleOptions","CreateDate","Create Date","datetime",False,False,None),
    ("schedule_options.create_user","ScheduleOptions","CreateUser","Create User","string",False,False,None),
    ("schedule_options.critical_activity_float_threshold","ScheduleOptions","CriticalActivityFloatThreshold","Critical Activity Float Threshold","duration",True,False,"working-time"),
    ("schedule_options.critical_activity_path_type","ScheduleOptions","CriticalActivityPathType","Critical Activity Path Type","enum",True,False,None),
    ("schedule_options.external_project_priority_limit","ScheduleOptions","ExternalProjectPriorityLimit","External Project Priority Limit","integer",True,False,None),
    ("schedule_options.ignore_other_project_relationships","ScheduleOptions","IgnoreOtherProjectRelationships","Ignore Other Project Relationships","boolean",True,False,None),
    ("schedule_options.include_external_res_ass","ScheduleOptions","IncludeExternalResAss","Include External Resource Assignments","boolean",True,False,None),
    ("schedule_options.last_update_date","ScheduleOptions","LastUpdateDate","Last Update Date","datetime",False,False,None),
    ("schedule_options.last_update_user","ScheduleOptions","LastUpdateUser","Last Update User","string",False,False,None),
    ("schedule_options.level_all_resources","ScheduleOptions","LevelAllResources","Level All Resources","boolean",True,False,None),
    ("schedule_options.level_within_float","ScheduleOptions","LevelWithinFloat","Level Within Float","boolean",True,False,None),
    ("schedule_options.make_open_ended_activities_critical","ScheduleOptions","MakeOpenEndedActivitiesCritical","Make Open-Ended Activities Critical","boolean",True,False,None),
    ("schedule_options.maximum_multiple_float_paths","ScheduleOptions","MaximumMultipleFloatPaths","Maximum Multiple Float Paths","integer",True,False,None),
    ("schedule_options.min_float_to_preserve","ScheduleOptions","MinFloatToPreserve","Minimum Float to Preserve","integer",True,False,None),
    ("schedule_options.multiple_float_paths_enabled","ScheduleOptions","MultipleFloatPathsEnabled","Multiple Float Paths Enabled","boolean",True,False,None),
    ("schedule_options.multiple_float_paths_ending_activity_object_id","ScheduleOptions","MultipleFloatPathsEndingActivityObjectId","Multiple Float Paths Ending Activity","object-id",True,False,None),
    ("schedule_options.multiple_float_paths_ending_activity_short_name","ScheduleOptions","MultipleFloatPathsEndingActivityShortName","Multiple Float Paths Ending Activity Short Name","string",True,False,None),
    ("schedule_options.multiple_float_paths_use_total_float","ScheduleOptions","MultipleFloatPathsUseTotalFloat","Multiple Float Paths Use Total Float","boolean",True,False,None),
    ("schedule_options.out_of_sequence_schedule_type","ScheduleOptions","OutOfSequenceScheduleType","Out of Sequence Schedule Type","enum",True,False,None),
    ("schedule_options.over_allocation_percentage","ScheduleOptions","OverAllocationPercentage","Over Allocation Percentage","double",True,False,"percent"),
    ("schedule_options.preserve_scheduled_early_and_late_dates","ScheduleOptions","PreserveScheduledEarlyAndLateDates","Preserve Scheduled Early and Late Dates","boolean",True,False,None),
    ("schedule_options.priority_list","ScheduleOptions","PriorityList","Priority List","string-array",True,False,None),
    ("schedule_options.project_id","ScheduleOptions","ProjectId","Project ID","string",False,False,None),
    ("schedule_options.project_object_id","ScheduleOptions","ProjectObjectId","Project Object ID","object-id",False,False,None),
    ("schedule_options.relationship_lag_calendar","ScheduleOptions","RelationshipLagCalendar","Relationship Lag Calendar","enum",True,False,None),
    ("schedule_options.resource_list","ScheduleOptions","ResourceList","Resource List","string-array",True,False,None),
    ("schedule_options.start_to_start_lag_calculation_type","ScheduleOptions","StartToStartLagCalculationType","Start-to-Start Lag Calculation Type","boolean",True,False,None),
    ("schedule_options.use_expected_finish_dates","ScheduleOptions","UseExpectedFinishDates","Use Expected Finish Dates","boolean",True,False,None),
    ("schedule_options.user_name","ScheduleOptions","UserName","User Name","string",False,False,None),
    ("schedule_options.user_object_id","ScheduleOptions","UserObjectId","User Object ID","object-id",False,False,None),
)


P6_FIELD_CATALOG: tuple[P6FieldDefinition, ...] = tuple(
    P6FieldDefinition(
        field_id=field_id,
        subject_area=subject_area,
        p6_field=p6_field,
        display_name=display_name,
        data_type=P6FieldType(data_type),
        writable=writable,
        computed=computed,
        unit=unit,
    )
    for field_id, subject_area, p6_field, display_name, data_type, writable, computed, unit in _ROWS
)


def field_catalog() -> tuple[P6FieldDefinition, ...]:
    return P6_FIELD_CATALOG


def fields_by_subject(subject_area: str) -> tuple[P6FieldDefinition, ...]:
    return tuple(field for field in P6_FIELD_CATALOG if field.subject_area == subject_area)


def get_field(field_id: str) -> P6FieldDefinition:
    for field in P6_FIELD_CATALOG:
        if field.field_id == field_id:
            return field
    raise KeyError(field_id)


def validate_catalog() -> None:
    ids = [field.field_id for field in P6_FIELD_CATALOG]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate field_id in P6 field registry")

    keys = [(field.subject_area, field.p6_field) for field in P6_FIELD_CATALOG]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate P6 field within subject area")

    required = {
        "Activity", "WBS", "Project", "Resource/Assignment",
        "Activity Step", "Expense", "Codes", "Baseline", "Financial Period", "ScheduleOptions",
    }
    actual = {field.subject_area for field in P6_FIELD_CATALOG}
    missing = required.difference(actual)
    if missing:
        raise ValueError(f"missing subject areas: {sorted(missing)}")


validate_catalog()
