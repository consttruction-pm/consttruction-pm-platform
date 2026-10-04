# P6 Activity Release 26 — Semantic Certification Tranche 10

Date: 2026-10-04

## Scope

This tranche certifies Oracle Release 26.4 field semantics for the following existing canonical Activity registry identities:

- EstimateToCompleteLaborUnits
- EstimatedWeight
- IsNewFeedback
- IsStarred
- IsTemplate
- IsWorkPackage
- NonLaborCost1Variance
- NonLaborCost2Variance
- NonLaborCost3Variance
- OwnerNamesArray

This artifact is semantic/source evidence only. It does not alter the Activity domain model, create a second registry, or certify persistence/import-export behavior.

## Evidence

### EstimateToCompleteLaborUnits

- Oracle type: Unit.
- Semantics: estimated quantity to complete the activity.
- Calculation: either remaining total units or PF × (baseline labor units − earned value), depending on the WBS earned-value technique.
- Oracle Integration API: getter documented; field may not be used in where/order-by.
- Disposition: computed/shared-core semantic field; not a user-entered canonical Activity value.

Source:
https://docs.oracle.com/cd/G48897_01/English/Integration_Documentation/p6_eppm_api_reference/com/primavera/integration/client/bo/object/Activity.html

### EstimatedWeight

- Oracle type: double.
- Semantics: estimation weight used for top-down estimation.
- Mutability: setter is documented in the Release 26.4 Activity Integration API.
- Disposition: writable Activity input with top-down estimation semantics.

Source:
https://docs.oracle.com/cd/G48897_01/English/Integration_Documentation/p6_eppm_api_reference/com/primavera/integration/client/bo/object/Activity.html

### IsNewFeedback

- Oracle type: boolean.
- Semantics: indicates whether a resource has sent feedback notes about the activity that have not been reviewed.
- Mutability: getter and setter are documented in the Release 26.4 Activity Integration API.
- Disposition: writable Activity flag.

Source:
https://docs.oracle.com/cd/G48897_01/English/Integration_Documentation/p6_eppm_api_reference/com/primavera/integration/client/bo/object/Activity.html

### IsStarred

- Oracle type: boolean.
- Semantics: indicates whether the activity is marked as starred.
- Mutability: getter and setter are documented in the Release 26.4 Activity Integration API.
- Disposition: writable Activity flag.

Source:
https://docs.oracle.com/cd/G48897_01/English/Integration_Documentation/p6_eppm_api_reference/com/primavera/integration/client/bo/object/Activity.html

### IsTemplate

- Oracle type: boolean.
- Semantics: indicates whether the business object is related to a template Project.
- Mutability: Release 26.4 Activity API documents the getter; no Activity setter is documented.
- Disposition: read-only Activity property unless separate authoritative P6 FieldSummary evidence proves an update surface.

Source:
https://docs.oracle.com/cd/G48897_01/English/Integration_Documentation/p6_eppm_api_reference/com/primavera/integration/client/bo/object/Activity.html

### IsWorkPackage

- Oracle type: boolean.
- Semantics: indicates whether the WBS is a workpackage in Prime.
- Mutability: Release 26 Activity REST exposes the property; Activity Integration API does not document an Activity setter in the current 26.4 surface reviewed for this tranche.
- Disposition: treat as read-only/product-state property pending explicit update/mutability evidence.

Source:
https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-put.html
https://docs.oracle.com/cd/G48897_01/English/Integration_Documentation/p6_eppm_api_reference/com/primavera/integration/client/bo/object/Activity.html

### NonLaborCost1Variance

- Oracle type: number/double.
- Semantics: primary baseline nonlabor cost minus at-completion nonlabor cost.
- Computation: BL nonlabor cost − at-completion nonlabor cost.
- Disposition: computed/read-only Activity value.

Source:
https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-put.html

### NonLaborCost2Variance

- Oracle type: number/double.
- Semantics: secondary baseline nonlabor cost minus at-completion nonlabor cost.
- Computation: BL nonlabor cost − at-completion nonlabor cost.
- Disposition: computed/read-only Activity value.

Source:
https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-put.html

### NonLaborCost3Variance

- Oracle type: number/double.
- Semantics: tertiary baseline nonlabor cost minus at-completion nonlabor cost.
- Computation: BL nonlabor cost − at-completion nonlabor cost.
- Disposition: computed/read-only Activity value.

Source:
https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-put.html

### OwnerNamesArray

- Oracle type: string array.
- Semantics: Activity owner names collection.
- Mutability: getter and setter are documented in the Release 26.4 Activity Integration API.
- Disposition: writable collection property; ownership business-object linkage remains distinct from the Activity field itself.

Source:
https://docs.oracle.com/cd/G48897_01/English/Integration_Documentation/p6_eppm_api_reference/com/primavera/integration/client/bo/object/Activity.html

## Registry alignment

All ten names already exist exactly once in the current canonical Activity registry. This tranche does not add new identities.

Current independent reconciliation on main:

- Release 26 Activity inventory: 275
- Exact canonical Activity matches: 275
- Inventory-only: 0
- Registry-only/non-exact: 9

## Certification boundary

Oracle source evidence establishes external field identity, type, meaning, and documented API mutability. It does not by itself certify:

- Shared-Core internal persistence behavior;
- SQLite/PostgreSQL round-trip preservation;
- XER/XML/XLSX import/export mapping;
- client presentation/editability;
- any scheduler-derived calculation implementation.

Those require separate internal evidence and regression gates.

## Guardrail

Do not change CPM, EVM, calendar, progress, Activity dataclass, or client scheduling semantics as part of this evidence tranche.
