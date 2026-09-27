# Competitive Completeness Matrix

Effective date: 2026-09-25

## Purpose
Track the gap between our current platform foundations and the breadth/depth expected from a modern construction PM + project-controls product, with the explicit release target defined by Principle 2.

## Release target
The objective at the commercial/public release gate is to demonstrate the most complete and forward-looking offering within the product's defined specialist scope, using a fresh competitor benchmark and evidence for every material gap. This is a release criterion, not an unsupported present-tense claim.

## Status legend
Foundation = architecture/specification exists; Implemented = source implementation exists; Verified = runtime regression evidence exists; Planned = required but not yet implemented; Adapter = external/integration boundary.

| Domain | Current state | Required next maturity | Release gate |
|---|---|---|---|
| P6 scheduling / CPM | Implemented + verified foundation | Continue parity edge packs and production UI | Gate A |
| P6 fields / columns / UDF / formulas / layouts | Architecture baseline + gap inventory | Build complete field registry, column/layout engine, safe formula engine and conformance fixtures | Gate A |
| Time/calendar/duration | Implemented + verified | Expand rich calendar configuration | Gate A |
| Progress / EVM / Earned Schedule | Implemented foundation | Connect field/commercial evidence and forecasts | A + B |
| Resource / Cost | Implemented foundation | Extend commitments, procurement and commercial forecasting | A + B |
| WBS / Activities / Gantt | Foundation | Complete production Web workflow and editing | B |
| Documents / OCR / RFI / Submittal / claims evidence | Specified | Build document service, search, revision, linkage and approvals | B |
| Daily field reporting | Partial/spec | Full mobile-first field workflow | B |
| Quality / inspections | Missing product module | Configurable inspections, observations, NCR/corrective actions | B |
| Safety | Missing product module | Incidents, observations, checklists and corrective actions | B |
| Punch list / closeout | Missing product module | Full issue-to-closeout workflow | B |
| Change / Variation / Claims | Partial | Entitlement, notice, impact, evidence and commercial workflow | B |
| Procurement | Missing product module | RFQ -> quotes -> comparison -> PO -> delivery -> commitment | B |
| Preconstruction / Estimating / Takeoff | Missing product module | Estimate, 2D/3D takeoff, tender and bid analysis | B |
| BIM / CDE / 4D / 5D | Missing product module | Model/document integration and mappings | B |
| Site reality / visual progress | Missing product module | Photo/360/drone evidence and AI verification | B |
| Risk | Schedule foundation | Enterprise risk register and quantitative analysis | A + B |
| Portfolio control | Partial foundation | Executive multi-project control room | B |
| AI copilot / agents | Architectural requirement | Grounded analysis, scenarios, actions and audit trail | B |
| Natural-language scheduling | Not implemented | Query + scenario + explainable changes | B |
| Predictive schedule risk | Not implemented | AI forecast/risk layer over Shared Core | B |
| ERP/accounting integration | Contract direction | AP/AR/commitments/actuals/forecast interfaces | B |
| Enterprise identity | Authorization boundary | SSO/SAML/OIDC and lifecycle | B |
| API ecosystem | Versioned internal contracts | Public/integration API and connectors | B |
| Commissioning / handover | Missing product module | Closeout and asset handover | B |
| GIS / weather / IoT | Not implemented | Optional adapters after core workflows | B if in scope |
| Supplier/subcontractor portal | Not implemented | External collaboration workflow | B if in scope |
| Benchmarking / lessons learned | Not implemented | Enterprise analytics and controlled AI learning loop | B |

## Release hard-stop conditions
- Any Gate A regression in established P6/shared calculation semantics.
- Any P0 item still only planned.
- A material competitor capability within scope has no implementation/integration decision.
- AI decision features lack provenance, action controls or auditability.
- Web/Desktop/Mobile parity violates shared calculation authority.
- Export/import or API contracts lose calculation-ready types.
- Critical security, offline, performance, localization or data-integrity evidence is missing.

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