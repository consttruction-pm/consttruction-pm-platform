# Jalal 3 Weighted Progress Reconciliation — 2026-10-12

## Baseline and method

- Source workbook: `جلال3_اصلاح_مبنای_پیشرفت_2026-10-10.xlsx` (Library source; sheet `جلال 3`, refreshed after GitHub reconciliation dated 2026-10-10).
- Current repository `main` HEAD when reconciled: `1fcfe54119cc22623dc3c8b33a3400bbbcf0b63d` (this documentation update). The product-code baseline remains `488e683a8a65e4316cc14b106cda0989784372bc`; changes after it on main are documentation-only.
- Formula: `sum(weight × activity_completion_fraction)` across the 23 activities. Weights total 100.00.
- Earned weighted points: **59.50 / 100**. Remaining: **40.50 / 100**.
- This is a weighted implementation schedule indicator, not release readiness, deployment acceptance, or full P6 parity certification.
- Open/unmerged PRs receive zero incremental credit. In particular #1368, #1371, #1375 and #1376 are not counted as additional progress.
- No extra credit was inferred from commit counts or code volume.

## Activity-level weighted matrix

| # | Activity | Owner | Weight | Activity completion | Earned weighted points |
|---:|---|---|---:|---:|---:|
| 1 | Shared Core and P6 semantic parity | Jalal | 10 | 65% | 6.50 |
| 2 | CPM / Scheduling Engine | Jalal | 9 | 98% | 8.82 |
| 3 | Calendar / Duration / Lag / Constraint | Jalal | 5 | 93% | 4.65 |
| 4 | Progress / Float / OOS / Remaining Logic | Jalal | 6 | 85% | 5.10 |
| 5 | Formula Dependency DAG and Formula Engine | Jalal | 3 | 76% | 2.28 |
| 6 | Core regression / verification | Jalal | 3 | 70% | 2.10 |
| 7 | Backend HTTP / Application API boundary | Hasan | 5 | 100% | 5.00 |
| 8 | API / DTO / versioned contracts | Hasan | 3 | 35% | 1.05 |
| 9 | Database / PostgreSQL / transaction verification | Hasan | 3 | 85% | 2.55 |
| 10 | P6 Import / Export / Interchange round-trip | Hasan | 3 | 85% | 2.55 |
| 11 | Web P6 Workspace / Field / Layout | Farmj22002 | 7 | 100% | 7.00 |
| 12 | Web Gantt and core P6 pages | Farmj22002 | 5 | 55% | 2.75 |
| 13 | Dashboard / UX / Responsive Web | Farmj22002 | 3 | 40% | 1.20 |
| 14 | Web AI Assistant / Smart Guide | Farmj22002 | 3 | 20% | 0.60 |
| 15 | Mobile V1 Native Foundation / Local Project Shell | Farmj22002 | 5 | 15% | 0.75 |
| 16 | Mobile V1 Planning: WBS / Activity / Relationships / Schedule | Farmj22002 | 4 | 10% | 0.40 |
| 17 | Mobile V1 Field / Control Workflows | Farmj22002 | 3 | 0% | 0.00 |
| 18 | Mobile V1 Sync / Conflict / Auth / API | Hasan | 3 | 100% | 3.00 |
| 19 | Mobile V1 Shared Core Portability / Offline Deterministic Scheduling | Jalal | 2 | 100% | 2.00 |
| 20 | Mobile V1 Localization / AI / Voice / Native Readiness | Farmj22002 | 3 | 20% | 0.60 |
| 21 | Desktop Integration with Shared Core/API | Jalal | 4 | 10% | 0.40 |
| 22 | Multilingual Help / Documentation | Jalal | 2 | 10% | 0.20 |
| 23 | System-wide Integration / Regression / Release QA | Team | 6 | 0% | 0.00 |
|  | **Total** |  | **100** |  | **59.50** |

## Owner reconciliation

| Owner | Assigned weight | Earned weighted points | Completion within assigned scope |
|---|---:|---:|---:|
| Jalal | 44 | 32.05 | 72.84% |
| Hasan | 17 | 14.15 | 83.24% |
| Farmj22002 | 33 | 13.30 | 40.30% |
| Team-wide release QA | 6 | 0.00 | 0.00% |
| **Total** | **100** | **59.50** | **59.50% of full scope** |

## Reconciliation notes and current gates

1. The workbook's 59.50% supersedes the 59.41% figure from 2026-10-08; the difference is the verified CPM activity adjustment from 97% to 98% (+0.09 percentage point), plus the earlier accepted Web workspace increment already included in the workbook.
2. Main has no product-code merges after the workbook's product-code baseline; the commits through current main after that baseline are documentation-only. Thus the 59.50% remains the supported Jalal 3 indicator until a weighted capability changes on main.
3. PR #1375 adds an authenticated route/API composition test but uses `InMemoryWorkspaceReadProvider`; it does not close the production workspace provider/runtime gate in #1359.
4. PR #1376 adds typed-array interchange validation, but explicitly does not close canonical ScheduleOptions `PriorityList` / `ResourceList` mapping.
5. PR #1371 remains draft; the PostgreSQL integration pass alone is not full scheduling-matrix acceptance.
6. PR #1368 remains open; passing source-level CI is not pixel-match or live deployment acceptance.
7. The system-wide integration/release QA activity remains at 0% in this schedule until the release gate has direct evidence. This is intentional and must not be inferred from component CI alone.

## Refresh rule

After any product-code merge, map its changed capability to exactly one or more weighted activities, check overlap/duplicate credit, update only the evidenced activity fraction, and recalculate the weighted sum. Keep open PRs at zero incremental credit until merged and validated.
