# P6 Cross-Platform Presentation Contract v1

Issue #1226 defines the shared presentation boundary for P6 field, column/layout, and formula-authority results across Web, Desktop, and Mobile.

## Single authority

The canonical contract is apps/client-sync/src/p6-presentation-contract.ts with ID constructionpm://contracts/p6-presentation/v1.

It is a transport/presentation contract only. Field metadata, formula parsing/type/dependency analysis, and scheduling semantics remain authoritative in Shared Core/backend APIs. No client owns a P6 field catalog or formula evaluator.

## Versioned surfaces

- Field Registry: p6-field-registry.v1
- Layout: p6-layout.v1
- Formula authority result: p6-formula-authority-api.v1
- Common parity fixture: shared/contracts/p6-presentation-parity.fixture.json

Web, Desktop, and Mobile adapters are thin re-exports and validation boundaries over the same contract. They must not fork field metadata or formula semantics.

## Certification gate

The shared fixture deliberately carries registry.status = seeded_not_certified. Client validation preserves that status and never upgrades it to verified. Full P6 semantic parity remains gated on authoritative registry certification.

## Date/display rule

Jalali/Gregorian conversion remains presentation-only. Canonical field values and scheduling/calculation semantics are not reinterpreted by client adapters.

## Acceptance evidence

- One shared versioned contract.
- One shared registry/layout/formula fixture.
- Web, Desktop, and Mobile tests consume the same fixture.
- Layout order normalization is shared.
- Formula dependency IDs and result type are preserved.
- Registry certification status is preserved.
