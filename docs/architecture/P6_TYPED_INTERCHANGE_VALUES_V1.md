# P6 Typed Interchange Values v1

## Purpose

`P6InterchangeTypedValue` is the provider-neutral value contract used by P6 import/export adapters when a value must survive an interchange round trip without losing its semantic type.

It complements the P6 interchange mapping boundary; it does not parse XER, Primavera XML, XLS/XLSX, Microsoft Project XML or MPX files.

## Supported types

The contract preserves:

- `date`
- timezone-aware `datetime`
- finite `decimal`
- `duration` with an explicit unit
- `boolean`
- `enum`
- `integer`
- `string`

Optional `unit` and `currency` metadata are retained explicitly. Currency is metadata only; no currency conversion is performed here.

## Lossless policy

Values are validated before encoding and after decoding. Boolean, integer, decimal and datetime values are not silently coerced across incompatible types. Unknown data types fail closed.

Duration values carry their unit both in the typed value and serialized payload; conflicting unit metadata is rejected.

The JSON representation uses deterministic key ordering and decimal strings so decimal precision is not reduced by floating-point conversion.

## Boundary

Concrete provider/file adapters own file parsing and serialization. They should translate external fields through `P6InterchangeMapper` and use this value contract when the external representation needs an explicit typed payload.

Shared Core remains authoritative for P6 calculations and semantics, including Scheduling, Calendar/Duration calculations, Formula, Progress/EVM, Resource/Cost and financial calculations.

## Verification

Regression tests cover JSON round trips for all supported types, decimal/currency metadata, explicit duration units, and fail-closed validation for invalid or unsupported types.