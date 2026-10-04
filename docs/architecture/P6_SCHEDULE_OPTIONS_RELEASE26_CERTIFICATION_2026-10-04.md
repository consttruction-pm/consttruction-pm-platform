# P6 Schedule Options Release 26 — Certification Audit

Date: 2026-10-04

## Purpose

Audit the current Shared-Core `ScheduleOptions` surface against the Oracle Primavera P6 EPPM Release 26 ScheduleOptions contract and the Release 26.4 Integration API. This document records implementation boundaries; it does not invent a second scheduler.

## Oracle Release 26 configuration fields

Oracle Release 26 exposes these ScheduleOptions properties through the REST read contract:

- CalculateFloatBasedOnFinishDate
- ComputeTotalFloatType
- CreateDate
- CreateUser
- CriticalActivityFloatThreshold
- CriticalActivityPathType
- ExternalProjectPriorityLimit
- IgnoreOtherProjectRelationships
- IncludeExternalResAss
- LastUpdateDate
- LastUpdateUser
- LevelAllResources
- LevelWithinFloat
- MakeOpenEndedActivitiesCritical
- MaximumMultipleFloatPaths
- MinFloatToPreserve
- MultipleFloatPathsEnabled
- MultipleFloatPathsEndingActivityObjectId
- MultipleFloatPathsEndingActivityShortName
- MultipleFloatPathsUseTotalFloat
- OutOfSequenceScheduleType
- OverAllocationPercentage
- PreserveScheduledEarlyAndLateDates
- PriorityList
- ProjectId
- ProjectObjectId
- RelationshipLagCalendar
- ResourceList
- StartToStartLagCalculationType
- UseExpectedFinishDates
- UserName
- UserObjectId

Oracle documents the meanings of the criticality, multiple-float-path, out-of-sequence, relationship-lag-calendar, start-to-start lag, and expected-finish options in the current Release 26 REST contract.

Sources:
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-scheduleoptions-get.html
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-scheduleoptions-put.html
- https://docs.oracle.com/cd/G48897_01/English/Integration_Documentation/p6_eppm_api_reference/com/primavera/integration/client/bo/object/ScheduleOptions.html

## Current Shared-Core disposition

### Directly typed and wired through the normal scheduler

These options are represented in `ScheduleOptions` and consumed by the normal date-based scheduler:

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
- CalculateFloatBasedOnFinishDate

The multiple-float-path calculation is performed in Shared Core rather than in a client or backend adapter.

### Directly typed, with authoritative resource-leveling delegation

The following options are represented by the public typed `ScheduleOptions` surface and mapped into the existing `SchedulerLevelingInput` / `ResourceLevelingOptions` seam:

- LevelAllResources
- LevelWithinFloat
- MinFloatToPreserve
- OverAllocationPercentage
- ResourceList
- PriorityList
- PreserveScheduledEarlyAndLateDates

The evaluator detects a resource-leveling request and routes it to `schedule_with_resource_leveling`. That path strips only the leveling controls before invoking the normal CPM scheduler, then converts leveling movement into scheduler constraints and recalculates the authoritative early/late/float results. This preserves one calculation authority.

### Typed boundary fields intentionally rejected by plain scheduling

The plain `schedule()` entry point raises `UnsupportedScheduleOptionError` when these options are enabled without the dedicated capability seam:

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

This is intentional fail-closed behavior. These fields are not silently ignored or silently substituted with another calculation.

For resource-leveling fields, the authoritative evaluator provides the supported delegated path. For the remaining fields, a future capability must be implemented before direct scheduling may accept them.

### Read-only / persistence metadata

The Oracle contract also exposes:

- CreateDate
- CreateUser
- LastUpdateDate
- LastUpdateUser
- ProjectId
- ProjectObjectId
- UserName
- UserObjectId

These identify the ScheduleOptions record/user/project context and are not treated as mutable Shared-Core scheduling controls. Their persistence/API handling remains a separate backend certification concern.

## Product-specific / shared-core fields

The current Shared-Core `ScheduleOptions` also contains:

- mode
- data_date
- recalculate_resource_costs

These are product/core orchestration concepts and must not be represented as Oracle fields solely by name similarity. `recalculate_resource_costs` corresponds to a historical P6 scheduling capability but is not present in the current Release 26 REST ScheduleOptions property list reviewed for this audit.

## Important compatibility rule

A typed option existing in the model does not equal implementation certification. Certification requires:

1. Oracle field/type/mutability evidence;
2. Shared-Core calculation behavior or an explicit authoritative delegated seam;
3. persistence/API mapping where externally stored;
4. deterministic regression coverage.

No client may implement a competing interpretation of any ScheduleOptions calculation.

## Current findings

- The core P6 scheduling controls above are already represented in Shared Core.
- Resource-leveling has an explicit shared scheduling seam rather than a duplicate engine.
- Unsupported options fail closed instead of being ignored.
- Several P6 ScheduleOptions record metadata fields are intentionally separate from scheduling calculation controls.
- The current audit does not certify persistence/import/export parity for every ScheduleOptions field.

## Exit condition

The next implementation work should target only options that have a clearly defined authoritative calculation/capability seam and a reproducible regression scenario. No blanket enabling of currently unsupported options is permitted.
