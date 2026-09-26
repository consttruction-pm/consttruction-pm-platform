# Stage 34.2.5 — Field Operations Core

Status: implementation in progress.

## Scope

First production P0 field workflows for personnel attendance/timecards and equipment status/breakdown.

## Acceptance criteria

- Attendance/timecard records are tenant/project/revision/audit scoped.
- A timecard identifies person, date and workplace.
- Time may be represented with timezone-aware start/end timestamps.
- Recorded time can be split across multiple activities with exact Decimal quantities.
- Equipment reports identify equipment, date, workplace and operational status.
- A broken equipment report requires an explicit breakdown cause.
- Equipment usage may be split across multiple activities and carries optional meter hours.
- Existing Field Daily Log and Field Issue behavior remains unchanged.
- Web/Desktop/Mobile consume versioned contracts; calculations remain in Shared Core.
- Runtime contract/unit/persistence verification is required before merge.
