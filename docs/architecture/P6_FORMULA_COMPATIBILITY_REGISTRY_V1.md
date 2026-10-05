# Formula Compatibility Registry v1

This registry is a versioned compatibility metadata layer over the Shared Formula Core. It does not translate or evaluate formulas.

## Current scope

The canonical engine currently implements IF, SUM, MIN, MAX, ABS, ROUND, COALESCE, NOT, AND and OR. The registry records those canonical IDs and selected verified source-dialect names.

Microsoft Project documents IIf, Sum, Min, Max, Abs and Round as custom-field formula functions. Excel provides the corresponding common function family. Oracle P6 EPPM documents formula UDF statements using an IF/ELSE form and field/operator construction.

Mappings marked translation_required are deliberately not treated as direct evaluator aliases. Unknown names return unsupported.

## Boundary

Compatibility metadata only. No parser, evaluator, scheduling, calendar, EVM, resource/cost, API, persistence or client calculation semantics are changed.

## Next gates

Additional functions, localized names, separators, date/time semantics, coercion rules and import/export translations require independent source verification and focused tests before promotion to supported.
