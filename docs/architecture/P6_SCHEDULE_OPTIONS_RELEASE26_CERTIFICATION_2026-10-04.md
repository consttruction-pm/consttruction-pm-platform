# P6 Schedule Options Release 26 — Certification Audit

Date: 2026-10-04

## Purpose

Audit the current Shared-Core `ScheduleOptions` surface against Oracle Primavera P6 EPPM Release 26 and Release 26.4 ScheduleOptions contracts. This is a boundary/certification record, not a second scheduler.

## Oracle Release 26 ScheduleOptions properties

CalculateFloatBasedOnFinishDate; ComputeTotalFloatType; CreateDate; CreateUser; CriticalActivityFloatThreshold; CriticalActivityPathType; ExternalProjectPriorityLimit; IgnoreOtherProjectRelationships; IncludeExternalResAss; LastUpdateDate; LastUpdateUser; LevelAllResources; LevelWithinFloat; MakeOpenEndedActivitiesCritical; MaximumMultipleFloatPaths; MinFloatToPreserve; MultipleFloatPathsEnabled; MultipleFloatPathsEndingActivityObjectId; MultipleFloatPathsEndingActivityShortName; MultipleFloatPathsUseTotalFloat; OutOfSequenceScheduleType; OverAllocationPercentage; PreserveScheduledEarlyAndLateDates; PriorityList; ProjectId; ProjectObjectId; RelationshipLagCalendar; ResourceList; StartToStartLagCalculationType; UseExpectedFinishDates; UserName; UserObjectId.

Oracle documents the scheduling semantics for total-float calculation, critical path type, multiple float paths, out-of-sequence logic, relationship-lag calendar, start-to-start lag handling, and expected-finish handling.

Sources:
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-scheduleoptions-get.html
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-scheduleoptions-put.html
- https://docs.oracle.com/cd/G48897_01/English/Integration_Documentation/p6_eppm_api_reference/com/primavera/integration/client/bo/object/ScheduleOptions.html

## Current Shared-Core disposition

### Directly typed and consumed by normal scheduling

The current `ScheduleOptions` and scheduler consume:
- CalculateFloatBasedOnFinishDate
- ComputeTotalFloatType
- CriticalActivityFloatThreshold
- CriticalActivityPathType
- MakeOpenEndedActivitiesCritical
- MultipleFloatPathsEnabled
- MaximumMultipleFloatPaths
- MultipleFloatPathsEndingActivityObjectId
- MultipleFloatPathsUseTotalFloat
- OutOfSequenceScheduleType
- RelationshipLagCalendar
- StartToStartLagCalculationType
- UseExpectedFinishDates

### Resource-leveling options routed through the authoritative seam

The following are typed and mapped into the existing Shared-Core `SchedulerLevelingInput` / `ResourceLevelingOptions` boundary:
- LevelAllResources
- LevelWithinFloat
- MinFloatToPreserve
- OverAllocationPercentage
- ResourceList
- PriorityList
- PreserveScheduledEarlyAndLateDates

The evaluator selects the dedicated resource-leveling path when these controls request leveling. That path reuses the normal CPM scheduler for final dates/float and does not create a competing scheduling engine.

### Fail-closed options

Plain `schedule()` intentionally rejects these when the corresponding capability is requested without the authoritative seam:
- RecalculateResourceCosts
- IgnoreOtherProjectRelationships
- IncludeExternalResAss
- non-zero OverAllocationPercentage
- ResourceList
- PriorityList
- non-zero MinFloatToPreserve
- non-zero ExternalProjectPriorityLimit
- PreserveScheduledEarlyAndLateDates
- MultipleFloatPathsEndingActivityShortName

This is fail-closed behavior: the option is not silently ignored or replaced by another semantic.

### ScheduleOptions record metadata

CreateDate, CreateUser, LastUpdateDate, LastUpdateUser, ProjectId, ProjectObjectId, UserName and UserObjectId are record/user/project metadata, not Shared-Core calculation controls. Their persistence/API certification is a separate backend responsibility.

## Product/core orchestration fields

The current Shared-Core options also contain `mode`, `data_date`, and `recalculate_resource_costs`. These must not be presented as exact Oracle Release 26 field mappings solely from name similarity. In particular, `recalculate_resource_costs` is not present in the current Release 26 REST ScheduleOptions property list reviewed here.

## Certification boundary

Oracle schema/API evidence does not by itself certify internal persistence, interchange, or client behavior. Those require separate internal evidence and regression tests.

No client may implement competing ScheduleOptions calculation rules.

## Current finding

The project already has a typed P6 ScheduleOptions surface and an authoritative resource-leveling delegation seam. The remaining work is capability-by-capability certification/implementation for the fail-closed options, not another ScheduleOptions model.
