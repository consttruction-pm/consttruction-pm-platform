# P6 Activity Release 26 — Semantic Certification Tranche NEXT10H

Date: 2026-10-05  
Owner: Jalal  
Baseline: `main@48f0a95f91a1a98e50dee6e8f12ff31b78f741d4`  
Issue: #1146  
Scope: Shared-Core Activity field registry semantic/source evidence, with targeted metadata correction where Oracle Read Only evidence proves the existing writable/computed disposition was incorrect.

## Oracle authority

Oracle Primavera Integration API Release 26.4 Field Summary is authoritative for native type and Read Only classification. Oracle Activity Release 26 GET/PUT documentation and the Release 26.4 Activity business-object API are used for field meaning and writable method evidence.

## Exact fields

| P6 field | Oracle type | Oracle Read Only | Registry type | Registry writable | Registry computed | Registry unit |
|---|---|---:|---|---:|---:|---|
| ActualExpenseCost | Cost | Yes | DOUBLE | No | Yes | — |
| ActualMaterialCost | Cost | Yes | DOUBLE | No | Yes | — |
| ActualNonLaborCost | Cost | No | DOUBLE | Yes | No | — |
| ActualNonLaborUnits | Unit | No | DOUBLE | Yes | No | — |
| ActualThisPeriodLaborCost | Cost | No | DOUBLE | Yes | No | — |
| ActualThisPeriodLaborUnits | Unit | No | DOUBLE | Yes | No | — |
| ActualThisPeriodMaterialCost | Cost | Yes | DOUBLE | No | Yes | — |
| ActualThisPeriodNonLaborCost | Cost | No | DOUBLE | Yes | No | — |
| ActualThisPeriodNonLaborUnits | Unit | No | DOUBLE | Yes | No | — |
| ActualTotalCost | Cost | Yes | DOUBLE | No | Yes | — |

The Registry's internal `unit` value remains unchanged in this tranche; Oracle's native Cost/Unit type and semantic meaning are recorded separately from the internal normalization metadata.

## Semantic evidence

- ActualExpenseCost: actual costs for project expenses associated with the activity.
- ActualMaterialCost: sum of regular and overtime costs for material resources; Oracle marks it Read Only.
- ActualNonLaborCost: actual costs for nonlabor resources; Oracle exposes a setter, so the canonical Registry is corrected to writable/non-computed.
- ActualNonLaborUnits: actual units for nonlabor resources; Oracle exposes a setter, so the Registry is corrected to writable/non-computed.
- ActualThisPeriodLaborCost: actual labor cost during the current financial period; Oracle exposes a setter, so the Registry is corrected to writable/non-computed.
- ActualThisPeriodLaborUnits: actual labor units during the current financial period; Oracle exposes a setter, so the Registry is corrected to writable/non-computed.
- ActualThisPeriodMaterialCost: sum of material-resource costs for the current period; Oracle marks it Read Only and the Registry keeps it computed/non-writable.
- ActualThisPeriodNonLaborCost: actual current-period nonlabor cost; Oracle exposes a setter, so the Registry is corrected to writable/non-computed.
- ActualThisPeriodNonLaborUnits: actual current-period nonlabor units; Oracle exposes a setter, so the Registry is corrected to writable/non-computed.
- ActualTotalCost: actual total cost for the activity, including labor, nonlabor and project expenses; Oracle marks it Read Only and the Registry keeps it computed/non-writable.

## Certification boundary

No new Activity identities are added. The only implementation change is correction of six existing Registry writable/computed dispositions where Oracle's Read Only/setter evidence establishes that the prior metadata was incorrect.

No Activity dataclass expansion, CPM/EVM calculation change, calendar change, formula engine change, persistence/API schema change, import/export mapping, or client-side scheduling semantics are introduced.

## Oracle sources

- Oracle Integration API 26.4 Field Summary:
  https://docs.oracle.com/cd/G48897_01/English/Integration_Documentation/p6_eppm_api_reference/com/primavera/integration/client/bo/object/Activity.html
  and the Release 26.4 Field Summary:
  https://docs.oracle.com/cd/F51303_01/English/Integration/p6_pro_api_reference/FieldSummary.html
- Oracle P6 EPPM Release 26 Activity GET:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
- Oracle P6 EPPM Release 26 Activity PUT:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-put.html
