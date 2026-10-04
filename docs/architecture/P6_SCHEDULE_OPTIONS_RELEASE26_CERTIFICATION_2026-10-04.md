# P6 Schedule Options Release 26 — Certification Audit

Date: 2026-10-04

## Scope

Audit the current Shared-Core `ScheduleOptions` contract against Oracle Primavera P6 EPPM Release 26 / 26.4. This record documents implementation boundaries and does not create a second scheduling engine.

## Oracle Release 26 ScheduleOptions surface

CalculateFloatBasedOnFinishDate; ComputeTotalFloatType; CreateDate; CreateUser; CriticalActivityFloatThreshold; CriticalActivityPathType; ExternalProjectPriorityLimit; IgnoreOtherProjectRelationships; IncludeExternalResAss; LastUpdateDate; LastUpdateUser; LevelAllResources; LevelWithinFloat; MakeOpenEndedActivitiesCritical; MaximumMultipleFloatPaths; MinFloatToPreserve; MultipleFloatPathsEnabled; MultipleFloatPathsEndingActivityObjectId; MultipleFloatPathsEndingActivityShortName; MultipleFloatPathsUseTotalFloat; OutOfSequenceScheduleType; OverAllocationPercentage; PreserveScheduledEarlyAndLateDates; PriorityList; ProjectId; ProjectObjectId; RelationshipLagCalendar; ResourceList; StartToStartLagCalculationType; UseExpectedFinishDates; UserName; UserObjectId.

Oracle sources:
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-scheduleoptions-get.html
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-scheduleoptions-put.html
- https://docs.oracle.com/cd/G48897_01/English/Integration_Documentation/p6_eppm_api_reference/com/primavera/integration/client/bo/object/ScheduleOptions.html

## Current Shared-Core disposition

### Normal scheduler path

The typed Shared-Core `ScheduleOptions` values already consumed by the normal date-based scheduler are:

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

### Authoritative resource-leveling delegation

These controls are represented by the typed `ScheduleOptions` surface and mapped through the existing Shared-Core `SchedulerLevelingInput` / `ResourceLevelingOptions` seam:

- LevelAllResources
- LevelWithinFloat
- MinFloatToPreserve
- OverAllocationPercentage
- ResourceList
- PriorityList
- PreserveScheduledEarlyAndLateDates

The evaluator routes leveling requests to the existing leveling seam, then returns through the normal CPM scheduler for final dates and float. No competing scheduler is created.

### Fail-closed controls

Plain `schedule()` intentionally rejects capability-dependent options when the required authoritative seam is not supplied:

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

This behavior prevents silent omission or accidental semantic substitution.

### Record metadata

CreateDate, CreateUser, LastUpdateDate, LastUpdateUser, ProjectId, ProjectObjectId, UserName and UserObjectId are record/user/project metadata rather than scheduling calculations. Their persistence/API certification remains a separate backend concern.

## Product/core orchestration fields

The current Shared-Core model also includes `mode`, `data_date`, and `recalculate_resource_costs`. These should not be claimed as exact Oracle Release 26 field mappings solely by name similarity.

## Certification boundary

Oracle schema/API evidence does not certify internal persistence, interchange, or UI behavior. Those require project-side mapping and regression evidence.

No client may implement an alternate interpretation of ScheduleOptions semantics.

## Current finding

The major P6 scheduling option controls are typed and connected to authoritative Shared-Core behavior; resource leveling has a dedicated delegation boundary; unsupported capability-dependent controls fail closed. Remaining work is capability-specific implementation/certification, not another ScheduleOptions model.
