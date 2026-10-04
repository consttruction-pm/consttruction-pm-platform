# P6 Activity Release 26 — Non-Exact Legacy Seed Dispositions

Date: 2026-10-04
Owner: Jalal
Parent: #847 / #391 / #405
Baseline: current `main` 66a5c1fbced57fec11261e2d8436a6e4b1b2c468

## Current-main reconciliation

The authoritative Activity inventory contains 275 exact Release 26 Activity field names. The canonical typed Activity registry contains those 275 exact names plus 9 registry-only legacy/product-seed names. No Release 26 Activity inventory name is missing.

The two remaining registry-only names that require an explicit disposition are:

- `Calendar`
- `ActivityOwner`

The other seven registry-only names already have explicit Shared-Core alias resolutions:
ActivityId -> Id, ActivityName -> Name, ActivityStatus -> Status, ActivityType -> Type, UpdateUser -> LastUpdateUser, RemainingStartDate -> RemainingEarlyStartDate, RemainingFinishDate -> RemainingEarlyFinishDate.

## Oracle evidence

### Calendar

Oracle P6 EPPM Release 26 Read Activities exposes `CalendarName` as the calendar name and `CalendarObjectId` as the unique ID of the calendar assigned to the activity. There is no exact Activity field named `Calendar` in the Release 26 Activity schema.

Sources:
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/api-calendar.html

Therefore the legacy seed field `Calendar` is not treated as an alias to either exact field. Its semantics would be composite/ambiguous at a single-field boundary, so its explicit disposition is `outside_scope`. The exact canonical fields remain `CalendarName` and `CalendarObjectId`.

### ActivityOwner

Oracle P6 EPPM Release 26 Read Activities exposes `ActivityOwnerUserId` as the unique user ID of the activity owner. Oracle separately defines an `ActivityOwner` business object with its own REST endpoints and a multipart object identity composed from activity and user IDs.

The Activity schema also exposes `OwnerIDArray` and `OwnerNamesArray` as comma-separated owner IDs and names.

Sources:
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/api-activityowner.html

Therefore the legacy seed field `ActivityOwner` is not treated as an alias for `ActivityOwnerUserId`, `OwnerIDArray`, or `OwnerNamesArray`, and is explicitly classified as `outside_scope`.

## Boundary

This certification only defines non-exact registry disposition and prevents unsafe aliasing. It does not alter Activity scheduling, CPM/EVM, calendar calculation, formula evaluation, backend/API persistence, or client scheduling behavior.

## Acceptance

- No Release 26 Activity inventory names are missing from the canonical registry.
- `Calendar` and `ActivityOwner` are explicitly classified as non-exact legacy seed names.
- Neither legacy name is resolved by name similarity.
- The exact canonical Activity fields remain independently represented and test-covered.
