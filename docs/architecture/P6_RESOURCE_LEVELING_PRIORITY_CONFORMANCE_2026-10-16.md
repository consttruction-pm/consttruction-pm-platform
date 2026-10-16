# P6 Resource-Leveling Priority Conformance Matrix — 2026-10-16

**Status: PARTIAL / NOT CERTIFIED.** This is a source-to-rule-to-code/test record for review, not a claim of Oracle certification. No code change is authorized by an unresolved row. The applicable candidate PR remains Draft.

## Versioned official sources

1. **P6 Professional User Guide, Version 26 — Leveling priority definitions**  
   https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_priority_definitions.htm
2. **P6 Professional User Guide, Version 26 — Level resources**  
   https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/level_resources.htm
3. **P6 Professional Integration API — Activity fields, `Activity.LevelingPriority`**  
   https://docs.oracle.com/cd/F25600_01/English/Integration/p6_pro_api_reference/FieldSummary.html
4. **P6 EPPM REST API, Release 26 — Activity GET/PUT, `LevelingPriority`**  
   https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html  
   https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-put.html
5. **P6 EPPM User Guide — configuring resource-leveling priorities**  
   https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_user/7974_1.htm
6. **P6 EPPM ScheduleOptions REST GET/PUT, Release 26**  
   https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-scheduleoptions-get.html  
   https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-scheduleoptions-put.html

## Source-to-rule-to-code/test matrix

| ID | Source-derived rule | Current implementation / regression evidence | Disposition |
|---|---|---|---|
| RL-P6-01 | Configured priority rows are ordered; row order establishes precedence. Priorities are relevant when multiple activities compete for a resource at the same time. | Shared Core tuple keeps configured row order; `tests/scheduling/test_leveling_boundary.py::test_scheduler_leveling_boundary_maps_ordered_priority_list`. | **PARTIAL** — broad row-order test exists; full mixed-field, tie and both-pass precedence matrix remains open. |
| RL-P6-02 | With no configured priority rows, Activity ID is the fallback; ID values sort numeric first, alphabetic next, blank last. | `src/construction_pm/scheduling/resource_leveling.py::_activity_id_value_key`, `_priority_sort_key`, and backward comparator; resource-leveling tests cover numeric/alphabetic ordering and default ID fallback. | **PARTIAL** — exact-head tests pass; exhaustive blank IDs, numeric-equivalent spellings (for example `02` / `2`) and all backward ties still require review. |
| RL-P6-03 | The Professional v26 priority-table criterion is labelled **Activity Priority**. The Professional Integration API describes `Activity.LevelingPriority` as the resource-leveling priority enum: `Top`, `High`, `Normal`, `Low`, `Lowest`. EPPM REST Release 26 documents the same `LevelingPriority` field and values. | Canonical field registry entry: `activity.leveling_priority` → Activity `LevelingPriority`, string. Domain enum: `ActivityLevelingPriority`. Tests: `tests/scheduling/test_resource_leveling.py::test_activity_leveling_priority_accepts_only_documented_p6_values` and `test_activity_leveling_priority_orders_forward_candidates` / `...backward_candidates`. | **PARTIAL / REVIEW REQUIRED** — the mapping between Professional UI label `Activity Priority`, EPPM UI label `Activity Leveling Priority`, interchange field and canonical field must be signed off by an independent reviewer. |
| RL-P6-04 | Numeric **Project Leveling Priority** is a distinct concept from the Activity `LevelingPriority` enum; it must not be conflated with an activity's Top/High/Normal/Low/Lowest value. | Shared Core carries `project_priority` separately and validates its 1–100 range; forward/backward tests exercise higher/lower project rank behavior. | **PARTIAL** — version/profile source mapping and end-to-end persistence/import evidence still need independent confirmation. |
| RL-P6-05 | Sort direction applies to the selected priority field. For hierarchical fields, Professional documentation says Hierarchy appears only for eligible hierarchical criteria; it is not a universal third sort direction for every field. | `PrioritySortOrder` and `leveling_boundary._map_priority_list` currently support Ascending/Descending only. | **BLOCKED** for Hierarchy: Release 26 ScheduleOptions does not identify a canonical per-row Hierarchy wire representation/eligibility contract in the reviewed schema. Do not invent one; record an explicit unsupported boundary if vendor evidence cannot establish it. |
| RL-P6-06 | Source schemas do not by themselves certify the internal-to-wire mapping. Release 26 ScheduleOptions REST declares `PriorityList` and `ResourceList` as scalar strings; the Integration API presents array accessors. | Internal domain/snapshot use typed tuples/arrays; related issue #1379 tracks this interface-boundary mismatch. | **BLOCKED** — the REST inner encoding/escaping and lossless round-trip contract are not specified by the reviewed official schema. Do not guess delimiter or JSON encoding. |
| RL-P6-07 | A documented blank priority value and unavailable source data are not automatically the same state. Missing required authoritative data must not be silently fabricated. | Several priority fields fail closed with `MISSING_LEVELING_PRIORITY_VALUE`; the Activity ID key implements numeric/alphabetic/blank categories. | **PARTIAL** — define/test each applicable field's blank-vs-missing state per product profile before relaxing fail-closed validation. |

## Outstanding source-to-code review

### Potential Activity Priority alias mismatch — UNVERIFIED until independent sign-off

The current candidate boundary accepts both `activity_priority` and `activity_leveling_priority`, which resolve to different Shared Core values (numeric versus the LevelingPriority enum). The canonical P6 field registry maps `activity.leveling_priority` to `Activity.LevelingPriority`; it does not establish a separate numeric P6 Activity Priority field.

The official sources above support the UI/API label distinction and the five-value enum, but a reviewer must confirm the exact mapping for each supported product profile before implementation changes. Until approved:
- Do not silently alias a numeric internal field to the P6 UI criterion.
- Do not invent a separate P6 numeric field.
- Keep unresolved mapping `UNVERIFIED/BLOCKED`.
- Add a source-backed mapping test demonstrating the selected criterion flows through import/persistence/snapshot materialization into the same authoritative comparator.
- If numeric `activity_priority` is a CUBI-only extension, it needs an explicitly non-conflicting identifier and must not be represented as the P6 Professional **Activity Priority** field.

## Verification snapshot

- Candidate: PR #1457 (Draft, unmerged).
- Latest exact tested head before this matrix addition: `4491f94df3ff009691950f3b434d8466fb99122d`.
- ConstructionPM CI run `38842597822`: Python 3.11, 3.12, 3.13 each 2,603 passed / 90 skipped / 1 warning.
- Client Typecheck run `38842597848`: success.
- PostgreSQL Integration run `38842597826`: success.
- These runs verify that exact prior head only. CI must rerun for any new head.
- No independent semantic approval is recorded yet. The matrix remains **PARTIAL / NOT CERTIFIED** until the independent review and each applicable round-trip/priority edge-case gate is closed.
