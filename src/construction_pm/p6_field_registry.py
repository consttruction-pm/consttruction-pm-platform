from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


P6_FIELD_REGISTRY_REFERENCE_PRODUCT = "Oracle P6 Version 26 / 26.4"
P6_FIELD_REGISTRY_REFERENCE_VERSION = "26.4"
P6_FIELD_REGISTRY_STATUS = "seeded_not_certified"


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
    ("activity.accounting_variance","Activity","AccountingVariance","Accounting Variance","double",False,True,None),
    ("activity.accounting_variance_labor_units","Activity","AccountingVarianceLaborUnits","Accounting Variance Labor Units","double",False,True,None),
    ("activity.at_completion_duration","Activity","AtCompletionDuration","At Completion Duration","double",False,True,"working-time"),
    ("activity.at_completion_variance","Activity","AtCompletionVariance","At Completion Variance","double",False,True,"currency"),
    ("activity.duration2_variance","Activity","Duration2Variance","Duration 2 Variance","double",False,True,"working-time"),
    ("activity.duration3_variance","Activity","Duration3Variance","Duration 3 Variance","double",False,True,"working-time"),
    ("activity.duration_percent_of_planned","Activity","DurationPercentOfPlanned","Duration % of Planned","double",False,True,"percent"),
    ("activity.earned_value_cost","Activity","EarnedValueCost","Earned Value Cost","double",False,True,"currency"),
    ("activity.expense_cost1_variance","Activity","ExpenseCost1Variance","Expense Cost 1 Variance","double",False,True,"currency"),
    ("activity.expense_cost2_variance","Activity","ExpenseCost2Variance","Expense Cost 2 Variance","double",False,True,"currency"),
    ("activity.expense_cost3_variance","Activity","ExpenseCost3Variance","Expense Cost 3 Variance","double",False,True,"currency"),
    ("activity.expense_cost_percent_complete","Activity","ExpenseCostPercentComplete","Expense Cost % Complete","double",False,True,"percent"),
    ("activity.expense_cost_variance","Activity","ExpenseCostVariance","Expense Cost Variance","double",False,True,"currency"),
    ("activity.cost_percent_complete","Activity","CostPercentComplete","Cost % Complete","double",False,True,"percent"),
    ("activity.cost_percent_of_planned","Activity","CostPercentOfPlanned","Cost % of Planned","double",False,True,"percent"),
    ("activity.cost_performance_index","Activity","CostPerformanceIndex","Cost Performance Index","double",False,True,None),
    ("activity.duration_variance","Activity","DurationVariance","Duration Variance","double",False,True,"working-time"),
    ("activity.activity_name","Activity","ActivityName","Activity Name","string",True,False,None),
    ("activity.activity_status","Activity","ActivityStatus","Activity Status","enum",True,False,None),
    ("activity.activity_type","Activity","ActivityType","Activity Type","enum",True,False,None),
    ("activity.status_code","Activity","StatusCode","Status Code","enum",False,False,None),
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
    ("activity.duration1_variance","Activity","Duration1Variance","Duration 1 Variance","double",False,True,"working-time"),
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
    ("schedule_options.recalculate_resource_costs","ScheduleOptions","RecalculateResourceCosts","Recalculate Resource Costs","boolean",True,False,None),
    ("schedule_options.user_name","ScheduleOptions","UserName","User Name","string",False,False,None),
    ("schedule_options.user_object_id","ScheduleOptions","UserObjectId","User Object ID","object-id",False,False,None),

    ("activity.activity_owner_user_id","Activity","ActivityOwnerUserId","Activity Owner User Id","integer",True,False,None),
    ("activity.actual_expense_cost","Activity","ActualExpenseCost","Actual Expense Cost","double",False,True,None),
    ("activity.actual_material_cost","Activity","ActualMaterialCost","Actual Material Cost","double",False,True,None),
    ("activity.actual_non_labor_cost","Activity","ActualNonLaborCost","Actual Non Labor Cost","double",False,True,None),
    ("activity.actual_non_labor_units","Activity","ActualNonLaborUnits","Actual Non Labor Units","double",False,True,None),
    ("activity.actual_this_period_labor_cost","Activity","ActualThisPeriodLaborCost","Actual This Period Labor Cost","double",False,True,None),
    ("activity.actual_this_period_labor_units","Activity","ActualThisPeriodLaborUnits","Actual This Period Labor Units","double",False,True,None),
    ("activity.actual_this_period_material_cost","Activity","ActualThisPeriodMaterialCost","Actual This Period Material Cost","double",False,True,None),
    ("activity.actual_this_period_non_labor_cost","Activity","ActualThisPeriodNonLaborCost","Actual This Period Non Labor Cost","double",False,True,None),
    ("activity.actual_this_period_non_labor_units","Activity","ActualThisPeriodNonLaborUnits","Actual This Period Non Labor Units","double",False,True,None),
    ("activity.actual_total_cost","Activity","ActualTotalCost","Actual Total Cost","double",False,True,None),
    ("activity.actual_total_units","Activity","ActualTotalUnits","Actual Total Units","double",False,True,None),
    ("activity.at_completion_total_cost","Activity","AtCompletionTotalCost","At Completion Total Cost","double",False,True,None),
    ("activity.at_completion_total_units","Activity","AtCompletionTotalUnits","At Completion Total Units","double",False,True,None),
    ("activity.auto_compute_actuals","Activity","AutoComputeActuals","Auto Compute Actuals","boolean",True,False,None),
    ("activity.baseline1_duration","Activity","Baseline1Duration","Baseline1 Duration","double",False,True,None),
    ("activity.baseline1_finish_date","Activity","Baseline1FinishDate","Baseline1 Finish Date","date",False,True,None),
    ("activity.baseline1_planned_duration","Activity","Baseline1PlannedDuration","Baseline1 Planned Duration","double",False,True,None),
    ("activity.baseline1_planned_expense_cost","Activity","Baseline1PlannedExpenseCost","Baseline1 Planned Expense Cost","double",False,True,None),
    ("activity.baseline1_planned_labor_cost","Activity","Baseline1PlannedLaborCost","Baseline1 Planned Labor Cost","double",False,True,None),
    ("activity.baseline1_planned_material_cost","Activity","Baseline1PlannedMaterialCost","Baseline1 Planned Material Cost","double",False,True,"currency"),
    ("activity.baseline1_planned_non_labor_cost","Activity","Baseline1PlannedNonLaborCost","Baseline1 Planned Non Labor Cost","double",False,True,"currency"),
    ("activity.baseline1_planned_non_labor_units","Activity","Baseline1PlannedNonLaborUnits","Baseline1 Planned Non Labor Units","double",False,True,"units"),
    ("activity.baseline1_planned_total_cost","Activity","Baseline1PlannedTotalCost","Baseline1 Planned Total Cost","double",False,True,"currency"),
    ("activity.baseline1_start_date","Activity","Baseline1StartDate","Baseline1 Start Date","date",False,True,None),
    ("activity.baseline2_duration","Activity","Baseline2Duration","Baseline2 Duration","double",False,True,"working-time"),
    ("activity.baseline2_finish_date","Activity","Baseline2FinishDate","Baseline2 Finish Date","date",False,True,None),
    ("activity.baseline2_planned_duration","Activity","Baseline2PlannedDuration","Baseline2 Planned Duration","double",False,True,"working-time"),
    ("activity.baseline2_planned_expense_cost","Activity","Baseline2PlannedExpenseCost","Baseline2 Planned Expense Cost","double",False,True,"currency"),
    ("activity.baseline2_planned_labor_cost","Activity","Baseline2PlannedLaborCost","Baseline2 Planned Labor Cost","double",False,True,"currency"),
    ("activity.baseline2_planned_labor_units","Activity","Baseline2PlannedLaborUnits","Baseline2 Planned Labor Units","double",False,True,"units"),
    ("activity.baseline2_planned_material_cost","Activity","Baseline2PlannedMaterialCost","Baseline2 Planned Material Cost","double",False,True,"currency"),
    ("activity.baseline2_planned_non_labor_cost","Activity","Baseline2PlannedNonLaborCost","Baseline2 Planned Non Labor Cost","double",False,True,"currency"),
    ("activity.baseline2_planned_non_labor_units","Activity","Baseline2PlannedNonLaborUnits","Baseline2 Planned Non Labor Units","double",False,True,"units"),
    ("activity.baseline2_planned_total_cost","Activity","Baseline2PlannedTotalCost","Baseline2 Planned Total Cost","double",False,True,"currency"),
    ("activity.baseline2_start_date","Activity","Baseline2StartDate","Baseline2 Start Date","date",False,True,None),
    ("activity.baseline3_duration","Activity","Baseline3Duration","Baseline3 Duration","double",False,True,"working-time"),
    ("activity.baseline3_finish_date","Activity","Baseline3FinishDate","Baseline3 Finish Date","date",False,True,None),
    ("activity.baseline3_planned_duration","Activity","Baseline3PlannedDuration","Baseline3 Planned Duration","double",False,True,"working-time"),
    ("activity.baseline3_planned_expense_cost","Activity","Baseline3PlannedExpenseCost","Baseline3 Planned Expense Cost","double",False,True,"currency"),
    ("activity.baseline3_planned_labor_cost","Activity","Baseline3PlannedLaborCost","Baseline3 Planned Labor Cost","double",False,True,"currency"),
    ("activity.baseline3_planned_labor_units","Activity","Baseline3PlannedLaborUnits","Baseline3 Planned Labor Units","double",False,True,"units"),
    ("activity.baseline3_planned_material_cost","Activity","Baseline3PlannedMaterialCost","Baseline3 Planned Material Cost","double",False,True,"currency"),
    ("activity.baseline3_planned_non_labor_cost","Activity","Baseline3PlannedNonLaborCost","Baseline3 Planned Non Labor Cost","double",False,True,"currency"),
    ("activity.baseline3_planned_non_labor_units","Activity","Baseline3PlannedNonLaborUnits","Baseline3 Planned Non Labor Units","double",False,True,"units"),
    ("activity.baseline3_planned_total_cost","Activity","Baseline3PlannedTotalCost","Baseline3 Planned Total Cost","double",False,True,"currency"),
    ("activity.baseline3_start_date","Activity","Baseline3StartDate","Baseline3 Start Date","datetime",False,True,None),
    ("activity.external_early_start_date","Activity","ExternalEarlyStartDate","External Early Start Date","date",False,True,None),
    ("activity.external_late_finish_date","Activity","ExternalLateFinishDate","External Late Finish Date","date",False,True,None),
    ("activity.feedback","Activity","Feedback","Feedback","string",True,False,None),
    ("activity.financial_period_tmpl_id","Activity","FinancialPeriodTmplId","Financial Period Tmpl Id","integer",False,False,None),
    ("activity.finish_date","Activity","FinishDate","Finish Date","date",False,True,None),
    ("activity.finish_date1_variance","Activity","FinishDate1Variance","Finish Date1 Variance","double",False,True,"working-time"),
    ("activity.finish_date2_variance","Activity","FinishDate2Variance","Finish Date2 Variance","double",False,True,"working-time"),
    ("activity.finish_date3_variance","Activity","FinishDate3Variance","Finish Date3 Variance","double",False,True,"working-time"),
    ("activity.finish_date_variance","Activity","FinishDateVariance","Finish Date Variance","double",False,True,"working-time"),
    ("activity.guid","Activity","GUID","GUID","string",False,False,None),
    ("activity.has_future_bucket_data","Activity","HasFutureBucketData","Has Future Bucket Data","boolean",False,False,None),
    ("activity.id","Activity","Id","Id","string",True,False,None),
    ("activity.is_baseline","Activity","IsBaseline","Is Baseline","boolean",False,False,None),
    ("activity.is_critical","Activity","IsCritical","Is Critical","boolean",False,True,None),
    ("activity.is_longest_path","Activity","IsLongestPath","Is Longest Path","boolean",False,True,None),
    ("activity.labor_cost1_variance","Activity","LaborCost1Variance","Labor Cost1 Variance","double",False,True,"currency"),
    ("activity.labor_cost2_variance","Activity","LaborCost2Variance","Labor Cost2 Variance","double",False,True,"currency"),
    ("activity.labor_cost3_variance","Activity","LaborCost3Variance","Labor Cost3 Variance","double",False,True,"currency"),
    ("activity.labor_cost_percent_complete","Activity","LaborCostPercentComplete","Labor Cost Percent Complete","double",False,True,"percent"),
    ("activity.labor_cost_variance","Activity","LaborCostVariance","Labor Cost Variance","double",False,True,"currency"),
    ("activity.labor_units1_variance","Activity","LaborUnits1Variance","Labor Units1 Variance","double",False,True,"units"),
    ("activity.labor_units2_variance","Activity","LaborUnits2Variance","Labor Units2 Variance","double",False,True,"units"),
    ("activity.labor_units3_variance","Activity","LaborUnits3Variance","Labor Units3 Variance","double",False,True,"units"),
    ("activity.labor_units_percent_complete","Activity","LaborUnitsPercentComplete","Labor Units Percent Complete","double",False,True,"percent"),
    ("activity.labor_units_variance","Activity","LaborUnitsVariance","Labor Units Variance","double",False,True,"units"),
    ("activity.leveling_priority","Activity","LevelingPriority","Leveling Priority","string",True,False,None),
    ("activity.location_name","Activity","LocationName","Location Name","string",True,False,None),
    ("activity.location_object_id","Activity","LocationObjectId","Location Object Id","integer",True,False,None),
    ("activity.material_cost1_variance","Activity","MaterialCost1Variance","Material Cost1 Variance","double",False,True,"currency"),
    ("activity.material_cost2_variance","Activity","MaterialCost2Variance","Material Cost2 Variance","double",False,True,"currency"),
    ("activity.material_cost3_variance","Activity","MaterialCost3Variance","Material Cost3 Variance","double",False,True,"currency"),
    ("activity.last_update_date","Activity","LastUpdateDate","Last Update Date","datetime",False,False,None),
    ("activity.last_update_user","Activity","LastUpdateUser","Last Update User","string",False,False,None),
    ("activity.material_cost_percent_complete","Activity","MaterialCostPercentComplete","Material Cost % Complete","double",False,True,"percent"),
    ("activity.maximum_duration","Activity","MaximumDuration","Maximum Duration","double",True,False,"working-time"),
    ("activity.minimum_duration","Activity","MinimumDuration","Minimum Duration","double",True,False,"working-time"),
    ("activity.most_likely_duration","Activity","MostLikelyDuration","Most Likely Duration","double",True,False,"working-time"),
    ("activity.name","Activity","Name","Name","string",True,False,None),
    ("activity.nonlabor_cost_percent_complete","Activity","NonLaborCostPercentComplete","Nonlabor Cost % Complete","double",False,True,"percent"),
    ("activity.nonlabor_cost_variance","Activity","NonLaborCostVariance","Nonlabor Cost Variance","double",False,True,"currency"),
    ("activity.nonlabor_units1_variance","Activity","NonLaborUnits1Variance","Nonlabor Units 1 Variance","double",False,True,"units"),
    ("activity.nonlabor_units2_variance","Activity","NonLaborUnits2Variance","Nonlabor Units 2 Variance","double",False,True,"units"),
    ("activity.nonlabor_units3_variance","Activity","NonLaborUnits3Variance","Nonlabor Units 3 Variance","double",False,True,"units"),
    ("activity.nonlabor_units_percent_complete","Activity","NonLaborUnitsPercentComplete","Nonlabor Units % Complete","double",False,True,"percent"),
    ("activity.nonlabor_units_variance","Activity","NonLaborUnitsVariance","Nonlabor Units Variance","double",False,True,"units"),
    ("activity.notes_to_resources","Activity","NotesToResources","Notes to Resources","string",True,False,None),
    ("activity.object_id","Activity","ObjectId","Object ID","object-id",False,False,None),
    ("activity.owner_id_array","Activity","OwnerIDArray","Owner ID Array","string",True,False,None),
    ("activity.review_finish_date","Activity","ReviewFinishDate","Review Finish Date","datetime",True,False,None),
    ("activity.review_required","Activity","ReviewRequired","Review Required","boolean",True,False,None),
    ("activity.review_status","Activity","ReviewStatus","Review Status","enum",True,False,None),
    ("activity.actual_labor_cost","Activity","ActualLaborCost","Actual Labor Cost","double",False,True,"currency"),
    ("activity.actual_labor_units","Activity","ActualLaborUnits","Actual Labor Units","double",False,True,"units"),
    ("activity.at_completion_labor_cost","Activity","AtCompletionLaborCost","At Completion Labor Cost","double",False,True,"currency"),
    ("activity.at_completion_labor_units","Activity","AtCompletionLaborUnits","At Completion Labor Units","double",False,True,"units"),
    ("activity.at_completion_material_cost","Activity","AtCompletionMaterialCost","At Completion Material Cost","double",False,True,"currency"),
    ("activity.at_completion_non_labor_cost","Activity","AtCompletionNonLaborCost","At Completion Non Labor Cost","double",False,True,"currency"),
    ("activity.at_completion_non_labor_units","Activity","AtCompletionNonLaborUnits","At Completion Non Labor Units","double",False,True,"units"),
    ("activity.budget_at_completion","Activity","BudgetAtCompletion","Budget At Completion","double",False,True,"currency"),
    ("activity.cbs_code","Activity","CBSCode","CBS Code","string",True,False,None),
    ("activity.cbs_object_id","Activity","CBSObjectId","CBS Object ID","integer",False,False,None),
    ("activity.cost_variance","Activity","CostVariance","Cost Variance","double",False,True,"currency"),
    ("activity.create_date","Activity","CreateDate","Create Date","datetime",False,False,None),
    ("activity.data_date","Activity","DataDate","Data Date","datetime",False,False,None),
    ("activity.earned_value_labor_units","Activity","EarnedValueLaborUnits","Earned Value Labor Units","double",False,True,"units"),
    ("activity.estimate_at_completion_cost","Activity","EstimateAtCompletionCost","Estimate At Completion Cost","double",False,True,"currency"),
    ("activity.material_cost_variance","Activity","MaterialCostVariance","Material Cost Variance","double",False,True,"currency"),
    ("activity.percent_complete","Activity","PercentComplete","Percent Complete","double",True,False,"percent"),
    ("activity.performance_percent_complete","Activity","PerformancePercentComplete","Performance Percent Complete","double",False,True,"percent"),
    ("activity.performance_percent_complete_by_labor_units","Activity","PerformancePercentCompleteByLaborUnits","Performance Percent Complete By Labor Units","percentage",False,True,"percent"),
    ("activity.planned_expense_cost","Activity","PlannedExpenseCost","Planned Expense Cost","cost",False,True,"currency"),
    ("activity.planned_total_cost","Activity","PlannedTotalCost","Planned Total Cost","cost",False,True,"currency"),
    ("activity.planned_total_units","Activity","PlannedTotalUnits","Planned Total Units","unit",False,True,"units"),
    ("activity.post_resp_criticality_index","Activity","PostRespCriticalityIndex","Post Resp Criticality Index","percentage",True,False,"percent"),
    ("activity.post_response_pessimistic_finish","Activity","PostResponsePessimisticFinish","Post Response Pessimistic Finish","date",True,False,None),
    ("activity.post_response_pessimistic_start","Activity","PostResponsePessimisticStart","Post Response Pessimistic Start","date",True,False,None),
    ("activity.pre_resp_criticality_index","Activity","PreRespCriticalityIndex","Pre Resp Criticality Index","percentage",True,False,"percent"),
    ("activity.pre_response_pessimistic_finish","Activity","PreResponsePessimisticFinish","Pre Response Pessimistic Finish","date",True,False,None),
    ("activity.pre_response_pessimistic_start","Activity","PreResponsePessimisticStart","Pre Response Pessimistic Start","date",True,False,None),
    ("activity.planned_labor_cost","Activity","PlannedLaborCost","Planned Labor Cost","double",False,True,"currency"),
    ("activity.planned_labor_units","Activity","PlannedLaborUnits","Planned Labor Units","double",False,True,"units"),
    ("activity.duration_type","Activity","DurationType","Duration Type","enum",True,False,None),
    ("activity.planned_material_cost","Activity","PlannedMaterialCost","Planned Material Cost","double",True,False,"currency"),
    ("activity.planned_non_labor_cost","Activity","PlannedNonLaborCost","Planned Non Labor Cost","double",True,False,"currency"),
    ("activity.planned_non_labor_units","Activity","PlannedNonLaborUnits","Planned Non Labor Units","double",True,False,"units"),
    ("activity.planned_value_cost","Activity","PlannedValueCost","Planned Value Cost","double",False,True,"currency"),
    ("activity.planned_value_labor_units","Activity","PlannedValueLaborUnits","Planned Value Labor Units","double",False,True,"units"),
    ("activity.remaining_early_start_date","Activity","RemainingEarlyStartDate","Remaining Early Start Date","datetime",True,False,None),
    ("activity.remaining_labor_cost","Activity","RemainingLaborCost","Remaining Labor Cost","double",True,False,"currency"),
    ("activity.remaining_labor_units","Activity","RemainingLaborUnits","Remaining Labor Units","double",True,False,"units"),
    ("activity.remaining_material_cost","Activity","RemainingMaterialCost","Remaining Material Cost","double",True,False,"currency"),
    ("activity.remaining_non_labor_cost","Activity","RemainingNonLaborCost","Remaining Non Labor Cost","double",True,False,"currency"),
    ("activity.remaining_non_labor_units","Activity","RemainingNonLaborUnits","Remaining Non Labor Units","double",True,False,"units"),
    ("activity.resume_date","Activity","ResumeDate","Resume Date","datetime",True,False,None),
    ("activity.schedule_performance_index","Activity","SchedulePerformanceIndex","Schedule Performance Index","double",False,True,None),
    ("activity.scope_percent_complete","Activity","ScopePercentComplete","Scope Percent Complete","double",False,True,"percent"),
    ("activity.start_date_variance","Activity","StartDateVariance","Start Date Variance","double",False,True,"working-time"),
    ("activity.status","Activity","Status","Status","string",False,True,None),
    ("activity.suspend_date","Activity","SuspendDate","Suspend Date","datetime",True,False,None),
    ("activity.total_past_period_labor_cost","Activity","TotalPastPeriodLaborCost","Total Past Period Labor Cost","double",False,False,"currency"),
    ("activity.total_past_period_labor_units","Activity","TotalPastPeriodLaborUnits","Total Past Period Labor Units","double",False,False,"units"),
    ("activity.total_past_period_material_cost","Activity","TotalPastPeriodMaterialCost","Total Past Period Material Cost","double",False,False,"currency"),
    ("activity.total_past_period_non_labor_cost","Activity","TotalPastPeriodNonLaborCost","Total Past Period Non Labor Cost","double",False,False,"currency"),
    ("activity.total_past_period_non_labor_units","Activity","TotalPastPeriodNonLaborUnits","Total Past Period Non Labor Units","double",False,False,"units"),
    ("activity.type","Activity","Type","Type","string",True,False,None),
    ("activity.units_percent_complete","Activity","UnitsPercentComplete","Units Percent Complete","double",False,True,"percent"),
    ("activity.work_package_name","Activity","WorkPackageName","Work Package Name","string",True,False,None),
    ("activity.at_completion_expense_cost","Activity","AtCompletionExpenseCost","At Completion Expense Cost","double",False,True,"currency"),
    ("activity.at_completion_labor_units_variance","Activity","AtCompletionLaborUnitsVariance","At Completion Labor Units Variance","double",False,True,"units"),
    ("activity.baseline1_planned_labor_units","Activity","Baseline1PlannedLaborUnits","Baseline 1 Planned Labor Units","double",False,False,"units"),
    ("activity.baseline_planned_duration","Activity","BaselinePlannedDuration","Baseline Planned Duration","double",False,False,"working-time"),
    ("activity.baseline_planned_expense_cost","Activity","BaselinePlannedExpenseCost","Baseline Planned Expense Cost","double",False,False,"currency"),
    ("activity.baseline_planned_labor_cost","Activity","BaselinePlannedLaborCost","Baseline Planned Labor Cost","double",False,False,"currency"),
    ("activity.baseline_planned_labor_units","Activity","BaselinePlannedLaborUnits","Baseline Planned Labor Units","double",False,False,"units"),
    ("activity.baseline_planned_material_cost","Activity","BaselinePlannedMaterialCost","Baseline Planned Material Cost","double",False,False,"currency"),
    ("activity.baseline_planned_non_labor_cost","Activity","BaselinePlannedNonLaborCost","Baseline Planned Non Labor Cost","double",False,False,"currency"),
    ("activity.baseline_planned_non_labor_units","Activity","BaselinePlannedNonLaborUnits","Baseline Planned Non Labor Units","double",False,False,"units"),
    ("activity.baseline_planned_total_cost","Activity","BaselinePlannedTotalCost","Baseline Planned Total Cost","double",False,False,"currency"),
    ("activity.cbs_id","Activity","CBSId","CBS ID","integer",False,False,None),
    ("activity.calendar_name","Activity","CalendarName","Calendar Name","string",False,False,None),
    ("activity.calendar_object_id","Activity","CalendarObjectId","Calendar Object ID","integer",False,False,None),
    ("activity.cost_performance_index_labor_units","Activity","CostPerformanceIndexLaborUnits","Cost Performance Index Labor Units","double",False,True,None),
    ("activity.cost_variance_index","Activity","CostVarianceIndex","Cost Variance Index","double",False,True,None),
    ("activity.cost_variance_index_labor_units","Activity","CostVarianceIndexLaborUnits","Cost Variance Index Labor Units","double",False,True,None),
    ("activity.cost_variance_labor_units","Activity","CostVarianceLaborUnits","Cost Variance Labor Units","double",False,True,"units"),
    ("activity.estimate_at_completion_labor_units","Activity","EstimateAtCompletionLaborUnits","Estimate At Completion Labor Units","double",False,True,"units"),
    ("activity.estimate_to_complete","Activity","EstimateToComplete","Estimate To Complete","double",False,True,"currency"),
    ("activity.estimate_to_complete_labor_units","Activity","EstimateToCompleteLaborUnits","Estimate To Complete Labor Units","unit",False,True,"units"),
    ("activity.estimated_weight","Activity","EstimatedWeight","Estimated Weight","double",True,False,None),
    ("activity.is_new_feedback","Activity","IsNewFeedback","Is New Feedback","boolean",True,False,None),
    ("activity.is_starred","Activity","IsStarred","Is Starred","boolean",True,False,None),
    ("activity.is_template","Activity","IsTemplate","Is Template","boolean",False,False,None),
    ("activity.is_work_package","Activity","IsWorkPackage","Is Work Package","boolean",False,False,None),
    ("activity.nonlabor_cost1_variance","Activity","NonLaborCost1Variance","Nonlabor Cost 1 Variance","cost",False,True,"currency"),
    ("activity.nonlabor_cost2_variance","Activity","NonLaborCost2Variance","Nonlabor Cost 2 Variance","cost",False,True,"currency"),
    ("activity.nonlabor_cost3_variance","Activity","NonLaborCost3Variance","Nonlabor Cost 3 Variance","cost",False,True,"currency"),
    ("activity.owner_names_array","Activity","OwnerNamesArray","Owner Names Array","string",True,False,None),
)


P6_ACTIVITY_ALIAS_RESOLUTIONS: dict[str, str] = {
    "activity.activity_id": "activity.id",
    "activity.activity_name": "activity.name",
    "activity.activity_status": "activity.status",
    "activity.activity_type": "activity.type",
    "activity.updated_by": "activity.last_update_user",
}


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


def canonical_activity_field_id(field_id: str) -> str:
    return P6_ACTIVITY_ALIAS_RESOLUTIONS.get(field_id, field_id)


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

    by_id = {field.field_id: field for field in P6_FIELD_CATALOG}
    for alias_id, target_id in P6_ACTIVITY_ALIAS_RESOLUTIONS.items():
        alias = by_id.get(alias_id)
        target = by_id.get(target_id)
        if alias is None:
            raise ValueError(f"activity alias source does not exist: {alias_id}")
        if target is None:
            raise ValueError(f"activity alias target does not exist: {alias_id} -> {target_id}")
        if alias.subject_area != "Activity" or target.subject_area != "Activity":
            raise ValueError(f"activity alias must remain within Activity: {alias_id} -> {target_id}")
        if target_id in P6_ACTIVITY_ALIAS_RESOLUTIONS:
            raise ValueError(f"activity alias cannot target another alias: {alias_id} -> {target_id}")


validate_catalog()