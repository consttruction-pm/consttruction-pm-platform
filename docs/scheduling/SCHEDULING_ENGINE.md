# Scheduling Engine

## Configuration baseline
```json
{"duration":"working-day","calendar":"jalali-gregorian","lag":"working","constraints":"hybrid","mode":"both"}
```

## Required behavior
- Calendar-aware date arithmetic.
- WorkingTimeResolver as the source of truth for working/non-working time.
- FS, SS, FF and SF relationships.
- Forward pass and backward pass.
- Constraints and lag handling.
- Deterministic calculations.
- Project-specific calendar/settings travel with project export/import.
- Results must be reproducible across devices.

## Testing
Scheduling calculations require unit, integration and Primavera-conformance tests.