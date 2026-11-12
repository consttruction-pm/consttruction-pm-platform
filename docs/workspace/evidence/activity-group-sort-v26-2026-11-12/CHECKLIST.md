# ACT-002 — Grouping and sorting (2026-11-12)

- Contract: `cubi-activity-group-sort-v26.v1`
- Suite: `apps/web/e2e/activity-group-sort-v26.mjs`
- Tested code: `79712844d24317ee843c946a00347f10b93344da` (`79712844`)
- Fixture: local-full-stack preview, `preview-rps-01`, 14 activity rows, 7 WBS bands
- Help sources: [Sort activities](https://docs.oracle.com/cd/G48902_01/client_help/en_US/sort_activities.htm), [Group activities by field](https://docs.oracle.com/cd/G48902_01/client_help/en_US/group_activities_by_field.htm), [Grouping by hierarchy](https://docs.oracle.com/cd/G48902_01/client_help/en_US/grouping_by_hierarchy.htm), [Grouping activities by WBS path](https://docs.oracle.com/cd/G48902_01/client_help/en_US/grouping_activities_by_wbs_path.htm)

| # | Scenario | Cell | Result |
|---|---|---|---|
| 01 | The dialog offers WBS/None grouping and three sort rows; Start desc then Activity name asc yields the computed order and the Gantt rows follow the table | 1366×768 en LTR | PASS |
| 02 | Save Layout stores `metadata.groupSort` (`none`, Start desc/name asc, revision 2) and a full reload restores both the mode and the exact order | 1366×768 en LTR | PASS |
| 03 | WBS grouping renders 7 bands, activities inside every band are name-ascending, the Gantt follows, and Save + reload restores the grouping | 1366×768 en LTR | PASS |
| 04 | The Persian dialog (`گروه‌بندی و ترتیب`) and a Start-ascending table render RTL with no overflow and the computed order | 1280×720 fa RTL | PASS |
| 05 | The grouped/sorted layout fits 1920×1080 with no horizontal overflow and all 14 rows | 1920×1080 en LTR | PASS |

Machine-readable report: `activity-group-sort-v26.json` — 5/5 scenarios pass, `testedCodeSha` = `gitHead` = `79712844d24317ee843c946a00347f10b93344da`, zero exceptions, zero console errors, zero API failures. Screenshots: `01`–`05`.
