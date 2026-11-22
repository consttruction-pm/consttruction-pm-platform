# Three reference projects — source validation and import mapping (2026-11-22)

## What changed

Step 1 of the import mission: read and validate the master workbook **before**
any database write, and document where every one of its 94 sheets goes.

| Layer | File | Change |
| --- | --- | --- |
| Validator | `src/construction_pm/importing/reference_projects.py` | contract `cubi-reference-import-source.v1`: workbook reader, referential validation, cycle detection, per-project counts |
| Package | `src/construction_pm/importing/__init__.py` | public exports |
| CLI | `scripts/validate_reference_projects.py` | `SOURCE.xlsx [--out report.json] [--summary]`, exit 0/1 |
| Tests | `tests/test_reference_projects_import.py` | six cases on a synthetic openpyxl workbook |
| Mapping | `docs/engineering/CUBI_REFERENCE_PROJECTS_IMPORT_MAPPING.md` | field mapping, dispositions, gaps |
| Inventory | `docs/engineering/CUBI_REFERENCE_PROJECTS_SHEET_INVENTORY.csv` | 94 rows: counts, columns, PK, FK, disposition, target |
| Spec | `docs/ai-workbench/PROJECT_IMPORT_STAGING_SPEC.md` | status BLOCKED → PARTIAL with the source stage named |
| Status | `docs/ai-workbench/IMPLEMENTATION_STATUS.md` | import row points at the new contract |

## Source fingerprint

- File: `CUBI_Three_Reference_Projects_Master_Data_v1-1.xlsx`
- SHA-256: `0848454d2b8b77806986eb53cf36e95521d7e789ad8c4f0b2af78acb4e82fa26`
- 94 sheets, 3 projects, status date 2026-11-22, DEMO/SYNTHETIC

## Verification

```
python scripts/validate_reference_projects.py <source>.xlsx --summary
→ ok: true, error_count: 0, warning_count: 0
python -m pytest tests/test_reference_projects_import.py -q
→ 6 passed
```

Counts confirmed per project:

| Sheet | Total | Per project |
| --- | ---: | --- |
| EPS | 25 | 8 / 8 / 9 |
| OBS | 24 | 8 / 8 / 8 |
| WBS | 375 | 120 / 120 / 135 |
| Activities | 540 | 180 each |
| Activity Relationships | 714 | 238 each |
| Calendars | 9 | 3 each |
| Resource Master | 90 | 30 each |
| Equipment Register | 30 | 10 each |
| Resource Assignments | 720 | 240 each (180 Labor + 60 Equipment) |
| Baselines | 3 | 1 each |
| Baseline Activities | 540 | 180 each |
| Risk Register | 45 | 15 each |
| Document Register | 45 | 15 each |

## Findings recorded

- **Equipment is a resource.** Equipment IDs in assignments resolve only through
  `Equipment Register`. Merging that register into the resource index removes
  180 false `RESOURCE_ID_UNKNOWN` errors; the test locks this behaviour in both
  directions.
- **The `Data Validation` sheet is internally inconsistent.** It claims 325
  relationships per project and density ≥ 1.5, but the data has 238 per project
  (1.32 per activity) and all 714 IDs resolve. It is treated as metadata, never
  as truth.
- **No CPM, float or EVM value is imported as a fact.** Those sheets are
  classified *Derived* and must be reproduced by the canonical services.
- **18 sheets have no canonical home yet** (quality/HSE, contracts, procurement,
  vendors, issues, change requests, communication, material, import manifest) and
  are marked *Proposed Extension* rather than forced into an unrelated entity.

## Not claimed

- No project is created and no database is written in this step.
- No schedule run, histogram or EVM result is verified here.
- Supabase/PostgreSQL behaviour is not asserted.

## Artifact

- `source-validation-report.json` — the full report the CLI produced for this
  workbook (source digest, 94 sheet counts, zero issues).
