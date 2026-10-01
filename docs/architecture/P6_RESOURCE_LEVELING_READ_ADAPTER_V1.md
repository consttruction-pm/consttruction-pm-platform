# P6 Resource Leveling Read Adapter v1

## Purpose

The backend/application adapter bridges the authoritative p6-resource-read-api.v1 data into the existing Shared Core SchedulerLevelingInput boundary.

## Sources

- Resource assignments and time-phased assignment values are read only through P6ResourceReadAPI.
- Resource capacity is obtained through p6_resource_capacity_contract.py, using assignment calendar_id and ResourceCalendar.capacity_on(period).
- ResourceSpreadBucket is not interpreted as capacity.

## Mapping

- resource_assignment_period.period_start -> ResourceDemand.period.
- resource_assignment_period.units -> ResourceDemand.units without numeric conversion.
- resource_assignment_period.activity_id -> ResourceDemand.activity_id.
- resource_assignment_period.resource_id -> ResourceDemand.resource_id.
- capacity slices -> existing Shared Core ResourceCapacity.
- caller-provided LevelingActivity metadata (dates and float) remains untouched; the adapter does not calculate it.

## Scope and authorization

The requested BackendScope and authorization context are passed through the existing read API. Tenant/project authorization therefore remains owned by the existing API boundary, while project_revision is preserved in BackendScope. Decimal values are preserved end-to-end.

## Non-goals

No CPM, calendar, duration, float, leveling, resource spread, or cost calculation is performed. No new persistence table or resource model is introduced.

## Verification

Focused tests cover typed demand/capacity mapping, Decimal preservation, deterministic ordering, and authorization boundary behavior.
