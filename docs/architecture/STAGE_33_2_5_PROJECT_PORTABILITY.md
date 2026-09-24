# Stage 33.2.5 — Project Portability Contract

## Objective
A ConstructionPM project carries the versioned context required to reproduce authoritative calculations when moved between Desktop, Web, server or another compatible installation.

## Mandatory portable context
- Project identity and schema version.
- Calendar identity and calendar version.
- Scheduling settings.
- Calculation/schema version.
- Resource and Cost configuration required by project calculations.
- Project-specific rules.
- Language/data context when required for reproducible interpretation.
- Baseline/Current/Actual/Forecast context references where applicable.

## Rules
1. Export/import preserves calculation context; importing without required context is invalid.
2. Receiving clients validate supported schema versions before calculation.
3. Context is never silently replaced by local defaults.
4. Unsupported versions produce a typed compatibility error.
5. Web and Desktop consume the same portability contract.
6. Portability does not duplicate calculation logic.
7. The same inputs and versions must reproduce the same authoritative results.

## Current implementation
Versioned JSON Schema is established under shared/contracts/. Import/export validation and round-trip integration tests are the next step.
