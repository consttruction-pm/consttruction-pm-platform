# Competitive Completeness Matrix

Effective date: 2026-09-25

## Purpose
Track the gap between our current platform foundations and the breadth expected from a modern construction PM + project-controls product.

Legend: Foundation = architecture/specification exists; Implemented = source implementation exists; Verified = runtime regression evidence exists; Planned = required but not yet implemented; Adapter = external/integration boundary.

| Domain | Current state | Required next maturity |
|---|---|---|
| P6 scheduling / CPM | Implemented + verified foundation | Continue parity edge packs and production UI |
| Time/calendar/duration | Implemented + verified | Expand rich calendar configuration |
| Progress / EVM / Earned Schedule | Implemented foundation | Connect field/commercial evidence and forecasts |
| Resource / Cost | Implemented foundation | Extend commitments, procurement and commercial forecasting |
| WBS / Activities / Gantt | Foundation | Complete production Web workflow and editing |
| Documents / OCR / RFI / Submittal / claims evidence | Specified | Build document service, search, revision, linkage and approvals |
| Daily field reporting | Partial/spec | Full mobile-first field workflow |
| Quality / inspections | Missing product module | Configurable inspections, observations, NCR/corrective actions |
| Safety | Missing product module | Incidents, observations, checklists and corrective actions |
| Punch list / closeout | Missing product module | Full issue-to-closeout workflow |
| Change / Variation / Claims | Partial | Entitlement, notice, impact, evidence and commercial workflow |
| Procurement | Missing product module | RFQ -> quotes -> comparison -> PO -> delivery -> commitment |
| Preconstruction / Estimating / Takeoff | Missing product module | Estimate, 2D/3D takeoff, tender and bid analysis |
| BIM / CDE / 4D / 5D | Missing product module | Model/document integration and mappings |
| Site reality / visual progress | Missing product module | Photo/360/drone evidence and AI verification |
| Risk | Schedule foundation | Enterprise risk register and quantitative analysis |
| Portfolio control | Partial foundation | Executive multi-project control room |
| AI copilot / agents | Architectural requirement | Grounded analysis, scenarios, actions and audit trail |
| Natural-language scheduling | Not implemented | Query + scenario + explainable changes |
| Predictive schedule risk | Not implemented | AI forecast/risk layer over Shared Core |
| ERP/accounting integration | Contract direction | AP/AR/commitments/actuals/forecast interfaces |
| Enterprise identity | Authorization boundary | SSO/SAML/OIDC and lifecycle |
| API ecosystem | Versioned internal contracts | Public/integration API and connectors |
| Commissioning / handover | Missing product module | Closeout and asset handover |
| GIS / weather / IoT | Not implemented | Optional adapters after core workflows |
| Supplier/subcontractor portal | Not implemented | External collaboration workflow |
| Benchmarking / lessons learned | Not implemented | Enterprise analytics and controlled AI learning loop |

## P0
1. AI Project Controls Copilot + auditable agent framework.
2. Cross-domain project dependency graph.
3. Full field operations core.
4. Change/Variation/Notice/Claim workflow.
5. Portfolio/project control room.
6. Procurement + commercial commitments.
7. ERP/accounting integration contract.

## P1
1. Preconstruction/estimating/takeoff/bid.
2. BIM/CDE/4D/5D.
3. Visual/site-reality progress intelligence.
4. Quality and safety suites.
5. Commissioning/turnover/closeout.

## P2
GIS, weather, IoT, geofencing, supplier portal, SSO, e-signature, public API marketplace, BI/data warehouse and benchmarking.

## Non-regression boundary
Nothing in this matrix changes the authoritative meaning of P6 scheduling, calendar arithmetic, duration/lag, Progress/EVM, Resource/Cost or financial calculations. New modules integrate with those foundations through versioned contracts.