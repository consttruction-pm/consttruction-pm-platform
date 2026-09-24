# Client Localization and Presentation Boundary

Web, Desktop, and Mobile may localize presentation independently while preserving shared client semantics.

## Presentation-owned

Clients may localize:

- labels, validation hints, and stable error-code descriptions;
- Persian/English text;
- Gregorian/Jalali display formatting;
- decimal and currency display formatting;
- date/time display formatting;
- navigation and interaction layout.

## Shared/authoritative

Clients must not localize or reinterpret:

- ProjectContext identity;
- operation names;
- idempotency keys;
- optimistic-lock revisions;
- contract versions;
- stable error categories/codes;
- decimal values crossing the contract boundary;
- calendar arithmetic;
- scheduling, Progress/EVM, Resource/Cost, or reporting calculations.

Jalali/Gregorian conversion and calendar arithmetic remain in the authoritative Shared Core. A localized display must never change the underlying ISO-8601 or canonical contract value.

## Parity acceptance

Two clients are semantically equivalent when identical contract payloads produce identical operation identity, revision, numeric string values, stable error identity, and calculation inputs/outputs, even if their labels and visual presentation differ.
