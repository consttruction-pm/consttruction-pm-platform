# P6 Activity Release 26 — Semantic Certification Tranche NEXT5H

Date: 2026-10-05  
Owner: Jalal  
Issue: #1139  
Scope: certification/evidence only for five existing canonical Activity registry identities.

## Oracle evidence

Oracle P6 EPPM Release 26 Activity REST documentation and P6 Pro Integration API Field Summary are the external authority for field type, read-only behavior and published meaning.

| P6 field | Oracle type | Oracle Read Only | Existing registry type | Existing writable | Existing computed | Unit |
|---|---|---:|---|---:|---:|---|
| FreeFloat | Duration / number(double) | Yes | DURATION | No | Yes | working-time |
| LateStartDate | BeginDate | Yes | DATE | No | Yes | — |
| LateFinishDate | EndDate | Yes | DATE | No | Yes | — |
| PrimaryConstraintType | ConstraintType / string | No | ENUM | Yes | No | — |
| HasFutureBucketData | boolean | Yes | BOOLEAN | No | No | — |

### Semantic notes

- FreeFloat is the amount of time an activity can be delayed before delaying the start date of any successor.
- LateStartDate is the latest date the remaining work can start without delaying project finish.
- LateFinishDate is the latest date the activity can finish without delaying project finish.
- PrimaryConstraintType identifies the primary start/finish constraint applied to the activity; Oracle documents Start On, Start On or Before, Start On or After, Finish On, Finish On or Before, Finish On or After, and As Late As Possible.
- HasFutureBucketData indicates whether a resource assignment on the activity has future-bucket data.

The Oracle read-only flag is kept separate from the internal registry writable/computed disposition. In particular, a read-only P6 field is not automatically treated as an internally recalculated scheduler value.

## Certification boundary

All five identities already exist in the canonical Activity registry. This tranche adds no new field identities and does not change scheduling, calendar, formula, Progress/EVM, persistence, API, import/export, or client calculation behavior.

## Sources

- P6 EPPM Release 26 — Read Activities:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
- P6 Pro Integration API — Field Summary:
  https://docs.oracle.com/cd/F51303_01/English/Integration/p6_pro_api_reference/FieldSummary.html
- P6 Pro Activity Dates guidance:
  https://docs.oracle.com/cd/F51303_01/English/User_Guides/p6_pro_user/activity_dates.htm
