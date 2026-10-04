# P6 Activity Release 26 — Semantic Certification Tranche NEXT5I

Date: 2026-10-05
Owner: Jalal
Baseline: main@87d67972712aa65b4e18e72560244e993d2b3e86
Issue: #1143
Scope: Shared-Core typed P6 Activity field registry semantic/source evidence only.

## Oracle authority

Oracle P6 Integration API Field Summary is authoritative for native field type and Read Only classification. Oracle P6 EPPM Release 26 Activity GET/PUT documentation is authoritative for the current REST representation and field meaning.

## Exact fields

| P6 field | Oracle native type | Oracle Read Only | Registry type | Writable | Computed | Unit |
|---|---|---:|---|---:|---:|---|
| BaselineStartDate | BeginDate | Yes | DATE | No | Yes | working-time |
| BaselineFinishDate | EndDate | Yes | DATE | No | Yes | working-time |
| BaselineDuration | Duration | Yes | DURATION | No | Yes | working-time |
| PrimaryConstraintDate | java.util.Date | No | DATE | Yes | No | — |
| ExpectedFinishDate | EndDate | No | DATE | Yes | No | — |

The Oracle Field Summary uses X to mark Read Only. For the two fields without that marker, this tranche records Read Only as No and keeps that external fact separate from the internal writable/computed disposition.

## Semantic evidence

- BaselineStartDate: current start date of the activity in the project baseline; it follows the planned start date until the activity is started, then the actual start date.
- BaselineFinishDate: current finish date of the activity in the project baseline; it follows planned/remaining/actual finish according to activity state.
- BaselineDuration: duration for the activity in the project baseline, measured as working time using the activity calendar; Oracle defines it as actual duration plus remaining duration.
- PrimaryConstraintDate: constraint date for the activity when a constraint exists; the constraint type determines whether the date is a start or finish date, and the scheduler uses activity constraints.
- ExpectedFinishDate: date the activity is expected to be finished according to progress on work products; Oracle describes it as manually entered by people familiar with that progress.

## Certification boundary

All five identities already exist in the canonical Activity registry. This tranche adds only source/evidence documentation and deterministic registry regression coverage.

No Activity dataclass expansion, duplicate registry, CPM/EVM/calendar/formula implementation, persistence/API schema, import/export mapping, or client-side scheduling semantics are introduced.

## Oracle sources

- Oracle P6 Integration API Field Summary: https://docs.oracle.com/cd/F51303_01/English/Integration/p6_pro_api_reference/FieldSummary.html
- Oracle P6 EPPM Release 26 Activity GET: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
- Oracle P6 EPPM Release 26 Activity PUT: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-put.html
