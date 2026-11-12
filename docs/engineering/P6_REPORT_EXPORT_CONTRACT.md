# Report run export contract (`p6-report-api.v1`)

A report definition stores an ordered subset of one authoritative subject. A run
materializes that selection at one project revision and is immutable. Export
renders **the stored run only**; it never re-queries a repository, recalculates a
column, or applies a later definition edit.

## Endpoint

```
GET /api/projects/{project_id}/reports/{report_id}/runs/{run_id}/export
    ?format=csv|xlsx|pdf
    &locale=en|fa
```

- Requires project-read permission in the same tenant/project scope.
- `format` defaults to `csv`; `locale` defaults to `en` and is only used by PDF.
- Success returns the documented bytes with:

| Header | Meaning |
|---|---|
| `Content-Type` | `text/csv; charset=utf-8`, XLSX media type, or `application/pdf` |
| `Content-Disposition` | `attachment` plus RFC 6266 filename |
| `X-Content-SHA256` | SHA-256 of the exact response bytes |
| `X-Report-Run` | stored run identity |

- Unknown format → `400 REPORT_EXPORT_FORMAT_UNSUPPORTED`.
- Unknown locale → `400 REPORT_EXPORT_LOCALE_UNSUPPORTED`.
- Unknown run → `404`; cross-scope or missing permission → `403`.

The catalogue (`GET .../reports`) advertises `export_formats` and
`export_locales`.

## Stored-run semantics

`ReportRun` fixes `run_id`, `report_id`, `report_revision`, `project_revision`,
`subject`, `columns`, `rows`, `generated_at` and `generated_by`. All three
formats read these fields and nothing else:

- Column order is `run.columns`.
- Header labels come from the subject catalogue (`ReportField.label`).
- Cell values are the stored snapshot values; a changed live dataset cannot
  alter an old download.

## CSV

UTF-8 with BOM, `\n` line endings, catalogue labels in the first row. Values that
start with `=`, `+`, `-`, `@`, TAB or CR are prefixed with a literal apostrophe so
spreadsheet software cannot evaluate them.

## XLSX

One typed sheet: catalogue labels, declared `data_type` cells (integer, decimal,
boolean, date), frozen header, autofilter and bounded column widths. Formula
injection is neutralized the same way as CSV; identifiers stay text.

## PDF

Deterministic presentation of the same snapshot, built with reportlab:

- A4 portrait, fixed margins and column widths derived only from the stored
  content, so the same run + locale produces byte-identical output and the same
  `X-Content-SHA256` on every call.
- Every page repeats the identity block: subject label, report id, run id,
  project id, report revision, project revision, generated-at timestamp and
  actor.
- The table header repeats after each page break; the footer shows
  `Page N of M` and the run id.
- Cells wrap; a cell that cannot fit the page body fails closed with
  `REPORT_EXPORT_PDF_CELL_TOO_LONG` instead of truncating stored data.
- An empty run renders one page with an explicit "No rows" notice.
- PDF metadata (`Title`, `Author`, `Subject`, `Creator`, `Producer`) and the
  fixed creation/modification timestamp are part of the deterministic output.

### Locales and direction

| Locale | Dates | Numbers | Direction |
|---|---|---|---|
| `en` | Gregorian `YYYY-MM-DD` | grouped with `,`; `.` decimal | left-to-right |
| `fa` | Jalali `YYYY/MM/DD` | Persian digits, `٬` grouping, `٫` decimal | right-to-left |

`fa` also sets the PDF viewer preference `Direction = R2L` and a document
language tag. Persian/Arabic cell text is contextually shaped and reordered with
the Unicode bidi algorithm in both locales, so mixed Latin/Persian content keeps
its reading order. Identifiers (activity/resource/risk IDs) keep their stored
Latin digits; only typed dates/numbers and the document timestamp are localized.

### Fonts

The PDF embeds glyph subsets of DejaVu Sans (regular and bold) limited to Latin,
Arabic, Arabic Presentation Forms and common punctuation. The Bitstream Vera
license permits redistribution and requires the modified subset to be renamed;
the embedded font names are `CubiSans`/`CubiSans-Bold`. The license text ships at
`src/construction_pm/assets/fonts/LICENSE.txt`.

### Dependencies

Declared runtime dependencies: `reportlab>=4.4,<5`, `arabic-reshaper>=3.0,<4`,
`python-bidi>=0.6,<0.7`. Tests use `pypdf` (declared in the `test` extra) to
assert page count, metadata and extracted text.

## Out of scope in this slice

- Parameterized definitions and typed parameter provenance.
- Durable scheduled runs, retry/idempotent delivery and delivery checksums.
- The Web download wiring (owned by Agent 1); this contract is the backend seam.
- Persian catalogue labels for table headers: the stored catalogue labels are
  English today and are used verbatim in all formats.
