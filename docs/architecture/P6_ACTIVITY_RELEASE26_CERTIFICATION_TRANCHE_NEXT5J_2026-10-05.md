# P6 Activity Release 26 — Semantic Certification Tranche NEXT5J

Date: 2026-10-05  
Owner: Jalal  
Baseline: `main@48f101997be0b12d363d8c79a7838ea25b5cea2c`  
Issue: #1182  
Scope: Shared-Core typed P6 Activity field registry semantic/source evidence only.

## Exact fields

| P6 field | Oracle native type | Oracle Read Only | Internal registry type | Writable | Computed | Unit |
|---|---|---:|---|---:|---:|---|
| SuspendDate | BeginDate | No | DATETIME | Yes | No | — |
| TaskStatusCompletion | TaskStatusCompletion | No | COMPLEX | Yes | No | — |
| TaskStatusDates | TaskStatusDates | No | COMPLEX | Yes | No | — |
| TaskStatusIndicator | boolean | No | BOOLEAN | Yes | No | — |
| UnitsPercentComplete | Percent | No | DOUBLE | No | Yes | percent |

## Oracle semantic evidence

- **SuspendDate**: the start date from which progress of a task/resource-dependent activity is delayed. Oracle requires it to be later than ActualStartDate; the suspend/resume interval behaves as nonwork time on the applicable calendar.
- **TaskStatusCompletion**: completion status of the activity.
- **TaskStatusDates**: status of the activity according to the activity dates.
- **TaskStatusIndicator**: indicator of the activity status.
- **UnitsPercentComplete**: percentage complete of units for all labor and nonlabor resources assigned to the activity; computed as Actual Units / At Completion Units × 100 and constrained to 0–100.

Oracle's Release 26.4 Field Summary lists the native types and leaves the Read Only column blank for all five, which is recorded here as not Read Only. The internal registry deliberately keeps normalized storage types and computed/writable dispositions separate from Oracle-native type labels.

## Certification boundary

All five identities already exist in the canonical Activity registry. This tranche adds only source evidence and deterministic regression coverage. It does not add Activity identities, alter CPM/scheduling/calendar/formula/progress/EVM semantics, or change persistence/API/import-export behavior.

## Oracle sources

- Oracle P6 Pro Integration API Field Summary (Release 26.4):
  https://docs.oracle.com/cd/F51303_01/English/Integration/p6_pro_api_reference/FieldSummary.html
- Oracle P6 EPPM Release 26 Activity GET:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
- Oracle P6 EPPM Release 26 Activity PUT:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-put.html
