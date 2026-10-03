# P6 Activity alias resolution — 2026-10-04

## Scope

This evidence slice resolves five legacy/product-seed Activity registry names to canonical P6 identities already represented in the Shared-Core registry. It does not add Activity model fields, change scheduler calculations, or replace any existing canonical field.

The mapping is:

| Legacy/product seed | Canonical registry field | Oracle P6 identity | Disposition |
|---|---|---|---|
| `ActivityId` | `activity.id` | `Id` | product alias |
| `ActivityName` | `activity.name` | `Name` | product alias |
| `ActivityStatus` | `activity.status` | `Status` | product alias |
| `ActivityType` | `activity.type` | `Type` | product alias |
| `UpdateUser` | `activity.last_update_user` | `LastUpdateUser` | product alias |

## External P6 evidence

Oracle P6 EPPM REST API Release 26 documents:

- `Id` as the short Activity ID that uniquely identifies the Activity within the project. https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
- `Name` as the Activity name. https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
- `Status` as the current Activity status with the values Not Started, In Progress, and Completed. https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
- `Type` as the Activity type with the six documented P6 values. https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
- `LastUpdateUser` as the name of the user that last updated the Activity. https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html

The current-main registry already contains exact canonical rows for `Id`, `Name`, `Status`, `Type`, and `LastUpdateUser`. The change therefore records the older names as explicit product aliases instead of creating duplicate P6 identities.

## Semantic boundary

The alias metadata does not transfer writable/computed behavior from a legacy seed row to the canonical field. Consumers requiring P6 semantics must use the canonical target row. This is especially important for `Status`, whose canonical registry row is scheduler/application-derived and non-writable.

## Deliberately unresolved aliases

The following legacy names remain unresolved in this slice because current internal evidence is insufficient to certify a single canonical identity without crossing the backend/interchange evidence boundary:

- `ActivityOwner`
- `Calendar`
- `RemainingStartDate`
- `RemainingFinishDate`

The existing dedicated backend evidence lane for owner/calendar/remaining-finish remains authoritative for those decisions.

## Verification intent

The focused registry regression proves:

1. each resolved alias points to an existing Activity canonical row;
2. a product alias cannot become a second canonical P6 identity;
3. all five resolved Oracle identities are represented exactly once as canonical rows.

No CPM, EVM, calendar calculation, import/export algorithm, API contract, or client calculation was changed by this slice.
