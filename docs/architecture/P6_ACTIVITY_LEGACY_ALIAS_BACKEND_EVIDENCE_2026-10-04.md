# P6 Activity legacy alias backend evidence — 2026-10-04

## Scope

This artifact records the current-main Backend/Database/Interchange evidence requested by Issue #859 for:

- `ActivityOwner`
- `Calendar`
- `RemainingFinishDate`

It is evidence-only. No Activity dataclass, scheduler, CPM, EVM, client calculation, or persistence schema is changed.

## Current-main baseline

The evidence was inspected against current `main` after PR #1083, merge commit `d17e900ddc951154e90ff24fa51daa2cbc63244b`.

## Evidence matrix

| Legacy identity | Current canonical registry evidence | Persistence evidence | Interchange evidence | Disposition |
|---|---|---|---|---|
| ActivityOwner | Canonical Activity registry contains `ActivityOwner`, plus separate `OwnerNamesArray` and resource-owner identities. | `ActivityMaster` has no owner field/column. | The generic P6 mapping/interchange layer is registry-driven; no current-main mapping establishes a single lossless owner identity. | **Unresolved / ambiguous** |
| Calendar | Activity registry contains `Calendar`, `CalendarName`, and `CalendarObjectId`. | `ActivityMaster` has no calendar field/column; calendar assignment is represented by the scheduling/calendar subsystem rather than this master persistence row. | A generic interchange mapping can preserve distinct source fields, but no current-main evidence proves that name and object identity are one canonical field. | **Unresolved / ambiguous; keep name vs object identity distinct** |
| RemainingFinishDate | Registry contains legacy `RemainingFinishDate` and canonical `RemainingEarlyFinishDate` / `RemainingLateFinishDate`. Current alias metadata points the legacy identity to `RemainingEarlyFinishDate`. | `ActivityMaster` is not an authoritative storage proof for either scheduler-derived early/late finish output. | XER integration evidence already represents early/finish outputs as separate canonical fields; the mapper is registry-driven and rejects ambiguous canonical/source mappings. | **Unresolved for final certification; do not collapse early/late scheduler outputs** |

## Deterministic conclusions

1. No current-main persistence path proves a single canonical storage identity for `ActivityOwner`.
2. Calendar name and calendar object identity remain distinct concepts; no alias is certified by name similarity.
3. `RemainingFinishDate` cannot be certified as a single persisted/interchange identity merely because the current compatibility metadata points to early finish. The authoritative Shared-Core scheduler exposes early and late outputs separately, so final certification must preserve that distinction.
4. No new mapping is added by this evidence tranche. Ambiguity remains explicit for downstream Shared-Core certification.

## Files inspected

- `src/construction_pm/activity_master_repository.py`
- `src/construction_pm/p6_field_registry.py`
- `src/construction_pm/p6_mapping_registry.py`
- `src/construction_pm/p6_interchange_mapping.py`
- `src/construction_pm/p6_xer_codec.py`
- `tests/test_p6_xer_adapter_integration.py`
- `tests/test_p6_interchange_mapping.py`

## Guardrails

No calculation semantics, Activity model expansion, API behavior, persistence schema, scheduler behavior, or client behavior is introduced.
