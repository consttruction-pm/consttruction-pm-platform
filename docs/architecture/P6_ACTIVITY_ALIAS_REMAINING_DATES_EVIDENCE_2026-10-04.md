# P6 Activity alias resolution — remaining dates

Date: 2026-10-04  
Owner: Jalal  
Scope: Shared-Core P6 field alias resolution only.

## Resolved mappings

| Legacy/product-seed registry id | Canonical P6 registry id | P6 field | Basis |
|---|---|---|---|
| `activity.remaining_start` | `activity.remaining_early_start_date` | `RemainingEarlyStartDate` | Oracle P6/Gateway field mapping |
| `activity.remaining_finish` | `activity.remaining_early_finish_date` | `RemainingEarlyFinishDate` | Oracle P6/Gateway field mapping |

Oracle's P6 activity field mapping identifies Gateway `remainingStartDate` with P6 `RemainingEarlyStartDate` and Gateway `remainingFinishDate` with P6 `RemainingEarlyFinishDate`. Oracle's current P6 Activity reference also defines `RemainingEarlyStartDate` as the scheduled start of remaining work and `RemainingEarlyFinishDate` as the scheduler-calculated remaining finish boundary.  

Sources:
- https://docs.oracle.com/cd/F51420_01/English/User_Guides/prime_p6_bf_setup/gateway_prime_to_p6_bf_setup.pdf
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html

## Certification boundary

This change only extends `P6_ACTIVITY_ALIAS_RESOLUTIONS`. It does not change Activity persistence, the Activity dataclass, scheduler/CPM calculations, EVM formulas, calendars, client-side scheduling, or API schemas.

Backend persistence/interchange certification remains a separate acceptance item. In particular, the still-unresolved `ActivityOwner` and `Calendar` aliases are intentionally not mapped from name similarity or documentation alone.
