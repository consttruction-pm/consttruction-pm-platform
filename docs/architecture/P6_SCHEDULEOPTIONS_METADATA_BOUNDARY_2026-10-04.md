# P6 ScheduleOptions Release 26 — Metadata Boundary Certification

Date: 2026-10-04
Owner: Jalal
Baseline: main `ccbba8910539637056ec5ecf23a23d26bd6467c7`
Issue: #1088

## Scope

Certify the eight Oracle P6 Release 26 ScheduleOptions record/user/project metadata fields already represented in the typed P6 registry:

- CreateDate
- CreateUser
- LastUpdateDate
- LastUpdateUser
- ProjectId
- ProjectObjectId
- UserName
- UserObjectId

## Oracle semantics

Oracle Release 26 describes CreateDate/CreateUser and LastUpdateDate/LastUpdateUser as record lifecycle metadata, ProjectId/ProjectObjectId as project identity, and UserName/UserObjectId as user identity. The ScheduleOptions business object uses a multipart object identity composed of UserObjectId and ProjectObjectId.

Source: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-scheduleoptions-get.html

## Shared-Core boundary

These fields are not scheduling calculations. The Shared-Core `ScheduleOptions` dataclass therefore does not add them as scheduler controls. Persistence/API exposure remains a separate backend responsibility.

## Acceptance evidence

- 8/8 exact ScheduleOptions metadata names are present in the canonical typed registry with the expected types and non-calculation disposition.
- A focused regression confirms these metadata fields are absent from the scheduler calculation contract.
- No second ScheduleOptions model is introduced.
- No CPM, calendar, formula, progress, EVM, or client scheduling semantics are changed.
