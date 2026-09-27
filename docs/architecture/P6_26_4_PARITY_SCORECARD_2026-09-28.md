# P6 26.4 Parity Scorecard — 2026-09-28

## Interpretation

These percentages measure functional/architectural coverage, not raw CPU speed or wall-clock performance. A real performance benchmark requires identical projects, hardware, databases, client workloads and measured runs.

P6 Professional Version 26 / P6 EPPM 26.4 is treated as the 100% compatibility reference for the P6-overlap surface. The Construction PM percentage measures the current evidence-backed maturity of our implementation on that same surface.

## Current result

| Metric | Current |
|---|---:|
| P6 reference baseline | 100% |
| Construction PM overall product maturity | 78% |
| Construction PM current P6-parity coverage | 44% |
| P6-overlap gap remaining | 56% |

The 44% is a weighted engineering audit estimate, not Oracle certification.

## Weighted audit

| Area | Weight | Current coverage | Contribution |
|---|---:|---:|---:|
| Core scheduling/CPM semantics | 20% | 80% | 16.0% |
| Calendar/time arithmetic and assignment | 10% | 65% | 6.5% |
| Standard P6 field/input surface | 15% | 30% | 4.5% |
| Columns/layouts/UDF | 10% | 20% | 2.0% |
| Formula/calculated columns | 5% | 5% | 0.25% |
| Schedule calculation options | 10% | 35% | 3.5% |
| Resource/cost/leveling parity | 10% | 50% | 5.0% |
| P6 import/export interchange | 10% | 25% | 2.5% |
| Reporting/spreadsheets/profiles | 5% | 40% | 2.0% |
| Codes/baselines/financial periods | 5% | 35% | 1.75% |
| **Total** | **100%** |  | **44.0%** |

## Evidence behind the audit

Oracle's current Version 26 documentation confirms:
- the Activity Table supports configurable columns, column reordering, custom titles, width/alignment and reusable layouts;
- UDFs can be displayed in columns and grouped, sorted, filtered, reported and used by Global Change;
- UDF types include Text, Start Date, Finish Date, Cost, Indicator, Number and Integer;
- calendars include parent/global inheritance, date-specific nonwork/work overrides, detailed work hours and Hours per Time Period;
- current scheduling includes multiple float paths, Total/Free Float selection, ending activity and path count;
- leveling includes cross-project priorities, preservation of early/late dates, all-resource selection, within-float leveling and minimum-float preservation;
- the Version 26 XER Project Data Map contains dedicated mappings for Project, WBS, Activities, Schedule Options, Resources, Resource Rates, Resource Level Lists, Risks, Financial Periods, UDFs, Activity Period Actuals, Relationships, Steps, Resource Assignments and other structures.

## Why parity is below overall product maturity

The product already has substantial construction-specific capability and shared-core architecture that are not present as equivalent P6 surfaces. P6 parity therefore represents only the P6-overlap subset of the product.

## Release rule

The 44% must not be used as a release claim. Gate A remains closed until the P6 26.4 inventory reaches dispositioned 100% across all applicable fields/options/calendars/interchange mappings and the implementation has regression evidence.

## Superset policy

P6 is the compatibility floor for overlapping behavior, not the ceiling of the product.

The platform may add construction-specific capabilities such as field operations, configurable inspections/quality/safety, procurement/commercial commitments, change/claims/evidence, advanced documents/OCR, cross-domain control intelligence, offline-first workflows, bilingual/Jalali support, AI assistance and construction-specific integrations, provided these do not change the established P6 meaning where overlap exists.

## Next mandatory implementation order

1. P6 Field Registry.
2. Column/View/Layout engine.
3. Typed UDF/custom field engine.
4. Formula/Calculated Column engine.
5. Full Schedule Options contract and calculation implementation.
6. Full Calendar domain parity.
7. XER/XML/XLSX/MS Project interchange mapping and round-trip fixtures.
8. P6-specific conformance regression pack.

This scorecard is subordinate to the authoritative no-omission baseline:
docs/architecture/P6_26_4_PARITY_AND_NO_OMISSION.md
