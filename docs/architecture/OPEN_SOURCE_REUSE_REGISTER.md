# Open-Source Reuse Register

This register controls reuse of mature open-source components without creating a second source of truth.

## Accepted for controlled use

### pmcontrols — MIT

Repository: arikanatakan/pmcontrols.

Use only as an independent validation/oracle for selected CPM, PERT, EVM and earned-schedule reference cases. It must not replace the project's authoritative Shared Scheduling/P6 or Progress/EVM implementations.

Initial boundary: optional development/validation profile.

### Papermerge Core — Apache-2.0

Repository: papermerge/papermerge-core.

Use as a future reference/integration candidate for OCR, document indexing/search and document versioning behind the project's Document Storage/OCR/Search abstractions. Do not embed its domain model into Shared Core.

## Not selected for direct embedding

### OpenConstructionERP — AGPL-3.0

Useful construction capabilities were identified, but AGPL is not selected as a default dependency for the intended commercial product. Ideas may be studied; code is not imported.

### ProjectEngine — GPL-3.0

Useful scheduling/project-control reference, but GPL-3.0 is not selected for direct embedding.

### PyJobShop — MIT

License is compatible, but its main scope is constraint/production scheduling. It is not a drop-in replacement for our Primavera-compatible scheduling engine. Keep it as a future optimization/benchmark candidate only.

## Mandatory reuse rule

Shared scheduling, duration, calendar, Progress/EVM and Resource/Cost semantics remain in the project's Shared Domain/Calculation Core.

Every future adoption must record the repository, exact version/commit, license, boundary, mapping, removal strategy and regression/parity tests.

Reviewed: 2026-09-25.
