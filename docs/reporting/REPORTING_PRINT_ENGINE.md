# Reporting & Print Engine

Stage 32.7 — specification complete; typed authoritative dataset foundation implemented; full print/render engine remains pending.

## Architecture
Data -> Query -> Template -> Render.

The Print Engine is independent from UI and supports professional project, schedule, progress, cost, EVM, resource, quantity, risk, document, contract, delay, quality, management and audit reports.

## Output requirements
PDF and Excel-ready typed datasets; RTL/LTR; Persian/English; Jalali/Gregorian; A4 through A0; headers/footers; print preview; report batches; versioning; immutable issued snapshots; auditability.

Excel exports must keep numeric, date and duration fields typed and separate so formulas remain calculation-ready.

## Typed dataset foundation
The reporting boundary now exposes an authoritative, read-only typed dataset contract. It validates explicit tenant/project/source-revision context, unique column definitions, exact row/column shape, Decimal numeric values, ISO-compatible date/datetime values, explicit duration units, and Boolean fields. It rejects callable values and non-finite Decimal/duration values.

The reporting boundary performs no domain calculations. Scheduling/P6, Progress/EVM, Resource/Cost and financial semantics remain owned by their authoritative modules.
