# P6 Formula Field-Type Bridge v2

Status: implemented on branch \`codex/jalal/p6-formula-types-v2\`.

## Purpose

This slice connects the Shared/Core formula engine to the authoritative P6 field taxonomy without duplicating field definitions.

Safe mappings currently cover:

- String -> Text
- Date -> typed Date
- DateTime -> typed timezone-aware DateTime
- Decimal / Percentage / Integer / Double / Cost -> Number
- Boolean -> Boolean
- Enum -> Text
- Object ID -> Text

Field units are preserved in the formula schema for numeric-compatible fields.

## Fail-closed behavior

P6 Duration, Unit, Object-ID arrays, String arrays, Complex and Spread are not coerced into an unrelated formula type. They raise an explicit unsupported-field-type error until their authoritative Shared Core semantics are available.

## Date semantics

Date and timezone-aware DateTime fields can be compared and participate in the existing null-aware conditional/coalesce type system.

Date arithmetic is intentionally rejected in this slice. Calendar-aware date + duration, working-time arithmetic, Jalali/Gregorian normalization and related functions must delegate to the existing Shared Calendar/Duration Core in a later integration slice.

## Boundary

The adapter consumes \`P6FieldDefinition\` and returns \`FormulaSchemaValue\`. It does not own P6 field metadata, persistence, calendar calculations, scheduling calculations, or API/client behavior.
