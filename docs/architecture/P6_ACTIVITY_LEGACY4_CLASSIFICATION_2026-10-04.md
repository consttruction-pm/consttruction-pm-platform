# P6 Activity Release 26 — Remaining Four Legacy/Product-Seed Names

Date: 2026-10-04

## Purpose
Classify the four non-exact legacy/product-seed names that remain outside the exact 275-field Release 26 Activity inventory after #1057:

- ActivityOwner
- Calendar
- RemainingStartDate
- RemainingFinishDate

This document is an evidence classification only. It does not add a second calculation engine, expand the Activity domain model, or alter persistence/API authority.

## Oracle Release 26 evidence

### ActivityOwner
Oracle exposes ActivityOwner as a separate REST business object under /activityOwner, with create/read/update/delete endpoints. Its schema links ActivityObjectId to UserObjectId; it is not an Activity field named ActivityOwner.
Source: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/api-activityowner.html

### Calendar
Oracle Release 26 Activity exposes CalendarName and CalendarObjectId. The Activity schema does not establish a canonical Activity field named Calendar.
Source: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html

### RemainingStartDate / RemainingFinishDate
Oracle Release 26 exposes canonical Activity remaining dates as RemainingEarlyStartDate / RemainingEarlyFinishDate. RemainingStartDate and RemainingFinishDate are documented for ResourceAssignment/ResourceAssignmentCreate objects, where they describe resource work on an activity.
Sources:
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-resourceassignment-get.html
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-resourceassignment-put.html

## Classification

| Legacy/product-seed name | Classification | Canonical Activity mapping |
|---|---|---|
| ActivityOwner | Separate Oracle ActivityOwner business object; not an Activity field | None certified |
| Calendar | Legacy/product-seed shorthand; Release 26 Activity exposes CalendarName + CalendarObjectId | None certified |
| RemainingStartDate | ResourceAssignment field name, not Activity field | None certified; Activity uses RemainingEarlyStartDate |
| RemainingFinishDate | ResourceAssignment field name, not Activity field | None certified; Activity uses RemainingEarlyFinishDate |

## Guardrails

Do not promote any of the four names into exact Release 26 Activity identity based on name similarity. Preserve existing compatibility aliases only where an explicit canonical target is already independently proven. Keep persistence/import-export certification separate from Oracle inventory evidence.

## Current exact parity baseline

After merged PR #1057:

- Release 26 Activity inventory: 275
- Exact canonical Activity registry matches: 275
- Inventory-only: 0
- Registry-only/non-exact: 9

The four names in this document remain non-exact legacy/product-seed entries pending a deliberate compatibility/deprecation decision; they are not missing Release 26 Activity inventory fields.